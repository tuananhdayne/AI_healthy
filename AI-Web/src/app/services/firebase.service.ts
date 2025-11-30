import { Injectable } from '@angular/core';
import {
  Firestore,
  collection,
  addDoc,
  getDocs,
  query,
  where,
  updateDoc,
  deleteDoc,
  doc,
  DocumentData,
  QuerySnapshot,
  Timestamp,
  getDoc,
  setDoc
} from 'firebase/firestore';
import { firebaseDb } from '../../environments/firebase.config';
import { Observable, from } from 'rxjs';

export interface ChatMessage {
  id?: string;
  userId: string;
  userEmail: string;
  text: string;
  timestamp: Date | Timestamp;
  aiResponse?: string;
  role?: 'user' | 'assistant';
  sessionId?: string;
  metadata?: {
    intent?: string;
    intentConfidence?: number;
    risk?: string;
    stage?: string;
    sources?: Array<Record<string, any>>;
  };
}

export interface ChatSession {
  id?: string;
  userId: string;
  userEmail: string;
  sessionId: string;
  title: string;
  lastMessage: string;
  createdAt: Date | Timestamp;
  updatedAt: Date | Timestamp;
  messageCount: number;
}

export interface UserProfile {
  id?: string;
  uid: string;
  email: string;
  fullName: string;
  role: 'user' | 'admin';
  createdAt: Date | Timestamp;
  updatedAt: Date | Timestamp;
}

export interface UserCredentials {
  id?: string;
  uid: string;
  username: string;
  email: string;
  passwordHash: string;
  role?: 'user' | 'admin';
  status?: 'active' | 'inactive';
  pinCode?: string;
  fullName?: string;
  phone?: string;
  createdAt?: Date | Timestamp;
  updatedAt?: Date | Timestamp;
}

export interface HealthProfile {
  tuoi: number;
  chieuCao: number; // cm
  canNang: number; // kg
  mucVanDong: 'it' | 'vua' | 'nhieu';
  gioiTinh: 'nam' | 'nu' | 'khac';
  createdAt?: Date | Timestamp;
  updatedAt?: Date | Timestamp;
}

export interface AppSettingsDoc {
  id?: string;
  userId: string;
  theme: string;
  language: string;
  notifications: boolean;
  aiModel: string;
  apiKey: string;
  accent: string;
  voice: string;
  updatedAt: Date | Timestamp;
}

export interface MedicineReminderDoc {
  id?: string;
  user_id: string;
  user_email: string;
  medicine_name: string;
  time: string;
  repeat_type: 'daily' | 'weekly' | 'once';
  weekday?: number;
  start_date?: string;
  end_date?: string;
  notes?: string;
  created_at: Date | Timestamp;
  updated_at: Date | Timestamp;
  is_active: boolean;
  next_reminder_time?: string;
  last_sent?: string;
}

