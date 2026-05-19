# Chương 5. Triển khai hệ thống

## 5.1. Quá trình triển khai hệ thống
Dựa trên thiết kế chi tiết ở Chương 2, nhóm triển khai hệ thống chatbot y tế theo chuỗi bước tuần tự: chuẩn hóa dữ liệu và kho tri thức, xây dựng backend FastAPI, tích hợp bảo mật Firebase, phát triển giao diện Angular, hoàn thiện pipeline AI/RAG và cuối cùng đóng gói triển khai. Mục tiêu là hình thành một hệ sinh thái thống nhất, vận hành ổn định từ tầng phần cứng (máy chủ) tới trải nghiệm người dùng cuối.

### 5.1.1. Chuẩn bị cơ sở dữ liệu và kho tri thức
- **Firestore làm CSDL giao dịch**: khởi tạo các collection `users`, `healthProfiles`, `chatSessions`, `medicineReminders`. Mỗi document có khóa chính là UID hoặc session ID, kèm timestamp và metadata để hỗ trợ truy vấn realtime.
- **Chuẩn hóa schema**: định nghĩa rõ khóa ngoại lô-gic (ví dụ `medicineReminders.userId` tham chiếu `users.uid`), đặt chỉ số (indexes) trên các trường `userId`, `nextReminderTime` để truy xuất nhanh lịch nhắc.
- **Kho tri thức RAG**: xây dựng bộ tài liệu y tế tiếng Việt, chạy script `build_faiss.py` để tạo embeddings bằng Sentence-BERT và lưu thành các file `.faiss` riêng cho từng intent (đau bụng, sốt, lo âu,...). Mỗi record gồm `text`, `intent`, `vector`, `source` giúp truy vết nguồn.
- **Tối ưu truy vấn vector**: FAISS sử dụng index IVF + Flat phù hợp kích thước dữ liệu hiện tại. Khi cần mở rộng, có thể chuyển sang HNSW để tăng tốc độ tìm kiếm tương đồng.

### 5.1.2. Phát triển Backend API với FastAPI
- **Khởi tạo dự án**: cấu hình `api_server.py` làm entry point, cài đặt `fastapi`, `uvicorn`, `pydantic`, cùng các module nội bộ (`chatbot`, `intent`, `rag`, `generator`).
- **Kiến trúc module**:
  1. **Models & Schemas**: định nghĩa `ChatRequest`, `MedicineReminderRequest`, `ChatResponse`, đảm bảo dữ liệu vào/ra được kiểm soát chặt.
  2. **Services**: `chatbot.py` giữ toàn bộ logic điều phối (intent, follow-up, RAG guard, risk). `firestore_service.py` chịu trách nhiệm tương tác Firestore, `medicine_reminder_scheduler.py` xử lý tác vụ nền.
  3. **Controllers (Endpoints)**: `/api/chat`, `/api/medicine-reminders`, `/api/health-profile/exercise-suggestion`, `/api/chat/reset`, `/ready`, `/health`.
- **Luồng xử lý một request chat**:
  - FastAPI nhận JSON từ frontend → kiểm tra trạng thái models → gửi vào `run_chat_pipeline()`.
  - Pipeline phân loại intent, xác định follow-up/topic shift, khóa intent khi cần, trích xuất triệu chứng, đánh giá rủi ro.
  - RAG Gate quyết định có truy vấn FAISS không; nếu có, ghép context với history và health profile rồi chuyển cho Gemini.
  - Kết quả trả về gồm câu trả lời, intent, confidence, risk, danh sách nguồn, trạng thái (safety/clarification/rag_high_confidence/gemini_fallback).

