# Hướng dẫn thiết lập tính năng nhắc nhở uống thuốc

## Tổng quan

Tính năng nhắc nhở uống thuốc cho phép người dùng:
- Tạo lịch nhắc nhở uống thuốc (hàng ngày, hàng tuần, hoặc một lần)
- Nhận thông báo qua email khi đến giờ uống thuốc
- Quản lý danh sách lịch nhắc nhở

## Cấu trúc

### Backend (Python)
- **`api_server.py`**: API endpoints để quản lý reminders
  - `POST /api/medicine-reminders`: Tạo reminder mới
  - `GET /api/medicine-reminders/{user_id}`: Lấy danh sách reminders
  - `DELETE /api/medicine-reminders/{reminder_id}`: Xóa reminder
  - `POST /api/medicine-reminders/check`: Kiểm tra và gửi thông báo (gọi định kỳ)

- **`medicine_reminder_scheduler.py`**: Scheduled task chạy định kỳ để kiểm tra và gửi thông báo

### Frontend (Angular)
- **`medicine-reminder.component.ts/html/scss`**: Component quản lý reminders
- **`medicine-reminder.service.ts`**: Service gọi API
- Route: `/medicine-reminder`

### Firebase Functions
- **`sendMedicineReminder`**: Function gửi email nhắc nhở

## Cài đặt

### 1. Backend

#### Cài đặt dependencies
```bash
pip install requests
```

#### Chạy API server
```bash
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

#### Chạy scheduler (terminal riêng)
```bash
python medicine_reminder_scheduler.py
```

Scheduler sẽ kiểm tra reminders mỗi 60 giây và gửi thông báo khi đến giờ.

### 2. Frontend

Component đã được tích hợp vào routing. Truy cập `/medicine-reminder` để quản lý lịch nhắc nhở.

### 3. Firebase Functions

#### Deploy function gửi email
```bash
cd AI-Web/functions
npm install
firebase deploy --only functions:sendMedicineReminder
```

## Sử dụng

### Tạo lịch nhắc nhở

1. Đăng nhập vào hệ thống
2. Vào trang "Nhắc nhở" từ menu
3. Click "Thêm lịch nhắc nhở"
4. Điền thông tin:
   - Tên thuốc (bắt buộc)
   - Giờ uống (bắt buộc)
   - Lặp lại: Hàng ngày / Hàng tuần / Một lần
   - Ngày trong tuần (nếu chọn hàng tuần)
   - Ghi chú (tùy chọn)
5. Click "Tạo"

### Xem danh sách reminders

Trang "Nhắc nhở" hiển thị tất cả reminders đang hoạt động của bạn.

### Sửa/Xóa reminder

- Click "Sửa" để chỉnh sửa
- Click "Xóa" để xóa reminder

## Cấu hình

### Thay đổi tần suất kiểm tra

Trong `medicine_reminder_scheduler.py`, thay đổi:
```python
time.sleep(60)  # Thay 60 thành số giây mong muốn
```

### Cấu hình email

Hiện tại function `sendMedicineReminder` chỉ log. Để gửi email thật:

1. Cài đặt nodemailer hoặc SendGrid
2. Cấu hình SMTP credentials
3. Cập nhật code trong `AI-Web/functions/src/index.ts`

## Lưu ý

- Reminders hiện được lưu trong memory của API server (sẽ mất khi restart)
- Để lưu vĩnh viễn, cần tích hợp với Firestore hoặc database
- Email notification cần cấu hình SMTP để hoạt động thực tế

## Tích hợp với Firestore (TODO)

Để lưu reminders vào Firestore:

1. Cài đặt Firebase Admin SDK trong Python backend
2. Cập nhật API endpoints để lưu/đọc từ Firestore
3. Cập nhật frontend service để đồng bộ với Firestore