@Injectable({
  providedIn: 'root'
})
export class FirebaseService {
    /**
     * Gửi yêu cầu reset mật khẩu (gửi email từ admin)
     */
    async sendResetPassword(email: string, username: string): Promise<void> {
      // Gọi trực tiếp Cloud Function qua HTTP POST (CORS đã xử lý)
      const url = 'https://us-central1-giadienweb.cloudfunctions.net/sendResetPassword';
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, username })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Gửi email thất bại');
      }
    }
  constructor() {}

  // ============ User Credentials (Mã hóa) ============
  /**
   * Tạo credentials mã hóa cho tài khoản mới
   */
  async createUserCredentials(credentials: Omit<UserCredentials, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const docRef = await addDoc(collectionRef, {
      ...credentials,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now()
    });
    return docRef.id;
  }

  /**
   * Kiểm tra tên tài khoản đã tồn tại
   */
  async checkUsernameExists(username: string): Promise<boolean> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('username', '==', username));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    return !snapshot.empty;
  }

  /**
   * Lấy credentials bằng username
   */
  async getUserCredentialsByUsername(username: string): Promise<UserCredentials | null> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('username', '==', username));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    if (snapshot.empty) return null;
    const data = snapshot.docs[0].data();
    return {
      id: snapshot.docs[0].id,
      ...data,
      pinCode: data['pinCode'] || ''
    } as UserCredentials;
  }

  /**
   * Lấy credentials bằng email
   */
  async getUserCredentialsByEmail(email: string): Promise<UserCredentials | null> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('email', '==', email));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    if (snapshot.empty) return null;
    return {
      id: snapshot.docs[0].id,
      ...snapshot.docs[0].data()
    } as UserCredentials;
  }

  /**
   * Xóa credentials
   */
  async deleteUserCredentials(uid: string): Promise<void> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('uid', '==', uid));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    if (!snapshot.empty) {
      await deleteDoc(doc(firebaseDb, 'userCredentials', snapshot.docs[0].id));
    }
  }

  /**
   * Cập nhật quyền (role) cho user bằng username
   */
  async updateUserRoleByUsername(username: string, role: 'user' | 'admin'): Promise<void> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('username', '==', username));
    const snapshot = await getDocs(q);
    if (!snapshot.empty) {
      const docRef = doc(firebaseDb, 'userCredentials', snapshot.docs[0].id);
      await updateDoc(docRef, { role, updatedAt: Timestamp.now() });
    }
  }

  /**
   * Lấy tất cả documents trong collection `userCredentials`.
   */
  async getAllUserCredentials(): Promise<UserCredentials[]> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(collectionRef);
    return snapshot.docs.map(d => ({ id: d.id, ...d.data() } as UserCredentials));
  }

  /**
   * Cập nhật role cho doc trong `userCredentials` theo document id
   */
  async updateUserCredentialsRoleById(docId: string, role: 'user' | 'admin'): Promise<void> {
    const docRef = doc(firebaseDb, 'userCredentials', docId);
    await updateDoc(docRef, { role, updatedAt: Timestamp.now() });
  }

  /**
   * Xóa document trong `userCredentials` theo document id
   */
  async deleteUserCredentialsById(docId: string): Promise<void> {
    const docRef = doc(firebaseDb, 'userCredentials', docId);
    await deleteDoc(docRef);
  }

  // ============ Chat Messages ============
  async addChatMessage(message: Omit<ChatMessage, 'id' | 'timestamp'>): Promise<string> {
    const collectionRef = collection(firebaseDb, 'messages');
    const docRef = await addDoc(collectionRef, {
      ...message,
      timestamp: Timestamp.now()
    });
    return docRef.id;
  }

  async getChatMessages(userId: string): Promise<ChatMessage[]> {
    const collectionRef = collection(firebaseDb, 'messages');
    const q = query(collectionRef, where('userId', '==', userId));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    } as ChatMessage));
  }

  async getAllChatMessages(): Promise<ChatMessage[]> {
    const collectionRef = collection(firebaseDb, 'messages');
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(collectionRef);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    } as ChatMessage));
  }

  deleteChatMessage(messageId: string): Observable<void> {
    const docRef = doc(firebaseDb, 'messages', messageId);
    return from(deleteDoc(docRef));
  }

  // ============ Chat Sessions ============
  /**
   * Tạo hoặc cập nhật chat session
   */
  async saveChatSession(session: Omit<ChatSession, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    const collectionRef = collection(firebaseDb, 'chatSessions');
    
    // Kiểm tra xem session đã tồn tại chưa
    const q = query(
      collectionRef,
      where('userId', '==', session.userId),
      where('sessionId', '==', session.sessionId)
    );
    const snapshot = await getDocs(q);
    
    if (!snapshot.empty) {
      // Cập nhật session hiện có
      const docRef = doc(firebaseDb, 'chatSessions', snapshot.docs[0].id);
      await updateDoc(docRef, {
        title: session.title,
        lastMessage: session.lastMessage,
        updatedAt: Timestamp.now(),
        messageCount: session.messageCount
      });
      return snapshot.docs[0].id;
    } else {
      // Tạo session mới
      const docRef = await addDoc(collectionRef, {
        ...session,
        createdAt: Timestamp.now(),
        updatedAt: Timestamp.now()
      });
      return docRef.id;
    }
  }

  /**
   * Lấy tất cả chat sessions của user
   */
  async getChatSessions(userId: string): Promise<ChatSession[]> {
    const collectionRef = collection(firebaseDb, 'chatSessions');
    const q = query(
      collectionRef,
      where('userId', '==', userId)
    );
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    return snapshot.docs
      .map(doc => ({
        id: doc.id,
        ...doc.data()
      } as ChatSession))
      .sort((a, b) => {
        const aTime = a.updatedAt instanceof Timestamp ? a.updatedAt.toDate() : new Date(a.updatedAt);
        const bTime = b.updatedAt instanceof Timestamp ? b.updatedAt.toDate() : new Date(b.updatedAt);
        return bTime.getTime() - aTime.getTime(); // Mới nhất trước
      });
  }

  /**
   * Lấy messages của một session
   */
  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const collectionRef = collection(firebaseDb, 'messages');
    const q = query(
      collectionRef,
      where('sessionId', '==', sessionId)
    );
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    return snapshot.docs
      .map(doc => ({
        id: doc.id,
        ...doc.data()
      } as ChatMessage))
      .sort((a, b) => {
        const aTime = a.timestamp instanceof Timestamp ? a.timestamp.toDate() : new Date(a.timestamp);
        const bTime = b.timestamp instanceof Timestamp ? b.timestamp.toDate() : new Date(b.timestamp);
        return aTime.getTime() - bTime.getTime(); // Cũ nhất trước
      });
  }

  /**
   * Xóa chat session và tất cả messages của nó
   */
  async deleteChatSession(sessionId: string, userId: string): Promise<void> {
    // Xóa session
    const sessionsRef = collection(firebaseDb, 'chatSessions');
    const sessionQuery = query(
      sessionsRef,
      where('sessionId', '==', sessionId),
      where('userId', '==', userId)
    );
    const sessionSnapshot = await getDocs(sessionQuery);
    if (!sessionSnapshot.empty) {
      await deleteDoc(doc(firebaseDb, 'chatSessions', sessionSnapshot.docs[0].id));
    }

    // Xóa tất cả messages của session
    const messagesRef = collection(firebaseDb, 'messages');
    const messagesQuery = query(messagesRef, where('sessionId', '==', sessionId));
    const messagesSnapshot = await getDocs(messagesQuery);
    const deletePromises = messagesSnapshot.docs.map(d => deleteDoc(doc(firebaseDb, 'messages', d.id)));
    await Promise.all(deletePromises);
  }

  // ============ User Profiles ============
  async createUserProfile(uid: string, user: Omit<UserProfile, 'id' | 'createdAt' | 'updatedAt'>): Promise<void> {
    const collectionRef = collection(firebaseDb, 'users');
    await addDoc(collectionRef, {
      ...user,
      uid,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now()
    });
  }

  async getUserProfile(uid: string): Promise<UserProfile | null> {
    const collectionRef = collection(firebaseDb, 'users');
    const q = query(collectionRef, where('uid', '==', uid));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    if (snapshot.empty) return null;
    return {
      id: snapshot.docs[0].id,
      ...snapshot.docs[0].data()
    } as UserProfile;
  }

  async getAllUsers(): Promise<UserProfile[]> {
    const collectionRef = collection(firebaseDb, 'users');
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(collectionRef);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    } as UserProfile));
  }

  async updateUserRole(userId: string, role: 'user' | 'admin'): Promise<void> {
    const docRef = doc(firebaseDb, 'users', userId);
    await updateDoc(docRef, { role, updatedAt: Timestamp.now() });
  }

  deleteUser(userId: string): Observable<void> {
    const docRef = doc(firebaseDb, 'users', userId);
    return from(deleteDoc(docRef));
  }

  // ============ App Settings ============
  async saveSettings(userId: string, settings: Omit<AppSettingsDoc, 'id' | 'updatedAt'>): Promise<void> {
    const collectionRef = collection(firebaseDb, 'settings');
    // Check if settings already exist for this user
    const q = query(collectionRef, where('userId', '==', userId));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);

    if (snapshot.empty) {
      // Create new settings doc
      await addDoc(collectionRef, {
        ...settings,
        updatedAt: Timestamp.now()
      });
    } else {
      // Update existing settings
      const docRef = doc(firebaseDb, 'settings', snapshot.docs[0].id);
      await updateDoc(docRef, {
        ...settings,
        updatedAt: Timestamp.now()
      });
    }
  }

  async getSettings(userId: string): Promise<AppSettingsDoc | null> {
    const collectionRef = collection(firebaseDb, 'settings');
    const q = query(collectionRef, where('userId', '==', userId));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    if (snapshot.empty) return null;
    return {
      id: snapshot.docs[0].id,
      ...snapshot.docs[0].data()
    } as AppSettingsDoc;
  }

  deleteSettings(settingsId: string): Observable<void> {
    const docRef = doc(firebaseDb, 'settings', settingsId);
    return from(deleteDoc(docRef));
  }

  // ============ AI Models (for Admin) ============
  async addAIModel(model: any): Promise<string> {
    const collectionRef = collection(firebaseDb, 'aimodels');
    const docRef = await addDoc(collectionRef, {
      ...model,
      createdAt: Timestamp.now()
    });
    return docRef.id;
  }

  async getAIModels(): Promise<any[]> {
    const collectionRef = collection(firebaseDb, 'aimodels');
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(collectionRef);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  }

  deleteAIModel(modelId: string): Observable<void> {
    const docRef = doc(firebaseDb, 'aimodels', modelId);
    return from(deleteDoc(docRef));
  }

  /**
   * Lưu thông tin user Google vào Firestore nếu chưa tồn tại
   */
  async saveGoogleUserToFirestore(user: import('./auth.service').User): Promise<void> {
    const collectionRef = collection(firebaseDb, 'users');
    const q = query(collectionRef, where('id', '==', user.id));
    const snapshot = await getDocs(q);
    if (snapshot.empty) {
      await addDoc(collectionRef, {
        ...user,
        createdAt: new Date(),
        updatedAt: new Date()
      });
    }
  }

  /**
   * Cập nhật mật khẩu cho tài khoản (username/password)
   */
  /**
   * Cập nhật thông tin người dùng (fullName, email, phone) bằng username
   */
  async updateUserInfoByUsername(username: string, updates: { fullName?: string; email?: string; phone?: string }): Promise<void> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('username', '==', username));
    const snapshot = await getDocs(q);
    if (!snapshot.empty) {
      const docRef = doc(firebaseDb, 'userCredentials', snapshot.docs[0].id);
      const updateData: any = { updatedAt: Timestamp.now() };
      if (updates.fullName !== undefined) updateData.fullName = updates.fullName;
      if (updates.email !== undefined) updateData.email = updates.email;
      if (updates.phone !== undefined) updateData.phone = updates.phone;
      await updateDoc(docRef, updateData);
    }
  }

  /**
   * Cập nhật mã PIN bằng username
   */
  async updateUserPinByUsername(username: string, pinCode: string): Promise<void> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('username', '==', username));
    const snapshot = await getDocs(q);
    if (!snapshot.empty) {
      const docRef = doc(firebaseDb, 'userCredentials', snapshot.docs[0].id);
      await updateDoc(docRef, { 
        pinCode, 
        updatedAt: Timestamp.now() 
      });
    }
  }

  /**
   * Lấy thông tin user credentials bằng uid
   */
  async getUserCredentialsByUid(uid: string): Promise<UserCredentials | null> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('uid', '==', uid));
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    if (snapshot.empty) return null;
    const data = snapshot.docs[0].data();
    return {
      id: snapshot.docs[0].id,
      ...data,
      pinCode: data['pinCode'] || ''
    } as UserCredentials;
  }

  async updateUserPassword(username: string, newPasswordHash: string): Promise<void> {
    const collectionRef = collection(firebaseDb, 'userCredentials');
    const q = query(collectionRef, where('username', '==', username));
    const snapshot = await getDocs(q);

    if (!snapshot.empty) {
      const docRef = snapshot.docs[0].ref;
      await updateDoc(docRef, {
        passwordHash: newPasswordHash,
        updatedAt: new Date()
      });
    } else {
      throw new Error('Không tìm thấy tài khoản');
    }
  }

  // ============ Medicine Reminders ============
  /**
   * Tạo lịch nhắc nhở uống thuốc mới
   */
  async createMedicineReminder(reminder: Omit<MedicineReminderDoc, 'id' | 'created_at' | 'updated_at'>): Promise<string> {
    const collectionRef = collection(firebaseDb, 'medicineReminders');
    const docRef = await addDoc(collectionRef, {
      ...reminder,
      created_at: Timestamp.now(),
      updated_at: Timestamp.now()
    });
    return docRef.id;
  }

  /**
   * Lưu medicine reminder vào Firestore (từ frontend)
   */
  async saveMedicineReminder(reminder: Omit<MedicineReminderDoc, 'id' | 'created_at' | 'updated_at'>): Promise<string> {
    const collectionRef = collection(firebaseDb, 'medicineReminders');
    
    // Convert snake_case sang camelCase cho Firestore
    // Chỉ thêm field nếu có giá trị (không undefined/null)
    const firestoreData: any = {
      userId: reminder.user_id,
      userEmail: reminder.user_email,
      medicineName: reminder.medicine_name,
      time: reminder.time,
      repeatType: reminder.repeat_type,
      isActive: reminder.is_active !== undefined ? reminder.is_active : true,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now()
    };
    
    // Chỉ thêm weekday nếu có giá trị (cho weekly reminders)
    if (reminder.weekday !== undefined && reminder.weekday !== null) {
      firestoreData.weekday = reminder.weekday;
    }
    
    // Chỉ thêm startDate nếu có giá trị
    if (reminder.start_date) {
      firestoreData.startDate = reminder.start_date;
    }
    
    // Chỉ thêm endDate nếu có giá trị
    if (reminder.end_date) {
      firestoreData.endDate = reminder.end_date;
    }
    
    // Chỉ thêm notes nếu có giá trị
    if (reminder.notes) {
      firestoreData.notes = reminder.notes;
    }
    
    // Tính toán next reminder time
    if (reminder.time) {
      const now = new Date();
      const [hours, minutes] = reminder.time.split(':').map(Number);
      const reminderTime = new Date(now);
      reminderTime.setHours(hours, minutes, 0, 0);
      reminderTime.setSeconds(0, 0); // Đảm bảo seconds và milliseconds = 0
      
      // Nếu thời gian đã qua trong ngày hôm nay, set cho ngày mai
      if (reminderTime.getTime() <= now.getTime()) {
        reminderTime.setDate(reminderTime.getDate() + 1);
      }
      
      console.log(`📅 Calculated next reminder time: ${reminderTime.toLocaleString()} (from ${now.toLocaleString()})`);
      firestoreData.nextReminderTime = Timestamp.fromDate(reminderTime);
    }
    
    const docRef = await addDoc(collectionRef, firestoreData);
    console.log('✅ Đã lưu medicine reminder vào Firestore:', docRef.id);
    return docRef.id;
  }

  async getMedicineReminders(userId: string): Promise<MedicineReminderDoc[]> {
    const collectionRef = collection(firebaseDb, 'medicineReminders');
    // Frontend lưu với camelCase: userId, isActive
    const q = query(
      collectionRef,
      where('userId', '==', userId),
      where('isActive', '==', true)
    );
    const snapshot: QuerySnapshot<DocumentData> = await getDocs(q);
    const now = new Date();
    
    return snapshot.docs.map(docSnapshot => {
      const data = docSnapshot.data();
      
      // Convert nextReminderTime từ Firestore
      let nextReminderTime: string | undefined = undefined;
      if (data['nextReminderTime']) {
        const nextTime = data['nextReminderTime'].toDate ? data['nextReminderTime'].toDate() : new Date(data['nextReminderTime']);
        nextReminderTime = nextTime.toISOString();
        
        // Nếu nextReminderTime đã qua và là daily reminder, tự động update
        if (data['repeatType'] === 'daily' && nextTime.getTime() <= now.getTime()) {
          const [hours, minutes] = (data['time'] || '').split(':').map(Number);
          const newNextTime = new Date(now);
          newNextTime.setHours(hours, minutes, 0, 0);
          newNextTime.setSeconds(0, 0);
          
          // Nếu đã qua giờ hôm nay, set cho ngày mai
          if (newNextTime.getTime() <= now.getTime()) {
            newNextTime.setDate(newNextTime.getDate() + 1);
          }
          
          // Update trong Firestore (async, không block)
          const reminderDocId = docSnapshot.id;
          const docRef = doc(firebaseDb, 'medicineReminders', reminderDocId);
          updateDoc(docRef, {
            nextReminderTime: Timestamp.fromDate(newNextTime)
          }).then(() => {
            console.log(`🔄 Auto-updated nextReminderTime for reminder ${reminderDocId}: ${newNextTime.toLocaleString()}`);
          }).catch(err => {
            console.error(`❌ Error updating nextReminderTime:`, err);
          });
          
          nextReminderTime = newNextTime.toISOString();
        }
      }
      
      // Convert camelCase từ Firestore sang snake_case cho interface
      return {
        id: docSnapshot.id,
        user_id: data['userId'] || data['user_id'],
        user_email: data['userEmail'] || data['user_email'],
        medicine_name: data['medicineName'] || data['medicine_name'],
        time: data['time'],
        repeat_type: data['repeatType'] || data['repeat_type'],
        weekday: data['weekday'],
        start_date: data['startDate'] || data['start_date'],
        end_date: data['endDate'] || data['end_date'],
        notes: data['notes'],
        created_at: data['createdAt'] || data['created_at'],
        is_active: data['isActive'] !== undefined ? data['isActive'] : (data['is_active'] !== undefined ? data['is_active'] : true),
        next_reminder_time: nextReminderTime || data['next_reminder_time'],
        last_sent: data['lastSent'] ? (data['lastSent'].toDate ? data['lastSent'].toDate().toISOString() : data['lastSent']) : data['last_sent']
      } as MedicineReminderDoc;
    });
  }

  /**
   * Xóa (deactivate) lịch nhắc nhở
   */
  async deleteMedicineReminder(reminderId: string): Promise<void> {
    const docRef = doc(firebaseDb, 'medicineReminders', reminderId);
    await updateDoc(docRef, {
      isActive: false, // Backend dùng camelCase
      updatedAt: Timestamp.now()
    });
  }

  /**
   * Cập nhật lịch nhắc nhở
   */
  // ============ Health Profile ============
  /**
   * Lưu hoặc cập nhật health profile cho user
   */
  async saveHealthProfile(userId: string, profile: HealthProfile): Promise<void> {
    try {
      const docRef = doc(firebaseDb, 'users', userId, 'healthProfile', 'profile');
      
      // Đảm bảo tất cả fields được lưu đúng
      const profileData: any = {
        tuoi: Number(profile.tuoi),
        chieuCao: Number(profile.chieuCao),
        canNang: Number(profile.canNang),
        mucVanDong: profile.mucVanDong,
        gioiTinh: profile.gioiTinh || 'khac',
        updatedAt: Timestamp.now()
      };
      
      // Kiểm tra xem document đã tồn tại chưa
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        await updateDoc(docRef, profileData);
        console.log('✅ Đã cập nhật health profile vào Firestore cho user:', userId);
      } else {
        profileData.createdAt = Timestamp.now();
        await setDoc(docRef, profileData);
        console.log('✅ Đã tạo mới health profile vào Firestore cho user:', userId);
      }
      
      // Log để debug
      console.log('📋 Health profile data:', profileData);
    } catch (error) {
      console.error('❌ Lỗi khi lưu health profile:', error);
      throw error;
    }
  }

  /**
   * Lấy health profile của user
   */
  async getHealthProfile(userId: string): Promise<HealthProfile | null> {
    try {
      const docRef = doc(firebaseDb, 'users', userId, 'healthProfile', 'profile');
      const docSnap = await getDoc(docRef);
      
      if (docSnap.exists()) {
        const data = docSnap.data();
        return {
          tuoi: data['tuoi'] || 0,
          chieuCao: data['chieuCao'] || 0,
          canNang: data['canNang'] || 0,
          mucVanDong: data['mucVanDong'] || 'it',
          gioiTinh: data['gioiTinh'] || 'khac',
          createdAt: data['createdAt'],
          updatedAt: data['updatedAt']
        } as HealthProfile;
      }
      return null;
    } catch (error) {
      console.error('Error getting health profile:', error);
      return null;
    }
  }

  /**
   * Kiểm tra user đã có health profile chưa
   */
  async hasHealthProfile(userId: string): Promise<boolean> {
    const profile = await this.getHealthProfile(userId);
    return profile !== null;
  }

  async updateMedicineReminder(reminderId: string, updates: Partial<MedicineReminderDoc>): Promise<void> {
    const docRef = doc(firebaseDb, 'medicineReminders', reminderId);
    // Convert snake_case sang camelCase cho Firestore
    const firestoreUpdates: any = {};
    if (updates.last_sent !== undefined) {
      firestoreUpdates['lastSent'] = updates.last_sent ? Timestamp.fromDate(new Date(updates.last_sent)) : null;
    }
    if (updates.is_active !== undefined) {
      firestoreUpdates['isActive'] = updates.is_active;
    }
    if (updates.next_reminder_time !== undefined) {
      // Chỉ update nếu có giá trị
      if (updates.next_reminder_time) {
        firestoreUpdates['nextReminderTime'] = Timestamp.fromDate(new Date(updates.next_reminder_time));
      }
      // Nếu undefined hoặc null, không update (giữ nguyên giá trị cũ)
    }
    firestoreUpdates['updatedAt'] = Timestamp.now();
    await updateDoc(docRef, firestoreUpdates);
  }
}
