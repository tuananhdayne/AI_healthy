# 📋 CHI TIẾT CÁCH HOẠT ĐỘNG CỦA CHỨC NĂNG NHẮC NHỞ UỐNG THUỐC

## 🎯 TỔNG QUAN

Chức năng nhắc nhở uống thuốc là một hệ thống tự động giúp người dùng nhớ uống thuốc đúng giờ. Hệ thống hoạt động trên cả **Frontend (Angular)** và **Backend (Python FastAPI)**, sử dụng **Firebase Firestore** để lưu trữ dữ liệu và có thể gửi thông báo qua **Browser Notifications** và **Email**.

---

## 🏗️ KIẾN TRÚC HỆ THỐNG

### 1. **Frontend (Angular)**
- **Component**: `medicine-reminder.component.ts` - Giao diện quản lý lịch nhắc nhở
- **Service**: `medicine-reminder.service.ts` - Xử lý CRUD operations
- **Service**: `notification.service.ts` - Kiểm tra và gửi thông báo
- **Service**: `firebase.service.ts` - Tương tác trực tiếp với Firestore

### 2. **Backend (Python FastAPI)**
- **API Endpoints**: `api_server.py` - REST API cho medicine reminders
- **Scheduler**: `medicine_reminder_scheduler.py` - Script kiểm tra định kỳ (tùy chọn)
- **Firestore Service**: `firestore_service.py` - Lưu trữ dữ liệu vào Firestore

### 3. **Firebase Cloud Functions**
- **Function**: `sendMedicineReminder` - Gửi email nhắc nhở (tùy chọn)

---

## 📊 LUỒNG HOẠT ĐỘNG CHI TIẾT

### **BƯỚC 1: TẠO LỊCH NHẮC NHỞ**

#### 1.1. Người dùng tạo lịch nhắc nhở
- Người dùng vào trang **Medicine Reminder** (`medicine-reminder.component.html`)
- Điền form:
  - **Tên thuốc** (`medicine_name`)
  - **Giờ uống** (`time`) - Format: "HH:MM" (ví dụ: "08:00")
  - **Loại lặp lại** (`repeat_type`):
    - `daily`: Hàng ngày
    - `weekly`: Hàng tuần (cần chọn thứ trong tuần)
    - `once`: Một lần duy nhất
  - **Thứ trong tuần** (`weekday`) - Chỉ dùng cho `weekly` (0=Thứ 2, 6=Chủ nhật)
  - **Ngày bắt đầu** (`start_date`) - Tùy chọn
  - **Ngày kết thúc** (`end_date`) - Tùy chọn
  - **Ghi chú** (`notes`) - Tùy chọn

#### 1.2. Frontend xử lý
```typescript
// medicine-reminder.component.ts - saveReminder()
const reminderData = {
  user_id: user.id,
  user_email: user.email,
  medicine_name: this.medicineName.trim(),
  time: this.time,
  repeat_type: this.repeatType,
  weekday: this.repeatType === 'weekly' ? this.weekday : undefined,
  start_date: this.startDate || undefined,
  end_date: this.endDate || undefined,
  notes: this.notes.trim() || undefined,
  is_active: true
};
```

#### 1.3. Lưu vào Firestore
- **Service**: `medicine-reminder.service.ts` → `createReminder()`
- **Firebase Service**: `firebase.service.ts` → `saveMedicineReminder()`
- **Collection**: `medicineReminders` trong Firestore
- **Cấu trúc dữ liệu** (camelCase trong Firestore):
  ```javascript
  {
    id: "uuid-reminder-id",
    userId: "user-id",
    userEmail: "user@example.com",
    medicineName: "Paracetamol",
    time: "08:00",
    repeatType: "daily", // hoặc "weekly", "once"
    weekday: 0, // 0-6 (chỉ cho weekly)
    startDate: "2024-01-01", // ISO string
    endDate: "2024-12-31", // ISO string
    notes: "Uống sau khi ăn",
    isActive: true,
    createdAt: Timestamp,
    updatedAt: Timestamp,
    nextReminderTime: Timestamp, // Tính toán tự động
    lastSent: null // Sẽ được cập nhật khi gửi thông báo
  }
  ```

#### 1.4. Tính toán `next_reminder_time`
- **Backend** (`api_server.py` - `create_reminder()`):
  ```python
  # Parse time
  hour = int(time_parts[0])
  minute = int(time_parts[1])
  
  # Tính toán next reminder time
  reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
  
  # Nếu thời gian đã qua trong ngày hôm nay, set cho ngày mai
  if reminder_time < now:
      reminder_time += timedelta(days=1)
  ```

