# 📋 TỔNG QUAN THAY ĐỔI - Authentication System

## 🌐 Cập nhật 2025-11-21: Triển khai Chatbot Web End-to-End

- Thêm FastAPI (`api_server.py`) biến pipeline Python thành REST API (`/api/chat`, `/api/chat/reset`, `/health`).
- Nâng cấp `chatbot.py` để hỗ trợ đa phiên (`session_id`), trả về metadata (intent, risk, stage, sources).
- Tạo `DEPLOYMENT_GUIDE.md` hướng dẫn chi tiết run API + build Angular + deploy (Firebase Hosting / server riêng).
- Frontend Angular:
  - Thêm `ChatService` dùng `HttpClient` gọi API, chuẩn hóa response.
  - Nâng cấp `ChatUIComponent` (UI, history, trạng thái, hiển thị nguồn, xử lý lỗi, spinner).
  - Bổ sung môi trường `environment.ts`/`environment.prod.ts`, cấu hình file replacement trong `angular.json`, import `HttpClientModule`.
  - Cập nhật unit test `chat-ui.component.spec.ts`.

## ✨ Tính Năng Được Thêm

### 1. ✅ Tên Tài Khoản Độc Nhất (Unique Username)
- Kiểm tra username không trùng lặp trong Firestore
- Thêm field `username` vào form đăng ký
- Thay thế email bằng username trong form đăng nhập
- Error message: "Tên tài khoản đã tồn tại. Vui lòng chọn tên khác."

### 2. 🔐 Mã Hóa Mật Khẩu (Password Encryption)
- Sử dụng Base64 để mã hóa mật khẩu (có thể nâng cấp bcrypt)
- Mật khẩu không bao giờ lưu ở dạng plain text
- Mã hóa khi đăng ký, giải mã khi đăng nhập để so sánh

### 3. 💾 Lưu Trữ Trên Firestore
- Collection: `userCredentials`
- Mỗi document chứa: uid, username, email, passwordHash, createdAt, updatedAt
- Cho phép quản lý người dùng từ Firestore console

---

## 📝 Các File Được Sửa

### 1. `src/app/services/auth.service.ts` - ✅ CẬP NHẬT
**Thêm:**
- Interface `UserCredentials` - Định nghĩa cấu trúc credentials
- Method `encryptPassword()` - Mã hóa mật khẩu bằng Base64
- Method `decryptPassword()` - Giải mã mật khẩu
- Method `checkUsernameExists()` - Kiểm tra username độc nhất
- Method `getUserCredentialsByUsername()` - Lấy credentials từ Firestore
- Method `loginWithUsername()` - Đăng nhập bằng username
- Method `registerWithUsername()` - Đăng ký bằng username

**Sửa:**
- Thêm `username` field vào User interface
- Inject `FirebaseService` vào constructor
- Cập nhật login/register methods để support username

### 2. `src/app/services/firebase.service.ts` - ✅ CẬP NHẬT
**Thêm:**
- Interface `UserCredentials` - Định nghĩa cấu trúc
- Method `createUserCredentials()` - Tạo credentials mới
- Method `checkUsernameExists()` - Kiểm tra username
- Method `getUserCredentialsByUsername()` - Lấy credentials bằng username
- Method `getUserCredentialsByEmail()` - Lấy credentials bằng email
- Method `updateUserPassword()` - Cập nhật mật khẩu
- Method `deleteUserCredentials()` - Xóa credentials

**Lợi ích:**
- Tập trung quản lý Firestore operations
- Dễ bảo trì và nâng cấp

### 3. `src/app/login/login.component.ts` - ✅ CẬP NHẬT
**Sửa:**
- Thay đổi form field từ `email` thành `username`
- Gọi `authService.loginWithUsername()` thay vì Firebase auth
- Thêm xử lý async/await cho login
- Thêm Remember Me functionality
- Thêm error/success messages

### 4. `src/app/login/login.component.html` - ✅ CẬP NHẬT
**Sửa:**
- Thay trường input "Email" thành "Tên tài khoản"
- Thêm alert box để hiển thị error messages
- Thêm icon user cho username field

### 5. `src/app/register/register.component.ts` - ✅ CẬP NHẬT
**Thêm:**
- Field `username` với validation: 3-20 ký tự
- Message success/error handling
- Gọi `authService.registerWithUsername()`

**Sửa:**
- Inject `AuthService` vào constructor
- Thêm logic xử lý đăng ký độc lập
- Thêm error/success messages
- Auto redirect đến login sau khi đăng ký thành công

### 6. `src/app/register/register.component.html` - ✅ CẬP NHẬT
**Sửa:**
- Thêm field "Tên tài khoản" (bắt buộc, 3-20 ký tự)
- Thêm alert boxes cho error/success messages
- Validation messages cho username

