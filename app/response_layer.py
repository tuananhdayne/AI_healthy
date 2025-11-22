# app/response_layer.py

def need_more_info(user_input: str, intent: str):
    """
    Quyết định có cần hỏi thêm triệu chứng không.
    Trả True = cần hỏi thêm.
    """

    text = user_input.lower().strip()

    # 1) Nếu câu quá ngắn → chắc chắn chưa rõ
    if len(text.split()) <= 4:
        return True

    # 2) Từ khóa giúp xác định câu rõ ràng theo intent
    CLEAR_SIGNS = {
        "bao_dau_dau": ["trán", "thái dương", "sau gáy", "đau âm ỉ", "nhói", "2 ngày", "nhiều ngày"],
        "bao_dau_bung": ["bên phải", "bên trái", "âm ỉ", "dữ dội", "quặn", "sau ăn", "trên rốn", "dưới rốn"],
        "bao_sot": ["38", "39", "nhiệt độ", "ho", "rát", "lạnh run"],
        "bao_ho": ["đờm", "khò khè", "khan", "nhiều ngày", "từng cơn"],
        "bao_met": ["chóng mặt", "khó thở", "mệt kéo dài"],
        "lo_lang_stress": ["khó ngủ", "căng thẳng", "áp lực", "lo nhiều"],
        "tu_van_dinh_duong": ["ăn gì", "uống gì", "nên ăn"],
        "tu_van_tap_luyen": ["bài tập", "thể dục", "tập luyện"],
    }

    # Intent có từ khóa rõ → không cần hỏi thêm
    if intent in CLEAR_SIGNS:
        for kw in CLEAR_SIGNS[intent]:
            if kw in text:
                return False

    # Nếu không khớp → cần hỏi thêm
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
