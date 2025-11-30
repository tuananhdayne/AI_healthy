from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# ==============================
# ĐƯỜNG DẪN MODEL INTENT
# ==============================

intent_model_path = r"D:\CHAT BOT TTCS\model\phobert_intent_model_v5"

print("🔄 Loading PhoBERT Intent Model...")
tokenizer = AutoTokenizer.from_pretrained(intent_model_path, use_fast=False)
model = AutoModelForSequenceClassification.from_pretrained(intent_model_path)

# ==============================
# INTENT MAPPING
# ==============================

id2label = {
    0: "bao_dau_bung",
    1: "bao_dau_dau",
    2: "bao_ho",
    3: "bao_met",
    4: "bao_sot",
    5: "chao_hoi",
    6: "lo_lang_stress",
    7: "nhac_nho_uong_thuoc",
    8: "tu_van_dinh_duong",
    9: "tu_van_tap_luyen"
}

intent_to_file = {
    "bao_dau_bung": "bao_dau_bung.txt",
    "bao_dau_dau": "bao_dau_dau.txt",
    "bao_ho": "bao_ho.txt",
    "bao_met": "bao_met.txt",
    "bao_sot": "bao_sot.txt",
    "lo_lang_stress": "lo_lang_stress.txt",
    "tu_van_dinh_duong": "tu_van_dinh_duong.txt",
    "tu_van_tap_luyen": "tu_van_tap_luyen.txt"
}

# ==============================
# HÀM DỰ ĐOÁN INTENT
# ==============================

def detect_intent(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = model(**inputs).logits
        pred = torch.argmax(logits, dim=1).item()

    return id2label[pred]


# ==============================
# ROUTING: CHỌN XỬ LÝ
# ==============================

def route_intent(user_input):
    intent = detect_intent(user_input)

    # Greeting
    if intent == "chao_hoi":
        return {
            "type": "greeting",
            "intent": intent,
            "rag_file": None
        }

    # Reminder (rule-based)
    if intent == "nhac_nho_uong_thuoc":
        return {
            "type": "reminder",
            "intent": intent,
            "rag_file": None
        }

    # RAG-based intents
    rag_file = intent_to_file.get(intent, None)

    return {
        "type": "rag",
        "intent": intent,
        "rag_file": rag_file
    }


# ==============================
# TEST NGAY
# ==============================

if __name__ == "__main__":
    text = "Tôi bị đau đầu khi thay đổi thời tiết"
    result = route_intent(text)
    print("\n🧠 Intent:", result["intent"])
    print("📄 Loại xử lý:", result["type"])
    print("📁 File RAG:", result["rag_file"])
