# Hướng Dẫn Hệ Thống Xác Thực Người Dùng

## Tổng Quan

Hệ thống xác thực của ứng dụng GiaDienWeb đã được cập nhật để hỗ trợ:
- ✅ **Tên tài khoản độc nhất** - Không có hai tài khoản nào có cùng username
- ✅ **Mã hóa mật khẩu** - Mật khẩu được lưu mã hóa (Base64) trong Firestore
- ✅ **Lưu trữ trên Firestore** - Tất cả credentials được lưu an toàn trên Firestore

## Kiến Trúc Hệ Thống

### Collections trong Firestore

#### 1. `userCredentials` - Lưu trữ thông tin xác thực
```json
{
  "uid": "user_1234567890",
  "username": "john_doe",
  "email": "john@example.com",
  "passwordHash": "am9obl9wYXNzd29yZA==",  // Base64 mã hóa
  "createdAt": "2025-11-18T10:30:00Z",
  "updatedAt": "2025-11-18T10:30:00Z"
}
```

### Services

#### `AuthService` - Quản lý xác thực người dùng

**Các method chính:**

1. **`registerWithUsername(username, email, password)`**
   - Đăng ký tài khoản mới với username, email, password
   - Kiểm tra username có độc nhất hay không
   - Mã hóa password trước khi lưu
   - Return: `Promise<User | null>`

```typescript
const user = await this.authService.registerWithUsername(
  'john_doe',
  'john@example.com',
  'password123'
);
```

2. **`loginWithUsername(username, password)`**
   - Đăng nhập với username và password
   - Kiểm tra password so với hash lưu trữ
   - Return: `Promise<User | null>`

```typescript
const user = await this.authService.loginWithUsername(
  'john_doe',
  'password123'
);
```

3. **`checkUsernameExists(username)`**
   - Kiểm tra xem username đã tồn tại hay chưa
   - Return: `Promise<boolean>`

```typescript
const exists = await this.authService.checkUsernameExists('john_doe');
```

4. **`logout()`**
   - Đăng xuất người dùng
   - Clear localStorage

#### `FirebaseService` - Quản lý Firestore

**Các method chính:**

1. **`createUserCredentials(credentials)`**
   - Tạo credentials mới trong Firestore
   - Return: `Promise<string>` (document ID)

2. **`checkUsernameExists(username)`**
   - Kiểm tra username trong Firestore
   - Return: `Promise<boolean>`

3. **`getUserCredentialsByUsername(username)`**
   - Lấy credentials bằng username
   - Return: `Promise<UserCredentials | null>`

4. **`updateUserPassword(uid, newPasswordHash)`**
   - Cập nhật mật khẩu người dùng
   - Mật khẩu phải được mã hóa trước khi gửi

## Quy Trình Đăng Ký

1. Người dùng nhập: username, email, password
2. Kiểm tra username độc nhất
3. Mã hóa password bằng Base64
4. Lưu credentials vào Firestore collection `userCredentials`
5. Tạo session user trong localStorage
6. Redirect đến trang login

```typescript
// Trong RegisterComponent
onSubmit(): void {
  const { username, email, password } = this.registerForm.value;
  
  this.authService.registerWithUsername(username, email, password)
    .then(user => {
      if (user) {
        this.router.navigate(['/login']);
      }
    });
}
```

## Quy Trình Đăng Nhập

1. Người dùng nhập: username, password
2. Tìm credentials trong Firestore bằng username
3. Kiểm tra password:
   - Lấy passwordHash từ Firestore
   - Giải mã hash
   - So sánh với password nhập vào
4. Nếu đúng: Tạo session user và redirect đến chat
5. Nếu sai: Hiển thị error message

```typescript
// Trong LoginComponent
onSubmit(): void {
  const { username, password } = this.loginForm.value;
  
  this.authService.loginWithUsername(username, password)
    .then(user => {
      if (user) {
        this.router.navigate(['/chat']);
      } else {
        this.showError = true;
        this.errorMessage = 'Tài khoản hoặc mật khẩu không chính xác';
      }
    });
}
```

