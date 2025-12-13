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


# ============================
# INTENT CONTINUITY & CONTEXT GUARD
# ============================

import re


def get_intent_label(intent: str) -> str:
    """
    Map intent code sang label tiếng Việt dễ hiểu.
    """
    INTENT_LABELS = {
        "bao_dau_bung": "đau bụng",
        "bao_dau_dau": "đau đầu",
        "bao_ho": "ho",
        "bao_met_moi": "mệt mỏi",
        "bao_sot": "sốt",
        "lo_lang_stress": "lo lắng/stress",
        "tu_van_dinh_duong": "tư vấn dinh dưỡng",
        "tu_van_tap_luyen": "tư vấn tập luyện",
        "chao_hoi": "chào hỏi",
        "nhac_nho_uong_thuoc": "nhắc nhở uống thuốc",
        "other": "chủ đề khác",
        "unknown": "không xác định"
    }
    return INTENT_LABELS.get(intent, intent)


def get_intent_category(intent: str) -> str:
    """
    Phân loại intent thành: "symptom", "advisory", "no_rag"
    
    Returns:
        "symptom": Intent triệu chứng (an toàn cao, ngưỡng cao)
        "advisory": Intent tư vấn (ít rủi ro, ngưỡng thấp)
        "no_rag": Intent không dùng RAG (luôn Gemini)
    """
    # Intent triệu chứng (an toàn cao)
    SYMPTOM_INTENTS = {
        "bao_dau_dau",
        "bao_dau_bung",
        "bao_sot",
        "bao_ho",
        "bao_met_moi"
    }
    
    # Intent tư vấn (ít rủi ro)
    ADVISORY_INTENTS = {
        "tu_van_dinh_duong",
        "tu_van_tap_luyen"
    }
    
    # Intent không dùng RAG
    NO_RAG_INTENTS = {
        "other",
        "chao_hoi",
        "unknown",
        "lo_lang_stress",  # Có thể thêm vào đây nếu cần
        "nhac_nho_uong_thuoc"  # Có thể thêm vào đây nếu cần
    }
    
    if intent in SYMPTOM_INTENTS:
        return "symptom"
    elif intent in ADVISORY_INTENTS:
        return "advisory"
    elif intent in NO_RAG_INTENTS:
        return "no_rag"
    else:
        # Default: coi như no_rag để an toàn
        return "no_rag"


def get_rag_gate_thresholds(intent_category: str) -> tuple[float, float]:
    """
    Trả về ngưỡng RAG gate dựa trên loại intent.
    
    Returns:
        (strong_threshold, soft_threshold): 
        - strong_threshold: Ngưỡng cho STRONG RAG (>= ngưỡng này)
        - soft_threshold: Ngưỡng cho SOFT RAG (từ ngưỡng này đến strong_threshold)
        - < soft_threshold: NO RAG
    
    Logic:
        - symptom: (0.80, 0.70) - Ngưỡng cao vì an toàn
        - advisory: (0.75, 0.65) - Ngưỡng thấp hơn vì ít rủi ro
        - no_rag: (1.0, 1.0) - Luôn không dùng RAG
    """
    if intent_category == "symptom":
        return (0.80, 0.70)  # STRONG >= 0.80, SOFT >= 0.70
    elif intent_category == "advisory":
        return (0.75, 0.65)  # STRONG >= 0.75, SOFT >= 0.65
    else:  # no_rag
        return (1.0, 1.0)  # Luôn không dùng RAG


