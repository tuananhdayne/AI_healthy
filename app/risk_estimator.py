# app/risk_estimator.py

def estimate_risk(symptoms):
    """
    Trả về:
    - "high" = cảnh báo ngay
    - "medium" = cẩn trọng
    - "low" = an toàn
    """

    danger = symptoms["danger_signs"]

    if len(danger) > 0:
        return "high"

    # Nếu không rõ thông tin nào
    if symptoms["location"] is None and symptoms["intensity"] is None:
        return "medium"

    return "low"
