# chatbot.py

from threading import Lock # để thread-safe
from typing import Any, Dict, Optional # typing
from intent.intent_classifier import IntentClassifier # lớp phân loại intent
from rag.retriever import Retriever # lớp retriever RAG
from generator.gemini_generator import generate_medical_answer  # hàm generate answer từ Gemini
from app.response_layer import (
    #hỏi thêm thông tin
    need_more_info, 
    # xây dựng câu hỏi làm rõ
    build_clarification_question,
    # kiểm tra có phải follow-up không
    is_follow_up,
    # kiểm tra có phải đổi chủ đề không
    is_topic_shift,
    # phân tích câu trả lời xác nhận đổi chủ đề
    parse_switch_confirm,
    # lấy label intent
    get_intent_label,
    # lấy category intent
    get_intent_category,
    # lâý ngưỡng gate RAG
    get_rag_gate_thresholds
)
from app.symptom_extractor import extract_symptoms
from app.risk_estimator import estimate_risk

# ============================
# KHỞI TẠO CÁC MODEL (LAZY LOADING)
# ============================
# Lazy Loading: Không tải models ngay khi import module
# Lợi ích: 
#   - Tiết kiệm memory nếu chỉ import chatbot nhưng không dùng chat
#   - Tải models khi cần (lần đầu gọi run_chat_pipeline)
#   - Sử dụng _models_lock để thread-safe

intent_model_path = r"D:\CHAT BOT TTCS\model\intent_model"
rag_path = r"D:\CHAT BOT TTCS\rag"

# Không load models ngay khi import - sẽ load khi cần
intent_classifier: Optional[IntentClassifier] = None
retriever: Optional[Retriever] = None
_models_initialized = False
_models_lock = Lock()

conversation_states: Dict[str, Dict[str, Any]] = {}
conversation_lock = Lock()

# Hàm đảm bảo models đã được load
def _ensure_models_loaded():
    """Đảm bảo tất cả models đã được tải trước khi dùng
    
    Phương pháp:
    1. Kiểm tra _models_initialized flag
    2. Nếu chưa tải, acquire lock và tải 3 model:
       - IntentClassifier: Phân loại intent từ text
       - Retriever: Tìm kiếm tài liệu RAG
       - Gemini Model: Kiểm tra API connection
    3. Sử dụng double-check pattern để tránh race condition
    
    Double-check pattern:
    - Check 1: Ngoài lock (nhanh, tránh lock không cần)
    - Check 2: Trong lock (chính xác, tránh 2 thread load cùng lúc)
    """
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

# hàm lấy hoặc tạo trạng thái hội thoại cho một session
def _get_or_create_state(session_id: str) -> Dict[str, Any]:
    """Lấy hoặc tạo mới trạng thái hội thoại cho một session
    
    Mỗi session (user) có state riêng để:
    - Lưu lịch sử hội thoại (conversation_history)
    - Lưu intent hiện tại (last_intent) để nhận diện follow-up
    - Lưu triệu chứng cuối cùng (last_symptoms) để truy vấn
    - Quản lý pending intent (khi chờ xác nhận đổi chủ đề)
    - Quản lý intent lock (ổn định intent khi có follow-up)
    
    State structure:
    {
        'last_intent': str | None,                  # Intent cuối cùng được xác định
        'last_symptoms': dict | None,               # Triệu chứng được trích xuất
        'conversation_history': [(q, a), ...],      # Lịch sử Q&A (tối đa 2 cặp)
        'intent_lock': {'intent': str, 'turns': int} | None,  # Ổn định intent trong N lượt
        'pending_intent': str | None,               # Intent mới chờ xác nhận
        'pending_from_intent': str | None,          # Intent cũ trước khi chuyển
        'pending_type': str | None                  # Loại pending (intent_switch_confirm)
    }
    """
    with conversation_lock:
        if session_id not in conversation_states:
            conversation_states[session_id] = {
                "last_intent": None,
                "last_symptoms": None,
                "conversation_history": [],  # Lưu lịch sử hội thoại (tối đa 2 cặp Q&A gần nhất)
                "intent_lock": None,  # { "intent": str, "turns": int } | None
                "pending_intent": None,  # Intent mới đang chờ xác nhận
                "pending_from_intent": None,  # Intent cũ
                "pending_type": None  # "intent_switch_confirm" | None
            }
        return conversation_states[session_id]

