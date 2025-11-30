import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ====== ĐƯỜNG DẪN MODEL INTENT ======
MODEL_PATH = r"D:\CHAT BOT TTCS\model\phobert_intent_model_v5"  
# ====== Load model ======
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=False)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

print("✔ Model intent đã load xong!")

# ====== Danh sách intent ======
INTENTS = [
    "bao_dau_bung",
    "bao_dau_dau",
    "bao_ho",
    "bao_met",
    "bao_sot",
    "chao_hoi",
    "lo_lang_stress",
    "nhac_nho_uong_thuoc",
    "tu_van_dinh_duong",
    "tu_van_tap_luyen",
]

# ====== Hàm dự đoán intent ======
def predict_intent(text: str):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)
        conf, pred_idx = torch.max(probs, dim=1)

    intent = INTENTS[pred_idx.item()]
    confidence = round(float(conf.item()), 3)
    return intent, confidence


# ====== Test mẫu ======
test_texts = [
    "Đầu hơi nặng, người nóng, chắc bị sốt rồi.",
    "Ho khan cả tuần, uống mật ong không khỏi.",
    "Nhắc tôi uống thuốc lúc 9h tối.",
    "Chào bot, hôm nay thế nào?",
    "Ăn uống không ngon, ngủ không yên, chắc stress quá.",
    "Bị đau bụng sau khi ăn đồ cay.",
    "Nên ăn gì buổi tối để giảm cân vậy?",
    "Tập gym buổi sáng hay buổi tối tốt hơn?",
    "Tôi đang bị ốm phải làm sao",
    "Tôi bị sốt",
]

print("\n===== KẾT QUẢ DỰ ĐOÁN =====")
for text in test_texts:
    intent, conf = predict_intent(text)
    print(f"{text:65s} → {intent:22s} (conf={conf:.3f})")
