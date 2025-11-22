# app/symptom_extractor.py

import re

def extract_symptoms(text: str):
    text = text.lower()

    result = {
        "location": None,
        "duration": None,
        "intensity": None,
        "extra": [],
        "danger_signs": []
    }

    # Vị trí cơ thể
    LOCATIONS = {
        "trán", "thái dương", "sau gáy", "đỉnh đầu",
        "bên trái", "bên phải", "trên rốn", "dưới rốn",
        "bụng trên", "bụng dưới", "ngực", "lưng"
    }

    for loc in LOCATIONS:
        if loc in text:
            result["location"] = loc
            break

    # Thời gian
    duration_match = re.search(r"(\d+)\s*(ngày|hôm|tiếng|tuần)", text)
    if duration_match:
        result["duration"] = duration_match.group(0)

    # Mức độ
    if any(w in text for w in ["âm ỉ", "nhói", "dữ dội", "quặn"]):
        for w in ["âm ỉ", "nhói", "dữ dội", "quặn"]:
            if w in text:
                result["intensity"] = w
                break

    # Triệu chứng phụ
    EXTRA = ["buồn nôn", "nôn", "chóng mặt", "sốt", "khó thở", "ho", "ngất"]
    for e in EXTRA:
        if e in text:
            result["extra"].append(e)

    # Dấu hiệu nguy hiểm
    DANGER = ["khó thở", "ngất", "đau dữ dội", "mất ý thức", "đau ngực"]
    for d in DANGER:
        if d in text:
            result["danger_signs"].append(d)

    return result
