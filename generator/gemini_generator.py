"""
Generator sử dụng Google Gemini API thay vì Gemma local
Nhanh hơn và không cần load model nặng
"""

import os
import google.generativeai as genai
from typing import Optional

# Hỗ trợ đọc .env nếu đã cài python-dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    try:
        load_dotenv()
    except Exception as e:
        print(f"⚠️ Không thể load file .env: {e}. Hệ thống sẽ tiếp tục dùng biến môi trường của OS.")

# Model sẽ được load lazy trong _get_model()
_gemini_model = None
_model_initialized = False
_client_configured = False


def _get_api_key() -> str:
    """Lấy API key từ biến môi trường theo thứ tự: GEMINI_API_KEY -> GOOGLE_API_KEY."""
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key_value = os.environ.get(key_name)
        if key_value and key_value.strip():
            return key_value.strip()
    return ""


def _ensure_client_configured():
    """Cấu hình Gemini client một cách an toàn."""
    global _client_configured
    if _client_configured:
        return

    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "Thiếu API key Gemini. Vui lòng set GEMINI_API_KEY (hoặc GOOGLE_API_KEY) trong biến môi trường/.env."
        )

    genai.configure(api_key=api_key)
    _client_configured = True


def _get_model():
    """Lazy load model khi cần"""
    global _gemini_model, _model_initialized
    
    if _model_initialized and _gemini_model is not None:
        return _gemini_model
    
    try:
        _ensure_client_configured()
        # Sử dụng gemini-2.0-flash (nhanh, quota tốt: 15 RPM, 1M TPM)
        # Có thể đổi sang:
        # - gemini-2.5-pro: Chất lượng cao nhất nhưng chậm hơn (2 RPM, 125K TPM)
        # - gemini-2.5-flash: Cân bằng tốt (15 RPM, 250K TPM)
        # - gemini-2.0-flash-lite: Nhẹ nhất (30 RPM, 1M TPM)
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
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
        
        # Tạo generation config để tối ưu cho chatbot y tế - chất lượng cao nhất
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,  # Giảm xuống để chính xác và nhất quán hơn (0.7 = cân bằng tốt) ít nói linh tinh
            top_p=0.9,        # Tập trung vào các tokens có xác suất cao hơn  độ an toàn khi chọn từ
            top_k=40,         # Chọn từ top K tokens  40 từ có xác suất cao nhất
            max_output_tokens=2048 ,  #  số từ , dấu tối đa trong câu trả lời
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