---

### **BƯỚC 2: KIỂM TRA VÀ GỬI THÔNG BÁO**

#### 2.1. Khởi động Notification Service
- Khi người dùng đăng nhập, `NotificationService` được khởi động
- **File**: `notification.service.ts` → `start()`
- **Cơ chế**:
  ```typescript
  // Kiểm tra quyền thông báo
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }
  
  // Kiểm tra mỗi 60 giây (1 phút)
  this.checkInterval = window.setInterval(() => {
    this.checkAndSendNotifications();
  }, 60000);
  
  // Kiểm tra ngay lập tức
  this.checkAndSendNotifications();
  ```

#### 2.2. Kiểm tra Medicine Reminders
- **Method**: `checkMedicineReminders(userId, now)`
- **Tần suất**: Mỗi 60 giây (1 phút)
- **Quy trình**:

  **a) Lấy danh sách reminders:**
  ```typescript
  const reminders = await this.firebaseService.getMedicineReminders(userId);
  // Lọc chỉ lấy reminders có isActive = true
  ```

  **b) Với mỗi reminder, kiểm tra:**
  ```typescript
  // 1. Kiểm tra reminder có active không
  if (!reminder.is_active) continue;
  
  // 2. Parse thời gian
  const reminderTime = this.parseTime(reminder.time); // "08:00" → {hour: 8, minute: 0}
  const currentTime = now.getHours() * 60 + now.getMinutes(); // Phút trong ngày
  const reminderMinutes = reminderTime.hour * 60 + reminderTime.minute;
  
  // 3. Tính khoảng cách thời gian
  const diff = Math.abs(currentTime - reminderMinutes);
  
  // 4. Kiểm tra xem đã đến giờ chưa (trong vòng 5 phút)
  if (diff <= 5 && diff >= 0) {
    // Đã đến giờ!
  }
  ```

  **c) Kiểm tra tránh gửi trùng:**
  ```typescript
  const lastSent = reminder.last_sent ? new Date(reminder.last_sent) : null;
  const timeSinceLastSent = lastSent 
    ? (now.getTime() - lastSent.getTime()) / (1000 * 60) 
    : Infinity;
  
  // Chỉ gửi nếu chưa gửi hoặc đã qua 5 phút
  if (!lastSent || timeSinceLastSent > 5) {
    // Gửi thông báo
  }
  ```

#### 2.3. Gửi Browser Notification
- **Method**: `sendNotification(title, body)`
- **Điều kiện**:
  - `Notification.permission === 'granted'`
  - `pushNotifications` được bật trong settings
- **Code**:
  ```typescript
  const notification = new Notification('🔔 Nhắc nhở uống thuốc', {
    body: `Đã đến giờ uống thuốc: ${reminder.medicine_name} (${reminder.time})`,
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    tag: 'health-reminder',
    requireInteraction: false
  });
  
  // Tự động đóng sau 5 giây
  setTimeout(() => {
    notification.close();
  }, 5000);
  ```

#### 2.4. Gửi Email Reminder (Tùy chọn)
- **Method**: `sendEmailReminder(email, reminder)`
- **Firebase Function**: `sendMedicineReminder`
- **URL**: `https://us-central1-giadienweb.cloudfunctions.net/sendMedicineReminder`
- **Payload**:
  ```json
  {
    "email": "user@example.com",
    "medicine_name": "Paracetamol",
    "time": "08:00",
    "message": "Đã đến giờ uống thuốc: Paracetamol (08:00). Uống sau khi ăn"
  }
  ```
- **Lưu ý**: Hiện tại email reminder đang được comment trong code để tránh lỗi CORS khi function chưa deploy

#### 2.5. Cập nhật trạng thái reminder
Sau khi gửi thông báo, hệ thống cập nhật:

**a) Cho reminder loại `daily`:**
```typescript
nextReminderTime = new Date(now);
nextReminderTime.setHours(hours, minutes, 0, 0);
// Nếu đã qua giờ hôm nay, set cho ngày mai
if (nextReminderTime.getTime() <= now.getTime()) {
  nextReminderTime.setDate(nextReminderTime.getDate() + 1);
}
```

