# chatbot.py

from threading import Lock
from typing import Any, Dict, Optional

from intent.intent_classifier import IntentClassifier
from rag.retriever import Retriever
from generator.gemini_generator import generate_medical_answer
from app.response_layer import (
    need_more_info, 
    build_clarification_question,
    is_follow_up,
    is_topic_shift,
    parse_switch_confirm,
    get_intent_label,
    get_intent_category,
    get_rag_gate_thresholds
)
from app.symptom_extractor import extract_symptoms
from app.risk_estimator import estimate_risk

# ============================
# KHỞI TẠO CÁC MODEL (LAZY LOADING)
# ============================

intent_model_path = r"D:\CHAT BOT TTCS\model\intent_model"
rag_path = r"D:\CHAT BOT TTCS\rag"

# Không load models ngay khi import - sẽ load khi cần
intent_classifier: Optional[IntentClassifier] = None
retriever: Optional[Retriever] = None
_models_initialized = False
_models_lock = Lock()

conversation_states: Dict[str, Dict[str, Any]] = {}
conversation_lock = Lock()


def _ensure_models_loaded():
    """Đảm bảo models đã được load"""
    global intent_classifier, retriever, _models_initialized
    
    if _models_initialized:
        return
    
    with _models_lock:
        if _models_initialized:  # Double check
            return
        
        print("🔄 Đang khởi tạo models trong chatbot module...")
        
        # Load Intent Classifier
        if intent_classifier is None:
            intent_classifier = IntentClassifier(intent_model_path)
        
        # Load RAG Retriever
        if retriever is None:
            retriever = Retriever(rag_path)
        
        # Gemini API không cần load model, chỉ cần kiểm tra API key
        from generator.gemini_generator import _get_model
        try:
            _get_model()  # Test API connection
        except Exception as e:
            print(f"⚠️ Cảnh báo: Không thể kết nối Gemini API: {e}")
            print("   Hệ thống vẫn sẽ hoạt động nhưng có thể gặp lỗi khi generate answer")
        
        _models_initialized = True
        print("✅ Models trong chatbot module đã sẵn sàng!")

# Chỉ in message này khi chạy trực tiếp (không phải khi import)
if __name__ == "__main__":
    # Khi chạy trực tiếp, load models ngay
    _ensure_models_loaded()
    print("🤖 Chatbot y tế sẵn sàng. Nhập 'quit' để thoát.\n")


# ============================
# QUẢN LÝ TRẠNG THÁI HỘI THOẠI
# ============================


def _get_or_create_state(session_id: str) -> Dict[str, Any]:
    with conversation_lock:
        if session_id not in conversation_states:
            conversation_states[session_id] = {
                "last_intent": None,
                "last_symptoms": None,
                "conversation_history": [],  # Lưu lịch sử hội thoại (tối đa 6 cặp Q&A gần nhất)
                "intent_lock": None,  # { "intent": str, "turns": int } | None
                "pending_intent": None,  # Intent mới đang chờ xác nhận
                "pending_from_intent": None,  # Intent cũ
                "pending_type": None  # "intent_switch_confirm" | None
            }
        return conversation_states[session_id]


def reset_conversation(session_id: str) -> None:
    with conversation_lock:
        conversation_states.pop(session_id, None)


# ============================
# HÀM CHAT CHÍNH
# ============================


