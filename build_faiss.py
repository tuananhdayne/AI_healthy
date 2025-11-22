import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from load_data import load_documents

# ======================
# CONFIG
# ======================

data_folder = r"D:\CHAT BOT TTCS\data"
embed_folder = r"D:\CHAT BOT TTCS\embeddings"

os.makedirs(embed_folder, exist_ok=True)

output_index = os.path.join(embed_folder, "medical_index.faiss")
output_docs = os.path.join(embed_folder, "documents.pkl")

# ======================
# LOAD DATA
# ======================

print("🔄 Đang tải dữ liệu...")
documents = load_documents(data_folder)
print("👉 Tổng số đoạn:", len(documents))

# ======================
# LOAD EMBEDDING MODEL
# ======================

print("🔄 Đang load model embedding...")
embedder = SentenceTransformer("keepitreal/vietnamese-sbert")

# ======================
# EMBEDDING + NORMALIZE (COSINE)
# ======================

print("🔄 Đang tạo embedding...")
embeddings = embedder.encode(documents)
embeddings = np.array(embeddings).astype("float32")

# Normalize để cosine similarity chính xác
embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

dim = embeddings.shape[1]

# ======================
# FAISS INDEX — COSINE (IP)
# ======================

print("🔄 Đang tạo FAISS IndexFlatIP...")
index = faiss.IndexFlatIP(dim)     # inner product = cosine similarity
index.add(embeddings)

# ======================
# SAVE FILE
# ======================

faiss.write_index(index, output_index)
pickle.dump(documents, open(output_docs, "wb"))

print("\n🎉 Hoàn thành build FAISS COSINE!")
print("📁 Index:", output_index)
print("📁 Documents:", output_docs)
