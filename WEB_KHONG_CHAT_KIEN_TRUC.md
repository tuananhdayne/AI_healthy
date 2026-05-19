# Kiến trúc web (không bao gồm chức năng chat)

Tài liệu này mô tả các file/web module **không trực tiếp thuộc pipeline chat**, và tóm tắt thêm vai trò của `api_server.py` như cổng API giữa web và backend chatbot.

---

## 1. Các file backend web hỗ trợ (ngoài chat)

### 1.0 api_server.py – Cổng API giữa web và chatbot

- Vai trò tổng quan:
  - Là server FastAPI lắng nghe các request HTTP từ ứng dụng web (Angular) và các client khác.
  - Cấu hình CORS để web có thể gọi các endpoint như `/api/chat`, `/api/health-profile/*`, `/api/medicine-reminders/*`.
  - Trong sự kiện `startup`, tiến hành load model, RAG, kiểm tra Gemini và gán vào module `chatbot.py`.
- Chức năng chính liên quan tới web (không đi sâu vào pipeline chat):
  - `GET /health`: kiểm tra tình trạng server (healthcheck) cho web/deployment.
  - `GET /ready`: cho frontend biết models đã sẵn sàng hay chưa để hiển thị giao diện chat phù hợp.
  - Các endpoint tiện ích khác phục vụ web như gợi ý tập luyện, hồ sơ sức khỏe, nhắc uống thuốc (ví dụ `/api/health-profile/exercise-suggestion`, các route cho medicine reminders...).
  - Đóng vai trò "cầu nối" giữa thế giới HTTP/JSON của web và các hàm Python phía sau (chatbot, Firestore service, scheduler nhắc thuốc).

### 1.1 firestore_service.py – Dịch vụ làm việc với Firestore

- Vai trò tổng quan:
  - Cung cấp một lớp tiện ích Python để làm việc với **Google Firestore** từ backend.
  - Dùng cho hai loại dữ liệu chính:
    - Lưu **lịch sử hội thoại** (messages, chatSessions) – hiện tại frontend đang chủ động lưu.
    - Lưu **lịch nhắc uống thuốc** (medicineReminders).
- Chức năng chính:
  - `initialize_firestore()`
    - Khởi tạo Firestore client dùng `firebase_admin`.
    - Tự tìm file service account qua biến môi trường `FIREBASE_SERVICE_ACCOUNT_KEY` hoặc các đường dẫn mặc định.
    - Xử lý các trường hợp thiếu credential hoặc lỗi `DEFAULT_UNIVERSE_DOMAIN`.
  - `get_db()`
    - Trả về Firestore client toàn cục `_db` (đã được khởi tạo 1 lần).

- Các nhóm hàm nghiệp vụ:
  - **Conversation operations**:
    - `save_chat_message(...)`:
      - Lưu từng message (user/assistant) vào collection `messages`.
      - Gắn các trường: `userId`, `userEmail`, `sessionId`, `text`, `role`, `timestamp`, `metadata`.
    - `save_chat_session(...)`:
      - Tạo/cập nhật document trong collection `chatSessions`.
      - Đảm bảo mỗi session của user có title, `createdAt`, `updatedAt`.
  - **Medicine reminder operations**:
    - `save_medicine_reminder(reminder_data)`:
      - Lưu document vào collection `medicineReminders` với các trường đã chuyển sang kiểu/time phù hợp Firestore (`nextReminderTime`, `lastSent`, `createdAt`, ...).
      - Đổi tên các field từ snake_case (Python) sang camelCase cho Firestore (`user_id` → `userId`, ...).
    - (Các hàm khác trong phần sau file – ví dụ: cập nhật, xoá, lấy reminders – phục vụ hệ thống nhắc uống thuốc).

### 1.2 medicine_reminder_scheduler.py – Scheduler nhắc uống thuốc

- Vai trò:
  - Script Python chạy độc lập, có nhiệm vụ **gọi API backend định kỳ** để kiểm tra và gửi thông báo nhắc nhở uống thuốc.
- Cách hoạt động:
  - Biến `API_BASE_URL = "http://localhost:8000"` – trỏ tới server FastAPI.
  - `check_and_send_reminders()`:
    - Gửi request `POST` tới endpoint `/api/medicine-reminders/check` trên backend.
    - Đọc kết quả JSON, log số lượng thông báo đã gửi (`sent`).
  - `main()`:
    - In thông tin khởi động scheduler.
    - Vòng lặp vô hạn:
      - Mỗi 60 giây:
        - In timestamp hiện tại.
        - Gọi `check_and_send_reminders()`.
      - Bắt `KeyboardInterrupt` để dừng an toàn.
