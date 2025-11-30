from intent.intent_classifier import IntentClassifier
from rag.retriever import Retriever
from generator.gemma_generator import load_gemma, generate_answer
from app.response_layer import build_prompt, classify_confidence

print("🚀 Đang khởi động toàn bộ hệ thống...")

# 1. Load intent
print("🔄 Loading PhoBERT intent classifier...")
intent_model = IntentClassifier(r"D:/CHAT BOT TTCS/model/phobert_intent_model_v5")

# 2. Load RAG
print("🔄 Loading RAG retriever...")
retriever = Retriever(r"D:/CHAT BOT TTCS")

# 3. Load Gemma
print("🔄 Loading Gemma LLM...")
load_gemma(r"D:/CHAT BOT TTCS/model/gemma")

print("\n🔥 TẤT CẢ MODEL ĐÃ SẴN SÀNG!")
print("🤖 Chatbot y tế đã khởi động. Nhập 'quit' để thoát.\n")

# ======== Loop ========
while True:
    user = input("Bạn: ").strip()
    if user.lower() == "quit":
        break

    intent = intent_model.predict_intent(user)
    print("🧠 Intent:", intent)

    # Retrieve
    docs = retriever.search(user, k=3)

    context = "\n".join(d["text"] for d in docs)
    conf_score = docs[0]["cosine"]
    conf_lvl = classify_confidence(conf_score)

    prompt = build_prompt(context, user, conf_lvl)

    answer = generate_answer(prompt)
    print("Bot:", answer)
