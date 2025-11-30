# 🔐 Hệ Thống Xác Thực - Hướng Dẫn Nhanh

## ✅ Tính Năng Đã Triển Khai

### 1. Tên Tài Khoản Độc Nhất (Unique Username)
- Kiểm tra tên tài khoản tồn tại trong Firestore
- Không cho phép đăng ký 2 tài khoản cùng username
- Khi đăng ký, tên tài khoản là **bắt buộc**

### 2. Mã Hóa Mật Khẩu (Password Encryption)
- Mật khẩu được mã hóa bằng **Base64** trước khi lưu
- Khi đăng nhập, hệ thống giải mã và so sánh mật khẩu
- Mật khẩu không bao giờ lưu ở dạng plain text

### 3. Lưu Trữ Trên Firestore
- Collection: `userCredentials`
- Mỗi document chứa: uid, username, email, passwordHash, createdAt, updatedAt

---

## 📝 Cách Sử Dụng

### Đăng Ký Tài Khoản

```typescript
// URL: http://localhost:4200/register

// Form Fields:
- Tên tài khoản: john_doe (3-20 ký tự)
- Họ và tên: John Doe
- Email: john@example.com
- Số điện thoại: 0123456789
- Ngày sinh: 1990-01-01
- PIN Code: 123456
- Mật khẩu: myPassword123 (tối thiểu 6 ký tự)
- Xác nhận mật khẩu
- Đồng ý điều khoản

// Kết quả:
✅ Đăng ký thành công → Redirect đến /login sau 2 giây
❌ Tên tài khoản đã tồn tại → Hiển thị error message
```

### Đăng Nhập

```typescript
// URL: http://localhost:4200/login

// Form Fields:
- Tên tài khoản: john_doe
- Mật khẩu: myPassword123
- Ghi nhớ tài khoản: (tùy chọn)

// Kết quả:
✅ Đăng nhập thành công → Redirect đến /chat
❌ Tài khoản không tồn tại → Hiển thị error message
❌ Mật khẩu sai → Hiển thị error message
```

---

## 🗄️ Cấu Trúc Firestore

### Collection: `userCredentials`

```json
{
  "id": "doc_id_auto_generated",
  "uid": "user_1234567890",
  "username": "john_doe",
  "email": "john@example.com",
  "passwordHash": "bXlQYXNzd29yZDEyMw==",  // Base64 encoded
  "createdAt": "2025-11-18T10:30:00Z",
  "updatedAt": "2025-11-18T10:30:00Z"
}
```

---

## 🔧 API Reference

### AuthService Methods

#### 1. Đăng Ký
```typescript
async registerWithUsername(
  username: string,
  email: string,
  password: string
): Promise<User | null>
```

**Ví dụ:**
```typescript
const user = await this.authService.registerWithUsername(
  'john_doe',
  'john@example.com',
  'MyPassword123'
);

if (user) {
  console.log('Đăng ký thành công:', user);
} else {
  console.log('Đăng ký thất bại');
}
```

#### 2. Đăng Nhập
```typescript
async loginWithUsername(
  username: string,
  password: string
): Promise<User | null>
```

**Ví dụ:**
```typescript
const user = await this.authService.loginWithUsername('john_doe', 'MyPassword123');

if (user) {
  console.log('Đăng nhập thành công:', user.username);
} else {
  console.log('Đăng nhập thất bại');
}
```

#### 3. Kiểm Tra Username Độc Nhất
```typescript
async checkUsernameExists(username: string): Promise<boolean>
```

**Ví dụ:**
```typescript
const exists = await this.authService.checkUsernameExists('john_doe');
console.log('Username đã tồn tại?', exists); // true hoặc false
```

#### 4. Đăng Xuất
```typescript
logout(): Observable<void>
```

**Ví dụ:**
```typescript
this.authService.logout().subscribe(() => {
  console.log('Đã đăng xuất');
  this.router.navigate(['/login']);
});
```