# hàm tạo câu trả lời y tế với prompt tinh chỉnh
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
        system_instruction = """Bạn là trợ lý y tế chuyên nghiệp, thông minh và đồng cảm với kiến thức y tế sâu rộng.

PHONG CÁCH TRẢ LỜI (Chất lượng cao, giống ChatGPT):
- Trả lời TỰ NHIÊN, MƯỢT MÀ, DỄ HIỂU như đang trò chuyện với bạn
- Trả lời CHI TIẾT và ĐẦY ĐỦ (5-10 câu) để giải thích rõ ràng, không bỏ sót thông tin quan trọng
- Sử dụng ngôn ngữ thân thiện, đồng cảm nhưng vẫn chuyên nghiệp và chính xác
- Đưa ra nhiều góc nhìn, giải thích nguyên nhân, cách xử lý, và lời khuyên cụ thể
- Trả lời có cấu trúc rõ ràng, dễ đọc (có thể dùng bullet points hoặc phân đoạn nếu phù hợp)
- QUAN TRỌNG: KHÔNG dùng markdown formatting (không dùng **, *, #, hoặc các ký hiệu markdown khác)
- Trả lời bằng văn bản thuần túy, tự nhiên, như đang nói chuyện trực tiếp

🔒 NGUYÊN TẮC CỐT LÕI - TÁCH BẠCH THÔNG TIN:

1. USER FACTS (Thông tin từ người dùng):
   - CHỈ sử dụng những gì người dùng NÓI TRỰC TIẾP trong câu hỏi/câu trả lời
   - KHÔNG tự suy ra, KHÔNG giả định, KHÔNG thêm triệu chứng mà người dùng chưa nói
   - Nếu người dùng chỉ nói "tôi đau ở rốn" → CHỈ biết họ đau ở rốn, KHÔNG suy ra đầy hơi, chướng bụng, ăn cay...

2. RAG KNOWLEDGE (Kiến thức tham khảo):
   - Đây là KIẾN THỨC Y TẾ THAM KHẢO từ database, KHÔNG phải bệnh sử của người dùng
   - Dùng để GIẢI THÍCH, HƯỚNG DẪN, nhưng KHÔNG GÁN cho người dùng
   - Ví dụ đúng: "Đau bụng ở vùng rốn thường có thể liên quan đến các vấn đề tiêu hóa. Một số nguyên nhân thường gặp bao gồm..."
   - Ví dụ SAI: "Dựa trên những triệu chứng bạn đã chia sẻ như đầy hơi, chướng bụng..." (nếu user chưa nói)

3. TUYỆT ĐỐI KHÔNG:
   - ❌ Nói "Dựa trên những triệu chứng bạn đã chia sẻ như..." khi triệu chứng đó KHÔNG có trong user input
   - ❌ Nói "Có thể thấy bạn đang gặp..." về triệu chứng mà user chưa nói
   - ❌ Tự suy ra nguyên nhân cụ thể (ăn cay, căng thẳng...) nếu user chưa nói
   - ❌ Gán các triệu chứng từ RAG knowledge cho user

4. QUY TẮC TRẢ LỜI:
   - Bắt đầu bằng việc xác nhận những gì người dùng NÓI TRỰC TIẾP
   - Sau đó sử dụng RAG knowledge để GIẢI THÍCH các khả năng, nguyên nhân thường gặp (dưới dạng kiến thức chung)
   - Đưa ra lời khuyên dựa trên những gì người dùng đã nói
   - KHÔNG chẩn đoán bệnh cụ thể hoặc kê đơn thuốc
   - Kết thúc bằng lời khuyên đi khám bác sĩ nếu triệu chứng nghiêm trọng hoặc kéo dài
   - Nếu là câu trả lời tiếp theo, KHÔNG chào hỏi lại, trả lời trực tiếp và liền mạch"""
    else:
        # Mức thấp: Dùng Gemini tự do hơn (giống GPT)
        system_instruction = """Bạn là trợ lý y tế chuyên nghiệp, thông minh và đồng cảm với kiến thức y tế sâu rộng và khả năng giao tiếp tự nhiên.

PHONG CÁCH TRẢ LỜI (Chất lượng cao):
- Trả lời TỰ NHIÊN, MƯỢT MÀ, DỄ HIỂU như đang trò chuyện với bạn
- Phong cách chuyên gia nhưng nhẹ nhàng, trung tính và dễ tiếp cận
- Trả lời CHI TIẾT và ĐẦY ĐỦ (5-10 câu) để giải thích rõ ràng, không bỏ sót thông tin quan trọng
- Sử dụng ngôn ngữ thân thiện, đồng cảm nhưng vẫn chuyên nghiệp và chính xác
- Đưa ra giải thích nguyên nhân, cách xử lý, và lời khuyên cụ thể khi phù hợp
- Trả lời có cấu trúc rõ ràng, dễ đọc (có thể dùng bullet points hoặc phân đoạn nếu phù hợp)
- Nhớ được ngữ cảnh cuộc trò chuyện và trả lời liền mạch, không lặp lại thông tin
- QUAN TRỌNG: KHÔNG dùng markdown formatting (không dùng **, *, #, hoặc các ký hiệu markdown khác)
- Trả lời bằng văn bản thuần túy, tự nhiên, như đang nói chuyện trực tiếp

QUY TẮC QUAN TRỌNG:
1. Cung cấp thông tin y tế CHÍNH XÁC, CHI TIẾT dựa trên kiến thức y tế chung
2. Bạn KHÔNG được suy đoán bệnh lý hay kết luận chẩn đoán
3. KHÔNG được gợi ý nguyên nhân y tế khi người dùng không thật sự mô tả triệu chứng rõ ràng
4. Nếu người dùng nói câu mơ hồ ("tôi hơi khó chịu", "tôi không ổn") → Yêu cầu họ mô tả rõ hơn thay vì tự đoán bệnh
5. Nếu người dùng chỉ nói chuyện bình thường (thời tiết, xã giao, chat vu vơ) → Trả lời tự nhiên và thân thiện, KHÔNG đưa kiến thức y tế
6. CHỈ hỏi thêm khi KHÔNG RÕ triệu chứng, KHÔNG mặc định hỏi
7. Khi người dùng hỏi cụ thể, cung cấp thông tin y tế đầy đủ, giải thích rõ ràng về nguyên nhân, triệu chứng, cách xử lý
8. KHÔNG chẩn đoán bệnh cụ thể hoặc kê đơn thuốc
9. Luôn khuyến khích người dùng đi khám bác sĩ khi cần thiết hoặc triệu chứng nghiêm trọng
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
    
    # Thêm thông tin y tế (TÁCH BẠCH với user input)
    if use_rag_priority:
        prompt_parts.append("=" * 60)
        prompt_parts.append("KIẾN THỨC Y TẾ THAM KHẢO (RAG KNOWLEDGE):")
        prompt_parts.append("=" * 60)
        prompt_parts.append("⚠️ QUAN TRỌNG: Đây là KIẾN THỨC Y TẾ THAM KHẢO từ database, KHÔNG phải bệnh sử của người dùng.")
        prompt_parts.append("Chỉ dùng để GIẢI THÍCH và HƯỚNG DẪN. KHÔNG được gán các triệu chứng/nhận định trong kiến thức này cho người dùng.")
        prompt_parts.append("=" * 60)
        prompt_parts.append(context)
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
    else:
        if context and context.strip() and context != "Không tìm thấy thông tin cụ thể trong database.":
            prompt_parts.append("=" * 60)
            prompt_parts.append("KIẾN THỨC Y TẾ THAM KHẢO (RAG KNOWLEDGE):")
            prompt_parts.append("=" * 60)
            prompt_parts.append("⚠️ QUAN TRỌNG: Đây là KIẾN THỨC Y TẾ THAM KHẢO, KHÔNG phải bệnh sử của người dùng.")
            prompt_parts.append("=" * 60)
            prompt_parts.append(context)
            prompt_parts.append("=" * 60)
            prompt_parts.append("")
        else:
            prompt_parts.append("Không tìm thấy thông tin cụ thể trong database. Hãy trả lời dựa trên kiến thức y tế chung.\n")
    
    # Thêm câu hỏi hiện tại (USER FACTS - chỉ những gì user nói trực tiếp)
    prompt_parts.append("=" * 60)
    if is_follow_up:
        prompt_parts.append("THÔNG TIN TỪ NGƯỜI DÙNG (USER FACTS - CHỈ NHỮNG GÌ HỌ NÓI TRỰC TIẾP):")
        prompt_parts.append("=" * 60)
        prompt_parts.append("⚠️ QUAN TRỌNG: CHỈ sử dụng những gì người dùng nói trong phần này. KHÔNG tự suy ra thêm.")
        prompt_parts.append("=" * 60)
        prompt_parts.append(user_question)
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
        prompt_parts.append("⚠️ Đây là câu hỏi tiếp theo trong cuộc trò chuyện. Hãy trả lời TRỰC TIẾP và LIỀN MẠCH với ngữ cảnh trước đó. KHÔNG chào hỏi lại, KHÔNG lặp lại câu hỏi đã hỏi, KHÔNG giới thiệu lại bản thân.")
        prompt_parts.append("")
    else:
        prompt_parts.append("THÔNG TIN TỪ NGƯỜI DÙNG (USER FACTS - CHỈ NHỮNG GÌ HỌ NÓI TRỰC TIẾP):")
        prompt_parts.append("=" * 60)
        prompt_parts.append("⚠️ QUAN TRỌNG: CHỈ sử dụng những gì người dùng nói trong phần này. KHÔNG tự suy ra thêm triệu chứng hoặc nguyên nhân.")
        prompt_parts.append("=" * 60)
        prompt_parts.append(user_question)
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
    
    # Thêm hướng dẫn trả lời (tự nhiên, chi tiết, TUYỆT ĐỐI không gán RAG cho user)
    if use_rag_priority:
        prompt_parts.append("""Hãy trả lời một cách TỰ NHIÊN, CHÍNH XÁC và CHI TIẾT (Chất lượng cao):