def is_follow_up(text: str) -> bool:
    """
    Nhận diện follow-up keywords (tiếp diễn, nói tiếp về chủ đề cũ).
    Match theo ranh giới từ để tránh substring.
    """
    text_lower = text.lower().strip()
    
    # Follow-up keywords với ranh giới từ
    follow_up_patterns = [
        r'\bvẫn\b', r'\bvẫn thế\b', r'\bvẫn như thế\b',
        r'\bnhư trước\b', r'\bnhư hôm qua\b', r'\bnhư lúc trước\b',
        r'\bcòn\b', r'\bcòn bị\b', r'\bcòn thấy\b',
        r'\bkèm\b', r'\bkèm theo\b', r'\bthêm\b',
        r'\bhôm nay\b', r'\bsau đó\b',
        r'\bđỡ hơn\b', r'\bđỡ rồi\b', r'\bnặng hơn\b', r'\btệ hơn\b',
        r'\btăng lên\b', r'\bgiảm đi\b', r'\bgiảm xuống\b'
    ]
    
    # Kiểm tra match theo pattern (ranh giới từ)
    for pattern in follow_up_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False


def is_topic_shift(text: str) -> bool:
    """
    Nhận diện đổi chủ đề rõ ràng.
    """
    text_lower = text.lower().strip()
    
    # Topic shift keywords
    topic_shift_patterns = [
        r'\bcho hỏi\b', r'\bcho mình hỏi\b', r'\bcho tôi hỏi\b',
        r'\bnhân tiện\b',
        r'\bđổi chủ đề\b', r'\bvấn đề khác\b', r'\bcâu hỏi khác\b',
        r'\bmuốn hỏi về\b', r'\bhỏi thêm về\b', r'\bxin tư vấn\b',
        r'\bchuyển sang\b', r'\bđổi sang\b',
        r'\btư vấn dinh dưỡng\b', r'\btư vấn tập luyện\b'
    ]
    
    # Kiểm tra match theo pattern
    for pattern in topic_shift_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Xử lý đặc biệt: "ngoài ra" chỉ là topic shift nếu đi kèm các cụm rõ
    if re.search(r'\bngoài ra\b', text_lower):
        # Phải có các cụm rõ như "cho hỏi/nhân tiện/câu hỏi khác..."
        clear_shift_with_ngoai_ra = [
            r'\bcho hỏi\b', r'\bcho mình hỏi\b',
            r'\bnhân tiện\b',
            r'\bcâu hỏi khác\b', r'\bvấn đề khác\b'
        ]
        for pattern in clear_shift_with_ngoai_ra:
            if re.search(pattern, text_lower):
                return True
        # Nếu chỉ có "ngoài ra" mà không có cụm rõ → không phải topic shift
        return False
    
    return False


def parse_switch_confirm(text: str) -> bool | None:
    """
    Parse câu trả lời xác nhận đổi chủ đề.
    
    Returns:
        True: Xác nhận chuyển sang chủ đề mới
        False: Giữ chủ đề cũ
        None: Không rõ → cần hỏi lại
    """
    text_lower = text.lower().strip()
    
    # Xác nhận chuyển (True)
    confirm_patterns = [
        r'\bchuyển\b', r'\bđổi\b', r'\bđổi sang\b', r'\bchuyển sang\b',
        r'\bđúng\b', r'\bđúng rồi\b', r'\bđúng vậy\b',
        r'\bcó\b', r'\bcó đúng\b', r'\bphải\b', r'\bphải rồi\b',
        r'\bchủ đề mới\b', r'\bchủ đề khác\b'
    ]
    
    # Từ chối chuyển (False)
    reject_patterns = [
        r'\bkhông\b', r'\bkhông đúng\b', r'\bkhông phải\b',
        r'\bvẫn\b', r'\bvẫn giữ\b', r'\bgiữ\b', r'\bgiữ nguyên\b',
        r'\btiếp tục\b', r'\btiếp\b', r'\bvề\b', r'\bvề chủ đề cũ\b',
        r'\bchủ đề cũ\b', r'\bchủ đề trước\b'
    ]
    
    # Kiểm tra confirm
    for pattern in confirm_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Kiểm tra reject
    for pattern in reject_patterns:
        if re.search(pattern, text_lower):
            return False
    
    # Không rõ
    return None