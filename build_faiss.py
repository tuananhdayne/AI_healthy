import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer

# ================================
# 1) PATH
# ================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
EMB_DIR = os.path.join(BASE_DIR, "embeddings")

os.makedirs(EMB_DIR, exist_ok=True)

# Intent → filename mapping
INTENT_FILES = {
    "bao_dau_bung": "bao_dau_bung.txt",
    "bao_dau_dau": "bao_dau_dau.txt",
    "bao_ho": "bao_ho.txt",
    "bao_met_moi": "bao_met_moi.txt",
    "bao_sot": "bao_sot.txt",
    "lo_lang_stress": "lo_lang_stress.txt",
    "tu_van_dinh_duong": "tu_van_dinh_duong.txt",
    "tu_van_tap_luyen": "tu_van_tap_luyen.txt",

    # ❗ other KHÔNG có RAG → bỏ
}

# ================================
# 2) LOAD EMBEDDER
# ================================
print("🧠 Loading embedding model (Vietnamese-SBERT)...")
embedder = SentenceTransformer("keepitreal/vietnamese-sbert")


# ================================
# 3) NORMALIZER (quan trọng)
# ================================
def normalize_text(text):
    text = text.strip()
    text = " ".join(text.split())
    return text


# ================================
# 4) BUILD FAISS FOR EACH INTENT
# ================================
def build_for_intent(intent, filename):
    print(f"\n============================")
    print(f"🔍 Building FAISS for intent: {intent}")
    print(f"📄 File: {filename}")

    path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path):
        print("⚠ File không tồn tại → bỏ qua")
        return

    with open(path, "r", encoding="utf-8") as f:
        docs = [normalize_text(l) for l in f.readlines() if l.strip()]

    print(f"📌 {len(docs)} đoạn văn")

    # Encode
    embeddings = embedder.encode(
        docs,
        batch_size=64,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True  # QUAN TRỌNG! vector chuẩn hơn
    )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # DÙNG cosine similarity

    index.add(embeddings)

    # Save
    index_path = os.path.join(EMB_DIR, f"{intent}_index.faiss")
    docs_path = os.path.join(EMB_DIR, f"{intent}_docs.pkl")

    faiss.write_index(index, index_path)

    with open(docs_path, "wb") as f:
        pickle.dump(docs, f)

    print(f"✅ Saved index → {index_path}")
    print(f"✅ Saved docs  → {docs_path}")


# ================================
# 5) RUN ALL INTENTS
# ================================
for intent, filename in INTENT_FILES.items():
    build_for_intent(intent, filename)

print("\n🎉 DONE! Built FAISS for ALL INTENTS.")
