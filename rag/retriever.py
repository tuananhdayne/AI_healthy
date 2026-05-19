import faiss  # Thư viện FAISS để xử lý vector search
import pickle # Để load các document đã được lưu trữ
import numpy as np # Thư viện xử lý mảng số học
import os  
from sentence_transformers import SentenceTransformer # Mô hình embedding câu

class Retriever:
    def __init__(self, rag_path):
        # ======================
        # ĐƯỜNG DẪN
        # ======================
        self.embeddings_dir = r"D:\CHAT BOT TTCS\embeddings"
        
        print("🔄 Đang load model embedding...")
        self.embedder = SentenceTransformer("keepitreal/vietnamese-sbert")  # Dùng chung một encoder cho mọi intent để tránh lệch không gian vector
        
        # Cache cho các intent indexes (lazy load)
        self._intent_indexes = {}  # Lưu FAISS index đã load cho từng intent 
        self._intent_documents = {}  # Map intent -> danh sách đoạn văn tương ứng index
        
        # Danh sách các intent có sẵn (từ các file index có trong thư mục)
        self.available_intents = [
            "bao_dau_bung",
            "bao_dau_dau", 
            "bao_ho",
            "bao_met_moi",
            "bao_sot",
            "tu_van_dinh_duong",
            "tu_van_tap_luyen"
        ]
        
        print("✅ Retriever đã khởi tạo (sử dụng intent indexes riêng lẻ)")

    # ======================
    # HÀM CHUẨN HOÁ VECTOR
    # ======================
    def normalize(self, v):
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    # ======================
    # HÀM TRUY XUẤT TOP-K (search trong tất cả intent indexes)
    # ======================

    # 2. Fallback trong chatbot: nếu search_by_intent() lỗi hoặc thiếu index, hệ thống
    #    tự động gọi search_all_intents() để không bị mất câu trả lời.
    # 3. Mid gate (intent_conf ∈ [0.85, 0.97)): pipeline muốn tham khảo nhẹ toàn bộ dữ liệu
    #    khi không chắc intent, nên cần global search để lấy top-k đoạn tốt nhất.
    # 4. Khi bổ sung intent mới chưa build index riêng, search_all_intents() giúp degrade gracefully
    #    trước khi chuẩn hóa lại dữ liệu.
    # Vì vậy search_all_intents() duyệt qua từng index riêng, gom kết quả rồi lấy top-k chung.

    #tìm ra các tài liệu liên quan nhất từ tất cả các intent indexes
    def search_all_intents(self, query, k=3):
        """
        Search trong tất cả các intent indexes và trả về kết quả tốt nhất
        
        Trả về danh sách:
        [
            { "text": ..., "cosine": ..., "confidence": ... },
            ...
        ]
        """
        # vector hóa câu truy vấn
        query_emb = self.embedder.encode([query]).astype("float32")
        query_emb = self.normalize(query_emb)
        
        # Search trong tất cả các intent indexes
        # Gom tất cả kết quả vào một danh sách
        all_results = []
        # Duyệt qua tất cả inent có trong danh sách available_intents
        for intent in self.available_intents:
            try:
                # Lazy load index nếu chưa có
                if intent not in self._intent_indexes:
                    # đường dẫn tới file index và documents theo intent
                    index_path = os.path.join(self.embeddings_dir, f"{intent}_index.faiss")
                    docs_path = os.path.join(self.embeddings_dir, f"{intent}_docs.pkl")
                    #nếu file tồn tại thì load index và documents
                    if os.path.exists(index_path) and os.path.exists(docs_path):
                        # đọc các vector index từ file
                        self._intent_indexes[intent] = faiss.read_index(index_path)
                        with open(docs_path, "rb") as f:
                            # Đọc văn bản thô tương ứng từng vector, phục vụ trả kết quả RAG
                            self._intent_documents[intent] = pickle.load(f)
                    else:
                        continue  # Bỏ qua intent không có index
 
                # Lấy index và documents đã load
                intent_index = self._intent_indexes[intent]
                # trả về list các đoạn văn bản tương ứng với index
                intent_docs = self._intent_documents[intent]
                
                # Trả về điểm và vị trí index của các đoạn văn bản tương tự nhất
                scores, indices = intent_index.search(query_emb, k)
                
                # Thêm kết quả vào danh sách
                for score, idx in zip(scores[0], indices[0]):
                    cosine = float(score)
                    confidence = (cosine + 1) / 2
                    all_results.append({
                        #lấy ra đoạn văn bản tương ứng với index
                        "text": intent_docs[idx],
                        #tính điểm cosine và confidence
                        "cosine": cosine, # -1→1
                        "confidence": confidence,   #0→1
                        "intent": intent  # Lưu intent để debug
                    })
            except Exception as e:
                print(f"⚠️ Lỗi khi search trong intent '{intent}': {e}")
                continue
        
        # Sắp xếp theo confidence (cao nhất trước) và lấy top k
        all_results.sort(key=lambda x: x["confidence"], reverse=True)
        results = all_results[:k]
        
        # Bỏ field "intent" trong kết quả cuối cùng (chỉ dùng để debug)
        for r in results:
            r.pop("intent", None)
        
        # Trả về kết quả là danh sách các đoạn văn bản tương tự nhất
        return results
    
    # ======================
    # HÀM TRUY XUẤT THEO INTENT
    # ======================
    #truy xuất theo intent cụ thể
    def search_by_intent(self, intent: str, query: str, k=3):

        actual_intent = intent
        
        # Lazy load index nếu chưa có
        if actual_intent not in self._intent_indexes:
            # Chỉ load index/documents khi lần đầu gặp intent nhằm giảm thời gian khởi động
            index_path = os.path.join(self.embeddings_dir, f"{actual_intent}_index.faiss")
            docs_path = os.path.join(self.embeddings_dir, f"{actual_intent}_docs.pkl")
            
            if not os.path.exists(index_path) or not os.path.exists(docs_path):
                # Một số intent mới hoặc intent hiếm có thể chưa build index riêng.
                # Fallback gọi search_all_intents() để scan toàn bộ corpus thay vì trả về rỗng.
                print(f"⚠️ Không tìm thấy index riêng cho intent '{actual_intent}', dùng search thông thường")
                return self.search_all_intents(query, k)
            
            print(f"🔄 Đang load index cho intent: {actual_intent}")
            self._intent_indexes[actual_intent] = faiss.read_index(index_path)
            with open(docs_path, "rb") as f:
                # Đọc văn bản thô tương ứng từng vector, phục vụ trả kết quả RAG
                self._intent_documents[actual_intent] = pickle.load(f)
        # Lấy index và documents đã load
        intent_index = self._intent_indexes[actual_intent]
        intent_docs = self._intent_documents[actual_intent]
        
        # embedding câu của user 
        query_emb = self.embedder.encode([query]).astype("float32")  # Embed câu hỏi hiện tại
        query_emb = self.normalize(query_emb)
        
        # tìm index của đoạn văn bản tương tự nhất với inent được chỉ định
        scores, indices = intent_index.search(query_emb, k)  # Lấy top-k vector gần nhất trong intent này
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            cosine = float(score)
            confidence = (cosine + 1) / 2   # convert -1→1 thành 0→1
            
            results.append({
                "text": intent_docs[idx],
                "cosine": cosine,
                "confidence": confidence
            })
        
        return results
