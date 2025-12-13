import os
import re
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
    # có thể thêm intent mới sau này
}

# ================================
# 2) LOAD EMBEDDER
# ================================
print("🧠 Loading embedding model (Vietnamese-SBERT)...")
embedder = SentenceTransformer("keepitreal/vietnamese-sbert")

# ================================
# 3) NORMALIZER
# ================================
def normalize_text(text: str) -> str:
    text = text.strip()
    text = " ".join(text.split())
    return text

# ================================
# 4) LOAD DATA THEO ĐOẠN (RẤT QUAN TRỌNG)
# ================================
def load_paragraphs(path: str):
    """
    Mỗi đoạn (paragraph) = 1 tình huống = 1 embedding
    Chấp nhận:
    - 1 đoạn = 1 dòng
    - 1 đoạn = nhiều dòng
    Miễn là cách nhau bằng dòng trống
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    paragraphs = [
        normalize_text(p)
        for p in re.split(r"\n\s*\n", raw_text)
        if p.strip()
    ]

    return paragraphs

# ================================
# 5) BUILD FAISS FOR EACH INTENT
# ================================
def build_for_intent(intent: str, filename: str):
    print(f"\n============================")
    print(f"🔍 Building FAISS for intent: {intent}")
    print(f"📄 File: {filename}")

    path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path):
        print("⚠ File không tồn tại → bỏ qua")
        return

    docs = load_paragraphs(path)
    n_docs = len(docs)

    print(f"📌 Số đoạn load được: {n_docs}")

    # Cảnh báo format
    if n_docs < 50:
        print("⚠️ CẢNH BÁO: số đoạn quá ít → có thể file bị dính đoạn!")

    # ================================
    # ENCODE
    # ================================
    embeddings = embedder.encode(
        docs,
        batch_size=64,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True  # BẮT BUỘC cho cosine
    )

    dim = embeddings.shape[1]

    # Dùng Inner Product vì vector đã normalize
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # ================================
    # SAVE
    # ================================
    index_path = os.path.join(EMB_DIR, f"{intent}_index.faiss")
    docs_path = os.path.join(EMB_DIR, f"{intent}_docs.pkl")

    faiss.write_index(index, index_path)

    with open(docs_path, "wb") as f:
        pickle.dump(docs, f)

    print(f"✅ Saved FAISS index → {index_path}")
    print(f"✅ Saved docs        → {docs_path}")

# ================================
# 6) RUN ALL INTENTS
# ================================
for intent, filename in INTENT_FILES.items():
    build_for_intent(intent, filename)

print("\n🎉 DONE! Built FAISS for ALL INTENTS.")