- Triển khai thực tế:
  - Có thể được chạy bằng tay: `python medicine_reminder_scheduler.py`.
  - Hoặc tích hợp vào cron/scheduler trên server Windows/Linux.

---

## 2. Cấu hình và dịch vụ Firebase/Firestore (thuộc AI-Web)

### 2.1 AI-Web/firebase.json – Cấu hình Firebase dự án web

- Mục `firestore`:
  - `database`: `(default)` – sử dụng database mặc định.
  - `location`: `asia-southeast1` – vùng của Firestore.
  - `rules`: `firestore.rules` – đường dẫn file rules.
  - `indexes`: `firestore.indexes.json` – đường dẫn file indexes.
- Mục `functions`:
  - `source`: `functions` – thư mục chứa Cloud Functions.
  - `ignore`: các file/thư mục không được deploy (`node_modules`, `.git`, log, `*.local`).
  - `predeploy`: lệnh chạy trước khi deploy functions:
    - `npm --prefix "$RESOURCE_DIR" run lint`
    - `npm --prefix "$RESOURCE_DIR" run build`

### 2.2 AI-Web/firestore.rules – Quy tắc bảo mật Firestore

- Định nghĩa quyền truy cập cho các collection chính:
  - `userCredentials` (lưu thông tin đăng nhập người dùng):
    - Chỉ cho phép người dùng đã xác thực đọc/ghi document của **chính mình** (so sánh `request.auth.uid` với `resource.data.uid`).
    - Cho phép tạo mới khi `request.auth != null`.
    - Không cho phép xóa (`allow delete: if false`).
  - `users` (profiles người dùng):
    - Người dùng chỉ được đọc/ghi document có `userId` trùng với `request.auth.uid`.
  - `messages` (lịch sử chat, cả user và assistant):
    - Cho phép tạo message mới khi đã đăng nhập.
    - Chỉ đọc/xóa message mà `userId` trùng với `request.auth.uid`.
  - `chatSessions` (danh sách phiên chat):
    - Tạo mới: user đã đăng nhập.
    - Đọc/cập nhật/xóa: chỉ cho phép chính chủ `userId`.
  - `medicineReminders` (nhắc uống thuốc):
    - Tạo mới: yêu cầu `request.auth.uid == request.resource.data.userId`.
    - Đọc/cập nhật/xóa: chỉ cho phép chính chủ.
- Fallback tạm thời:
  - `match /{document=**}` với điều kiện thời gian `request.time < timestamp.date(2025, 12, 18)` – cho phép tạm đọc/ghi các collection khác tới ngày nhất định (debug/dev).

### 2.3 AI-Web/functions/index.js – Cloud Function gửi email reset mật khẩu

- Vai trò:
  - Cloud Function HTTP (Node.js) dùng để **gửi email reset mật khẩu** cho người dùng.
- Thành phần:
  - Sử dụng các thư viện:
    - `firebase-functions`, `firebase-admin` để truy cập Firestore.
    - `nodemailer` để gửi email qua Gmail.
    - `cors` để cho phép gọi từ frontend.
  - Cấu hình Gmail:
    - `gmailEmail`, `gmailPassword` (App Password khi bật 2FA).
    - `nodemailer.createTransport({ service: 'gmail', auth: { user, pass } })`.
- Hàm chính `exports.sendResetPassword = functions.https.onRequest((req, res) => { ... })`:
  - Dùng CORS để xử lý request từ web.
  - Chỉ cho phép method `POST`.
  - Nhận `email`, `username` từ `req.body`.
  - Sinh mật khẩu mới ngẫu nhiên (8 ký tự) và mã hóa Base64 (`passwordHash`).
  - Tìm document `userCredentials` theo email:
    - Nếu không tìm thấy → trả lỗi 404 `Email không tồn tại`.
    - Nếu có → update `passwordHash`, `forceChangePassword`, `updatedAt`.
  - Gửi email chứa mật khẩu mới cho user.
  - Trả về `{ success: true }` nếu thành công, `{ error: ... }` nếu lỗi.

### 2.4 Các tài liệu cấu hình/xác thực khác