🔒 NGUYÊN TẮC BẮT BUỘC:

1. USER FACTS - CHỈ sử dụng những gì người dùng NÓI TRỰC TIẾP:
   - Bắt đầu bằng việc xác nhận triệu chứng/vấn đề mà người dùng đã nói
   - Ví dụ: Nếu người dùng nói "tôi đau ở rốn" → Chỉ nói về đau ở rốn, KHÔNG thêm đầy hơi, chướng bụng, ăn cay...

2. RAG KNOWLEDGE - Dùng để GIẢI THÍCH, KHÔNG GÁN:
   - Sử dụng kiến thức y tế tham khảo thêm nếu kiến thức được cung cấp phù hợp với câu hỏi hoặc triệu chứng của người dùng 
   - Dùng ngôn ngữ chung: "Đau bụng ở vùng rốn thường có thể liên quan đến...", "Một số nguyên nhân thường gặp bao gồm..."
   - TUYỆT ĐỐI KHÔNG nói: "Dựa trên những triệu chứng bạn đã chia sẻ như..." khi triệu chứng đó KHÔNG có trong user input
   - TUYỆT ĐỐI KHÔNG nói: "Có thể thấy bạn đang gặp..." về triệu chứng mà user chưa nói

3. CẤU TRÚC TRẢ LỜI:
   - Xác nhận những gì người dùng đã nói (ngắn gọn)
   - Giải thích các khả năng/nguyên nhân thường gặp (dùng kiến thức tham khảo, ngôn ngữ chung)
   - Đưa ra lời khuyên dựa trên những gì người dùng đã nói
   - Trả lời ĐẦY ĐỦ và CHI TIẾT (5-10 câu) để giải thích rõ ràng