### 5.1.3. Tích hợp xác thực và bảo mật
- **Firebase Authentication**: frontend dùng `AngularFireAuth` để đăng nhập (Email/Password, Google). Backend nhận `user_id`, `user_email` từ client và có thể mở rộng thêm bước verify token (ID Token) để tăng bảo mật.
- **Quản lý phiên & state**: `session_id` được sinh ở frontend hoặc backend. Backend duy trì `conversation_states` trong bộ nhớ để nhớ lịch sử tối đa 6 lượt. Khi người dùng reset hoặc logout, endpoint `/api/chat/reset` xóa state tương ứng.
- **Bảo vệ API**: cấu hình CORS theo biến `ALLOWED_ORIGINS`, giới hạn truy cập từ domain được phép. Các biến môi trường (`GEMINI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `PORT`) được lưu trong file `.env` riêng cho dev/prod.
- **An toàn dữ liệu**: khi Firestore lỗi, backend chuyển sang lưu trữ tạm trong `app.state` để tránh mất nhắc thuốc. Log cảnh báo được in ra console để đội vận hành can thiệp.

### 5.1.4. Xây dựng giao diện người dùng Angular
- **Khởi tạo dự án**: `AI-Web/` sử dụng Angular CLI 15, tích hợp `@angular/fire` để kết nối Firebase, `rxjs` để quản lý luồng dữ liệu realtime.
- **Thành phần giao diện chính**:
  - **ChatInterfaceComponent**: hiển thị hội thoại, gửi câu hỏi, render reply cùng sources, cảnh báo an toàn, câu hỏi làm rõ.
  - **HealthProfileComponent**: cho phép nhập chiều cao, cân nặng, mức vận động; gọi API `/api/health-profile/exercise-suggestion` và hiển thị JSON kết quả.
  - **MedicineReminderComponent**: CRUD lịch nhắc thuốc, đồng bộ realtime với Firestore.
- **Trải nghiệm người dùng**: sử dụng SCSS tùy chỉnh trong `styles.scss`, thiết kế responsive, hỗ trợ chế độ sáng/tối. Thêm animation nhẹ khi xuất hiện reply để tạo cảm giác hội thoại tự nhiên.
- **Kết nối với backend**: services như `chat.service.ts`, `reminder.service.ts` sử dụng `HttpClient` gọi các endpoint FastAPI, xử lý lỗi (retry, hiển thị toast) và đính kèm thông tin người dùng.

### 5.1.5. Hoàn thiện pipeline AI, RAG và dịch vụ nền
- **PhoBERT Intent Classifier**: load lazy để tiết kiệm RAM; mô hình trả về top-2 intent và confidence, là cơ sở cho các nhánh follow-up/topic shift/pending confirm.
- **Sentence-BERT + FAISS**: retriever ưu tiên search theo intent (dữ liệu cùng chủ đề) để tránh leakage. Nếu confidence của doc < ngưỡng soft, pipeline fallback sang Gemini thuần tuý.
- **Gemini Generator**: nhận input gồm context, câu hỏi người dùng, intent, conversation history, cờ `is_follow_up` và `use_rag_priority`. Prompt được thiết kế đảm bảo câu trả lời y tế an toàn, không kê đơn, luôn khuyến nghị khám bác sĩ khi cần.
- **Risk & Clarification Layer**: trước khi trả kết quả, pipeline kiểm tra `risk == "high"` để đưa ra cảnh báo. Nếu câu hỏi mơ hồ, hệ thống dựng câu hỏi làm rõ tương ứng intent.
- **Medicine Reminder Scheduler**: script Python hoặc Firebase Scheduled Function gọi `/api/medicine-reminders/check`, gửi email qua Cloud Functions khi đến giờ uống thuốc, cập nhật `nextReminderTime` để tránh trùng lặp.

### 5.1.6. Đóng gói, triển khai và vận hành
- **Triển khai backend**: chạy `uvicorn api_server:app --host 0.0.0.0 --port 8000` trên Windows Server hoặc Ubuntu. Với môi trường production, dùng systemd service hoặc Docker container để tự động restart.
- **Triển khai frontend**: `ng build --configuration production`, deploy thư mục `dist` lên Firebase Hosting hoặc Nginx. Có thể cấu hình CloudFront/CDN để giảm độ trễ.
- **Biến môi trường và bí mật**: mỗi môi trường (dev/staging/prod) có file `.env` riêng chứa API key Gemini, đường dẫn service account, danh sách origin được phép.
- **Giám sát**: sử dụng `/health` cho liveness probe, `/ready` cho readiness. Log Uvicorn và pipeline (intent, rag_mode, stage) được ghi vào console; có thể thu thập qua ELK/Cloud Logging để phân tích.
- **Kiểm thử và bàn giao**: kiểm tra toàn bộ luồng chat (symptom, dinh dưỡng, tư vấn luyện tập), thử nghiệm scheduler gửi email, xác thực login/logout, đảm bảo frontend render tốt trên desktop/laptop. Sau khi đạt yêu cầu, ghi nhận checklist vận hành (truy cập server, cập nhật FAISS, xoá session cũ) và chuyển giao cho đội support.

## 5.2. Môi trường và thành phần triển khai
### 5.2.1. Môi trường triển khai
| Môi trường | Thành phần chính | Ghi chú |
| --- | --- | --- |
| Phát triển local | Windows 11, Python 3.10+, Node.js 18+, Angular CLI 15, Firebase Emulator (tùy chọn) | Sử dụng `start_backend.bat` và `ng serve` để debug nhanh. |
| Triển khai server/cloud | Ubuntu 22.04 LTS (hoặc Windows Server), Python 3.10+, Uvicorn/Gunicorn, Docker (tùy chọn), Firebase Cloud | Deploy backend như service (systemd/Docker). Frontend build `ng build` và host trên Firebase Hosting hoặc Nginx. |
| Ngôn ngữ / Framework | Python (FastAPI, asyncio), Angular 15, Typescript, Firebase Admin SDK, Gemini API | Kho model AI đặt trên ổ đĩa máy chủ hoặc volume Docker. |

### 5.2.2. Thành phần triển khai
- **Frontend (Angular 15)**: thư mục `AI-Web/`, sử dụng `@angular/fire` để tương tác Firebase Auth/Firestore, render lịch sử hội thoại, hồ sơ người dùng, lịch nhắc thuốc.
- **Backend (FastAPI + Uvicorn)**: file [api_server.py](api_server.py) khởi tạo pipeline, exposes REST endpoints `/api/chat`, `/api/medicine-reminders`, `/api/health-profile/exercise-suggestion`, `/ready`, `/health`.
- **Pipeline AI**: [chatbot.py](chatbot.py) điều phối Intent Classifier (PhoBERT), Retriever Sentence-BERT + FAISS, Gemini Generator, và các tầng logic (follow-up, risk, clarification, health profile context).
- **Hệ thống RAG**: thư mục `rag/`, `embeddings/` chứa index FAISS cho từng chủ đề; `build_faiss.py` hỗ trợ tái xây dựng.
- **Mô hình AI**: `model/intent_model/` (PhoBERT fine-tuned) và Sentence-BERT checkpoint. Gemini API dùng biến môi trường API key.
- **Firebase (Firestore + Authentication)**: `firestore_service.py` quản lý lưu nhắc thuốc, hồ sơ sức khỏe; `AI-Web/firebase.json` cấu hình hosting; `functions/` chứa Cloud Functions gửi email/notification.
- **Dịch vụ nền**: `medicine_reminder_scheduler.py` cron job kiểm tra lịch nhắc, `start_backend.sh/.bat` để boot backend, logging xuất console + tích hợp Firestore nếu cần.

## 5.3. Quy trình cài đặt và cấu hình
### 5.3.1. Backend FastAPI
1. **Chuẩn bị môi trường**
   - Cài Python 3.10+ và tạo virtual env: `python -m venv .venv && .venv\Scripts\activate` (Windows) hoặc `source .venv/bin/activate` (Linux).
   - Cài đặt libs: `pip install -r requirements.txt`.
2. **Cấu hình biến môi trường**
   - `GOOGLE_APPLICATION_CREDENTIALS` trỏ tới `serviceAccountKey.json` để Firebase Admin SDK hoạt động.
   - `GEMINI_API_KEY`, `ALLOWED_ORIGINS`, `PORT`, `RELOAD` (tùy nhu cầu).
3. **Chuẩn bị model & index**
   - Đặt PhoBERT fine-tuned vào `model/intent_model/` (cấu trúc đã có).
   - Đặt FAISS index vào `embeddings/` và config retriever trong `rag/retriever.py`.
4. **Khởi chạy**
   - Dev: `uvicorn api_server:app --reload --port 8000` hoặc chạy `start_backend.bat`.
   - Prod: sử dụng `uvicorn`/`gunicorn` với `--workers 2` sau reverse proxy (Nginx) hoặc đóng gói Docker.
5. **Kết nối pipeline AI**
   - Khi server bật, event `startup` load Intent Classifier + Retriever và test pipeline. Nếu RAM hạn chế, cân nhắc lazy loading (đã hỗ trợ trong `chatbot.py`).

### 5.3.2. Frontend Angular
1. `cd AI-Web && npm install`.
2. Tạo file `src/environments/environment.ts` chứa `firebaseConfig`, `apiBaseUrl` (`http://localhost:8000`).
3. Chạy `npm run start` để mở `http://localhost:4200`, kiểm tra chat UI, health profile, lịch nhắc.
4. Build production: `npm run build` → output `AI-Web/dist`. Deploy lên Firebase Hosting (`firebase deploy`) hoặc serve qua Nginx.
5. Kết nối backend thông qua service lớp Angular (ví dụ `chat.service.ts`) gọi `/api/chat`, hiển thị reply + sources + lịch sử, đồng bộ Firestore để lưu hội thoại, hồ sơ.

### 5.3.3. Firebase và dịch vụ nền
1. **Firestore**
   - Tạo project Firebase, bật Firestore (mode production).
   - Tạo collections: `chatSessions`, `healthProfiles`, `medicineReminders`.
2. **Authentication**
   - Bật Email/Password hoặc Google Sign-In tùy nhu cầu.
   - Frontend dùng `AngularFireAuth` để đăng nhập, gửi `user_id`, `user_email` xuống backend.
3. **Firebase Config**
   - Deploy security rules (`AI-Web/firestore.rules`) và indexes (`AI-Web/firestore.indexes.json`).
   - `firebase.json` định nghĩa hosting + Cloud Functions.
4. **Cloud Functions / Scheduler**
   - Thư mục `AI-Web/functions/` chứa Node.js function gửi email nhắc thuốc (`sendMedicineReminder`). Deploy bằng `firebase deploy --only functions`.
   - Tác vụ cron: chạy `medicine_reminder_scheduler.py` mỗi phút (Windows Task Scheduler hoặc Linux cron) để hit endpoint `/api/medicine-reminders/check` hoặc chạy logic trực tiếp.

## 5.4. Các API chính
### 5.4.1. API Chat tư vấn sức khỏe
- **Endpoint**: `POST /api/chat`
- **Chức năng**: nhận `message`, `session_id`, `user_id`, điều phối pipeline Intent → Context detection → RAG Guard → Gemini sinh câu trả lời, trả thêm `intent`, `symptoms`, `risk`, `sources`, `stage`.
- **Luồng xử lý**: FastAPI gọi `_run_chat_pipeline()` trong `chatbot.py`, pipeline lazy-load models, quản lý `conversation_state`, truy xuất FAISS qua `Retriever`, fallback Gemini khi cần.
- **Vai trò RAG pipeline**: `Retriever.search_by_intent()` lấy context theo intent, gate strong/soft threshold trước khi truyền vào `generate_medical_answer()`.

### 5.4.2. API quản lý lịch nhắc nhở uống thuốc
- **Endpoints**: `POST /api/medicine-reminders`, `GET /api/medicine-reminders/{user_id}`, `DELETE /api/medicine-reminders/{reminder_id}`, `POST /api/medicine-reminders/check`.
- **Chức năng**: tạo/cập nhật/xóa nhắc nhở, đồng bộ Firestore, scheduler `check` endpoint để gửi thông báo.
- **Luồng dữ liệu**: frontend gửi thông tin thuốc, backend chuẩn hóa giờ, lưu Firestore (kèm `nextReminderTime`), scheduler đọc Firestore, gọi Cloud Function gửi email, cập nhật lần tiếp theo.
- **Vai trò**: mở rộng hệ thống từ tư vấn sang quản lý chăm sóc cá nhân.

### 5.4.3. API hồ sơ sức khỏe
- **Endpoint**: `POST /api/health-profile/exercise-suggestion`.
- **Chức năng**: nhận BMI, chiều cao, cân nặng, mức vận động; gọi Gemini tạo JSON kế hoạch tập luyện; frontend hiển thị ở tab hồ sơ.
- **Luồng dữ liệu**: user cập nhật hồ sơ → Firestore lưu → frontend gửi request → backend xây prompt + system instruction → Gemini trả JSON → backend chuẩn hóa.

### 5.4.4. API xác thực và quản trị
- **Health & readiness**: `GET /health`, `GET /ready` phục vụ monitoring, load balancer check.
- **Session reset**: `POST /api/chat/reset` xóa state hội thoại (dùng khi user refresh hoặc logout).
- **Authentication**: phía backend tin cậy user ID/email từ Firebase Auth token do frontend đính kèm; có thể mở rộng middleware verify ID token để bảo mật hơn.

## 5.5. Vận hành và giám sát
- **Khởi động dịch vụ**: dùng systemd/Docker để chạy `uvicorn api_server:app` như service. Frontend build và host tĩnh.
- **Kiểm tra trạng thái**: probes `GET /health` (liveness) và `GET /ready` (readiness). Log server in ra console, có thể ship sang Cloud Logging.
- **Giám sát lỗi/hiệu năng**: bật `uvicorn` access log, kết hợp Cloud Monitoring hoặc Prometheus exporter (tùy chọn). Theo dõi thời gian load models trên startup log.
- **Scheduler**: đảm bảo cron gọi `/api/medicine-reminders/check` mỗi phút, hoặc dùng Firebase Scheduled Functions. Nhật ký gửi email nằm trong Cloud Functions log.
- **Sao lưu cấu hình**: lưu `serviceAccountKey.json`, FAISS index, model weights trên storage an toàn. Dùng git + CI để triển khai frontend/backend.

## 5.6. Kết luận chương triển khai
Kiến trúc triển khai đã kết nối đầy đủ frontend Angular, backend FastAPI, pipeline AI (Intent + RAG + Gemini), Firebase và các dịch vụ nền. Quy trình cài đặt rõ ràng từ môi trường local đến server, bao gồm cấu hình Firestore, Authentication và scheduler. Hệ thống đáp ứng yêu cầu chức năng (tư vấn, nhắc thuốc, hồ sơ sức khỏe) lẫn yêu cầu phi chức năng (bảo trì, giám sát, mở rộng). Đây là nền tảng sẵn sàng mở rộng sang các kênh giao tiếp mới hoặc bổ sung mô-đun AI khác trong tương lai.
