# 📋 Danh sách Model Gemini có sẵn

## 🚀 Model được sử dụng mặc định

**gemini-2.0-flash** (Mặc định)
- ✅ Nhanh nhất
- ✅ Quota tốt: 15 RPM, 1M TPM, 200 RPD
- ✅ Phù hợp cho chatbot real-time

## 📊 Các model khác có thể dùng

### Model Flash (Nhanh)
1. **gemini-2.0-flash-lite**
   - 30 RPM, 1M TPM, 200 RPD
   - Nhẹ nhất, phù hợp cho high-volume

2. **gemini-2.5-flash**
   - 15 RPM, 250K TPM, 1K RPD
   - Cân bằng tốt

3. **gemini-2.5-flash-tts** (Multimodal)
   - 3 RPM, 10K TPM, 15 RPD
   - Hỗ trợ text-to-speech

### Model Pro (Chất lượng cao)
1. **gemini-2.5-pro**
   - 2 RPM, 125K TPM, 50 RPD
   - Chất lượng cao nhất nhưng chậm hơn

2. **gemini-3-pro**
   - 125K TPM
   - Model mới nhất

## ⚙️ Cách đổi model

### Cách 1: Biến môi trường (Khuyến nghị)
```bash
# Windows
set GEMINI_MODEL=gemini-2.5-pro

# Linux/Mac
export GEMINI_MODEL=gemini-2.5-pro
```

### Cách 2: Sửa trong code
Sửa file `generator/gemini_generator.py`:
```python
model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")  # Đổi model ở đây
```

## 💡 Khuyến nghị

- **Chatbot real-time**: `gemini-2.0-flash` (mặc định)
- **Cần chất lượng cao**: `gemini-2.5-pro`
- **High volume**: `gemini-2.0-flash-lite`
- **Cân bằng**: `gemini-2.5-flash`

## 📝 Lưu ý

- RPM = Requests Per Minute
- TPM = Tokens Per Minute  
- RPD = Requests Per Day
- Model sẽ tự động fallback sang `gemini-2.5-flash` nếu model chính không hoạt động