**b) Cho reminder loại `weekly`:**
```typescript
nextReminderTime = new Date(now);
nextReminderTime.setHours(hours, minutes, 0, 0);
const currentDay = nextReminderTime.getDay();
const targetDay = reminder.weekday;
let daysUntilNext = (targetDay - currentDay + 7) % 7;
if (daysUntilNext === 0 && nextReminderTime <= now) {
  daysUntilNext = 7; // Nếu đã qua giờ hôm nay, set cho tuần sau
}
nextReminderTime.setDate(nextReminderTime.getDate() + daysUntilNext);
```

**c) Cho reminder loại `once`:**
```typescript
// Deactivate sau khi gửi
await this.firebaseService.updateMedicineReminder(reminder.id, {
  last_sent: now.toISOString(),
  is_active: false
});
```

**d) Cập nhật `last_sent` và `next_reminder_time`:**
```typescript
await this.firebaseService.updateMedicineReminder(reminder.id, {
  last_sent: now.toISOString(),
  next_reminder_time: nextReminderTime.toISOString()
});
```

---

### **BƯỚC 3: QUẢN LÝ LỊCH NHẮC NHỞ**

#### 3.1. Xem danh sách reminders
- **Component**: `medicine-reminder.component.ts` → `loadReminders()`
- **Service**: `medicine-reminder.service.ts` → `getReminders(userId)`
- **Firebase**: `firebase.service.ts` → `getMedicineReminders(userId)`
- **Query Firestore**:
  ```typescript
  const q = query(
    collection(firebaseDb, 'medicineReminders'),
    where('userId', '==', userId),
    where('isActive', '==', true)
  );
  ```

#### 3.2. Chỉnh sửa reminder
- Người dùng click "Sửa" trên một reminder
- Form được điền với dữ liệu hiện tại
- Khi lưu: Xóa reminder cũ và tạo mới (vì chưa có API update riêng)

#### 3.3. Xóa reminder
- **Method**: `deleteReminder(reminderId)`
- **Cơ chế**: Không xóa thật, chỉ set `isActive = false`
- **Code**:
  ```typescript
  await updateDoc(docRef, {
    isActive: false,
    updatedAt: Timestamp.now()
  });
  ```

---

## 🔄 BACKEND SCHEDULER (Tùy chọn)

### **medicine_reminder_scheduler.py**
- Script Python chạy độc lập để kiểm tra reminders
- **Cơ chế**: Gọi API `/api/medicine-reminders/check` mỗi 60 giây
- **Sử dụng**: Khi muốn kiểm tra reminders từ server thay vì frontend
- **Cách chạy**:
  ```bash
  python medicine_reminder_scheduler.py
  ```

### **API Endpoint: `/api/medicine-reminders/check`**
- **Method**: POST
- **Chức năng**: Kiểm tra tất cả reminders active và gửi thông báo
- **Logic tương tự frontend**: Kiểm tra thời gian, gửi email, cập nhật trạng thái

---

## 📦 CẤU TRÚC DỮ LIỆU

### **Firestore Collection: `medicineReminders`**

#### **Document Structure (camelCase trong Firestore):**
```typescript
{
  id: string,                    // Document ID
  userId: string,                 // ID của user
  userEmail: string,              // Email của user
  medicineName: string,           // Tên thuốc
  time: string,                   // Format: "HH:MM"
  repeatType: 'daily' | 'weekly' | 'once',
  weekday?: number,               // 0-6 (chỉ cho weekly)
  startDate?: string,            // ISO date string
  endDate?: string,              // ISO date string
  notes?: string,                // Ghi chú
  isActive: boolean,             // Trạng thái active
  createdAt: Timestamp,          // Thời gian tạo
  updatedAt: Timestamp,          // Thời gian cập nhật
  nextReminderTime?: Timestamp,  // Thời gian nhắc tiếp theo
  lastSent?: Timestamp           // Thời gian gửi thông báo lần cuối
}
```

---

## ⚙️ CÁC THAM SỐ QUAN TRỌNG

### **1. Tần suất kiểm tra**
- **Frontend**: Mỗi **60 giây** (1 phút)
- **Backend Scheduler**: Mỗi **60 giây** (1 phút)

### **2. Khoảng thời gian gửi thông báo**
- **Window**: **5 phút** trước và sau giờ nhắc
- **Ví dụ**: Nếu nhắc lúc 08:00, sẽ gửi từ 07:55 đến 08:05

### **3. Tránh gửi trùng**
- **Cooldown**: **5 phút** giữa các lần gửi
- Nếu đã gửi trong 5 phút vừa rồi, sẽ bỏ qua

