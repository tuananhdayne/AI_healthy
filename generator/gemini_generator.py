"""
Generator sử dụng Google Gemini API thay vì Gemma local
Nhanh hơn và không cần load model nặng
"""

import os
import google.generativeai as genai
from typing import Optional

# API Key - có thể set qua biến môi trường GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAmRD3y8JJKEz1l79hnrmqYlu6haMKPwjk")

# Khởi tạo Gemini client
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Model sẽ được load lazy trong _get_model()
    _gemini_model = None
    _model_initialized = False
except Exception as e:
    print(f"⚠️ Lỗi khi cấu hình Gemini API: {e}")
    _model_initialized = False


def _get_model():
    """Lazy load model khi cần"""
    global _gemini_model, _model_initialized
    
    if _model_initialized and _gemini_model is not None:
        return _gemini_model
    
    try:
        # Sử dụng gemini-2.0-flash (nhanh, quota tốt: 15 RPM, 1M TPM)
        # Có thể đổi sang:
        # - gemini-2.5-pro: Chất lượng cao nhất nhưng chậm hơn (2 RPM, 125K TPM)
        # - gemini-2.5-flash: Cân bằng tốt (15 RPM, 250K TPM)
        # - gemini-2.0-flash-lite: Nhẹ nhất (30 RPM, 1M TPM)
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        _gemini_model = genai.GenerativeModel(model_name)
        _model_initialized = True
        print(f"✅ Gemini API đã sẵn sàng! (Model: {model_name})")
        return _gemini_model
    except Exception as e:
        print(f"❌ Lỗi khi khởi tạo Gemini model: {e}")
        # Thử fallback sang model khác
        try:
            print("🔄 Đang thử model gemini-2.5-flash...")
            _gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            _model_initialized = True
            print("✅ Gemini API đã sẵn sàng! (Model: gemini-2.5-flash)")
            return _gemini_model
        except Exception as e2:
            print(f"❌ Lỗi khi thử model fallback: {e2}")
            raise


def generate_answer(prompt: str, system_instruction: Optional[str] = None) -> str:
    """
    Sinh câu trả lời từ Gemini API
    
    Args:
        prompt: Câu hỏi hoặc prompt cần xử lý
        system_instruction: Hướng dẫn hệ thống (optional)
    
    Returns:
        Câu trả lời từ Gemini
    """
    try:
        model = _get_model()
        
        # Tạo generation config để tối ưu cho chatbot y tế (giống GPT)
        generation_config = genai.types.GenerationConfig(
            temperature=0.8,  # Tăng một chút để tự nhiên hơn
            top_p=0.95,       # Đa dạng câu trả lời hơn
            top_k=40,         # Chọn từ top K tokens
            max_output_tokens=2048,  # Tăng độ dài để trả lời chi tiết hơn (giống GPT)
        )
        
        # Nếu có system instruction, thêm vào prompt
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"
        
        # Gọi API
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        # Lấy text từ response (xử lý nhiều format)
        if hasattr(response, 'text'):
            answer = response.text.strip()
        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
            if hasattr(response.candidates[0], 'content'):
                answer = response.candidates[0].content.parts[0].text.strip()
            else:
                answer = str(response.candidates[0]).strip()
        else:
            answer = str(response).strip()
        
        # Xử lý trường hợp response rỗng
        if not answer:
            return "Xin lỗi, tôi không thể tạo câu trả lời. Vui lòng thử lại."
        
        # Loại bỏ markdown formatting để câu trả lời tự nhiên hơn
        import re
        # Loại bỏ ** (bold markdown) - giữ lại nội dung bên trong
        answer = re.sub(r'\*\*(.*?)\*\*', r'\1', answer)
        # Loại bỏ các dấu ** còn sót lại (nếu có)
        answer = answer.replace('**', '')
        # Loại bỏ # (heading markdown)
        answer = re.sub(r'^#+\s*', '', answer, flags=re.MULTILINE)
        # Giữ lại bullet points (dấu * ở đầu dòng) vì đó là format hợp lệ
        
        return answer
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Lỗi khi gọi Gemini API: {error_msg}")
        
        # Xử lý các lỗi thường gặp
        if "API_KEY" in error_msg or "authentication" in error_msg.lower():
            return "⚠️ Lỗi xác thực API. Vui lòng kiểm tra API key."
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return "⚠️ Đã vượt quá giới hạn API. Vui lòng thử lại sau."
        else:
            return f"⚠️ Lỗi khi xử lý: {error_msg[:100]}"


