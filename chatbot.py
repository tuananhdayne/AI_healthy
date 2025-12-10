# chatbot.py

from threading import Lock
from typing import Any, Dict, Optional

from intent.intent_classifier import IntentClassifier
from rag.retriever import Retriever
from generator.gemini_generator import generate_medical_answer
from app.response_layer import need_more_info, build_clarification_question
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
                "conversation_history": []  # Lưu lịch sử hội thoại (tối đa 5 cặp Q&A gần nhất)
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

    # 1) Intent
    intent, intent_conf = intent_classifier.predict_with_conf(cleaned_input)
    print(f"🧠 Intent: {intent} | conf={intent_conf:.2f}")

    # 2) Symptom Extraction
    symptoms = extract_symptoms(cleaned_input)
    risk = estimate_risk(symptoms)

    # 3) Lưu vào memory
    state["last_intent"] = intent
    state["last_symptoms"] = symptoms
    state["last_user_input"] = cleaned_input
    
    # Lưu user input vào conversation history ngay (trước khi generate reply)
    history_list = state.get("conversation_history", [])
    # Lưu user input với bot reply = None (sẽ cập nhật sau)
    history_list.append((cleaned_input, None))
    state["conversation_history"] = history_list

    response: Dict[str, Any] = {
        "session_id": session_id,
        "intent": intent,
        "intent_confidence": float(intent_conf),
        "symptoms": symptoms,
        "risk": risk,
        "clarification_needed": False,
        "clarification_question": None,
        "sources": [],
        "stage": "generation"
    }

    # 4) Người dùng nói tiếp các từ mơ hồ: "vẫn thế", "đỡ hơn rồi"
    if cleaned_input.lower() in ["vẫn thế", "như hôm qua", "đỡ hơn", "nặng hơn"]:
        last = state.get("last_symptoms")
        if last:
            response["reply"] = (
                "💬 Bạn đang nói về triệu chứng trước đó. Bạn có thể mô tả thêm không? "
                f"Mình ghi nhận lần trước là: {last}"
            )
        else:
            response["reply"] = "Bạn mô tả triệu chứng hiện tại rõ hơn nhé!"
        response["stage"] = "follow_up"
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

    # 7) RAG RETRIEVAL - Tìm thông tin trong database
    # Logic mới: Nếu intent confidence >= 0.998 → search RAG theo intent
    # Nếu intent là "other"/"unknown" hoặc confidence < 0.98 → dùng Gemini tự do
    
    use_rag = False
    context = ""
    docs = []
    
    # Kiểm tra intent confidence
    if intent_conf >= 0.998 and intent not in ["other", "unknown"]:
        # Intent confidence cao → search RAG theo intent
        print(f"✅ Intent confidence cao ({intent_conf:.3f}), search RAG theo intent: {intent}")
        try:
            docs = retriever.search_by_intent(intent, cleaned_input, k=5)  # Tăng từ 3 lên 5 để có nhiều context hơn
            response["sources"] = docs
            
            # Tính confidence từ RAG results
            rag_confidence = docs[0]["confidence"] if docs else 0.0
            rag_cosine = docs[0]["cosine"] if docs else -1.0
            
            print(f"📚 RAG Confidence: {rag_confidence:.3f} | Cosine: {rag_cosine:.3f}")
            
            # Xây dựng context từ RAG
            context = "\n".join([d["text"] for d in docs]) if docs else ""
            use_rag = True
        except Exception as e:
            print(f"⚠️ Lỗi khi search RAG theo intent: {e}, fallback về search thông thường")
            docs = retriever.search(cleaned_input, k=5)  # Tăng từ 3 lên 5
            response["sources"] = docs
            context = "\n".join([d["text"] for d in docs]) if docs else ""
            use_rag = True
    elif intent in ["other", "unknown"] or intent_conf < 0.98:
        # Intent là "other"/"unknown" hoặc confidence thấp → dùng Gemini tự do (không search RAG)
        print(f"⚠️ Intent '{intent}' với confidence {intent_conf:.3f} < 0.98, dùng Gemini tự do")
        response["sources"] = []
        context = ""  # Không có context từ RAG
        use_rag = False
    else:
        # Trường hợp khác: search RAG thông thường
        docs = retriever.search(cleaned_input, k=5)  # Tăng từ 3 lên 5 để có nhiều context hơn
        response["sources"] = docs
        
        # Tính confidence từ RAG results
        rag_confidence = docs[0]["confidence"] if docs else 0.0
        rag_cosine = docs[0]["cosine"] if docs else -1.0
        
        print(f"📚 RAG Confidence: {rag_confidence:.3f} | Cosine: {rag_cosine:.3f}")
        
        # Xây dựng context từ RAG
        context = "\n".join([d["text"] for d in docs]) if docs else ""
        use_rag = True

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
    
    # Xây dựng conversation history để bot nhớ ngữ cảnh (giống GPT - nhớ nhiều vòng hội thoại)
    conversation_history = None
    is_follow_up = False
    
    # Lấy lịch sử hội thoại từ state (tối đa 5 cặp Q&A gần nhất)
    history_list = state.get("conversation_history", [])
    
    # Lọc bỏ entry cuối cùng nếu chưa có reply (đó là câu hỏi hiện tại)
    # Chỉ lấy các cặp Q&A đã hoàn chỉnh
    complete_history = [(q, a) for q, a in history_list if a is not None]
    
    # Debug: In ra conversation history để kiểm tra
    if complete_history:
        print(f"📝 Conversation history có {len(complete_history)} cặp Q&A:")
        for i, (q, a) in enumerate(complete_history[-3:], 1):
            print(f"   {i}. User: {q[:50]}... | Bot: {a[:50] if a else 'None'}...")
    
    # Kiểm tra xem có phải câu trả lời tiếp theo sau clarification không
    last_clarification_question = state.get("last_clarification_question")
    last_user_input_before_clarification = state.get("last_user_input_before_clarification")
    last_intent = state.get("last_intent")
    last_symptoms = state.get("last_symptoms")
    
    # Xây dựng conversation history từ nhiều nguồn
    history_parts = []
    
    # 1. Nếu có clarification question trước đó
    if last_clarification_question and last_user_input_before_clarification:
        is_follow_up = True
        history_parts.append("Lịch sử cuộc trò chuyện:")
        history_parts.append(f"👤 Người dùng: \"{last_user_input_before_clarification}\"")
        history_parts.append(f"🤖 Bạn: \"{last_clarification_question}\"")
        history_parts.append(f"\n👉 Bây giờ người dùng trả lời: \"{cleaned_input}\"")
    # 2. Nếu có lịch sử hội thoại từ các lần trước (Q&A đã hoàn chỉnh)
    elif complete_history:
        is_follow_up = True
        history_parts.append("Lịch sử cuộc trò chuyện trước đó:")
        # Lấy 4-5 cặp gần nhất để có đủ ngữ cảnh
        for i, (q, a) in enumerate(complete_history[-5:], 1):
            history_parts.append(f"\n[{i}] 👤 Người dùng: {q}")
            history_parts.append(f"    🤖 Bạn: {a}")
        history_parts.append(f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\"")
    # 3. Nếu có thông tin từ lần trước (intent, symptoms) nhưng chưa có history đầy đủ
    elif last_intent and last_symptoms and not complete_history:
        is_follow_up = True
        history_parts.append("Thông tin từ cuộc trò chuyện trước:")
        history_parts.append(f"👤 Người dùng đã mô tả về: {last_intent}")
        if last_symptoms.get("location"):
            history_parts.append(f"   - Vị trí: {last_symptoms.get('location')}")
        if last_symptoms.get("intensity"):
            history_parts.append(f"   - Mức độ: {last_symptoms.get('intensity')}")
        history_parts.append(f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\"")
    
    if history_parts:
        conversation_history = "\n".join(history_parts)
        is_follow_up = True  # Đảm bảo is_follow_up = True nếu có history

    # 9) THÊM HEALTH PROFILE CONTEXT VÀO CONTEXT (nếu có)
    if health_profile_context:
        # Thêm health profile context vào đầu context
        if context:
            context = health_profile_context + "\n\n" + context
        else:
            context = health_profile_context

    # 11) PHÂN TẦNG TRẢ LỜI
    # Logic mới: Nếu đã search RAG theo intent (confidence >= 0.998) → dùng RAG
    # Nếu intent là "other"/"unknown" hoặc confidence < 0.98 → dùng Gemini tự do
    
    if use_rag and context:
        # Đã search RAG theo intent → trả lời dựa vào RAG
        rag_confidence = docs[0]["confidence"] if docs else 0.0
        print(f"✅ Dùng RAG với confidence: {rag_confidence:.3f}")
        response["stage"] = "rag_high_confidence"
        response["reply"] = generate_medical_answer(
            context=context,
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up,
            use_rag_priority=True  # Ưu tiên sử dụng RAG context
        )
    else:
        # Intent là "other"/"unknown" hoặc confidence < 0.98 → dùng Gemini tự do
        print("⚠️ Dùng Gemini tự do (không có RAG context)")
        response["stage"] = "gemini_fallback"
        response["reply"] = generate_medical_answer(
            context="",  # Không có context từ RAG
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up,
            use_rag_priority=False  # Không ưu tiên RAG, để Gemini tự do
        )
    
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
    if is_follow_up and "last_clarification_question" in state:
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
