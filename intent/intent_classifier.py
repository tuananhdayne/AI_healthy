from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F


class IntentClassifier:
    def __init__(self, model_path):
        print("🔄 Loading PhoBERT Intent Model...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map="auto"
        )
        self.model.eval()

        # Map ID → label
        self.id2label = {
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

    # ------------------------
    # Chỉ trả về nhãn intent
    # ------------------------
    def predict_intent(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.model.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits
            pred_id = torch.argmax(logits, dim=1).item()

        return self.id2label.get(pred_id, "unknown")

    # ------------------------
    # Trả về nhãn + độ tin cậy
    # ------------------------
    def predict_with_conf(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.model.device)

        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = F.softmax(logits, dim=1)

        conf, pred_id = torch.max(probs, dim=1)
        pred_id = pred_id.item()
        conf = conf.item()

        # Xử lý an toàn — hỗ trợ key là số hoặc chuỗi
        label = (
            self.id2label.get(pred_id) or
            self.id2label.get(str(pred_id)) or
            "unknown"
        )

        return label, conf