def run_chat_pipeline(user_input: str, session_id: str = "default", user_id: Optional[str] = None) -> Dict[str, Any]:
    # Đảm bảo models đã được load
    _ensure_models_loaded()
    
    cleaned_input = (user_input or "").strip()

    if not cleaned_input:
        return {
            "session_id": session_id,
            "reply": "Bạn hãy nhập câu hỏi hoặc mô tả triệu chứng cụ thể hơn nhé.",
            "intent": None,
            "intent_confidence": 0.0,
            "symptoms": {},
            "risk": None,
            "clarification_needed": False,
            "clarification_question": None,
            "sources": [],
            "stage": "validation"
        }

    state = _get_or_create_state(session_id)
    
    # Lưu user input vào conversation history ngay (trước khi generate reply)
    history_list = state.get("conversation_history", [])
    history_list.append((cleaned_input, None))
    state["conversation_history"] = history_list
    
    # Khởi tạo response template
    response: Dict[str, Any] = {
        "session_id": session_id,
        "intent": None,
        "intent_confidence": 0.0,
        "symptoms": {},
        "risk": None,
        "clarification_needed": False,
        "clarification_question": None,
        "sources": [],
        "stage": "generation"
    }
    
    # ============================
    # ƯU TIÊN XỬ LÝ (Thứ tự bắt buộc)
    # ============================
    
    last_intent = state.get("last_intent")
    pending_type = state.get("pending_type")
    
    # ============================
    # BƯỚC 1: PENDING FLOW (Nếu đang chờ xác nhận đổi chủ đề)
    # ============================
    pending_intent_before = state.get("pending_intent")
    rag_mode = None  # Khởi tạo để dùng trong log (sẽ được set sau)
    intent_decision_reason = "unknown"  # Khởi tạo (sẽ được set ở các BƯỚC)
    
    
    if pending_type == "intent_switch_confirm":
        pending_intent = state.get("pending_intent")
        pending_from_intent = state.get("pending_from_intent")
        
        print(f"\n{'='*60}")
        print(f"🔄 PENDING FLOW - Đang xử lý xác nhận đổi chủ đề")
        print(f"   pending_intent (trước): {pending_intent}")
        print(f"   pending_from_intent: {pending_from_intent}")
        print(f"{'='*60}\n")
        
        # Parse câu trả lời xác nhận
        confirm_result = parse_switch_confirm(cleaned_input)
        
        if confirm_result is True:
            # Xác nhận chuyển sang chủ đề mới
            intent = pending_intent
            conf1 = 1.0  # 🔧 Reset conf1 vì user xác nhận rõ
            # Xóa pending fields
            state.pop("pending_intent", None)
            state.pop("pending_from_intent", None)
            state.pop("pending_type", None)
            print(f"✅ User xác nhận chuyển từ {pending_from_intent} sang {intent}")
            # Tiếp tục xử lý với intent mới
            
        elif confirm_result is False:
            # Giữ chủ đề cũ
            intent = pending_from_intent
            conf1 = 1.0  # 🔧 Reset conf1 vì user xác nhận rõ
            # Xóa pending fields
            state.pop("pending_intent", None)
            state.pop("pending_from_intent", None)
            state.pop("pending_type", None)
            print(f"✅ User giữ chủ đề cũ: {intent}")
            # Tiếp tục xử lý với intent cũ
            
        else:
            # Không rõ → hỏi lại, không đổi intent, không RAG
            from_intent_label = get_intent_label(pending_from_intent) if pending_from_intent else "chủ đề trước"
            to_intent_label = get_intent_label(pending_intent) if pending_intent else "chủ đề mới"
            response["reply"] = (
                f"💬 Bạn muốn hỏi tiếp về {from_intent_label} hay chuyển sang {to_intent_label}? "
                "Vui lòng trả lời rõ ràng (ví dụ: 'chuyển' hoặc 'giữ')."
            )
            response["stage"] = "pending_confirm"
            
            # Log trước khi return
            print(f"\n{'='*60}")
            print(f"📊 LOG SUMMARY")
            print(f"   intent_new: {pending_intent} (pending)")
            print(f"   conf_new: N/A (pending)")
            print(f"   last_intent: {pending_from_intent}")
            print(f"   final_intent: {pending_from_intent} (giữ cũ)")
            print(f"   is_follow_up: False")
            print(f"   is_topic_shift: False")
            print(f"   pending_intent (trước): {pending_intent}")
            print(f"   pending_intent (sau): {pending_intent} (giữ nguyên)")
            print(f"   rag_intent: N/A (chưa xử lý)")
            print(f"   rag_mode: None (chưa xử lý)")
            print(f"   use_rag: False")
            print(f"   stage: {response['stage']}")
            print(f"{'='*60}\n")
            
            # Cập nhật conversation history với reply
            if history_list and history_list[-1][1] is None:
                history_list[-1] = (history_list[-1][0], response["reply"])
            return response
    
    # ============================
    # BƯỚC 2: INTENT CLASSIFICATION - TOP-2
    # ============================
    top2 = intent_classifier.predict_topk(cleaned_input, k=2)
    intent1, conf1 = top2[0]
    intent2, conf2 = top2[1] if len(top2) > 1 else ("other", 0.0)
    
    # Giữ tương thích với code còn lại
    intent_new, intent_conf = intent1, conf1
    
    print(f"\n{'='*60}")
    print(f"🧠 INTENT CLASSIFICATION (TOP-2)")
    print(f"   intent1: {intent1} (conf1: {conf1:.4f})")
    print(f"   intent2: {intent2} (conf2: {conf2:.4f})")
    print(f"   last_intent: {last_intent}")
    print(f"{'='*60}\n")
    
    # ============================
    # BƯỚC 3: NHẬN DIỆN FOLLOW-UP & TOPIC SHIFT
    # ============================
    is_follow_up_flag = is_follow_up(cleaned_input)
    is_topic_shift_flag = is_topic_shift(cleaned_input)
    
    print(f"📌 CONTEXT DETECTION")
    print(f"   is_follow_up: {is_follow_up_flag}")
    print(f"   is_topic_shift: {is_topic_shift_flag}\n")
    
    # ============================
    # BƯỚC 4: TOPIC SHIFT RÕ (Cho phép đổi chủ đề)
    # ============================
    if is_topic_shift_flag and not is_follow_up_flag:
        # Đổi chủ đề rõ → cho phép đổi
        intent = intent_new
        print(f"✅ TOPIC SHIFT: Đổi sang {intent}")
        # Xóa intent lock nếu có (vì đổi chủ đề rõ)
        state.pop("intent_lock", None)
        final_intent = intent
        intent_decision_reason = "topic_shift"
        
    # ============================
    # BƯỚC 5: FOLLOW-UP (Giữ chủ đề cũ)
    # ============================
    elif is_follow_up_flag and last_intent and not is_topic_shift_flag:
        # Follow-up → ưu tiên tuyệt đối giữ intent cũ
        intent = last_intent
        print(f"✅ FOLLOW-UP: Giữ intent cũ {intent}")
        final_intent = intent
        intent_decision_reason = "follow_up"
        
    # ============================
    # BƯỚC 6: TOP-2 SWITCH OVERRIDE (Đổi chủ đề CHẮC hoặc PENDING)
    # ============================
    elif last_intent and intent1 != last_intent and not is_follow_up_flag and not is_topic_shift_flag:
        # 6.1) Đổi NGAY khi rất chắc
        if conf1 >= 0.98 and conf2 <= 0.02:
            intent = intent1
            state.pop("intent_lock", None)  # Xóa lock vì TOP-2 override
            print(f"✅ TOP-2 OVERRIDE (NGAY): conf1={conf1:.4f} >= 0.98, conf2={conf2:.4f} <= 0.02 → Đổi sang {intent1}")
            final_intent = intent
            intent_decision_reason = "top2_override_sure"
        
        # 6.2) Mơ hồ → TẠO PENDING hỏi xác nhận
        elif 0.85 <= conf1 < 0.98:
            state["pending_intent"] = intent1
            state["pending_from_intent"] = last_intent
            state["pending_type"] = "intent_switch_confirm"
            
            from_label = get_intent_label(last_intent)
            to_label = get_intent_label(intent1)
            
            response["reply"] = (
                f"💬 Bạn đang muốn hỏi tiếp về {from_label} hay chuyển sang {to_label}? "
                "Vui lòng trả lời rõ ràng."
            )
            response["stage"] = "intent_switch_confirm"
            response["intent"] = last_intent  # Giữ intent cũ trong response
            response["intent_confidence"] = float(conf1)
            
            print(f"❓ TOP-2 OVERRIDE (PENDING): 0.85 <= conf1={conf1:.4f} < 0.98 → Hỏi xác nhận")
            
            # Log trước khi return
            pending_intent_after = state.get("pending_intent")
            print(f"\n{'='*60}")
            print(f"📊 LOG SUMMARY - PENDING CREATED")
            print(f"   intent1: {intent1} (conf1: {conf1:.4f})")
            print(f"   intent2: {intent2} (conf2: {conf2:.4f})")
            print(f"   last_intent: {last_intent}")
            print(f"   final_intent: {last_intent} (giữ cũ, chờ xác nhận)")
            print(f"   decision: top2_override_pending")
            print(f"   is_follow_up: {is_follow_up_flag}")
            print(f"   is_topic_shift: {is_topic_shift_flag}")
            print(f"   pending_intent (trước): {pending_intent_before}")
            print(f"   pending_intent (sau): {pending_intent_after}")
            print(f"   rag_intent: N/A")
            print(f"   rag_mode: None")
            print(f"   use_rag: False")
            print(f"   stage: {response['stage']}")
            print(f"{'='*60}\n")
            
            # Cập nhật conversation history với reply
            if history_list and history_list[-1][1] is None:
                history_list[-1] = (history_list[-1][0], response["reply"])
            return response
        
        # 6.3) Khác → kiểm tra conf1 để giữ hay đổi
        else:
            # Nếu conf1 quá thấp (<0.85) → không rủi ro đổi, giữ last_intent hoặc other
            if conf1 < 0.85:
                intent = last_intent if last_intent else "other"
                print(f"⚠️ TOP-2 DEFAULT (conf1<0.85): conf1={conf1:.4f} quá thấp → Giữ {intent}")
                intent_decision_reason = "top2_low_conf"
            else:
                # conf1 >= 0.85 → dùng intent1
                intent = intent_new
                print(f"ℹ️ TOP-2 DEFAULT: conf1={conf1:.4f} ∈ [0.85, 0.98) → Dùng intent1 {intent1}")
                intent_decision_reason = "top2_default"
            final_intent = intent
    
    # ============================
    # BƯỚC 7: INTENT LOCK (Stabilization - không chặn TOP-2 override)
    # ============================
    elif state.get("intent_lock") and not is_follow_up_flag and not is_topic_shift_flag:
        intent_lock = state["intent_lock"]
        locked_intent = intent_lock.get("intent")
        turns_left = intent_lock.get("turns", 0)
        
        if turns_left > 0:
            # Dùng intent lock
            intent = locked_intent
            intent_lock["turns"] = turns_left - 1
            print(f"🔒 INTENT LOCK: Dùng {intent} (còn {turns_left - 1} lượt)")
            final_intent = intent
            intent_decision_reason = "intent_lock"
            if turns_left - 1 <= 0:
                state.pop("intent_lock", None)
        else:
            # Hết lượt → dùng default
            intent = intent_new
            state.pop("intent_lock", None)
            final_intent = intent
            intent_decision_reason = "default_after_lock"
            
    # ============================
    # BƯỚC 8: DEFAULT
    # ============================
    else:
        intent = intent_new
        final_intent = intent
        intent_decision_reason = "default"
        print(f"ℹ️ DEFAULT: Dùng intent1 {intent1}")
    
    # ============================
    # BƯỚC 9: SET INTENT LOCK (Chỉ nếu intent ổn định & conf cao & symptom category)
    # ============================
    # Chỉ set lock khi:
    # - final_intent == last_intent (nói tiếp cùng chủ đề)
    # - conf1 >= 0.98 (rất chắc)
    # - intent là symptom category (tránh lock cho other, tư vấn)
    intent_category = get_intent_category(final_intent)
    if (final_intent == last_intent and conf1 >= 0.98 and 
        final_intent not in ["other", "unknown"] and 
        intent_category == "symptom"):
        state["intent_lock"] = {"intent": final_intent, "turns": 2}
        print(f"🔒 SET LOCK: final_intent={final_intent} (symptom), conf1={conf1:.4f} >= 0.98\n")
    else:
        state.pop("intent_lock", None)
    
    # ============================
    # BƯỚC 10: SYMPTOM EXTRACTION & RISK
    # ============================
    symptoms = extract_symptoms(cleaned_input)
    risk = estimate_risk(symptoms)
    
    # Lưu vào memory
    state["last_intent"] = intent
    state["last_symptoms"] = symptoms
    state["last_user_input"] = cleaned_input
    
    # Cập nhật response
    response["intent"] = intent
    response["intent_confidence"] = float(intent_conf)
    response["symptoms"] = symptoms
    response["risk"] = risk

    # 5) RISK LAYER — phát hiện nguy hiểm
    if risk == "high":
        danger_signs = symptoms.get("danger_signs") or []
        danger_text = ", ".join(danger_signs) if danger_signs else "dấu hiệu nguy hiểm"
        response["reply"] = (
            "⚠️ Mình phát hiện có dấu hiệu nguy hiểm như: "
            + danger_text
            + ". Bạn nên đi khám bác sĩ càng sớm càng tốt để đảm bảo an toàn."
        )
        response["stage"] = "safety"
        return response

    # 6) CLARIFICATION LAYER — chỉ hỏi khi thực sự không rõ triệu chứng
    # KHÔNG hỏi mặc định, chỉ hỏi khi câu rất mơ hồ
    if need_more_info(cleaned_input, intent):
        question = build_clarification_question(intent)
        response["reply"] = (
            "💬 Để hiểu rõ hơn và trả lời chính xác, bạn cho mình biết thêm nhé:\n"
            f"{question}"
        )
        response["clarification_needed"] = True
        response["clarification_question"] = question
        response["stage"] = "clarification"
        # Lưu câu hỏi clarification vào state
        state["last_clarification_question"] = question
        state["last_user_input_before_clarification"] = cleaned_input
        return response

    # ============================
    # BƯỚC 11: RAG GUARD (Bắt buộc - Tránh RAG sai chủ đề)
    # ============================
    # Follow-up tuyệt đối không được search_by_intent(intent_new)
    if is_follow_up_flag and last_intent:
        rag_intent = last_intent  # Dùng intent cũ
        print(f"🛡️ RAG Guard: Follow-up → dùng intent cũ cho RAG: {rag_intent}")
    else:
        rag_intent = intent  # Dùng intent hiện tại
    
    print(f"\n📚 RAG GUARD")
    print(f"   rag_intent: {rag_intent} (dùng cho RAG search)")
    print(f"   (final_intent: {final_intent}, last_intent: {last_intent})\n")
    
    # ============================
    # BƯỚC 12: RAG RETRIEVAL với Gate Logic theo loại Intent
    # ============================
    use_rag = False
    context = ""
    docs = []
    rag_mode = None  # "strong", "soft", hoặc None
    
    # Phân loại intent để xác định ngưỡng
    intent_category = get_intent_category(rag_intent)
    strong_threshold, soft_threshold = get_rag_gate_thresholds(intent_category)
    
    print(f"\n📊 RAG GATE LOGIC")
    print(f"   rag_intent: {rag_intent}")
    print(f"   intent_category: {intent_category}")
    print(f"   thresholds: STRONG >= {strong_threshold:.2f}, SOFT >= {soft_threshold:.2f}")
    
    # Kiểm tra intent có dùng RAG không
    if intent_category == "no_rag":
        # Intent không dùng RAG → luôn Gemini
        print(f"❌ Intent '{rag_intent}' không dùng RAG → Gemini fallback")
        response["sources"] = []
        context = ""
        use_rag = False
    elif intent_conf >= 0.97 and rag_intent not in ["other", "unknown"]:
        # HIGH: Intent confidence cao → RAG theo intent
        print(f"✅ High gate: Intent confidence {intent_conf:.3f} >= 0.97, search RAG theo intent: {rag_intent}")
        try:
            # Lấy tối đa 5 documents (sẽ chọn số lượng sau dựa trên confidence)
            docs = retriever.search_by_intent(rag_intent, cleaned_input, k=5)
            response["sources"] = docs
            
            if docs:
                rag_confidence = docs[0].get("confidence", 0.0)
                rag_cosine = docs[0].get("cosine", -1.0)
                print(f"📚 RAG Confidence (top1): {rag_confidence:.3f} | Cosine: {rag_cosine:.3f}")
                
                # Áp dụng gate logic theo loại intent
                if rag_confidence >= strong_threshold:
                    # STRONG RAG: 3-5 đoạn
                    num_docs = min(5, len(docs))
                    context = "\n".join([d.get("text", "") for d in docs[:num_docs]])
                    use_rag = True
                    rag_mode = "strong"
                    print(f"✅ STRONG RAG: {rag_confidence:.3f} >= {strong_threshold:.2f} → dùng {num_docs} đoạn")
                elif rag_confidence >= soft_threshold:
                    # SOFT RAG: 1-2 đoạn, chỉ tham khảo
                    num_docs = min(2, len(docs))
                    context = "\n".join([d.get("text", "") for d in docs[:num_docs]])
                    use_rag = True
                    rag_mode = "soft"
                    print(f"🟡 SOFT RAG: {rag_confidence:.3f} >= {soft_threshold:.2f} → dùng {num_docs} đoạn (chỉ tham khảo)")
                else:
                    # NO RAG: Confidence quá thấp
                    print(f"❌ NO RAG: {rag_confidence:.3f} < {soft_threshold:.2f} → Gemini fallback")
                    use_rag = False
                    context = ""
                    rag_mode = None
            else:
                print("⚠️ RAG không trả về kết quả → fallback Gemini")
                use_rag = False
                context = ""
                
        except Exception as e:
            print(f"⚠️ Lỗi khi search RAG theo intent: {e}, fallback về search thông thường")
            try:
                docs = retriever.search(cleaned_input, k=5)
                response["sources"] = docs
                if docs:
                    rag_confidence = docs[0].get("confidence", 0.0)
                    if rag_confidence >= strong_threshold:
                        context = "\n".join([d.get("text", "") for d in docs[:5]])
                        use_rag = True
                        rag_mode = "strong"
                    elif rag_confidence >= soft_threshold:
                        context = "\n".join([d.get("text", "") for d in docs[:2]])
                        use_rag = True
                        rag_mode = "soft"
                    else:
                        use_rag = False
                        context = ""
                else:
                    use_rag = False
                    context = ""
            except:
                use_rag = False
                context = ""
                
    elif 0.85 <= intent_conf < 0.97 and rag_intent not in ["other", "unknown"]:
        # MID: Có thể RAG global nhẹ (nếu intent không đổi)
        print(f"⚠️ Mid gate: Intent confidence {intent_conf:.3f} trong khoảng [0.85, 0.97)")
        if intent_new == last_intent and intent_category != "no_rag":
            # Intent không đổi → có thể RAG global
            try:
                docs = retriever.search(cleaned_input, k=3)
                response["sources"] = docs
                if docs:
                    rag_confidence = docs[0].get("confidence", 0.0)
                    if rag_confidence >= soft_threshold:
                        # Chỉ dùng SOFT RAG khi mid gate
                        num_docs = min(2, len(docs))
                        context = "\n".join([d.get("text", "") for d in docs[:num_docs]])
                        use_rag = True
                        rag_mode = "soft"
                        print(f"🟡 Mid gate: SOFT RAG global với confidence {rag_confidence:.3f} ({num_docs} đoạn)")
                    else:
                        use_rag = False
                        context = ""
                else:
                    use_rag = False
                    context = ""
            except:
                use_rag = False
                context = ""
        else:
            # Intent đổi hoặc no_rag → không RAG
            print("⚠️ Mid gate: Intent đổi hoặc no_rag → không RAG, để Gemini/clarify xử lý")
            use_rag = False
            context = ""
            
    else:
        # LOW: Gemini fallback
        print(f"⚠️ Low gate: Intent '{rag_intent}' với confidence {intent_conf:.3f} < 0.85 hoặc other/unknown → Gemini fallback")
        response["sources"] = []
        context = ""
        use_rag = False
    
    print(f"   rag_mode: {rag_mode}")
    print(f"   use_rag: {use_rag}\n")

    # 8) LẤY HEALTH PROFILE (nếu có user_id)
    health_profile_context = ""
    if user_id:
        try:
            from firestore_service import get_health_profile
            profile = get_health_profile(user_id)
            if profile:
                # Tính BMI
                chieu_cao_m = profile.get('chieuCao', 0) / 100
                can_nang = profile.get('canNang', 0)
                bmi = can_nang / (chieu_cao_m ** 2) if chieu_cao_m > 0 else 0
                
                # Xác định category BMI
                if bmi < 18.5:
                    bmi_category = "hơi gầy"
                elif bmi < 25:
                    bmi_category = "cân đối"
                elif bmi < 30:
                    bmi_category = "hơi thừa cân"
                else:
                    bmi_category = "thừa cân nhiều"
                
                # Chuyển đổi mức vận động
                muc_van_dong_labels = {
                    'it': 'Ít',
                    'vua': 'Vừa',
                    'nhieu': 'Nhiều'
                }
                muc_van_dong_label = muc_van_dong_labels.get(profile.get('mucVanDong', 'it'), 'Ít')
                
                # Chuyển đổi giới tính
                gioi_tinh_labels = {
                    'nam': 'Nam',
                    'nu': 'Nữ',
                    'khac': 'Khác'
                }
                gioi_tinh_label = gioi_tinh_labels.get(profile.get('gioiTinh', 'khac'), 'Khác')
                
                # Tạo health profile context
                health_profile_context = f"""[PROFILE]
Tuổi: {profile.get('tuoi', 'N/A')}
Giới tính: {gioi_tinh_label}
Chiều cao: {profile.get('chieuCao', 'N/A')} cm
Cân nặng: {profile.get('canNang', 'N/A')} kg
Mức vận động: {muc_van_dong_label}
BMI: {bmi:.1f} ({bmi_category})
[/PROFILE]

Dựa vào hồ sơ trên, hãy đưa ra gợi ý tập luyện nhẹ, an toàn, dễ thực hiện phù hợp với:
- BMI: {bmi_category} ({bmi:.1f})
- Giới tính: {gioi_tinh_label}
- Mức vận động hiện tại: {muc_van_dong_label}
- Tuổi: {profile.get('tuoi', 'N/A')}

QUAN TRỌNG: Không được chẩn đoán bệnh, không được gợi ý thuốc. Chỉ đưa ra lời khuyên tập luyện và lối sống nhẹ nhàng, an toàn.

"""
                print(f"📋 Đã load health profile cho user {user_id[:8]}... (BMI: {bmi:.1f}, {bmi_category})")
        except Exception as e:
            print(f"⚠️ Không thể load health profile: {e}")
            health_profile_context = ""

    # 10) PHÂN TẦNG TRẢ LỜI
    # Mức 1: RAG confidence cao (>= 0.7) → Trả lời dựa vào data
    # Mức 2: RAG confidence thấp (< 0.7) → Dùng Gemini
    # Mức 3: Risk cao hoặc không chắc chắn → Trả lời an toàn, khuyên gặp bác sĩ
    
    # ============================
    # BƯỚC 13: XÂY DỰNG CONVERSATION HISTORY (GPT-like context)
    # ============================
    conversation_history = None
    
    # Lấy lịch sử hội thoại từ state (tối đa 6 cặp Q&A gần nhất)
    history_list = state.get("conversation_history", [])
    
    # Lọc bỏ entry cuối cùng nếu chưa có reply (đó là câu hỏi hiện tại)
    complete_history = [(q, a) for q, a in history_list if a is not None]
    
    # Debug: In ra conversation history để kiểm tra
    if complete_history:
        print(f"📝 Conversation history có {len(complete_history)} cặp Q&A:")
        for i, (q, a) in enumerate(complete_history[-3:], 1):
            print(f"   {i}. User: {q[:50]}... | Bot: {a[:50] if a else 'None'}...")
    
    # Kiểm tra xem có phải câu trả lời tiếp theo sau clarification không
    last_clarification_question = state.get("last_clarification_question")
    last_user_input_before_clarification = state.get("last_user_input_before_clarification")
    last_symptoms = state.get("last_symptoms")
    
    # Xây dựng conversation history từ nhiều nguồn
    history_parts = []
    
    # 1. Nếu có clarification question trước đó
    if last_clarification_question and last_user_input_before_clarification:
        history_parts.append("Lịch sử cuộc trò chuyện:")
        history_parts.append(f"👤 Người dùng: \"{last_user_input_before_clarification}\"")
        history_parts.append(f"🤖 Bạn: \"{last_clarification_question}\"")
        history_parts.append(f"\n👉 Bây giờ người dùng trả lời: \"{cleaned_input}\"")
    # 2. Nếu có lịch sử hội thoại từ các lần trước (Q&A đã hoàn chỉnh)
    elif complete_history:
        history_parts.append("Lịch sử cuộc trò chuyện trước đó:")
        # Lấy 4-5 cặp gần nhất để có đủ ngữ cảnh
        for i, (q, a) in enumerate(complete_history[-5:], 1):
            history_parts.append(f"\n[{i}] 👤 Người dùng: {q}")
            history_parts.append(f"    🤖 Bạn: {a}")
        history_parts.append(f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\"")
    # 3. Nếu có thông tin từ lần trước (intent, symptoms) nhưng chưa có history đầy đủ
    elif last_intent and last_symptoms and not complete_history:
        history_parts.append("Thông tin từ cuộc trò chuyện trước:")
        history_parts.append(f"👤 Người dùng đã mô tả về: {last_intent}")
        if last_symptoms.get("location"):
            history_parts.append(f"   - Vị trí: {last_symptoms.get('location')}")
        if last_symptoms.get("intensity"):
            history_parts.append(f"   - Mức độ: {last_symptoms.get('intensity')}")
        history_parts.append(f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\"")
    
    if history_parts:
        conversation_history = "\n".join(history_parts)

    # 9) THÊM HEALTH PROFILE CONTEXT VÀO CONTEXT (nếu có)
    if health_profile_context:
        # Thêm health profile context vào đầu context
        if context:
            context = health_profile_context + "\n\n" + context
        else:
            context = health_profile_context

    # ============================
    # BƯỚC 14: PHÂN TẦNG TRẢ LỜI (Response Layer)
    # ============================
    pending_intent_after = state.get("pending_intent")
    
    # 6) CLARIFICATION LAYER — chỉ hỏi khi thực sự không rõ triệu chứng
    if need_more_info(cleaned_input, intent):
        question = build_clarification_question(intent)
        response["reply"] = (
            "💬 Để hiểu rõ hơn và trả lời chính xác, bạn cho mình biết thêm nhé:\n"
            f"{question}"
        )
        response["clarification_needed"] = True
        response["clarification_question"] = question
        response["stage"] = "clarification"
        # Lưu câu hỏi clarification vào state
        state["last_clarification_question"] = question
        state["last_user_input_before_clarification"] = cleaned_input
        
        # Log trước khi return
        print(f"\n{'='*60}")
        print(f"📊 LOG SUMMARY - CLARIFICATION")
        print(f"   intent_new: {intent_new}")
        print(f"   conf_new: {intent_conf:.3f}")
        print(f"   last_intent: {last_intent}")
        print(f"   final_intent: {final_intent}")
        print(f"   is_follow_up: {is_follow_up_flag}")
        print(f"   is_topic_shift: {is_topic_shift_flag}")
        print(f"   pending_intent (trước): {pending_intent_before}")
        print(f"   pending_intent (sau): {pending_intent_after}")
        print(f"   rag_intent: N/A (chưa RAG)")
        print(f"   rag_mode: None (chưa RAG)")
        print(f"   use_rag: False")
        print(f"   stage: {response['stage']}")
        print(f"{'='*60}\n")
        
        # Cập nhật conversation history với reply
        if history_list and history_list[-1][1] is None:
            history_list[-1] = (history_list[-1][0], response["reply"])
        return response
    
    # 5) RISK LAYER — phát hiện nguy hiểm
    if risk == "high":
        danger_signs = symptoms.get("danger_signs") or []
        danger_text = ", ".join(danger_signs) if danger_signs else "dấu hiệu nguy hiểm"
        response["reply"] = (
            "⚠️ Mình phát hiện có dấu hiệu nguy hiểm như: "
            + danger_text
            + ". Bạn nên đi khám bác sĩ càng sớm càng tốt để đảm bảo an toàn."
        )
        response["stage"] = "safety"
        
        # Log trước khi return
        print(f"\n{'='*60}")
        print(f"📊 LOG SUMMARY - RISK HIGH")
        print(f"   intent_new: {intent_new}")
        print(f"   conf_new: {intent_conf:.3f}")
        print(f"   last_intent: {last_intent}")
        print(f"   final_intent: {final_intent}")
        print(f"   is_follow_up: {is_follow_up_flag}")
        print(f"   is_topic_shift: {is_topic_shift_flag}")
        print(f"   pending_intent (trước): {pending_intent_before}")
        print(f"   pending_intent (sau): {pending_intent_after}")
        print(f"   rag_intent: N/A (không RAG khi risk high)")
        print(f"   rag_mode: None (không RAG khi risk high)")
        print(f"   use_rag: False")
        print(f"   stage: {response['stage']}")
        print(f"{'='*60}\n")
        
        # Cập nhật conversation history với reply
        if history_list and history_list[-1][1] is None:
            history_list[-1] = (history_list[-1][0], response["reply"])
        return response
    
    # Generate answer với RAG hoặc Gemini
    if use_rag and context:
        # Dùng RAG với context
        rag_confidence = docs[0].get("confidence", 0.0) if docs else 0.0
        print(f"✅ Dùng RAG với confidence: {rag_confidence:.3f}")
        response["stage"] = "rag_high_confidence"
        response["reply"] = generate_medical_answer(
            context=context,
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up_flag,
            use_rag_priority=True  # Ưu tiên sử dụng RAG context
        )
    else:
        # Dùng Gemini tự do (không có RAG context)
        print("⚠️ Dùng Gemini tự do (không có RAG context)")
        response["stage"] = "gemini_fallback"
        response["reply"] = generate_medical_answer(
            context="",  # Không có context từ RAG
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up_flag,
            use_rag_priority=False  # Không ưu tiên RAG, để Gemini tự do
        )
    
    # ============================
    # LOG SUMMARY (In ra tất cả thông tin cần thiết) - MỖI LƯỢT
    # ============================
    print(f"\n{'='*60}")
    print(f"📊 LOG SUMMARY - MỖI LƯỢT")
    print(f"   TOP-2: intent1={intent1} (conf1={conf1:.4f}), intent2={intent2} (conf2={conf2:.4f})")
    print(f"   intent_new: {intent_new}")
    print(f"   conf_new: {intent_conf:.4f}")
    print(f"   last_intent: {last_intent}")
    print(f"   final_intent: {final_intent}")
    print(f"   decision: {intent_decision_reason}")
    print(f"   is_follow_up: {is_follow_up_flag}")
    print(f"   is_topic_shift: {is_topic_shift_flag}")
    print(f"   pending_intent (trước): {pending_intent_before}")
    print(f"   pending_intent (sau): {state.get('pending_intent', 'None')}")
    print(f"   rag_intent: {rag_intent}")
    print(f"   rag_mode: {rag_mode} (strong/soft/None)")
    print(f"   use_rag: {use_rag}")
    print(f"   stage: {response.get('stage', 'unknown')}")
    print(f"{'='*60}\n")
    
    # Mức nữa: Nếu risk cao hoặc intent confidence thấp → Trả lời an toàn
    if risk == "high" or (intent_conf < 0.5 and response["stage"] not in ["safety", "rag_high_confidence"]):
        print("🛡️ Mức nữa: Risk cao hoặc không chắc chắn, trả lời an toàn")
        safety_message = (
            "⚠️ Dựa trên thông tin bạn cung cấp, tôi khuyên bạn nên đi gặp bác sĩ để được "
            "tư vấn và kiểm tra chính xác. Tôi chỉ có thể cung cấp thông tin tham khảo, "
            "không thể thay thế cho chẩn đoán y tế chuyên nghiệp.\n\n"
        )
        if response["reply"]:
            response["reply"] = safety_message + response["reply"]
        else:
            response["reply"] = safety_message + "Vui lòng liên hệ với bác sĩ càng sớm càng tốt."
        response["stage"] = "safety_recommendation"
    
    # Cập nhật conversation history với bot reply (giống GPT - nhớ lịch sử)
    # User input đã được lưu trước đó, giờ chỉ cần cập nhật reply
    if "reply" in response and response["reply"]:
        history_list = state.get("conversation_history", [])
        # Tìm entry cuối cùng (câu hỏi hiện tại) và cập nhật reply
        if history_list and history_list[-1][1] is None:
            history_list[-1] = (history_list[-1][0], response["reply"])
        else:
            # Nếu không tìm thấy, thêm mới (fallback)
            history_list.append((cleaned_input, response["reply"]))
        
        # Giữ tối đa 6 cặp Q&A gần nhất để không tốn quá nhiều token
        # (6 vì có thể có 1 entry chưa có reply)
        if len(history_list) > 6:
            history_list.pop(0)
        state["conversation_history"] = history_list
    
    # Xóa clarification question sau khi đã trả lời
    if is_follow_up_flag and "last_clarification_question" in state:
        state.pop("last_clarification_question", None)
        state.pop("last_user_input_before_clarification", None)
    
    return response


def chat(user_input: str, session_id: str = "default") -> str:
    result = run_chat_pipeline(user_input, session_id=session_id)
    return result["reply"]


# ============================
# VÒNG LẶP CHAT
# ============================

if __name__ == "__main__":
    while True:
        user = input("\nBạn: ").strip()
        if user.lower() == "quit":
            print("Tạm biệt bạn 👋 Chúc bạn nhiều sức khỏe!")
            break

        reply = chat(user, session_id="cli")
        print("Bot:", reply)
