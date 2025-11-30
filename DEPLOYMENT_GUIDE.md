# 🚀 Hướng dẫn triển khai chatbot HealthyAI lên web

## 1. Kiến trúc tổng quan

- **Python backend**: `api_server.py` (FastAPI) gọi toàn bộ pipeline Intent + RAG + Gemma trong `chatbot.py`.
- **Frontend Angular**: thư mục `AI-Web/` hiển thị UI chat, đăng nhập Firebase, gọi API `/api/chat`.
- **Kênh giao tiếp**: REST JSON. Mỗi cuộc trò chuyện có `session_id` riêng để backend giữ ngữ cảnh.

```
Trình duyệt → Angular (ng serve / Firebase Hosting / Vercel)
            → gọi https://<domain-python>/api/chat (FastAPI + Uvicorn + GPU/CPU)
```

---

## 2. Chuẩn bị môi trường Python (API)

```bash
cd D:\CHAT BOT TTCS
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install fastapi uvicorn[standard]  # + các thư viện sẵn có của chatbot (torch, transformers, sentence-transformers, faiss, ...)
```

> Nếu bạn đang dùng file `requirements.txt` riêng, chỉ cần thêm `fastapi` và `uvicorn[standard]`.

### Chạy API cục bộ

```bash
python -m uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

Tuỳ chọn biến môi trường:

| Biến | Ý nghĩa |
| --- | --- |
| `PORT` | Đổi port (mặc định 8000) |
| `ALLOWED_ORIGINS` | Danh sách domain cho phép CORS, ví dụ `https://chat.example.com,http://localhost:4200` |
| `RELOAD` | `1` để bật reload trong môi trường dev |

### Triển khai API

- **Windows / Linux server**: dùng `uvicorn` + `pm2` hoặc `systemd`.
- **Docker**: đóng gói Python + model, publish port 8000.
- **Cloud Run / Azure Container Apps**: build image rồi deploy, nhớ mount model/FAISS.
- **Reverse proxy**: dùng Nginx/Traefik để ánh xạ `https://api.yourdomain.com → localhost:8000`.

---

## 3. Frontend Angular

```bash
cd D:\CHAT BOT TTCS\AI-Web
npm install
```

### Cấu hình endpoint

- **Dev**: file `src/environments/environment.ts` mặc định trỏ `http://localhost:8000`.
- **Prod**: chỉnh `src/environments/environment.prod.ts` thành domain API thật (ví dụ `https://api.yourdomain.com`).
- Ngoài ra có thể gán nhanh tại runtime:

```html
<script>
  window.__APP_API_URL__ = 'https://api.yourdomain.com';
</script>
```

### Chạy cục bộ

```bash
npm run start          # hoặc: ng serve --port 4200
```

- Mặc định UI sẽ gọi `http://localhost:8000/api/chat`, nên hãy đảm bảo API đang chạy.
- Đăng nhập Firebase vẫn hoạt động như trước.

### Build và deploy

```bash
ng build --configuration production
```

- Thư mục `dist/gia-dien-web/` là static site.
- Có thể deploy lên:
  - **Firebase Hosting** (đã có `firebase.json`).
  - **Vercel / Netlify / S3 + CloudFront**.
  - **Máy chủ Nginx** (copy thư mục dist rồi cấu hình Nginx phục vụ static).

> Nếu frontend và backend ở cùng domain, có thể reverse proxy `/api` về FastAPI để tránh CORS.

---

## 4. Luồng triển khai mẫu (Firebase Hosting + VM chạy FastAPI)

1. **VM/Server**:
   - Copy toàn bộ thư mục dự án.
   - Cài Python, tạo venv, cài dependencies, chạy `uvicorn api_server:app --host 0.0.0.0 --port 8000`.
   - Cấu hình reverse proxy/HTTPS (Nginx + certbot) → `https://api.healthyai.vn`.
2. **Frontend**:
   - `ng build --configuration production`.
   - `firebase deploy --only hosting`.
   - Trong `environment.prod.ts` đặt `apiBaseUrl: 'https://api.healthyai.vn'`.
3. **Kiểm thử**:
   - Mở `https://<firebase-app>.web.app/chat`.
   - Kiểm tra network tab gọi `https://api.healthyai.vn/api/chat`.

---

## 5. Mẹo vận hành

- Sử dụng `session_id` riêng cho từng tab để tránh lẫn ngữ cảnh.
- Giám sát log FastAPI để xem `intent`, `risk`, `stage` (đã được trả về cho UI).
- Với model lớn (Gemma), cân nhắc tải trước khi server khởi động và dùng GPU dành riêng.
- Nếu cần scale, tách retriever/Gemma sang dịch vụ riêng (microservice) và gọi qua gRPC/REST.

---

## 6. Checklist trước khi go-live

- [ ] Đã cấu hình HTTPS cho cả frontend + backend.
- [ ] CORS chỉ cho phép domain tin cậy.
- [ ] Kiểm thử các case: câu chào, báo nguy hiểm, yêu cầu làm rõ.
- [ ] Sao lưu FAISS + dữ liệu embeddings.
- [ ] Thiết lập giám sát tài nguyên (RAM, GPU) vì Gemma tiêu tốn đáng kể.

Chúc bạn triển khai thành công chatbot HealthyAI trên web! Nếu cần thêm automation (CI/CD, Dockerfile), hãy mở issue hoặc yêu cầu bổ sung. 💪

