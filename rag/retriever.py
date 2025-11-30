import faiss
import pickle
import numpy as np
import os
from sentence_transformers import SentenceTransformer

class Retriever:
    def __init__(self, rag_path):
        # ======================
        # ĐƯỜNG DẪN
        # ======================
        self.embeddings_dir = r"D:\CHAT BOT TTCS\embeddings"
        
        print("🔄 Đang load model embedding...")
        self.embedder = SentenceTransformer("keepitreal/vietnamese-sbert")
        
        # Cache cho các intent indexes (lazy load)
        self._intent_indexes = {}
        self._intent_documents = {}
        
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
    def search(self, query, k=3):
        """
        Search trong tất cả các intent indexes và trả về kết quả tốt nhất
        
        Trả về danh sách:
        [
            { "text": ..., "cosine": ..., "confidence": ... },
            ...
        ]
        """
        # Embed query
        query_emb = self.embedder.encode([query]).astype("float32")
        query_emb = self.normalize(query_emb)
        
        # Search trong tất cả các intent indexes
        all_results = []
        
        for intent in self.available_intents:
            try:
                # Lazy load index nếu chưa có
                if intent not in self._intent_indexes:
                    index_path = os.path.join(self.embeddings_dir, f"{intent}_index.faiss")
                    docs_path = os.path.join(self.embeddings_dir, f"{intent}_docs.pkl")
                    
                    if os.path.exists(index_path) and os.path.exists(docs_path):
                        self._intent_indexes[intent] = faiss.read_index(index_path)
                        with open(docs_path, "rb") as f:
                            self._intent_documents[intent] = pickle.load(f)
                    else:
                        continue  # Bỏ qua intent không có index
                
                intent_index = self._intent_indexes[intent]
                intent_docs = self._intent_documents[intent]
                
                # Search trong index của intent này
                scores, indices = intent_index.search(query_emb, k)
                
                # Thêm kết quả vào danh sách
                for score, idx in zip(scores[0], indices[0]):
                    cosine = float(score)
                    confidence = (cosine + 1) / 2
                    all_results.append({
                        "text": intent_docs[idx],
                        "cosine": cosine,
                        "confidence": confidence,
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
        
        return results
    
    # ======================
    # HÀM TRUY XUẤT THEO INTENT
    # ======================
    def search_by_intent(self, intent: str, query: str, k=3):
        """
        Search trong index riêng của intent
        
        Args:
            intent: Tên intent (ví dụ: "bao_dau_bung", "bao_dau_dau")
            query: Câu query để search
            k: Số lượng kết quả trả về
        
        Returns:
            Danh sách kết quả tương tự search()
        """
        # Không cần mapping nữa vì model mới đã dùng "bao_met_moi" trực tiếp
        actual_intent = intent
        
        # Lazy load index và documents cho intent này
        if actual_intent not in self._intent_indexes:
            index_path = os.path.join(self.embeddings_dir, f"{actual_intent}_index.faiss")
            docs_path = os.path.join(self.embeddings_dir, f"{actual_intent}_docs.pkl")
            
            if not os.path.exists(index_path) or not os.path.exists(docs_path):
                # Nếu không có index riêng cho intent này, fallback về search thông thường
                print(f"⚠️ Không tìm thấy index riêng cho intent '{actual_intent}', dùng search thông thường")
                return self.search(query, k)
            
            print(f"🔄 Đang load index cho intent: {actual_intent}")
            self._intent_indexes[actual_intent] = faiss.read_index(index_path)
            with open(docs_path, "rb") as f:
                self._intent_documents[actual_intent] = pickle.load(f)
        
        intent_index = self._intent_indexes[actual_intent]
        intent_docs = self._intent_documents[actual_intent]
        
        # Embed query
        query_emb = self.embedder.encode([query]).astype("float32")
        query_emb = self.normalize(query_emb)
        
        # Search trong index của intent
        scores, indices = intent_index.search(query_emb, k)
        
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