### 7. `src/app/app.module.ts` - ✅ CẬP NHẬT
**Sửa:**
- Import `FirebaseService`
- Thêm `FirebaseService` vào providers

---

## 📦 Firestore Collection Structure

### Collection: `userCredentials`

```
{
  id: "auto_generated_doc_id",
  uid: "user_1234567890",
  username: "john_doe",
  email: "john@example.com",
  passwordHash: "am9obl9wYXNzd29yZA==",  // Base64 encoded
  createdAt: Timestamp,
  updatedAt: Timestamp
}
```

---

## 🔄 Flow Xác Thực

### Đăng Ký
```
Form Submit
    ↓
Validate Form (username 3-20 chars, password min 6 chars)
    ↓
Check Username Exists in Firestore
    ├─ If exists: ❌ Error "Tên tài khoản đã tồn tại"
    └─ If not: Continue
    ↓
Encrypt Password (Base64)
    ↓
Save to Firestore userCredentials
    ├─ On Success: ✅ "Đăng ký thành công!"
    └─ On Error: ❌ Error message
    ↓
Save User to localStorage
    ↓
Redirect to /login (after 2 seconds)
```

### Đăng Nhập
```
Form Submit
    ↓
Validate Form
    ↓
Get Credentials from Firestore by Username
    ├─ If not found: ❌ "Tài khoản không tồn tại"
    └─ If found: Continue
    ↓
Decrypt Password & Compare with Input
    ├─ If match: ✅ Continue
    └─ If not match: ❌ "Mật khẩu không chính xác"
    ↓
Save User to localStorage
    ↓
Save Remember Me (if checked)
    ↓
Redirect to /chat
```

---

## 🧪 Testing Manual

### Test Case 1: Đăng Ký Tài Khoản Mới
1. Navigate to `http://localhost:4200/register`
2. Fill form:
   - Tên tài khoản: `testuser123`
   - Email: `test@example.com`
   - Password: `Test123!`
3. Click Đăng Ký
4. **Expected:** Success message, redirect to login
5. **Verify:** Check Firestore → `userCredentials` collection has new document

### Test Case 2: Đăng Ký Trùng Username
1. Navigate to register again
2. Use same username: `testuser123`
3. **Expected:** Error "Tên tài khoản đã tồn tại"

### Test Case 3: Đăng Nhập Chính Xác
1. Navigate to `http://localhost:4200/login`
2. Enter:
   - Tên tài khoản: `testuser123`
   - Password: `Test123!`
3. Click Đăng Nhập
4. **Expected:** Redirect to `/chat`, localStorage has user data

### Test Case 4: Đăng Nhập Sai Mật Khẩu
1. Use same username, wrong password
2. **Expected:** Error "Mật khẩu không chính xác"

### Test Case 5: Username Không Tồn Tại
1. Use non-existent username
2. **Expected:** Error "Tài khoản không tồn tại"

---

## 🚀 Hướng Dẫn Deployment

### 1. Cập nhật Firestore Security Rules
- Copy content từ `FIRESTORE_SECURITY_RULES.txt`
- Paste vào Firebase Console → Firestore → Rules
- Publish rules

### 2. Test trên Production
- Build: `ng build --prod`
- Deploy: `firebase deploy`

### 3. Tạo Firestore Index (nếu cần)
- Firebase console sẽ suggest khi cần
- Một index cho collection `userCredentials` trên field `username`

---

## 📚 Tài Liệu Thêm

- `AUTHENTICATION_GUIDE.md` - Chi tiết đầy đủ
- `SETUP_QUICK_START.md` - Hướng dẫn nhanh
- `FIRESTORE_SECURITY_RULES.txt` - Security rules

---

## ⚠️ Lưu Ý Quan Trọng

### Bảo Mật - Cần Nâng Cấp
1. **Base64 không phải encryption**: Cần thay bằng bcrypt hoặc crypto
2. **Firestore Rules**: Hiện chưa có authentication chặt
3. **HTTPS**: Đảm bảo HTTPS được bật trên production

### Khuyến Nghị
1. Thêm 2-Factor Authentication
2. Thêm rate limiting cho login
3. Thêm password reset functionality
4. Thêm email verification

---

## 🎯 Next Steps

1. ✅ Test local deployment
2. ⏳ Cập nhật Firestore Rules
3. ⏳ Thêm bcrypt để bảo mật hơn
4. ⏳ Thêm email verification
5. ⏳ Deploy to production

---

## 📞 Liên Hệ & Hỗ Trợ

Nếu có bất kỳ vấn đề nào, kiểm tra:
- Console logs (F12 → Console)
- Firestore console
- Firebase Auth logs