4. TUYỆT ĐỐI KHÔNG:
   - ❌ Tự suy ra triệu chứng mà người dùng chưa nói
   - ❌ Gán nguyên nhân cụ thể (ăn cay, căng thẳng...) nếu user chưa nói
   - ❌ Dùng ngôn ngữ như thể RAG knowledge là bệnh sử của user
   - ❌ Chẩn đoán hay kê thuốc
   - ❌ Dùng markdown formatting (**, *, #)
   - ❌ Thêm thông tin không liên quan

Trả lời:""")
    else:
        prompt_parts.append("""Hãy trả lời một cách TỰ NHIÊN, CHÍNH XÁC và CHI TIẾT (Chất lượng cao):
- Trả lời dựa trên kiến thức y tế chung, CHI TIẾT và ĐẦY ĐỦ (5-10 câu)
- Giải thích rõ ràng về nguyên nhân, triệu chứng, cách xử lý, và lời khuyên khi phù hợp
- CHỈ trả lời những gì liên quan trực tiếp đến câu hỏi của người dùng, nhưng có thể giải thích thêm nếu hữu ích
- KHÔNG thêm thông tin không liên quan hoặc không được hỏi
- KHÔNG tự động đề xuất các chủ đề khác nếu người dùng không hỏi
- QUAN TRỌNG: Nếu câu hỏi của người dùng MƠ HỒ hoặc KHÔNG RÕ RÀNG về triệu chứng → CHỈ KHI ĐÓ mới hỏi thêm để làm rõ. KHÔNG mặc định hỏi.
- Nếu người dùng chỉ nói chuyện bình thường (không phải về y tế) → Trả lời tự nhiên, thân thiện, KHÔNG đưa kiến thức y tế
- Nếu người dùng mô tả triệu chứng rõ ràng → Trả lời dựa trên kiến thức y tế, giải thích chi tiết, KHÔNG suy đoán bệnh
- Dễ hiểu, thân thiện, như đang trò chuyện với chuyên gia y tế
- Có thể dùng bullet points hoặc phân đoạn nếu phù hợp để dễ đọc
- QUAN TRỌNG: KHÔNG dùng markdown formatting (KHÔNG dùng **, *, #, hoặc các ký hiệu markdown)
- Trả lời bằng văn bản thuần túy, tự nhiên, không dùng dấu ** để làm đậm chữ
- KHÔNG chẩn đoán hay kê thuốc
- KHÔNG suy đoán bệnh lý hay kết luận triệu chứng
- Kết thúc bằng lời khuyên đi khám bác sĩ nếu triệu chứng nghiêm trọng hoặc kéo dài
- Nếu là câu trả lời tiếp theo, trả lời trực tiếp, không chào hỏi lại

Trả lời:""")
    
    prompt = "\n".join(prompt_parts)
    # dùng prompt để gọi Gemini trả về câu trả lời
    return generate_answer(prompt, system_instruction=system_instruction)

# Hàm tạo câu trả lời chào hỏi tự nhiên
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
