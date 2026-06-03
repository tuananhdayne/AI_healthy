# 🚀 Cài đặt Gemini API

## 🔐 Cấu hình bảo mật (bắt buộc)

API key **không được hardcode trong code**. Dự án đọc key từ biến môi trường:

- `GEMINI_API_KEY` (ưu tiên)
- `GOOGLE_API_KEY` (fallback an toàn)

## 📦 Cài đặt thư viện

### Cách 1: Dùng requirements.txt (Khuyến nghị)
```bash
pip install -r requirements.txt
```

### Cách 2: Cài thủ công
```bash
pip install google-generativeai python-dotenv
```

## 🔧 Cấu hình API Key

### Cách 1: Tạo file `.env` (khuyến nghị cho local)

Copy từ file mẫu:
```bash
cp .env.example .env
```

Sau đó cập nhật:
```env
GEMINI_API_KEY=your_real_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### Cách 2: Set biến môi trường trực tiếp

**Windows:**
```bash
set GEMINI_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY=your_api_key_here
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
- Không commit file `.env`, file key hoặc API key thực lên Git

## 🆘 Xử lý lỗi

### Lỗi: "ModuleNotFoundError: No module named 'google.generativeai'"
```bash
pip install google-generativeai
```

### Lỗi: "ModuleNotFoundError: No module named 'dotenv'"
```bash
pip install python-dotenv
```

### Lỗi: "API key invalid"
- Kiểm tra `GEMINI_API_KEY` trong `.env` hoặc biến môi trường
- Đảm bảo key còn hiệu lực trong Google AI Studio / Google Cloud

### Lỗi: "Quota exceeded"
- Đã vượt quota miễn phí
- Đợi reset quota hoặc nâng cấp tài khoản