---

## 📊 Flow Đăng Ký

```
User nhập form
    ↓
[Kiểm tra Validation]
    ├─ ❌ Invalid → Hiển thị lỗi
    └─ ✅ Valid → Tiếp tục
    ↓
[Kiểm tra Username độc nhất]
    ├─ ❌ Tồn tại → Error: "Tên tài khoản đã tồn tại"
    └─ ✅ Mới → Tiếp tục
    ↓
[Mã hóa Password]
    ↓ Base64(password)
    ↓
[Lưu vào Firestore]
    ├─ ❌ Lỗi → Error message
    └─ ✅ Thành công
    ↓
[Lưu localStorage]
    ↓
[Hiển thị Success Message]
    ↓
[Redirect /login sau 2s]
```

---

## 📊 Flow Đăng Nhập

```
User nhập form
    ↓
[Kiểm tra Validation]
    ├─ ❌ Invalid → Hiển thị lỗi
    └─ ✅ Valid → Tiếp tục
    ↓
[Tìm Username trong Firestore]
    ├─ ❌ Không tìm thấy → Error: "Tài khoản không tồn tại"
    └─ ✅ Tìm thấy → Tiếp tục
    ↓
[Giải mã Password từ Firestore]
    ↓ Base64Decode(passwordHash)
    ↓
[So sánh Password]
    ├─ ❌ Không khớp → Error: "Mật khẩu không chính xác"
    └─ ✅ Khớp → Tiếp tục
    ↓
[Lưu User vào localStorage]
    ↓
[Lưu Remember Me (tùy chọn)]
    ↓
[Redirect /chat]
```

---

## ⚙️ Cấu Hình FirebaseService

### Các Methods Hỗ Trợ

```typescript
// Tạo credentials mới
async createUserCredentials(
  credentials: Omit<UserCredentials, 'id' | 'createdAt' | 'updatedAt'>
): Promise<string>

// Kiểm tra username tồn tại
async checkUsernameExists(username: string): Promise<boolean>

// Lấy credentials bằng username
async getUserCredentialsByUsername(username: string): Promise<UserCredentials | null>

// Lấy credentials bằng email
async getUserCredentialsByEmail(email: string): Promise<UserCredentials | null>

// Cập nhật mật khẩu
async updateUserPassword(uid: string, newPasswordHash: string): Promise<void>

// Xóa credentials
async deleteUserCredentials(uid: string): Promise<void>
```

---

## 🧪 Testing Checklist

- [ ] Đăng ký tài khoản mới với username độc nhất
- [ ] Kiểm tra Firestore có tạo document mới trong `userCredentials`
- [ ] Thử đăng ký với username đã tồn tại → Phải hiển thị error
- [ ] Đăng nhập với username và password chính xác
- [ ] Kiểm tra localStorage có user data
- [ ] Đăng nhập với password sai → Phải hiển thị error
- [ ] Kiểm tra "Remember Me" → Lưu username lại
- [ ] Đăng xuất → localStorage được xóa
- [ ] Kiểm tra Base64 encoding của password

---

## 🚀 Nâng Cấp Được Khuyến Nghị

### 1. Thay Base64 bằng bcrypt
```bash
npm install bcryptjs
```

**Ưu điểm:**
- Bảo mật cao hơn
- Có salt và iterations
- Industry standard

### 2. Thêm 2-Factor Authentication (2FA)
- Email verification
- SMS verification
- Google Authenticator

### 3. Thêm Rate Limiting
- Giới hạn số lần đăng nhập sai
- Tạm khóa tài khoản sau X lần sai

### 4. Thêm Session Management
- Lưu session token trong Firestore
- Kiểm tra session expiration
- Refresh token mechanism

---

## 📞 Support

Để hiểu thêm chi tiết, xem file: `AUTHENTICATION_GUIDE.md`
