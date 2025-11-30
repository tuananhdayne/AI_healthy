# Hướng dẫn Deploy Firebase Function để gửi Email Reminder

## Vấn đề hiện tại
- Frontend đang gọi Firebase Function `sendMedicineReminder` nhưng function chưa được deploy
- Lỗi CORS: `Access-Control-Allow-Origin header is not present`

## Giải pháp

### Bước 1: Cài đặt dependencies
```bash
cd AI-Web/functions
npm install
```

**Lưu ý:** Nếu chưa có Firebase CLI, bạn có 2 cách:

**Cách 1: Cài đặt global (khuyến nghị)**
```bash
npm install -g firebase-tools
```

**Cách 2: Dùng npx (không cần cài global)**
```bash
# Thay vì dùng: firebase deploy
# Dùng: npx firebase-tools deploy
```

### Bước 2: Deploy function

**Nếu đã cài Firebase CLI global:**
```bash
# Deploy function sendMedicineReminder
firebase deploy --only functions:sendMedicineReminder

# Hoặc deploy tất cả functions
firebase deploy --only functions
```

**Nếu chưa cài global (dùng npx):**
```bash
# Deploy function sendMedicineReminder
npx firebase-tools deploy --only functions:sendMedicineReminder

# Hoặc deploy tất cả functions
npx firebase-tools deploy --only functions
```

**Lưu ý:** Lần đầu deploy cần đăng nhập:
```bash
npx firebase-tools login
```

### Bước 3: Kiểm tra function đã deploy
Sau khi deploy, function sẽ có URL:
```
https://us-central1-giadienweb.cloudfunctions.net/sendMedicineReminder
```

### Bước 4: Bật lại email reminder trong code
Sau khi deploy thành công, mở file:
`AI-Web/src/app/services/notification.service.ts`

Tìm dòng:
```typescript
// TODO: Bật lại sau khi deploy Firebase Function
/*
const user = this.authService.getCurrentUser();
if (user && user.email) {
  this.sendEmailReminder(user.email, reminder).catch((err: any) => {
    console.error('❌ Error sending email reminder:', err);
  });
}
*/
```

Và bỏ comment:
```typescript
const user = this.authService.getCurrentUser();
if (user && user.email) {
  this.sendEmailReminder(user.email, reminder).catch((err: any) => {
    console.error('❌ Error sending email reminder:', err);
  });
}
```

## Cấu hình Email (Tùy chọn)

Để gửi email thực tế, cần cấu hình trong `AI-Web/functions/src/index.ts`:

1. Cài đặt nodemailer:
```bash
cd AI-Web/functions
npm install nodemailer
npm install --save-dev @types/nodemailer
```

2. Cập nhật code trong `sendMedicineReminder` function để gửi email thật.

## Lưu ý
- Hiện tại function chỉ log, chưa gửi email thật
- Cần cấu hình SMTP (Gmail, SendGrid, etc.) để gửi email thực tế
- Email reminder đã được tạm thời tắt trong frontend để tránh lỗi CORS