## Bảo Mật - Yêu Cầu Nâng Cấp

### ⚠️ Hiện Tại (Base64)
- Base64 không phải encryption thực sự
- Chỉ dùng để encode, không encode dữ liệu nhạy cảm

### 💡 Nâng Cấp Được Khuyến Nghị

#### 1. Dùng bcrypt thay vì Base64
```bash
npm install bcryptjs
```

```typescript
import * as bcrypt from 'bcryptjs';

// Mã hóa khi đăng ký
const passwordHash = await bcrypt.hash(password, 10);

// Kiểm tra khi đăng nhập
const isPasswordValid = await bcrypt.compare(password, passwordHash);
```

#### 2. Dùng Firebase Authentication
```typescript
// Thay vì lưu credentials tự, dùng Firebase Auth
import { createUserWithEmailAndPassword } from 'firebase/auth';

const userCredential = await createUserWithEmailAndPassword(
  auth, 
  email, 
  password
);
```

#### 3. Thêm Firestore Security Rules
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /userCredentials/{document=**} {
      allow read, write: if request.auth.uid == resource.data.uid;
    }
  }
}
```

## Cấu Trúc User Model

```typescript
export interface User {
  id: string;              // user_1234567890
  email: string;           // john@example.com
  fullName: string;        // John Doe
  username: string;        // john_doe
  role: 'user' | 'admin';  // user
  token?: string;
}

export interface UserCredentials {
  id?: string;             // Firestore document ID
  uid: string;             // user_1234567890
  username: string;        // john_doe
  email: string;           // john@example.com
  passwordHash: string;    // am9obl9wYXNzd29yZA==
  createdAt?: Timestamp;
  updatedAt?: Timestamp;
}
```

## Form Validation

### Đăng Ký (RegisterComponent)
- `username`: bắt buộc, 3-20 ký tự
- `email`: bắt buộc, định dạng email hợp lệ
- `password`: bắt buộc, tối thiểu 6 ký tự
- `confirmPassword`: phải khớp với password
- `agreeTerms`: bắt buộc phải đồng ý

### Đăng Nhập (LoginComponent)
- `username`: bắt buộc, tối thiểu 3 ký tự
- `password`: bắt buộc, tối thiểu 6 ký tự
- `rememberMe`: tùy chọn

## Testing

### Test Đăng Ký
1. Mở ứng dụng → điều hướng đến `/register`
2. Nhập: username = `testuser123`, email = `test@example.com`, password = `Test123!`
3. Submit form
4. Kiểm tra Firestore: vào `userCredentials` collection, xem có document mới không

### Test Đăng Nhập
1. Mở ứng dụng → điều hướng đến `/login`
2. Nhập username = `testuser123`, password = `Test123!`
3. Submit form
4. Kiểm tra: user được redirect đến `/chat` và localStorage có data user

### Test Username Độc Nhất
1. Đăng ký lần 2 với cùng username = `testuser123`
2. Kỳ vọng: hiển thị error "Tên tài khoản đã tồn tại"

## Troubleshooting

### Lỗi: "userCredentials collection not found"
- **Nguyên nhân**: Firestore chưa có collection
- **Giải pháp**: Tạo collection `userCredentials` trong Firestore console

### Lỗi: "Property 'username' is missing"
- **Nguyên nhân**: User interface không có property username
- **Giải pháp**: Đảm bảo đã cập nhật User interface với username

### Mật khẩu không giải mã được
- **Nguyên nhân**: Lỗi mã hóa/giải mã
- **Giải pháp**: Kiểm tra Base64 encoding/decoding

## Tài Liệu Tham Khảo

- [Firebase Firestore Documentation](https://firebase.google.com/docs/firestore)
- [bcryptjs Documentation](https://github.com/dcodeIO/bcrypt.js)
- [Firebase Auth Documentation](https://firebase.google.com/docs/auth)
