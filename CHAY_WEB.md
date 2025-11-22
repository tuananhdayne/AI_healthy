# 🚀 Hướng dẫn chạy Web Chatbot

## ⚡ Cách nhanh nhất

### Bước 1: Khởi động Backend API (Terminal 1)

**Windows:**
```bash
cd D:\CHAT BOT TTCS
start_backend.bat
```

**Hoặc chạy thủ công:**
```bash
cd D:\CHAT BOT TTCS
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

**Lưu ý:**
- Models sẽ mất **2-5 phút** để load lần đầu
- Đợi đến khi thấy: `✅ TẤT CẢ MODELS ĐÃ SẴN SÀNG!`
- Server sẽ chạy tại: http://localhost:8000

### Bước 2: Khởi động Frontend Angular (Terminal 2)

Mở terminal mới:

```bash
cd D:\CHAT BOT TTCS\AI-Web
npm start
# hoặc
yarn start
# hoặc
ng serve
```

**Lưu ý:**
- Frontend sẽ chạy tại: http://localhost:4200
- Tự động mở trình duyệt hoặc mở thủ công

### Bước 3: Sử dụng

1. Mở trình duyệt: http://localhost:4200
2. Đăng nhập hoặc đăng ký tài khoản
3. Vào trang `/chat` để chat với bot

---

## ✅ Kiểm tra mọi thứ đã chạy đúng

### 1. Kiểm tra Backend:
```bash
# Mở trình duyệt hoặc dùng curl
http://localhost:8000/health
# Kết quả: {"status":"ok"}

http://localhost:8000/ready
# Kết quả khi models sẵn sàng:
# {"ready": true, "status": "Models đã sẵn sàng", "error": null}
```

### 2. Kiểm tra Frontend:
- Mở http://localhost:4200
- Nếu thấy trang web → Frontend OK
- Nếu thấy lỗi "Không kết nối được server" → Backend chưa chạy hoặc models chưa load xong

---

## 🔧 Xử lý lỗi thường gặp

### Lỗi: "ModuleNotFoundError: No module named 'fastapi'"

**Giải pháp:**
```bash
pip install fastapi uvicorn[standard]
```

### Lỗi: "Port 8000 already in use"

**Giải pháp:**
- Đổi port trong lệnh: `--port 8001`
- Hoặc đóng ứng dụng đang dùng port 8000

### Lỗi: "Models chưa sẵn sàng"

**Giải pháp:**
- Đợi thêm vài phút (models đang load)
- Kiểm tra console backend xem có lỗi không
- Kiểm tra đủ RAM (cần ít nhất 8GB cho Gemma)

### Lỗi: Frontend không kết nối được Backend

**Giải pháp:**
1. Kiểm tra backend đã chạy: http://localhost:8000/health
2. Kiểm tra CORS trong `api_server.py` (đã cấu hình sẵn)
3. Kiểm tra `environment.ts` có đúng URL không

---

## 📝 Thứ tự đúng:

1. ✅ **Bước 1**: Khởi động Backend (đợi models load xong - 2-5 phút)
2. ✅ **Bước 2**: Khởi động Frontend
3. ✅ **Bước 3**: Mở trình duyệt và sử dụng

---

## 🎯 Tips

- **Luôn khởi động Backend trước** vì models cần thời gian load
- **Giữ cả 2 terminal mở** (1 cho backend, 1 cho frontend)
- **Kiểm tra `/ready` endpoint** để biết models đã sẵn sàng chưa
- **Xem console logs** để biết tiến trình load models

---

## 🆘 Cần hỗ trợ?

- Xem file `QUICK_START.md` để biết chi tiết hơn
- Kiểm tra log trong terminal backend
- Kiểm tra console trình duyệt (F12)