### **4. Browser Notification**
- **Auto-close**: Tự động đóng sau **5 giây**
- **Permission**: Cần user cho phép

---

## 🔐 BẢO MẬT VÀ PHÂN QUYỀN

### **1. User Isolation**
- Mỗi user chỉ thấy và quản lý reminders của chính mình
- Query Firestore luôn filter theo `userId`

### **2. Firestore Security Rules**
- Cần cấu hình rules để đảm bảo user chỉ đọc/ghi reminders của mình
- Ví dụ:
  ```javascript
  match /medicineReminders/{reminderId} {
    allow read, write: if request.auth != null 
      && request.resource.data.userId == request.auth.uid;
  }
  ```

---

## 🚀 TÍNH NĂNG NÂNG CAO

### **1. Email Reminder**
- Sử dụng Firebase Cloud Function `sendMedicineReminder`
- Cần deploy function trước khi sử dụng
- Có thể tích hợp với SendGrid, Nodemailer, etc.

### **2. Backend Scheduler**
- Chạy độc lập trên server
- Không phụ thuộc vào frontend
- Có thể dùng cron job để chạy tự động

### **3. Multiple Reminders**
- Một user có thể tạo nhiều reminders
- Mỗi reminder hoạt động độc lập
- Có thể có nhiều reminders cùng giờ

---

## 🐛 XỬ LÝ LỖI

### **1. Firestore không kết nối được**
- Frontend fallback về memory storage (tạm thời)
- Backend fallback về in-memory dictionary

### **2. Notification permission bị từ chối**
- Vẫn kiểm tra reminders (có thể gửi email)
- Log warning nhưng không throw error

### **3. Email function chưa deploy**
- Log warning nhưng không throw error
- Browser notification vẫn hoạt động bình thường

---

## 📝 GHI CHÚ QUAN TRỌNG

1. **Frontend là chính**: Hệ thống chủ yếu chạy trên frontend, kiểm tra mỗi phút
2. **Backend scheduler là tùy chọn**: Chỉ dùng khi muốn kiểm tra từ server
3. **Email reminder tạm thời tắt**: Đang comment trong code để tránh lỗi CORS
4. **Timezone**: Hệ thống sử dụng timezone của browser/server
5. **Xóa = Deactivate**: Không xóa thật, chỉ set `isActive = false`

---

## 🔧 CÁCH SỬ DỤNG

### **1. Tạo reminder mới:**
1. Vào trang Medicine Reminder
2. Click "Thêm lịch nhắc nhở"
3. Điền form và lưu

### **2. Xem danh sách:**
- Tự động load khi vào trang
- Hiển thị tất cả reminders active

### **3. Chỉnh sửa:**
- Click "Sửa" trên reminder
- Thay đổi thông tin và lưu

### **4. Xóa:**
- Click "Xóa" trên reminder
- Xác nhận xóa

### **5. Nhận thông báo:**
- Tự động kiểm tra mỗi phút
- Gửi browser notification khi đến giờ
- (Tùy chọn) Gửi email nếu function đã deploy

---

## 📚 CÁC FILE LIÊN QUAN

### **Frontend:**
- `AI-Web/src/app/medicine-reminder/medicine-reminder.component.ts`
- `AI-Web/src/app/medicine-reminder/medicine-reminder.component.html`
- `AI-Web/src/app/services/medicine-reminder.service.ts`
- `AI-Web/src/app/services/notification.service.ts`
- `AI-Web/src/app/services/firebase.service.ts`

### **Backend:**
- `api_server.py` (endpoints: `/api/medicine-reminders/*`)
- `firestore_service.py` (functions: `save_medicine_reminder`, `get_medicine_reminders`, etc.)
- `medicine_reminder_scheduler.py` (optional scheduler)

### **Firebase Functions:**
- `AI-Web/functions/src/index.ts` (function: `sendMedicineReminder`)

---

## ✅ KẾT LUẬN

Hệ thống nhắc nhở uống thuốc là một giải pháp hoàn chỉnh với:
- ✅ Giao diện quản lý dễ sử dụng
- ✅ Kiểm tra tự động mỗi phút
- ✅ Browser notifications
- ✅ Hỗ trợ email reminders (tùy chọn)
- ✅ Hỗ trợ nhiều loại lặp lại (daily, weekly, once)
- ✅ Lưu trữ bền vững trên Firestore
- ✅ Xử lý lỗi tốt với fallback mechanisms

Hệ thống đảm bảo người dùng không bao giờ quên uống thuốc đúng giờ! 💊⏰

