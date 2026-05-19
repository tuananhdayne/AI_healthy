# app/symptom_extractor.py

import re 

# Hàm trích xuất triệu chứng từ văn bản người dùng để phục vụ đánh giá rủi ro
def extract_symptoms(text: str):
    text = (text or "").lower()

    result = {
        "location": None,
        "duration": None,
        "intensity": None,
        "extra": [],
        "danger_signs": []
    }

    # Vị trí cơ thể (bao gồm cách nói trái/phải/trên/dưới)
    LOCATIONS = {
        "trán", "thái dương", "sau gáy", "đỉnh đầu",
        "bên trái", "bên phải", "trên rốn", "dưới rốn",
        "bụng trên", "bụng dưới", "hạ sườn", "thượng vị",
        "ngực", "lưng", "vai", "cổ", "hông", "gối"
    }
    for loc in LOCATIONS:
        if loc in text:
            result["location"] = loc
            break

    # Thời gian: bắt cả số + đơn vị (tiếng/giờ/ngày/tuần/tháng) và mốc "mấy ngày", "vài tuần"
    duration_match = re.search(r"((\d+|mấy|vài)\s*(tiếng|giờ|ngày|hôm|tuần|tháng))", text)
    if duration_match:
        result["duration"] = duration_match.group(0)

    # Mức độ đau/khó chịu
    INTENSITIES = ["âm ỉ", "nhói", "dữ dội", "quặn", "nhẹ", "vừa", "nặng", "chói", "ran rát"]
    for w in INTENSITIES:
        if w in text:
            result["intensity"] = w
            break

    # Triệu chứng phụ thường gặp
    EXTRA = [
        "buồn nôn", "nôn", "chóng mặt", "hoa mắt", "sốt", "ớn lạnh",
        "khó thở", "ho", "đờm", "tiêu chảy", "táo bón", "mất ngủ"
    ]
    for e in EXTRA:
        if e in text:
            result["extra"].append(e)

    # Dấu hiệu nguy hiểm (mở rộng thêm dấu hiệu thần kinh/hô hấp nặng)
    DANGER = [
        "khó thở", "ngất", "đau dữ dội", "mất ý thức", "đau ngực",
        "tê liệt", "co giật", "mờ mắt", "bất tỉnh", "không cử động được",
        "yếu liệt", "nói khó", "khó nói", "thở rít", "thở gấp"
    ]
    for d in DANGER:
        if d in text:
            result["danger_signs"].append(d)

    # Nếu có sốt, thử bắt nhiệt độ để enrich extra
    temp_match = re.search(r"(3[6-9]|4[0-2])\s*(độ|c)", text)
    if temp_match and "sốt" not in result["extra"]:
        result["extra"].append("sốt")

    return result
