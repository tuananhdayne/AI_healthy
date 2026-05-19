import os
import re
import csv
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
# 4) LOAD DATA THEO ĐOẠN
# ================================
def load_paragraphs(path: str):
    """
    Mỗi đoạn (paragraph) = 1 tình huống = 1 embedding
    Tách đoạn bằng dòng trống
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    paragraphs = [
        normalize_text(p)
        for p in re.split(r"\n\s*\n", raw_text)
        if p.strip()
    ]
    return paragraphs

def dedupe_keep_order(items: list[str]) -> tuple[list[str], int]:
    """Loại trùng nhưng giữ nguyên thứ tự. Trả về (list_moi, so_trung_bi_loai)."""
    seen = set()
    out = []
    dup_count = 0
    for x in items:
        if x in seen:
            dup_count += 1
            continue
        seen.add(x)
        out.append(x)
    return out, dup_count

def text_preview(s: str, max_len: int = 140) -> str:
    """Preview 1 đoạn để debug (không in quá dài)."""
    if len(s) <= max_len:
        return s
    return s[:max_len].rstrip() + "..."

def calc_text_stats(docs: list[str]) -> dict:
    """Tính avg/max độ dài ký tự + top 3 đoạn dài nhất."""
    if not docs:
        return {
            "avg_chars": 0,
            "max_chars": 0,
            "top3": [],
        }

    lengths = [len(d) for d in docs]
    avg_chars = sum(lengths) / len(lengths)
    max_chars = max(lengths)

    # top 3 longest (index + length + preview)
    idx_sorted = sorted(range(len(docs)), key=lambda i: len(docs[i]), reverse=True)[:3]
    top3 = [
        {
            "rank": k + 1,
            "idx": i,
            "chars": len(docs[i]),
            "preview": text_preview(docs[i], 180),
        }
        for k, i in enumerate(idx_sorted)
    ]

    return {
        "avg_chars": avg_chars,
        "max_chars": max_chars,
        "top3": top3,
    }

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
        return {
            "intent": intent,
            "filename": filename,
            "exists": False,
            "n_docs_raw": 0,
            "n_docs_final": 0,
            "dups_removed": 0,
            "avg_chars": 0,
            "max_chars": 0,
            "built": False,
        }

    docs_raw = load_paragraphs(path)
    n_docs_raw = len(docs_raw)

    # Lọc trùng (nếu có)
    docs, dups_removed = dedupe_keep_order(docs_raw)
    n_docs = len(docs)

    stats = calc_text_stats(docs)

    print(f"📌 Số đoạn load được (raw):   {n_docs_raw}")
    print(f"📌 Số đoạn sau lọc trùng:     {n_docs}  (loại trùng: {dups_removed})")
    print(f"📏 Độ dài ký tự trung bình:   {stats['avg_chars']:.1f}")
    print(f"📏 Độ dài ký tự lớn nhất:     {stats['max_chars']}")

    # In top 3 đoạn dài nhất để bắt lỗi dính đoạn
    if n_docs > 0:
        print("🔎 Top 3 đoạn dài nhất (để kiểm tra dính đoạn):")
        for t in stats["top3"]:
            print(f"   #{t['rank']} | idx={t['idx']} | chars={t['chars']} | {t['preview']}")

    # Cảnh báo format
    if n_docs < 50:
        print("⚠️ CẢNH BÁO: số đoạn quá ít → có thể file bị dính đoạn!")

    # Cảnh báo dính đoạn theo độ dài (heuristic)
    # Nếu có đoạn quá dài, rất dễ là quên dòng trống
    if stats["max_chars"] >= 900:
        print("⚠️ CẢNH BÁO: Có đoạn rất dài (>=900 chars) → khả năng cao file bị dính đoạn (thiếu dòng trống).")

    # Skip file rỗng / toàn trùng
    if n_docs == 0:
        print("⚠️ File rỗng hoặc toàn đoạn trùng → bỏ qua build FAISS cho intent này.")
        return {
            "intent": intent,
            "filename": filename,
            "exists": True,
            "n_docs_raw": n_docs_raw,
            "n_docs_final": 0,
            "dups_removed": dups_removed,
            "avg_chars": stats["avg_chars"],
            "max_chars": stats["max_chars"],
            "built": False,
        }

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

    return {
        "intent": intent,
        "filename": filename,
        "exists": True,
        "n_docs_raw": n_docs_raw,
        "n_docs_final": n_docs,
        "dups_removed": dups_removed,
        "avg_chars": stats["avg_chars"],
        "max_chars": stats["max_chars"],
        "built": True,
    }

# ================================
# 6) RUN ALL INTENTS + SUMMARY + CSV
# ================================
results = []
total_final = 0

for intent, filename in INTENT_FILES.items():
    r = build_for_intent(intent, filename)
    results.append(r)
    total_final += r["n_docs_final"]

print("\n============================")
print("📊 TỔNG KẾT SỐ ĐOẠN THEO INTENT")
print("============================")
print(f"{'INTENT':<20} {'FILE':<24} {'RAW':>6} {'FINAL':>6} {'DUP':>6} {'AVGCH':>8} {'MAXCH':>8} {'BUILT':>7}")
print("-" * 95)

for r in results:
    built_flag = "YES" if r["built"] else "NO"
    print(f"{r['intent']:<20} {r['filename']:<24} {r['n_docs_raw']:>6} {r['n_docs_final']:>6} "
          f"{r['dups_removed']:>6} {r['avg_chars']:>8.1f} {r['max_chars']:>8} {built_flag:>7}")

print("-" * 95)
print(f"✅ Tổng số đoạn (FINAL) toàn bộ intent: {total_final}")

# Export CSV summary
csv_path = os.path.join(EMB_DIR, "summary.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["intent", "file", "raw", "final", "dup_removed", "avg_chars", "max_chars", "built"])
    for r in results:
        writer.writerow([
            r["intent"],
            r["filename"],
            r["n_docs_raw"],
            r["n_docs_final"],
            r["dups_removed"],
            f"{r['avg_chars']:.1f}",
            r["max_chars"],
            "YES" if r["built"] else "NO"
        ])

print(f"📄 Saved summary CSV → {csv_path}")
print("🎉 DONE! Built FAISS for ALL INTENTS.")