# hàm reset trạng thái hội thoại cho một session
def reset_conversation(session_id: str) -> None:
    with conversation_lock:
        conversation_states.pop(session_id, None)


# Hàm chat chính - xử lý input từ user và trả về response
def run_chat_pipeline(user_input: str, session_id: str = "default", user_id: Optional[str] = None) -> Dict[str, Any]:
    """Hàm chat chính - xử lý input từ user và trả về response
    
    === PIPELINE 14 BƯỚC ===
    
    BƯỚC 1: PENDING FLOW
    - Nếu đang chờ xác nhận đổi chủ đề → xử lý câu trả lời (yes/no/maybe)
    - Nếu user confirm → chuyển sang intent mới
    - Nếu user giữ → lại intent cũ
    - Nếu không rõ → hỏi lại
    
    BƯỚC 2: INTENT CLASSIFICATION (TOP-2)
    - Dùng PhoBERT để phân loại intent
    - Lấy top-2 intent với confidence
    
    BƯỚC 3: NHẬN DIỆN FOLLOW-UP & TOPIC SHIFT
    - Follow-up: User đang hỏi tiếp về chủ đề cũ
    - Topic shift: User rõ ràng đổi sang chủ đề mới
    
    BƯỚC 4-8: XỬ LÝ INTENT DECISION
    - Topic shift rõ → Đổi intent ngay
    - Follow-up + intent cũ → Giữ intent cũ
    - TOP-2 override: intent mới khác intent cũ
      * conf1 >= 0.98 → Đổi ngay (rất chắc)
      * 0.85 <= conf1 < 0.98 → Tạo pending hỏi xác nhận
      * conf1 < 0.85 → Giữ intent cũ (quá thấp)
    - Intent lock: Ổn định intent trong vài lượt
    - Default: Dùng intent1 nếu không có logic nào match
    
    BƯỚC 9: SET INTENT LOCK
    - Lock intent trong 2 lượt nếu: follow-up cùng intent + conf1 >= 0.98 + symptom category
    
    BƯỚC 10: SYMPTOM EXTRACTION & RISK
    - Trích xuất triệu chứng (location, intensity, duration, danger_signs)
    - Ước lượng risk (high/medium/low)
    
    BƯỚC 11: RAG GUARD
    - Follow-up BẮTBUỘC dùng intent cũ cho RAG (không search by intent_new)
    
    BƯỚC 12: RAG RETRIEVAL & GATE LOGIC
    - HIGH gate (conf >= 0.97): Search RAG theo intent → STRONG/SOFT/NO RAG
    - MID gate (0.85 <= conf < 0.97): Soft RAG global nếu intent không đổi
    - LOW gate (conf < 0.85): Gemini fallback
    
    BƯỚC 13: CONVERSATION HISTORY
    - Xây dựng context từ lịch sử Q&A (tối đa 2 cặp gần nhất)
    - Dùng cho Gemini để hiểu ngữ cảnh
    
    BƯỚC 14: RESPONSE LAYER
    - Risk high → Safety warning
    - Need clarification → Hỏi thêm info
    - Use RAG → Generate với RAG context
    - Fallback → Generate với Gemini tự do
    
    Args:
        user_input (str): Câu hỏi/mô tả từ user
        session_id (str): ID session để track hội thoại (default: "default")
        user_id (str, optional): ID user để lấy health profile từ Firestore
    
    Returns:
        Dict với keys:
        - session_id: ID session
        - reply: Câu trả lời từ bot
        - intent: Intent được xác định
        - intent_confidence: Độ tin cậy của intent (0-1)
        - symptoms: Dict triệu chứng được trích xuất
        - risk: Mức risk (high/medium/low)
        - clarification_needed: Có cần hỏi thêm không
        - sources: Danh sách RAG documents được dùng
        - stage: Stage xử lý (validation/pending_confirm/clarification/rag_high_confidence/gemini_fallback/safety)
    """
    # Đảm bảo models đã được load
    _ensure_models_loaded()
    
    cleaned_input = (user_input or "").strip()
#nếu input rỗng
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
# Lấy trạng thái hội thoại cho session
    state = _get_or_create_state(session_id)
