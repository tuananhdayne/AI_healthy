# 🚀 Hướng dẫn khởi động nhanh

## ⚡ Khởi động Backend API (Bắt buộc)

### Cách 1: Dùng script tự động (Khuyến nghị)

**Windows:**
```bash
start_backend.bat
```

**Linux/Mac:**
```bash
chmod +x start_backend.sh
./start_backend.sh
```

### Cách 2: Chạy thủ công

1. **Mở terminal/PowerShell tại thư mục dự án:**
   ```bash
   cd D:\CHAT BOT TTCS
   ```

2. **Kiểm tra Python:**
   ```bash
   python --version
   ```
   (Cần Python 3.8+)

3. **Cài đặt dependencies (nếu chưa có):**
   ```bash
   pip install fastapi uvicorn[standard]
   ```

4. **Khởi động server:**
   ```bash
   python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Kiểm tra server đã chạy:**
   - Mở trình duyệt: http://localhost:8000/docs
   - Hoặc: http://localhost:8000/health
   - Nếu thấy trang API docs hoặc `{"status":"ok"}` → Server đã chạy thành công!

### ⚠️ Lưu ý quan trọng:

- **Models sẽ mất vài phút để load lần đầu tiên** (Intent Classifier, RAG Retriever, Gemma Generator)
- Bạn sẽ thấy các dòng log như:
  ```
  🔄 Loading PhoBERT Intent Model...
  🔄 Đang load FAISS index...
  🔄 Đang load model embedding...
  ✅ Models đã sẵn sàng!
  ```
- **Đợi đến khi thấy "✅ Models đã sẵn sàng!"** trước khi test frontend

---

## 🌐 Khởi động Frontend Angular

1. **Mở terminal mới tại thư mục AI-Web:**
   ```bash
   cd D:\CHAT BOT TTCS\AI-Web
   ```

2. **Cài đặt dependencies (nếu chưa có):**
   ```bash
   npm install
   # hoặc
   yarn install
   ```

3. **Khởi động dev server:**
   ```bash
   ng serve
   # hoặc
   npm start
   # hoặc
   yarn start
   ```

4. **Mở trình duyệt:**
   - http://localhost:4200
   - Đăng nhập hoặc đăng ký
   - Vào trang `/chat` để test chatbot

---

## ✅ Kiểm tra kết nối

### 1. Kiểm tra Backend:
```bash
# Trong terminal/PowerShell
curl http://localhost:8000/health
# Hoặc mở trình duyệt: http://localhost:8000/health
```

**Kết quả mong đợi:**
```json
{"status":"ok"}
```

### 2. Kiểm tra Models đã sẵn sàng:
```bash
curl http://localhost:8000/ready
# Hoặc mở trình duyệt: http://localhost:8000/ready
```

**Kết quả khi models đã sẵn sàng:**
```json
{"ready": true, "status": "Models đã sẵn sàng"}
```

**Kết quả khi models đang tải:**
```json
{"ready": false, "status": "Models đang tải, vui lòng đợi..."}
```

### 3. Kiểm tra Frontend kết nối Backend:

1. Mở trình duyệt → F12 (Developer Tools)
2. Vào tab **Network**
3. Reload trang `/chat`
4. Tìm request đến `http://localhost:8000/ready`
5. Kiểm tra:
   - ✅ **200 OK**: Kết nối thành công
   - ❌ **Failed / CORS error**: Backend chưa chạy hoặc CORS chưa cấu hình

---

## 🔧 Xử lý lỗi thường gặp

### Lỗi: "Không kết nối được với server"

**Nguyên nhân:**
1. Backend chưa được khởi động
2. Backend đang load models (chưa sẵn sàng)
3. Port 8000 bị chặn hoặc đã được sử dụng
4. Firewall chặn kết nối

**Giải pháp:**
1. ✅ Kiểm tra backend đã chạy: `curl http://localhost:8000/health`
2. ✅ Kiểm tra port 8000 có đang được sử dụng:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```
3. ✅ Nếu port bị chiếm, đổi port trong `api_server.py` hoặc dùng:
   ```bash
   python -m uvicorn api_server:app --host 0.0.0.0 --port 8001
   ```
   Và cập nhật `environment.ts`: `apiBaseUrl: 'http://localhost:8001'`

### Lỗi: "Models đang tải, vui lòng đợi..."

**Giải pháp:**
- Đợi thêm vài phút (models đang load lần đầu)
- Kiểm tra console backend xem có lỗi không
- Kiểm tra đủ RAM/GPU để load models

### Lỗi: CORS error

**Giải pháp:**
- Backend đã cấu hình CORS cho phép tất cả origins (`allow_origins=["*"]`)
- Nếu vẫn lỗi, kiểm tra biến môi trường `ALLOWED_ORIGINS`

---

## 📝 Thứ tự khởi động đúng:

1. ✅ **Bước 1**: Khởi động Backend API (đợi models load xong)
2. ✅ **Bước 2**: Khởi động Frontend Angular
3. ✅ **Bước 3**: Mở trình duyệt → http://localhost:4200/chat

---

## 🆘 Cần hỗ trợ?

- Kiểm tra log backend trong terminal
- Kiểm tra console trình duyệt (F12)
- Kiểm tra Network tab trong Developer Tools

