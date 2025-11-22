from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Biến toàn cục lưu model sau khi load
gemma_tokenizer = None
gemma_model = None


def load_gemma(model_path=r"D:/CHAT BOT TTCS/model/gemma"):
    global gemma_model, gemma_tokenizer

    print(f"🔄 Đang load Gemma từ local: {model_path}")

    gemma_tokenizer = AutoTokenizer.from_pretrained(model_path)

    gemma_model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch.float16
    )

    print("✅ Gemma đã load xong!")


def generate_answer(prompt):
    """
    Sinh text dựa trên model đã load từ load_gemma()
    """
    if gemma_model is None or gemma_tokenizer is None:
        raise ValueError("Bạn chưa load model! Hãy gọi load_gemma() trước khi generate.")

    inputs = gemma_tokenizer(prompt, return_tensors="pt").to(gemma_model.device)

    output = gemma_model.generate(
        **inputs,
        max_new_tokens=256,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
    )

    answer = gemma_tokenizer.decode(output[0], skip_special_tokens=True)
    return answer
