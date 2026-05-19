from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

"""
Module này chứa lớp IntentClassifier dùng để phân loại intent (ý định) từ text của người dùng.
Sử dụng mô hình PhoBERT đã được fine-tune để nhận diện các intent khác nhau như:
- Báo các triệu chứng bệnh (đau đầu, đau bụng, sốt, ho, mệt mỏi...)
- Tư vấn dinh dưỡng
- Tư vấn tập luyện
- Lo lắng/stress
- Các intent khác

Mô hình sử dụng công nghệ BERT (Bidirectional Encoder Representations from Transformers)
được pre-train trên tiếng Việt (PhoBERT) để có hiểu biết tốt về ngữ pháp và ngữ nghĩa tiếng Việt.
"""


class IntentClassifier:
    """
    Lớp phân loại intent sử dụng mô hình PhoBERT đã được fine-tune.
    
    Nhiệm vụ:
    - Đọc text từ người dùng
    - Phân loại text thuộc intent nào (ý định/mục đích người dùng là gì)
    - Trả về top-k intent có xác suất cao nhất cùng độ tin cậy
    """
    def __init__(self, model_path):
        """
        Khởi tạo IntentClassifier bằng cách tải mô hình từ đường dẫn được chỉ định.
        
        Args:
            model_path (str): Đường dẫn tới thư mục chứa mô hình PhoBERT đã được fine-tune.
                              Thư mục này phải chứa:
                              - config.json: Cấu hình mô hình
                              - pytorch_model.bin: Trọng số mô hình
                              - vocab.txt: Bộ từ vựng
                              - special_tokens_map.json: Mặt nạ token đặc biệt
                              Ví dụ: "model/intent_model"
        
        Returns:
            None
            
        Phụ thuộc:
            - Sử dụng device GPU nếu có sẵn (device_map="auto")
            - Mô hình sẽ ở chế độ eval() - không update weights
        """
        print("🔄 Loading PhoBERT Intent Model...")

        # Tải tokenizer: dùng để chuyển text thành token IDs
        # Tokenizer cần phải khớp với mô hình (cùng vocab)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Tải mô hình: mô hình phân loại chuỗi (SequenceClassification)
        # torch_dtype=torch.float32: sử dụng độ chính xác 32-bit (float32)
        # device_map="auto": tự động sử dụng GPU nếu có, nếu không dùng CPU
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map="auto"
        )
        
        # Chuyển mô hình sang chế độ eval (đánh giá)
        # Quan trọng vì nó sẽ disable dropout và batch normalization để có kết quả ổn định
        self.model.eval()

        # Lấy mapping từ ID số sang label text từ config của mô hình
        # Ví dụ: {0: "báo_đau_đầu", 1: "báo_đau_bụng", 2: "báo_sốt", ...}
        # Điều này được thiết lập lúc training và lưu trong model config
        self.id2label = self.model.config.id2label
        print(f"📋 Intent classes từ model config: {self.id2label}")

    # ========================
    # Dự đoán Top-K intent (K intent có xác suất cao nhất)
    # ========================
    def predict_topk(self, text, k=2):
        """
        Dự đoán K intent có xác suất cao nhất từ một câu text.
        
        Khi nào dùng:
        - Khi muốn lấy top intent + backup intent (nếu intent chính không đúng)
        - Khi muốn xem các intent khác mà mô hình cho là có thể xảy ra
        - Khi muốn debugging: xem intent nào mô hình gán điểm cao
        
        Phương pháp:
        1. Tokenize text
        2. Forward pass: tính logits
        3. Softmax: chuyển logits thành xác suất
        4. torch.topk: lấy K giá trị xác suất cao nhất và indices
        5. Chuyển indices thành labels
        
        Args:
            text (str): Câu text cần phân loại intent.
                       Ví dụ: "Bị ho và khó thở"
            k (int, optional): Số intent muốn trả về. Default = 2
                              Ví dụ: k=2 trả về top 2 intent
                              Nếu k lớn hơn số intent có sẵn, sẽ trả về tất cả
        
        Returns:
            list: Danh sách các tuple (intent_label, confidence), sắp xếp theo confidence giảm dần.
                  Ví dụ: [("báo_ho", 0.87), ("báo_sốt", 0.08)]
                  
                  Điều này có nghĩa:
                  - Mô hình 87% chắc chắn intent là "báo_ho"
                  - Mô hình 8% cho rằng có thể là "báo_sốt"
        
        Ghi chú:
            - Kết quả luôn sắp xếp từ confidence cao nhất tới thấp nhất
            - Tổng tất cả confidence sẽ bằng 1.0 (vì Softmax)
            - Dùng phương pháp này khi cần quyết định thay thế nếu intent chính không phù hợp
        """
        # Tokenize input text
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.model.device)

        # Forward pass để lấy logits
        with torch.no_grad():
            # Lấy logits
            logits = self.model(**inputs).logits
            # Softmax: chuyển logits thành xác suất (0-1)
            # dim=1: tính softmax trên dimension intent classes
            probs = F.softmax(logits, dim=1)

        # Lấy top-k: K giá trị xác suất cao nhất
        # torch.topk() trả về (top_values, top_indices)
        # k=min(k, len(self.model.config.id2label)): đảm bảo k không vượt quá số intent
        top_confs, top_ids = torch.topk(probs, k=min(k, len(self.model.config.id2label)), dim=1)
        
        # Xây dựng danh sách kết quả
        result = []
        # Lặp qua K intent được chọn
        for i in range(top_confs.shape[1]):
            # Lấy intent ID từ top_ids
            pred_id = top_ids[0, i].item()
            # Lấy độ tin cậy (xác suất) - giá trị từ 0-1
            conf = top_confs[0, i].item()  # 0-1 scale
            
            # Chuyển ID sang label text bằng id2label mapping
            label = self.model.config.id2label.get(pred_id, "unknown")
            # Thêm vào kết quả dưới dạng tuple (label, confidence)
            result.append((label, conf))
        
        return result
