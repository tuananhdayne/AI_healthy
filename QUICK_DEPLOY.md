# Hướng dẫn Deploy Firebase Function - Quick Start

## Bước 1: Cài đặt Firebase CLI (nếu chưa có)

**Cách 1: Cài global (khuyến nghị)**
```bash
npm install -g firebase-tools
```

**Cách 2: Dùng npx (không cần cài global)**
- Đã cài `firebase-tools` vào project rồi, có thể dùng `npx firebase-tools`

## Bước 2: Đăng nhập Firebase (lần đầu)

```bash
cd AI-Web/functions
npx firebase-tools login
```

Hoặc nếu đã cài global:
```bash
firebase login
```

## Bước 3: Khởi tạo Firebase project (nếu chưa có)

```bash
cd AI-Web
npx firebase-tools init functions
```

Chọn:
- Project: `giadienweb` (hoặc project ID của bạn)
- Language: TypeScript
- ESLint: Yes (hoặc No tùy bạn)

## Bước 4: Build TypeScript

```bash
cd AI-Web/functions
npm run build
```

## Bước 5: Deploy function

```bash
# Deploy function sendMedicineReminder
npx firebase-tools deploy --only functions:sendMedicineReminder
```

Hoặc nếu đã cài global:
```bash
firebase deploy --only functions:sendMedicineReminder
```

## Bước 6: Kiểm tra function đã deploy

Sau khi deploy thành công, function sẽ có URL:
```
https://us-central1-giadienweb.cloudfunctions.net/sendMedicineReminder
```

## Bước 7: Bật lại email reminder trong code

Mở file: `AI-Web/src/app/services/notification.service.ts`

Tìm dòng 150-156, bỏ comment:
```typescript
// Bỏ comment này:
const user = this.authService.getCurrentUser();
if (user && user.email) {
  this.sendEmailReminder(user.email, reminder).catch((err: any) => {
    console.error('❌ Error sending email reminder:', err);
  });
}
```

## Lưu ý

- Function hiện tại chỉ log, chưa gửi email thật
- Để gửi email thật, cần cấu hình SMTP trong `functions/src/index.ts`
- Xem file `DEPLOY_FIREBASE_FUNCTION.md` để biết thêm chi tiết