# lấy lịch sử trong firestore nếu chưa có
    if not state.get("conversation_history"):
        print(f"🗂️ Thử load history từ Firestore | session={session_id} | user_id={user_id}")
        try:
            from firestore_service import load_chat_history
            restored_history = load_chat_history(user_id, session_id, limit=2)
            if restored_history:
                state["conversation_history"] = restored_history
                print(
                    f"🗂️ Load thành công {len(restored_history)} cặp Q&A | session={session_id} | user_id={user_id}"
                )
            else:
                print(
                    f"ℹ️ History Firestore trống hoặc không đủ cặp | session={session_id} | user_id={user_id}"
                )
        except Exception as e:
            print(f"⚠️ Không thể load history từ Firestore | session={session_id} | user_id={user_id} | lỗi: {e}")
    
    # Lưu user input vào conversation history ngay (trước khi generate reply)
    history_list = state.get("conversation_history", [])
    history_list.append((cleaned_input, None))
    # Đánh dấu placeholder None để lát nữa ghép reply tương ứng, giữ thứ tự hội thoại chuẩn GPT
    state["conversation_history"] = history_list
    
    # Khởi tạo response template mới 
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
    intent_lock_before = state.get("intent_lock")
    
    # ============================
    # BƯỚC 1: PENDING FLOW (Xử lý xác nhận đổi chủ đề)
    # ============================
    # Nếu message đang chờ xác nhận đổi chủ đề
    # BƯỚC 1 sẽ xử lý câu trả lời này trước khi tiếp tục pipeline
    pending_intent_before = state.get("pending_intent")
    rag_mode = None  # Khởi tạo để dùng trong log (sẽ được set sau)
    intent_decision_reason = "unknown"  # Log cuối pipeline đọc lý do chốt intent tại bước nào
    
    #nếu đang chờ xác nhận đổi chủ đề
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
            # Giữ nguyên pending fields để hỏi lại
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
    
    # BƯỚC 2: INTENT CLASSIFICATION - TOP-2
    # Phân loại intent với PhoBERT lấy top-2
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
    
    # BƯỚC 3: NHẬN DIỆN FOLLOW-UP & TOPIC SHIFT
    #kiểm tra có phải follow-up hay đổi chủ đề rõ ràng không
    is_follow_up_flag = is_follow_up(cleaned_input)
    is_topic_shift_flag = is_topic_shift(cleaned_input)
    
    print(f"📌 CONTEXT DETECTION")
    print(f"   is_follow_up: {is_follow_up_flag}")
    print(f"   is_topic_shift: {is_topic_shift_flag}\n")
    
    # BƯỚC 4: TOPIC SHIFT RÕ (Cho phép đổi chủ đề)
    if is_topic_shift_flag and not is_follow_up_flag:
        # Đổi chủ đề rõ → cho phép đổi
        intent = intent_new
        print(f"✅ TOPIC SHIFT: Đổi sang {intent}")
        # Xóa intent lock nếu có (vì đổi chủ đề rõ)
        state.pop("intent_lock", None)
        final_intent = intent
        intent_decision_reason = "topic_shift"
        
    # BƯỚC 5: FOLLOW-UP (Giữ chủ đề cũ)
    #nếu là follow-up và có last_intent thì giữ intent cũ
    elif is_follow_up_flag and last_intent and not is_topic_shift_flag:
        # Follow-up → ưu tiên tuyệt đối giữ intent cũ
        intent = last_intent
        print(f"✅ FOLLOW-UP: Giữ intent cũ {intent}")
        final_intent = intent
        intent_decision_reason = "follow_up"
        
    # BƯỚC 6: TOP-2 SWITCH OVERRIDE (Đổi chủ đề CHẮC hoặc PENDING)
    #nếu intent mới khác intent cũ và không phải follow-up hay đổi chủ đề rõ
    elif last_intent and intent1 != last_intent and not is_follow_up_flag and not is_topic_shift_flag:
        # Ngưỡng override chung cho tất cả intent
        override_conf_threshold = 0.92
        override_conf2_max = 0.04

        # 6.1) Đổi NGAY khi rất chắc
        if conf1 >= override_conf_threshold and conf2 <= override_conf2_max:
            intent = intent1
            state.pop("intent_lock", None)  # Xóa lock vì TOP-2 override
            print(
                f"✅ TOP-2 OVERRIDE (NGAY): conf1={conf1:.4f} >= {override_conf_threshold:.2f}, conf2={conf2:.4f} <= {override_conf2_max:.2f} → Đổi sang {intent1}"
            )
            final_intent = intent
            intent_decision_reason = "top2_override_sure"
        
        # 6.2) Mơ hồ → TẠO PENDING hỏi xác nhận
        elif 0.85 <= conf1 < 0.92:
            state["pending_intent"] = intent1
            state["pending_from_intent"] = last_intent
            state["pending_type"] = "intent_switch_confirm"
            
            from_label = get_intent_label(last_intent)
            to_label = get_intent_label(intent1)
            
            response["reply"] = (
                f"💬 Bạn đang muốn hỏi tiếp về {from_label} hay chuyển sang {to_label}? "
                "Vui lòng trả lời rõ ràng."
            )
            # Đặt stage để biết đang chờ xác nhận
            response["stage"] = "intent_switch_confirm"
            response["intent"] = last_intent  # Giữ intent cũ trong response
            response["intent_confidence"] = float(conf1)
            
            print(f"❓ TOP-2 OVERRIDE (PENDING): 0.85 <= conf1={conf1:.4f} < 0.92 → Hỏi xác nhận")
            
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
                # conf1 >= 0.85 → dùng intent1 nếu không có last_intent 
                intent = intent_new
                print(f"ℹ️ TOP-2 DEFAULT: conf1={conf1:.4f} ∈ [0.85, 0.92) → Dùng intent1 {intent1}")
                intent_decision_reason = "top2_default"
            final_intent = intent
    
    # BƯỚC 7: INTENT LOCK (Stabilization - không chặn TOP-2 override)
    # nếu có intent lock và không phải follow-up, không có topic shift, không có pending, thì dùng intent lock
    elif state.get("intent_lock") and not is_follow_up_flag and not is_topic_shift_flag:
        intent_lock = state["intent_lock"]
        locked_intent = intent_lock.get("intent")
        turns_left = intent_lock.get("turns", 0)
        # Nếu còn lượt lock thì dùng intent lock
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
            # Hết lượt → dùng default intent mới
            intent = intent_new
            state.pop("intent_lock", None)
            final_intent = intent
            intent_decision_reason = "default_after_lock"
            
    # ============================
    # BƯỚC 8: DEFAULT
    # ============================
    # nếu không có logic nào match thì dùng intent1
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
    # - conf1 >= 0.92 (rất chắc)
    # - intent là symptom category (tránh lock cho other, tư vấn)
    intent_category = get_intent_category(final_intent)
    lock_reason = None
    if (final_intent == last_intent and conf1 >= 0.92 and 
        final_intent not in ["other", "unknown"] and 
        intent_category == "symptom"):
        state["intent_lock"] = {"intent": final_intent, "turns": 2}
        lock_reason = "set_lock"
        print(f"🔒 SET LOCK: final_intent={final_intent} (symptom), conf1={conf1:.4f} >= 0.92\n")
    else:
        # Không set lock: ghi lý do để debug
        if final_intent != last_intent:
            lock_reason = "intent_changed"
        elif conf1 < 0.92:
            lock_reason = "conf_below_0.92"
        elif final_intent in ["other", "unknown"]:
            lock_reason = "intent_other_unknown"
        elif intent_category != "symptom":
            lock_reason = "intent_not_symptom"
        state.pop("intent_lock", None)
        if lock_reason:
            print(f"ℹ️ NO LOCK: {lock_reason}")
    intent_lock_after = state.get("intent_lock")
    
    # ============================
    # BƯỚC 10: SYMPTOM EXTRACTION & RISK
    # ============================
    # trích xuất các triệu chứng và ước lượng mức độ nguy hiểm trong hàm extract_symptoms của file symptom_extractor.py
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

    # Log nhanh triệu chứng trích xuất và mức risk để dễ theo dõi pipeline
    print(f"🩺 SYMPTOM EXTRACTOR → loc={symptoms.get('location')} | dur={symptoms.get('duration')} | intensity={symptoms.get('intensity')} | extra={symptoms.get('extra')} | danger={symptoms.get('danger_signs')} | risk={risk}")

    # 5) RISK LAYER — phát hiện nguy hiểm
    #n nếu risk cao thì cảnh báo an toàn
    if risk == "high":
        danger_signs = symptoms.get("danger_signs") or []
        danger_text = ", ".join(danger_signs) if danger_signs else "dấu hiệu nguy hiểm"
        response["reply"] = (
            "⚠️ Mình phát hiện có dấu hiệu nguy hiểm như: "
            + danger_text
            + ". Bạn nên đi khám bác sĩ càng sớm càng tốt để đảm bảo an toàn."
        )
        # Đánh dấu stage safety để log
        response["stage"] = "safety"
        return response

    # ============================
    # BƯỚC 11: RAG GUARD (Bắt buộc - Tránh RAG sai chủ đề)
    # ============================
    # Follow-up tuyệt đối không được search_by_intent(intent_new)
    # nếu là follow-up thì dùng intent cũ cho RAG
    if is_follow_up_flag and last_intent:
        rag_intent = last_intent  # Dùng intent cũ
        print(f"🛡️ RAG Guard: Follow-up → dùng intent cũ cho RAG: {rag_intent}")
    else:
        rag_intent = intent  # Dùng intent hiện tại
    
    print(f"\n📚 RAG GUARD")
    print(f"   rag_intent: {rag_intent} (dùng cho RAG search)")
    print(f"   (final_intent: {final_intent}, last_intent: {last_intent})\n")
    
    # ============================
    # BƯỚC 12: RAG RETRIEVAL với các mode 
    # ============================
    use_rag = False
    context = ""
    docs = []
    rag_mode = None  # "strong", "soft", hoặc None
    
    # Phân loại intent để xác định ngưỡng
    intent_category = get_intent_category(rag_intent)
    strong_threshold, soft_threshold = get_rag_gate_thresholds(intent_category)
    # Mỗi intent category (symptom, lifestyle, no_rag, ...) map sang ngưỡng riêng để tránh trả lời quá tự tin
    
    print(f"\n📊 RAG GATE LOGIC")
    print(f"   rag_intent: {rag_intent}")
    print(f"   intent_category: {intent_category}")
    print(f"   thresholds: STRONG >= {strong_threshold:.2f}, SOFT >= {soft_threshold:.2f}")
    
    # Kiểm tra intent có dùng RAG không
    # Case 1: intent_category == no_rag → luôn Gemini
    if intent_category == "no_rag":
        # Intent không dùng RAG → luôn Gemini
        print(f"❌ Intent '{rag_intent}' không dùng RAG → Gemini fallback")
        response["sources"] = []
        context = ""
        use_rag = False
    # Case 2: intent_conf rất cao → HIGH gate, search_by_intent
    elif intent_conf >= 0.92 and rag_intent not in ["other", "unknown"]:
        # HIGH: Chắc chắn RAG theo intent 
        print(f"✅ High gate: Intent confidence {intent_conf:.3f} >= 0.92, search RAG theo intent: {rag_intent}")
        try:
            # Lấy tối đa 5 documents (sẽ chọn số lượng sau dựa trên confidence)
            docs = retriever.search_by_intent(rag_intent, cleaned_input, k=5)
            response["sources"] = docs
        #nếu có lỗi khi search theo intent thì fallback về search all intents
            if docs:
                rag_confidence = docs[0].get("confidence", 0.0)
                rag_cosine = docs[0].get("cosine", -1.0)
                print(f"📚 RAG Confidence (top1): {rag_confidence:.3f} | Cosine: {rag_cosine:.3f}")
                
                # HIGH gate + doc strong: dùng STRONG RAG (tối đa 5 đoạn)
                if rag_confidence >= strong_threshold:
                    # STRONG RAG: dùng nhiều hơn (tối đa 5 đoạn) cho câu trả lời giàu nội dung
                    num_docs = min(5, len(docs))
                    context_parts = []
                    for i, d in enumerate(docs[:num_docs], start=1):
                        context_parts.append(f"[ĐOẠN {i}]\n" + d.get("text", ""))
                    context = "\n\n".join(context_parts)
                    use_rag = True
                    rag_mode = "strong"
                    print(f"✅ STRONG RAG: {rag_confidence:.3f} >= {strong_threshold:.2f} → dùng {num_docs} đoạn")
                # HIGH gate + doc medium: dùng SOFT RAG (1-2 đoạn tham khảo)
                elif rag_confidence >= soft_threshold:
                    # SOFT RAG: 1-2 đoạn, chỉ tham khảo nhẹ
                    num_docs = min(2, len(docs))
                    context_parts = []
                    for i, d in enumerate(docs[:num_docs], start=1):
                        context_parts.append(f"[ĐOẠN {i}]\n" + d.get("text", ""))
                    context = "\n\n".join(context_parts)
                    use_rag = True
                    rag_mode = "soft"
                    print(f"🟡 SOFT RAG: {rag_confidence:.3f} >= {soft_threshold:.2f} → dùng {num_docs} đoạn (chỉ tham khảo)")
                # HIGH gate + doc thấp: bỏ RAG
                else:
                    # NO RAG: Confidence quá thấp
                    print(f"❌ NO RAG: {rag_confidence:.3f} < {soft_threshold:.2f} → Gemini fallback")
                    use_rag = False
                    context = ""
                    rag_mode = None
            # HIGH gate nhưng không có docs → Gemini
            else:
                print("⚠️ RAG không trả về kết quả → fallback Gemini")
                use_rag = False
                context = ""
        # Nếu search_by_intent lỗi → fallback search_all_intents rồi áp dụng lại gate
        except Exception as e:
            print(f"⚠️ Lỗi khi search RAG theo intent: {e}, fallback về search thông thường")
            try:
                docs = retriever.search_all_intents(cleaned_input, k=5)
                response["sources"] = docs
                # Kiểm tra docs trả về
                if docs:
                    rag_confidence = docs[0].get("confidence", 0.0)
                    # Fallback doc strong → STRONG RAG
                    if rag_confidence >= strong_threshold:
                        # STRONG RAG fallback: tối đa 5 đoạn
                        num_docs = min(5, len(docs))
                        context_parts = []
                        for i, d in enumerate(docs[:num_docs], start=1):
                            context_parts.append(f"[ĐOẠN {i}]\n" + d.get("text", ""))
                        context = "\n\n".join(context_parts)
                        use_rag = True
                        rag_mode = "strong"
                    # Fallback doc medium → SOFT RAG
                    elif rag_confidence >= soft_threshold:
                        # SOFT RAG fallback: 1-2 đoạn
                        num_docs = min(2, len(docs))
                        context_parts = []
                        for i, d in enumerate(docs[:num_docs], start=1):
                            context_parts.append(f"[ĐOẠN {i}]\n" + d.get("text", ""))
                        context = "\n\n".join(context_parts)
                        use_rag = True
                        rag_mode = "soft"
                    # Fallback doc thấp → bỏ RAG
                    else:
                        use_rag = False
                        context = ""
                else:
                    use_rag = False
                    context = ""
            except:
                use_rag = False
                context = ""
    # Case 3: intent_conf trung bình → MID gate, chỉ soft RAG global nếu bám intent cũ
    elif 0.85 <= intent_conf < 0.92 and rag_intent not in ["other", "unknown"]:
        # MID: Có thể RAG global nhẹ (nếu intent không đổi)
        print(f"⚠️ Mid gate: Intent confidence {intent_conf:.3f} trong khoảng [0.85, 0.92)")
        # nếu intent không đổi và không phải no_rag thì có thể RAG 
        if intent_new == last_intent and intent_category != "no_rag":
            # Chỉ cho phép global search khi user vẫn bám intent cũ → giảm nguy cơ lôi nhầm tài liệu intent khác
            # Intent không đổi → có thể RAG global
            try:
                docs = retriever.search_all_intents(cleaned_input, k=3)
                response["sources"] = docs
                if docs:
                    rag_confidence = docs[0].get("confidence", 0.0)
                    if rag_confidence >= soft_threshold:
                        # Chỉ dùng SOFT RAG khi mid gate, lấy 1-2 đoạn
                        num_docs = min(2, len(docs))
                        context_parts = []
                        for i, d in enumerate(docs[:num_docs], start=1):
                            context_parts.append(f"[ĐOẠN {i}]\n" + d.get("text", ""))
                        context = "\n\n".join(context_parts)
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
            # Intent đổi hoặc intent_category no_rag → không RAG mid gate
            print("⚠️ Mid gate: Intent đổi hoặc no_rag → không RAG, để Gemini/clarify xử lý")
            use_rag = False
            context = ""
            
    else:
        # Case 4: intent_conf thấp hoặc intent other/unknown → luôn Gemini
        print(f"⚠️ Low gate: Intent '{rag_intent}' với confidence {intent_conf:.3f} < 0.85 hoặc other/unknown → Gemini fallback")
        response["sources"] = []
        context = ""
        use_rag = False
    
    print(f"   rag_mode: {rag_mode}")
    print(f"   use_rag: {use_rag}\n")


    # GHI CHÚ PHÂN TẦNG TRẢ LỜI
    # Mức 1: RAG confidence cao (>= 0.7) → Trả lời dựa vào data
    # Mức 2: RAG confidence thấp (< 0.7) → Dùng Gemini
    # Mức 3: Risk cao hoặc không chắc chắn → Trả lời an toàn, khuyên gặp bác sĩ
    
    # ============================
    # BƯỚC 13: XÂY DỰNG CONVERSATION HISTORY 
    # ============================
    # Tạo lịch sử hội thoại để cung cấp ngữ cảnh, giữ mạch trao đổi cho LLM
    conversation_history = None
    
    # Lấy lịch sử hội thoại từ state (tối đa 2 cặp Q&A gần nhất)
    history_list = state.get("conversation_history", [])
    
    # Lọc bỏ entry cuối cùng nếu chưa có reply (đó là câu hỏi hiện tại)
    complete_history = [(q, a) for q, a in history_list if a is not None]
    
    # Debug: In ra toàn bộ conversation history sẽ dùng cho prompt (tối đa 2 cặp)
    if complete_history:
        print(f"📝 Conversation history (full, tối đa 2 cặp): {len(complete_history)} cặp | session={session_id} | user_id={user_id}")
        for i, (q, a) in enumerate(complete_history, 1):
            user_preview = (q or "")[:120]
            bot_preview = (a or "")[:120]
            print(f"   {i}. User: {user_preview} | Bot: {bot_preview}")
    else:
        print(f"📝 Conversation history trống | session={session_id} | user_id={user_id}")
    
    # Kiểm tra xem có phải câu trả lời tiếp theo sau clarification không
    last_clarification_question = state.get("last_clarification_question")
    last_user_input_before_clarification = state.get("last_user_input_before_clarification")
    last_symptoms = state.get("last_symptoms")
    
    # Xây dựng conversation history từ nhiều nguồn
    # MỤC ĐÍCH: Tạo ngữ cảnh cho Gemini hiểu mạch hội thoại → trả lời liền mạch, không lặp lại câu hỏi
    history_parts = []  # Gom nhiều nguồn ngữ cảnh khác nhau rồi ghép thành đoạn prompt duy nhất
    
    # ===== CASE 1: ƯU TIÊN CLARIFICATION FLOW (khi bot vừa hỏi thêm info) =====
    # Tình huống: Bot hỏi "Bạn đau ở đâu?" → User trả lời "ở rốn"
    # Vấn đề: Nếu không ghép lại đúng cặp hỏi-trả lời, Gemini sẽ không hiểu "ở rốn" là trả lời cho câu hỏi nào
    # Giải pháp: Ghép đúng 3 phần: câu hỏi ban đầu của user → câu hỏi clarification của bot → câu trả lời mới của user
    if last_clarification_question and last_user_input_before_clarification:
        history_parts.append("Lịch sử cuộc trò chuyện:")
        history_parts.append(f"👤 Người dùng: \"{last_user_input_before_clarification}\"")  # Câu hỏi ban đầu (ví dụ: "Tôi đau bụng")
        history_parts.append(f"🤖 Bạn: \"{last_clarification_question}\"")  # Bot hỏi thêm (ví dụ: "Bạn đau ở vị trí nào?")
        history_parts.append(f"\n👉 Bây giờ người dùng trả lời: \"{cleaned_input}\"")  # User trả lời (ví dụ: "ở rốn")
    
    # ===== CASE 2: LỊCH SỬ HỘI THOẠI BÌNH THƯỜNG (có đầy đủ Q&A trước đó) =====
    # Tình huống: User chat bình thường nhiều lượt: "đau đầu" → "nặng lắm" → "uống thuốc gì?"
    # Vấn đề: Nếu không có lịch sử, Gemini sẽ quên ngữ cảnh, trả lời như câu đầu tiên
    # Giải pháp: Lấy 4-5 cặp Q&A gần nhất để Gemini nhớ được mạch hội thoại
    # Lưu ý: Không lấy quá nhiều vì tốn token và Gemini dễ bị nhiễu thông tin cũ
    elif complete_history:
        history_parts.append("Lịch sử cuộc trò chuyện trước đó:")
        # Lấy 4-5 cặp gần nhất để có đủ ngữ cảnh (complete_history[-5:] = 5 cặp cuối)
        for i, (q, a) in enumerate(complete_history[-5:], 1):
            history_parts.append(f"\n[{i}] 👤 Người dùng: {q}")  # Câu hỏi của user
            history_parts.append(f"    🤖 Bạn: {a}")  # Câu trả lời của bot
        history_parts.append(f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\"")  # Câu hỏi hiện tại
    
    # ===== CASE 3: FALLBACK KHI CHƯA CÓ HISTORY ĐẦY ĐỦ (user mới chat, Firestore chưa có data) =====
    # Tình huống: Lần đầu user chat, hoặc Firestore trống, nhưng vẫn có intent/symptoms từ lượt trước (trong RAM)
    # Vấn đề: Không có lịch sử Q&A đầy đủ nhưng có thông tin triệu chứng → cần tận dụng
    # Giải pháp: Tóm tắt thông tin có được (intent, location, intensity) để Gemini biết user đang nói về gì
    # Ví dụ: User nói "đau đầu dữ lắm" (lượt 1, chưa có history) → lượt 2 hỏi "uống thuốc gì?" → cần biết context là "đau đầu"
    elif last_intent and last_symptoms and not complete_history:
        history_parts.append("Thông tin từ cuộc trò chuyện trước:")
        history_parts.append(f"👤 Người dùng đã mô tả về: {last_intent}")  # Ví dụ: "bao_dau_dau" (intent về đau đầu)
        if last_symptoms.get("location"):
            history_parts.append(f"   - Vị trí: {last_symptoms.get('location')}")  # Ví dụ: "thái dương"
        if last_symptoms.get("intensity"):
            history_parts.append(f"   - Mức độ: {last_symptoms.get('intensity')}")  # Ví dụ: "dữ dội"
        history_parts.append(f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\"")  # Câu hỏi hiện tại
    
    # Ghép tất cả các parts thành 1 chuỗi conversation_history duy nhất để gửi cho Gemini
    if history_parts:
        conversation_history = "\n".join(history_parts)

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
        # Đánh dấu stage clarification để log 
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
        # Đánh dấu stage safety để log
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
        # Log chi tiết RAG context để debug
        print(f"\n{'='*60}")
        print("🧾 GEMINI DEBUG - RAG CONTEXT")
        print(f"👉 User question: {cleaned_input}")
        print("👉 RAG context (đã ghép):")
        print(context)
        if docs:
            # Hiển thị đúng số lượng docs được dùng (dựa vào rag_mode)
            num_display = 5 if rag_mode == "strong" else 2 if rag_mode == "soft" else len(docs)
            print(f"👉 RAG raw docs (top {num_display}):")
            for i, d in enumerate(docs[:num_display], 1):
                text_preview = (d.get('text', '') or '')
                print(f"   [{i}] conf={d.get('confidence', 0.0):.3f} | text={text_preview[:300]}...")
        print(f"{'='*60}\n")

        response["stage"] = "rag_high_confidence"
        gemini_answer = generate_medical_answer(
            context=context,
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up_flag,
            use_rag_priority=True  # Ưu tiên sử dụng RAG context
        )
        # Log full answer từ Gemini để kiểm tra cắt nội dung
        print(f"\n{'='*60}")
        print("🧾 GEMINI DEBUG - ANSWER (WITH RAG)")
        print(gemini_answer)
        print(f"{'='*60}\n")
        response["reply"] = gemini_answer
    else:
        # Dùng Gemini tự do (không có RAG context)
        print("⚠️ Dùng Gemini tự do (không có RAG context)")
        print(f"\n{'='*60}")
        print("🧾 GEMINI DEBUG - NO RAG CONTEXT")
        print(f"👉 User question: {cleaned_input}")
        if conversation_history:
            print("👉 Conversation history gửi vào Gemini:")
            print(conversation_history)
        print(f"{'='*60}\n")
        #đánh dấu stage để log 
        response["stage"] = "gemini_fallback"
        gemini_answer = generate_medical_answer(
            context="",  # Không có context từ RAG
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up_flag,
            use_rag_priority=False  # Không ưu tiên RAG, để Gemini tự do
        )
        print(f"\n{'='*60}")
        print("🧾 GEMINI DEBUG - ANSWER (NO RAG)")
        print(gemini_answer)
        print(f"{'='*60}\n")
        response["reply"] = gemini_answer
    
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
    print(f"   intent_lock (trước): {intent_lock_before}")
    print(f"   intent_lock (sau): {intent_lock_after}")
    if lock_reason:
        print(f"   intent_lock_reason: {lock_reason}")
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
        # Đánh dấu stage safety_recommendation để log
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
        
        # Giữ tối đa 2 cặp Q&A gần nhất để không tốn quá nhiều token
        # (2 vì có thể có 1 entry chưa có reply)
        if len(history_list) > 2:
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

