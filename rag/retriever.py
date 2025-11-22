import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

class Retriever:
    def __init__(self, rag_path):
        # ======================
        # ĐƯỜNG DẪN
        # ======================
        index_path = r"D:\CHAT BOT TTCS\embeddings\medical_index.faiss"
        docs_path = r"D:\CHAT BOT TTCS\embeddings\documents.pkl"

        print("🔄 Đang load FAISS index (cosine)...")
        self.index = faiss.read_index(index_path)

        print("🔄 Đang load danh sách documents...")
        with open(docs_path, "rb") as f:
            self.documents = pickle.load(f)

        print("🔄 Đang load model embedding...")
        self.embedder = SentenceTransformer("keepitreal/vietnamese-sbert")

    # ======================
    # HÀM CHUẨN HOÁ VECTOR
    # ======================
    def normalize(self, v):
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    # ======================
    # HÀM TRUY XUẤT TOP-K
    # ======================
    def search(self, query, k=3):
        """
        Trả về danh sách:
        [
            { "text": ..., "cosine": ..., "confidence": ... },
            ...
        ]
        """

        # Embed query
        query_emb = self.embedder.encode([query]).astype("float32")

        # Normalize để cosine similarity chính xác
        query_emb = self.normalize(query_emb)

        # Search: FAISS trả ra cosine similarity
        scores, indices = self.index.search(query_emb, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            cosine = float(score)
            confidence = (cosine + 1) / 2   # convert -1→1 thành 0→1

            results.append({
                "text": self.documents[idx],
                "cosine": cosine,
                "confidence": confidence
            })

        return results
