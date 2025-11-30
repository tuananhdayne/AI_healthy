from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_path = r"D:\CHAT BOT TTCS\model\gemma"

print("🔄 Đang load Gemma 2B IT local...")

tokenizer = AutoTokenizer.from_pretrained(model_path)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    device_map="auto",
    low_cpu_mem_usage=True
)

prompt = "Xin chào, bạn đang hoạt động chứ?"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    output = model.generate(
        **inputs,
        max_new_tokens=50,
        temperature=0.2
    )

print("\n🟢 OUTPUT GEMMA:")
print(tokenizer.decode(output[0], skip_special_tokens=True))
