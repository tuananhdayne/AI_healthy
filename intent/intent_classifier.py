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

        # Lấy id2label từ model config (đồng bộ với model training)
        self.id2label = self.model.config.id2label
        print(f"📋 Intent classes từ model config: {self.id2label}")

    # ------------------------
    # Chỉ trả về nhãn intent
    # ------------------------
    def predict_intent(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.model.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits
            pred_id = torch.argmax(logits, dim=1).item()

        # Đọc từ model.config.id2label
        label = self.model.config.id2label.get(pred_id, "unknown")
        return label

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

        # Đọc từ model.config.id2label
        label = self.model.config.id2label.get(pred_id, "unknown")
        return label, conf

    # ========================
    # Trả về TOP-K intent (0-1 scale)
    # ========================
    def predict_topk(self, text, k=2):
        """Trả về top-k intent với confidence (0-1).
        
        Returns:
            [(intent1, conf1), (intent2, conf2), ...]
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.model.device)

        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = F.softmax(logits, dim=1)

        # Lấy top-k
        top_confs, top_ids = torch.topk(probs, k=min(k, len(self.model.config.id2label)), dim=1)
        
        result = []
        for i in range(top_confs.shape[1]):
            pred_id = top_ids[0, i].item()
            conf = top_confs[0, i].item()  # 0-1 scale
            
            label = self.model.config.id2label.get(pred_id, "unknown")
            result.append((label, conf))
        
        return result