def generate_medical_answer(
    context: str, 
    user_question: str, 
    intent: Optional[str] = None,
    conversation_history: Optional[str] = None,
    is_follow_up: bool = False,
    use_rag_priority: bool = False
) -> str:
    """
    Tạo câu trả lời y tế tối ưu với prompt được tinh chỉnh
    
    Args:
        context: Ngữ cảnh từ RAG retrieval
        user_question: Câu hỏi của người dùng
        intent: Intent đã phân loại (optional)
        conversation_history: Lịch sử cuộc trò chuyện trước đó (optional)
        is_follow_up: Có phải câu trả lời tiếp theo không (optional)
        use_rag_priority: Nếu True, ưu tiên sử dụng thông tin từ RAG (mức cao)
    
    Returns:
        Câu trả lời y tế an toàn và chính xác
    """
    # System instruction cho chatbot y tế (giống GPT - tự nhiên, chi tiết, hữu ích)
    if use_rag_priority:
        # Mức cao: Ưu tiên RAG data
        system_instruction = """Bạn là trợ lý y tế chuyên nghiệp, thông minh và đồng cảm. Tôi đã tìm thấy thông tin chính xác trong database y tế.

PHONG CÁCH TRẢ LỜI (giống ChatGPT):
- Trả lời TỰ NHIÊN, MƯỢT MÀ, DỄ HIỂU như đang trò chuyện với bạn
- Có thể trả lời CHI TIẾT (3-8 câu) khi cần thiết để giải thích rõ ràng
- Sử dụng ngôn ngữ thân thiện, đồng cảm nhưng vẫn chuyên nghiệp
- Có thể đưa ra nhiều góc nhìn hoặc giải thích thêm nếu hữu ích
- Trả lời một cách có cấu trúc, dễ đọc (có thể dùng bullet points nếu phù hợp)
- QUAN TRỌNG: KHÔNG dùng markdown formatting (không dùng **, *, #, hoặc các ký hiệu markdown khác)
- Trả lời bằng văn bản thuần túy, tự nhiên, như đang nói chuyện trực tiếp

QUY TẮC:
1. TRẢ LỜI CHỦ YẾU DỰA TRÊN THÔNG TIN ĐÃ CUNG CẤP từ database
2. Ưu tiên sử dụng thông tin từ database, có thể bổ sung kiến thức chung nếu cần
3. KHÔNG chẩn đoán bệnh cụ thể hoặc kê đơn thuốc
4. Nếu là câu trả lời tiếp theo, KHÔNG chào hỏi lại, trả lời trực tiếp và liền mạch
5. Luôn kết thúc bằng lời khuyên đi khám bác sĩ nếu triệu chứng nghiêm trọng"""
    else:
        # Mức thấp: Dùng Gemini tự do hơn (giống GPT)
        system_instruction = """Bạn là trợ lý y tế chuyên nghiệp, thông minh và đồng cảm. Bạn có kiến thức y tế rộng và khả năng giao tiếp tự nhiên.

PHONG CÁCH TRẢ LỜI:
- Trả lời TỰ NHIÊN, MƯỢT MÀ, DỄ HIỂU như đang trò chuyện với bạn
- Phong cách chuyên gia nhưng nhẹ nhàng và trung tính
- Có thể trả lời CHI TIẾT (3-8 câu) khi cần thiết để giải thích rõ ràng
- Sử dụng ngôn ngữ thân thiện, đồng cảm nhưng vẫn chuyên nghiệp
- Trả lời một cách có cấu trúc, dễ đọc (có thể dùng bullet points nếu phù hợp)
- Nhớ được ngữ cảnh cuộc trò chuyện và trả lời liền mạch
- QUAN TRỌNG: KHÔNG dùng markdown formatting (không dùng **, *, #, hoặc các ký hiệu markdown khác)
- Trả lời bằng văn bản thuần túy, tự nhiên, như đang nói chuyện trực tiếp

QUY TẮC QUAN TRỌNG:
1. Bạn KHÔNG được suy đoán bệnh lý
2. KHÔNG được kết luận triệu chứng
3. KHÔNG được gợi ý nguyên nhân y tế khi người dùng không thật sự mô tả triệu chứng rõ ràng
4. Nếu người dùng nói câu mơ hồ ("tôi hơi khó chịu", "tôi không ổn") → Yêu cầu họ mô tả rõ hơn thay vì tự đoán bệnh
5. Nếu người dùng chỉ nói chuyện bình thường (thời tiết, xã giao, chat vu vơ) → Trả lời tự nhiên và thân thiện, KHÔNG đưa kiến thức y tế
6. CHỈ hỏi thêm khi KHÔNG RÕ triệu chứng, KHÔNG mặc định hỏi
7. Cung cấp thông tin y tế dựa trên kiến thức chung khi người dùng hỏi cụ thể
8. KHÔNG chẩn đoán bệnh cụ thể hoặc kê đơn thuốc
9. Luôn khuyến khích người dùng đi khám bác sĩ khi cần thiết
10. QUAN TRỌNG: Nếu đây là câu trả lời tiếp theo trong cuộc trò chuyện, KHÔNG chào hỏi lại, trả lời trực tiếp và liền mạch với ngữ cảnh trước đó"""
    
    # Xây dựng prompt với ngữ cảnh
    prompt_parts = []
    
    # Thêm lịch sử cuộc trò chuyện nếu có (format rõ ràng để Gemini hiểu ngữ cảnh)
    if conversation_history:
        prompt_parts.append("=" * 60)
        prompt_parts.append("LỊCH SỬ CUỘC TRÒ CHUYỆN TRƯỚC ĐÓ:")
        prompt_parts.append("=" * 60)
        prompt_parts.append(conversation_history)
        prompt_parts.append("=" * 60)
        prompt_parts.append("")  # Dòng trống để phân tách
    
    # Thêm thông tin y tế
    if use_rag_priority:
        prompt_parts.append(f"THÔNG TIN Y TẾ TỪ DATABASE (ƯU TIÊN SỬ DỤNG):\n\n{context}\n")
    else:
        if context and context.strip() and context != "Không tìm thấy thông tin cụ thể trong database.":
            prompt_parts.append(f"Thông tin y tế tham khảo:\n\n{context}\n")
        else:
            prompt_parts.append("Không tìm thấy thông tin cụ thể trong database. Hãy trả lời dựa trên kiến thức y tế chung.\n")
    
    # Thêm câu hỏi hiện tại
    if is_follow_up:
        prompt_parts.append(f"👉 CÂU HỎI/THÔNG TIN MỚI CỦA NGƯỜI DÙNG:")
        prompt_parts.append(f"{user_question}\n")
        prompt_parts.append("⚠️ QUAN TRỌNG: Đây là câu hỏi tiếp theo trong cuộc trò chuyện. Hãy trả lời TRỰC TIẾP và LIỀN MẠCH với ngữ cảnh trước đó. KHÔNG chào hỏi lại, KHÔNG lặp lại câu hỏi đã hỏi, KHÔNG giới thiệu lại bản thân.")
    else:
        prompt_parts.append(f"👉 CÂU HỎI CỦA NGƯỜI DÙNG:")
        prompt_parts.append(f"{user_question}\n")
    
    # Thêm hướng dẫn trả lời (giống GPT - tự nhiên, chi tiết, KHÔNG trả lời thừa)
    if use_rag_priority:
        prompt_parts.append("""Hãy trả lời một cách TỰ NHIÊN và CHÍNH XÁC (giống ChatGPT):
- Trả lời dựa CHỦ YẾU trên thông tin từ database đã cung cấp
- CHỈ trả lời những gì liên quan trực tiếp đến câu hỏi của người dùng
- KHÔNG thêm thông tin không liên quan hoặc không được hỏi
- KHÔNG tự động đề xuất các chủ đề khác (như tập luyện, giảm cân) nếu người dùng không hỏi
- Có thể giải thích thêm nếu hữu ích, nhưng phải liên quan đến câu hỏi
- Trả lời đủ dài để giải thích rõ ràng (3-6 câu tùy độ phức tạp), KHÔNG dài dòng
- Dễ hiểu, thân thiện, như đang trò chuyện
- Có thể dùng bullet points hoặc phân đoạn nếu phù hợp
- QUAN TRỌNG: KHÔNG dùng markdown formatting (KHÔNG dùng **, *, #, hoặc các ký hiệu markdown)
- Trả lời bằng văn bản thuần túy, tự nhiên, không dùng dấu ** để làm đậm chữ
- Không chẩn đoán hay kê thuốc
- Nếu là câu trả lời tiếp theo, trả lời trực tiếp, không chào hỏi lại

Trả lời:""")
    else:
        prompt_parts.append("""Hãy trả lời một cách TỰ NHIÊN và CHÍNH XÁC:
- Trả lời dựa trên kiến thức y tế chung
- CHỈ trả lời những gì liên quan trực tiếp đến câu hỏi của người dùng
- KHÔNG thêm thông tin không liên quan hoặc không được hỏi
- KHÔNG tự động đề xuất các chủ đề khác nếu người dùng không hỏi
- QUAN TRỌNG: Nếu câu hỏi của người dùng MƠ HỒ hoặc KHÔNG RÕ RÀNG về triệu chứng → CHỈ KHI ĐÓ mới hỏi thêm để làm rõ. KHÔNG mặc định hỏi.
- Nếu người dùng chỉ nói chuyện bình thường (không phải về y tế) → Trả lời tự nhiên, thân thiện, KHÔNG đưa kiến thức y tế
- Nếu người dùng mô tả triệu chứng rõ ràng → Trả lời dựa trên kiến thức y tế, KHÔNG suy đoán bệnh
- Trả lời đủ dài để giải thích rõ ràng (3-6 câu tùy độ phức tạp), KHÔNG dài dòng
- Dễ hiểu, thân thiện, như đang trò chuyện
- Có thể dùng bullet points hoặc phân đoạn nếu phù hợp
- QUAN TRỌNG: KHÔNG dùng markdown formatting (KHÔNG dùng **, *, #, hoặc các ký hiệu markdown)
- Trả lời bằng văn bản thuần túy, tự nhiên, không dùng dấu ** để làm đậm chữ
- KHÔNG chẩn đoán hay kê thuốc
- KHÔNG suy đoán bệnh lý hay kết luận triệu chứng
- Kết thúc bằng lời khuyên đi khám bác sĩ nếu triệu chứng nghiêm trọng
- Nếu là câu trả lời tiếp theo, trả lời trực tiếp, không chào hỏi lại

Trả lời:""")
    
    prompt = "\n".join(prompt_parts)
    
    return generate_answer(prompt, system_instruction=system_instruction)


def generate_greeting(user_greeting: str) -> str:
    """
    Tạo câu trả lời chào hỏi tự nhiên
    """
    prompt = f"""Người dùng chào hỏi: "{user_greeting}"

Hãy trả lời chào hỏi một cách thân thiện, ngắn gọn (1-2 câu) bằng tiếng Việt.
Giới thiệu bạn là trợ lý y tế và sẵn sàng hỗ trợ.

Trả lời:"""
    
    system_instruction = "Bạn là trợ lý y tế thân thiện, chuyên nghiệp. Trả lời ngắn gọn, tự nhiên."
    
    return generate_answer(prompt, system_instruction=system_instruction)