#### AI-Web/AUTHENTICATION_GUIDE.md – Hướng dẫn hệ thống xác thực

- Mô tả chi tiết kiến trúc xác thực:
  - Sử dụng collection `userCredentials` để lưu `uid`, `username`, `email`, `passwordHash`, `createdAt`, `updatedAt`.
  - `AuthService` trên frontend:
    - `registerWithUsername(username, email, password)` – đăng ký.
    - `loginWithUsername(username, password)` – đăng nhập.
    - `checkUsernameExists(username)` – kiểm tra trùng username.
    - `logout()` – đăng xuất.
  - `FirebaseService` trên frontend:
    - Tạo/đọc/cập nhật credentials trong Firestore.
- Quy trình đăng ký/đăng nhập, form validation, gợi ý nâng cấp bảo mật (dùng `bcrypt`, Firebase Auth, cải thiện Firestore Rules).

#### AI-Web/SETUP_QUICK_START.md – Hướng dẫn nhanh xác thực

- Tài liệu tóm tắt (quick-start) cho phần xác thực:
  - Tính năng đã triển khai: username độc nhất, mã hóa mật khẩu bằng Base64, lưu trên Firestore.
  - Cách dùng các màn hình `/register`, `/login`.
  - Cấu trúc collection `userCredentials` trong Firestore.
  - API của `AuthService` và `FirebaseService` (ở phía Angular).
  - Flow đăng ký và đăng nhập dạng sơ đồ bước.

---

## 3. Ứng dụng Angular (AI-Web/src) – Phần web giao diện người dùng

### 3.1 Cấu trúc chính

- `AI-Web/src/index.html`
  - File HTML gốc của ứng dụng Angular, chứa thẻ `<app-root></app-root>` để Angular mount.
- `AI-Web/src/main.ts`
  - Điểm vào (entry) của Angular, bootstrap module gốc (thường là `AppModule`).
- `AI-Web/src/styles.scss`
  - File stylesheet toàn cục cho toàn bộ ứng dụng web.
- `AI-Web/src/app/`
  - Chứa các module, component, service của ứng dụng (màn hình đăng nhập/đăng ký, dashboard, màn hình quản lý hồ sơ, health profile, nhắc thuốc, v.v.).
  - Các phần chat trực tiếp (ví dụ `ChatComponent`) thuộc chức năng chat nên không mô tả chi tiết ở tài liệu này.
- `AI-Web/src/environments/`
  - Chứa `environment.ts`, `environment.prod.ts` với cấu hình Firebase, API URL, ...

### 3.2 AI-Web/package.json – Thông tin project Angular

- Khai báo tên project (`GiaDienWeb`), version, scripts:
  - `ng serve`, `ng build`, `ng test`, `ng lint`, ...
- Khai báo dependencies:
  - `@angular/*`, `firebase`, `@angular/fire`, và các thư viện UI khác.
- Dùng cho việc cài đặt và build toàn bộ frontend.

### 3.3 AI-Web/README.md – Hướng dẫn Angular cơ bản

- Là README mặc định của Angular CLI:
  - Cách chạy `ng serve`, build, test, e2e,...
  - Liên kết tới tài liệu Angular CLI.

---

## 4. Tóm tắt mối liên hệ (web không chat)

- **firestore_service.py**: cầu nối giữa backend Python và Firestore cho việc lưu **messages**, **chatSessions**, **medicineReminders**.
- **medicine_reminder_scheduler.py**: scheduler bằng Python để định kỳ gọi API backend kiểm tra và gửi nhắc uống thuốc.
- **AI-Web/firebase.json + firestore.rules**: cấu hình và bảo vệ dữ liệu Firestore cho toàn bộ web app (users, userCredentials, messages, chatSessions, medicineReminders).
- **AI-Web/functions/index.js**: Cloud Function phục vụ nghiệp vụ **reset mật khẩu qua email**, không liên quan tới pipeline chat.
- **AUTHENTICATION_GUIDE.md + SETUP_QUICK_START.md**: tài liệu thiết kế và hướng dẫn nhanh hệ thống **xác thực user** trên web.
- **AI-Web/src (Angular app)**: giao diện người dùng (UI) của hệ thống, bao gồm các trang đăng nhập, đăng ký, profile, dashboard, nhắc thuốc, ...; các phần chat đã được mô tả riêng trong tài liệu backend chat.
