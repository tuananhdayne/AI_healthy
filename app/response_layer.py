# app/response_layer.py

def need_more_info(user_input: str, intent: str):
    """
    Quyết định có cần hỏi thêm triệu chứng không.
    CHỈ trả True khi thực sự KHÔNG RÕ triệu chứng (rất mơ hồ).
    KHÔNG hỏi mặc định.
    """

    text = user_input.lower().strip()
    words = text.split()
    
    # 1) Nếu intent là "other" → không hỏi, để Gemini tự xử lý
    if intent == "other" or intent == "unknown":
        return False
    
    # 2) Nếu câu quá ngắn (<= 2 từ) VÀ không có từ khóa triệu chứng → có thể mơ hồ
    # Nhưng nếu có từ khóa triệu chứng thì vẫn OK
    if len(words) <= 2:
        # Kiểm tra xem có từ khóa triệu chứng cơ bản không
        symptom_keywords = ["đau", "sốt", "ho", "mệt", "buồn nôn", "chóng mặt", "khó thở", "lo", "căng thẳng"]
        has_symptom_keyword = any(kw in text for kw in symptom_keywords)
        if not has_symptom_keyword:
            return True  # Câu quá ngắn và không có từ khóa triệu chứng
    
    # 3) Từ khóa giúp xác định câu rõ ràng theo intent
    CLEAR_SIGNS = {
        "bao_dau_dau": ["trán", "thái dương", "sau gáy", "đau âm ỉ", "nhói", "2 ngày", "nhiều ngày", "đau đầu"],
        "bao_dau_bung": ["bên phải", "bên trái", "âm ỉ", "dữ dội", "quặn", "sau ăn", "trên rốn", "dưới rốn", "đau bụng"],
        "bao_sot": ["38", "39", "nhiệt độ", "ho", "rát", "lạnh run", "sốt"],
        "bao_ho": ["đờm", "khò khè", "khan", "nhiều ngày", "từng cơn", "ho"],
        "bao_met_moi": ["chóng mặt", "khó thở", "mệt kéo dài", "mệt", "mỏi"],
        "lo_lang_stress": ["khó ngủ", "căng thẳng", "áp lực", "lo nhiều", "lo lắng"],
        "tu_van_dinh_duong": ["ăn gì", "uống gì", "nên ăn", "dinh dưỡng", "thực phẩm"],
        "tu_van_tap_luyen": ["bài tập", "thể dục", "tập luyện", "vận động"],
    }

    # Intent có từ khóa rõ → không cần hỏi thêm
    if intent in CLEAR_SIGNS:
        for kw in CLEAR_SIGNS[intent]:
            if kw in text:
                return False  # Đã rõ ràng, không cần hỏi

    # 4) Nếu câu có độ dài hợp lý (>= 5 từ) → coi như đủ thông tin, không hỏi
    if len(words) >= 5:
        return False
    
    # 5) Chỉ hỏi khi câu rất ngắn (3-4 từ) VÀ không có từ khóa rõ ràng
    # Nhưng nếu có từ khóa triệu chứng cơ bản thì vẫn OK
    symptom_keywords = ["đau", "sốt", "ho", "mệt", "buồn nôn", "chóng mặt", "khó thở", "lo", "căng thẳng"]
    has_symptom_keyword = any(kw in text for kw in symptom_keywords)
    
    if has_symptom_keyword:
        return False  # Có từ khóa triệu chứng, đủ để trả lời
    
    # 6) Chỉ hỏi khi thực sự mơ hồ (câu ngắn và không có từ khóa)
    return True



def build_clarification_question(intent: str):
    """
    Hỏi thêm triệu chứng nếu thông tin chưa đủ rõ.
    """

    QUESTIONS = {
        "bao_dau_dau": "Bạn đang đau đầu ở vị trí nào (trán, thái dương, sau gáy)? Mức độ đau ra sao?",
        "bao_dau_bung": "Bạn đau bụng ở vị trí nào (trên rốn, dưới rốn, bên trái, bên phải)? Đau âm ỉ hay quặn từng cơn?",
        "bao_sot": "Bạn sốt khoảng bao nhiêu độ và xuất hiện từ khi nào?",
        "bao_ho": "Bạn ho khan hay ho có đờm? Tần suất ho như thế nào?",
        "bao_met": "Bạn mệt mỏi từ khi nào? Có kèm chóng mặt hoặc khó thở không?",
        "lo_lang_stress": "Bạn cảm thấy lo lắng trong tình huống nào? Có ảnh hưởng đến giấc ngủ không?",
        "tu_van_dinh_duong": "Bạn muốn tư vấn dinh dưỡng cho mục đích gì (tăng cân, giảm cân, ăn lành mạnh…)?",
        "tu_van_tap_luyen": "Bạn muốn tập luyện để cải thiện điều gì (sức khỏe tổng quát, giảm cân, tăng cơ…)?",
    }

    return QUESTIONS.get(intent, "Bạn có thể mô tả rõ hơn tình trạng của bạn không?")
