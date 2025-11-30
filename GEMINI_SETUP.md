# 🚀 Cài đặt Gemini API

## ✅ Đã cấu hình sẵn

API key đã được cấu hình trong `generator/gemini_generator.py`:
```
AIzaSyCyAyS2hv9mJRkofPNi7p5SWycMR6xFuME
```

## 📦 Cài đặt thư viện

### Cách 1: Dùng requirements.txt (Khuyến nghị)
```bash
pip install -r requirements.txt
```

### Cách 2: Cài thủ công
```bash
pip install google-generativeai
```

## 🔧 Cấu hình API Key (Tùy chọn)

Nếu muốn dùng API key khác hoặc bảo mật hơn, set biến môi trường:

**Windows:**
```bash
set GEMINI_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY=your_api_key_here
```

Hoặc tạo file `.env`:
```
GEMINI_API_KEY=your_api_key_here
```

## ⚡ Lợi ích của Gemini API

1. **Nhanh hơn**: Không cần load model nặng (2-5 phút → vài giây)
2. **Nhẹ hơn**: Không tốn RAM/GPU cho model
3. **Chất lượng tốt**: Gemini Pro là model mạnh của Google
4. **Dễ scale**: Không lo về tài nguyên server

## 🎯 So sánh

| Tính năng | Gemma Local | Gemini API |
|-----------|-------------|------------|
| Thời gian load | 2-5 phút | < 1 giây |
| RAM cần | ~8GB+ | ~500MB |
| GPU cần | Có | Không |
| Tốc độ response | Chậm | Nhanh |
| Chi phí | Miễn phí | Miễn phí (có quota) |

## 📝 Lưu ý

- Gemini API có quota miễn phí (đủ cho development)
- Nếu vượt quota, có thể nâng cấp hoặc quay lại Gemma local
- API key đã được hardcode trong code (có thể cải thiện bằng .env)

## 🆘 Xử lý lỗi

### Lỗi: "ModuleNotFoundError: No module named 'google.generativeai'"
```bash
pip install google-generativeai
```

### Lỗi: "API key invalid"
- Kiểm tra API key trong `generator/gemini_generator.py`
- Hoặc set biến môi trường `GEMINI_API_KEY`

### Lỗi: "Quota exceeded"
- Đã vượt quota miễn phí
- Đợi reset quota hoặc nâng cấp tài khoản

