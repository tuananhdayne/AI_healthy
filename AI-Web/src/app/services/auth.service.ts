import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, from } from 'rxjs';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
  EmailAuthProvider,
  reauthenticateWithCredential,
  updatePassword,
  updateProfile,
  fetchSignInMethodsForEmail
} from 'firebase/auth';
import { firebaseAuth } from '../../environments/firebase.config';
import { FirebaseService } from './firebase.service';
import { ThemeService } from './theme.service';

export interface User {
  id: string;
  email: string;
  fullName: string | null;
  username: string;
  role: 'user' | 'admin'; // 'user' or 'admin'
  token?: string;
}

export interface UserCredentials {
  fullName?: string;
  id?: string;
  uid: string;
  username: string;
  email: string;
  passwordHash: string;
  role?: 'user' | 'admin';
  createdAt?: any;
  updatedAt?: any;
  phone?: string;
  pinCode?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly STORAGE_KEY = 'app_user_v1';
  // Start with no user until Firebase confirms the auth state to avoid stale UI from localStorage
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private firebaseService: FirebaseService, private themeService: ThemeService) {
    // Restore user from localStorage khi khởi động (cho username/password login)
    try {
      const savedUser = localStorage.getItem(this.STORAGE_KEY);
      if (savedUser) {
        const user = JSON.parse(savedUser);
        // Chỉ restore nếu có đầy đủ thông tin
        if (user && user.id && user.email) {
          this.currentUserSubject.next(user);
        }
      }
    } catch (e) {
      // ignore
    }

    // Listen to Firebase auth state changes (cho Google login)
    onAuthStateChanged(firebaseAuth, (firebaseUser) => {
      if (firebaseUser) {
        // Nếu Firebase logged-in user khác với current stored user thì cập nhật lại
        const user: User = {
          id: firebaseUser.uid,
          email: firebaseUser.email || '',
          fullName: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'User',
          username: firebaseUser.displayName || '',
          role: 'user',
          token: firebaseUser.refreshToken || ''
        };
        if (!this.currentUserSubject.value || this.currentUserSubject.value.id !== firebaseUser.uid) {
          this.setCurrentUser(user);
        }
      } else {
        // No firebase authenticated user: chỉ clear nếu không có user từ localStorage
        if (!this.currentUserSubject.value) {
          try {
            localStorage.removeItem(this.STORAGE_KEY);
          } catch (e) {
            // ignore storage errors
          }
        }
      }
    });
  }

  /**
   * Get current user from localStorage or BehaviorSubject.
   */
  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  /**
   * Set the current user (after login).
   */
  setCurrentUser(user: User): void {
    this.currentUserSubject.next(user);
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(user));
  }

  /**
   * Check if current user is an admin.
   */
  isAdmin(): boolean {
    return this.currentUserSubject.value?.role === 'admin';
  }

  /**
   * Check if user is logged in.
   */
  isLoggedIn(): boolean {
    return this.currentUserSubject.value !== null;
  }

  /**
   * Restore user from localStorage on app init.
   */
  private getUserFromStorage(): User | null {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return null;
      }
    }
    return null;
  }

  /**
   * Mã hóa mật khẩu bằng Base64 (có thể nâng cấp thành bcrypt hoặc crypto nếu cần)
   */
  private encryptPassword(password: string): string {
    return btoa(password); // Sử dụng Base64, hoặc có thể dùng crypto library tốt hơn
  }

  /**
   * Giải mã mật khẩu
   */
  private decryptPassword(hash: string): string {
    return atob(hash);
  }

  /**
   * ✅ Kiểm tra email đã tồn tại trong Firebase Authentication chưa
   */
  async checkEmailExists(email: string): Promise<boolean> {
    try {
      const methods = await fetchSignInMethodsForEmail(firebaseAuth, email);
      return methods.length > 0;
    } catch (error) {
      console.error('Lỗi kiểm tra email:', error);
      return false;
    }
  }

  /**
   * Kiểm tra tên tài khoản đã tồn tại trong Firestore
   */
  async checkUsernameExists(username: string): Promise<boolean> {
    return await this.firebaseService.checkUsernameExists(username);
  }

  /**
   * Lấy user credentials từ Firestore bằng username
   */
  async getUserCredentialsByUsername(username: string): Promise<UserCredentials | null> {
    return await this.firebaseService.getUserCredentialsByUsername(username);
  }

  /**
   * Đăng nhập với username và password (kiểm tra từ Firestore)
   */
  async loginWithUsername(username: string, password: string): Promise<User | null> {
    try {
      // Lấy credentials từ Firestore để tìm email tương ứng với username
      const credentials = await this.getUserCredentialsByUsername(username);
      if (!credentials || !credentials.email) {
        throw new Error('Tài khoản không tồn tại');
      }

      // Dùng Firebase Auth để đăng nhập bằng email + password
      const credential = await signInWithEmailAndPassword(firebaseAuth, credentials.email, password);
      const firebaseUser = credential.user;

      const user: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || credentials.email,
        fullName: firebaseUser.displayName || credentials.fullName || (credentials.email || '').split('@')[0],
        username: credentials.username,
        role: credentials.role === 'admin' ? 'admin' : 'user',
        token: firebaseUser.refreshToken || ''
      };
      this.setCurrentUser(user);

      // Ensure userCredentials exists and is synced
      try {
        const existing = await this.firebaseService.getUserCredentialsByUid(firebaseUser.uid);
        if (!existing) {
          await this.firebaseService.createUserCredentials({
            uid: firebaseUser.uid,
            username: credentials.username,
            email: firebaseUser.email || credentials.email,
            passwordHash: '',
            role: user.role
          } as any);
        }
      } catch (err) {
        console.warn('Không thể đồng bộ userCredentials sau login:', err);
      }

      return user;
    } catch (error: any) {
      console.error('Login error:', error);
      return null;
    }
  }

  /**
   * Đăng nhập cơ bản bằng email và password qua Firebase
   */
  async loginSimpleEmail(email: string, password: string, role: 'user' | 'admin' = 'user'): Promise<User | null> {
    try {
      const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
      const user: User = {
        id: credential.user.uid,
        email: credential.user.email || '',
        fullName: credential.user.displayName || email.split('@')[0],
        username: credential.user.displayName || '',
        role,
        token: credential.user.refreshToken || ''
      };
      this.setCurrentUser(user);
      
      // Đảm bảo có document trong userCredentials để admin đọc được
      try {
        const existing = await this.firebaseService.getUserCredentialsByUid(credential.user.uid);
        if (!existing) {
          await this.firebaseService.createUserCredentials({
            uid: credential.user.uid,
            username: credential.user.displayName || email.split('@')[0],
            email: credential.user.email || email,
            passwordHash: '',
            role
          } as any);
        }
      } catch (err) {
        console.warn('Không thể đồng bộ userCredentials sau login:', err);
      }
      return user;
    } catch (error: any) {
      console.error('Login error:', error);
      return null;
    }
  }

  /**
   * Hàm login cũ (Observable) - giữ lại để backward compatible
   */
  login(email: string, password: string, role: 'user' | 'admin' = 'user'): Observable<User> {
    return from(this.loginSimpleEmail(email, password, role).then(user => {
      if (!user) throw new Error('Login failed');
      return user;
    }));
  }

  /**
   * ✅ Đăng ký tài khoản mới với email, password qua Firebase (không cần username)
   */
  async registerSimpleEmail(email: string, password: string, fullName: string): Promise<User | null> {
    try {
      // ✅ Kiểm tra email đã tồn tại chưa
      const emailExists = await this.checkEmailExists(email);
      if (emailExists) {
        console.error('Email này đã được đăng ký rồi:', email);
        throw new Error('Email này đã được đăng ký. Vui lòng dùng email khác hoặc đăng nhập.');
      }

      // ✅ Kiểm tra password độ dài tối thiểu
      if (password.length < 6) {
        throw new Error('Mật khẩu phải có ít nhất 6 ký tự.');
      }

      const credential = await createUserWithEmailAndPassword(firebaseAuth, email, password);
      const firebaseUser = credential.user;
      
      // Set display name in Firebase profile
      try {
        await updateProfile(firebaseUser, { displayName: fullName || '' });
      } catch (err) {
        console.warn('Không thể set displayName cho user mới:', err);
      }

      // Tạo userCredentials trong Firestore
      try {
        await this.firebaseService.createUserCredentials({
          uid: firebaseUser.uid,
          username: fullName || email.split('@')[0],
          email: firebaseUser.email || email,
          passwordHash: this.encryptPassword(password),
          role: 'user',
          fullName: fullName || undefined,
          phone: '',
          pinCode: ''
        } as any);
      } catch (err) {
        console.error('Lỗi tạo userCredentials sau register:', err);
        // Xóa user Firebase nếu không tạo được Firestore doc
        try {
          await firebaseUser.delete();
        } catch (deleteErr) {
          console.warn('Không thể xóa Firebase user:', deleteErr);
        }
        throw new Error('Không thể tạo hồ sơ người dùng. Vui lòng thử lại.');
      }

      const user: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || email,
        fullName: fullName || email.split('@')[0],
        username: fullName || email.split('@')[0],
        role: 'user',
        token: firebaseUser.refreshToken || ''
      };
      this.setCurrentUser(user);
      console.log('✅ Đăng ký thành công:', user);
      return user;
    } catch (error: any) {
      console.error('Register error:', error);
      
      // ✅ Xử lý các lỗi Firebase cụ thể
      if (error.code === 'auth/email-already-in-use') {
        console.error('Email đã được đăng ký.');
      } else if (error.code === 'auth/weak-password') {
        console.error('Mật khẩu quá yếu (phải ≥ 6 ký tự).');
      } else if (error.code === 'auth/invalid-email') {
        console.error('Email không hợp lệ.');
      }
      
      return null;
    }
  }

  /**
   * Hàm register cũ (Observable) - giữ lại để backward compatible
   */
  register(email: string, password: string, fullName: string): Observable<User> {
    return from(this.registerSimpleEmail(email, password, fullName).then(user => {
      if (!user) throw new Error('Register failed');
      return user;
    }));
  }

  /**
   * Đăng ký tài khoản mới với username, email, password qua Firebase
   */
  async registerWithUsername(
    username: string, 
    email: string, 
    password: string, 
    additionalInfo?: { fullName?: string; phone?: string; pinCode?: string }
  ): Promise<User | null> {
    try {
      // ✅ Kiểm tra email đã tồn tại chưa
      const emailExists = await this.checkEmailExists(email);
      if (emailExists) {
        throw new Error('Email này đã được đăng ký. Vui lòng dùng email khác.');
      }

      // Kiểm tra tên tài khoản đã tồn tại
      const usernameExists = await this.checkUsernameExists(username);
      if (usernameExists) {
        throw new Error('Tên tài khoản đã tồn tại. Vui lòng chọn tên khác.');
      }
      
      // Lấy thông tin từ additionalInfo
      const fullName = additionalInfo?.fullName || email.split('@')[0];
      const phone = additionalInfo?.phone || '';
      const pinCode = additionalInfo?.pinCode || '';
      
      // Tạo user trong Firebase Authentication
      const credential = await createUserWithEmailAndPassword(firebaseAuth, email, password);
      const firebaseUser = credential.user;
      
      // Set display name in Firebase profile
      try {
        await updateProfile(firebaseUser, { displayName: fullName || username });
      } catch (err) {
        console.warn('Không thể set displayName cho user mới:', err);
      }

      // Tạo hoặc đồng bộ userCredentials trong Firestore (không lưu mật khẩu plaintext)
      try {
        await this.firebaseService.createUserCredentials({
          uid: firebaseUser.uid,
          username,
          email: firebaseUser.email || email,
          passwordHash: this.encryptPassword(password),
          role: 'user',
          pinCode: pinCode || undefined,
          fullName: fullName || undefined,
          phone: phone || undefined
        } as any);
      } catch (err) {
        console.error('Lỗi tạo userCredentials sau register:', err);
        // Xóa user Firebase nếu không tạo được Firestore doc
        try {
          await firebaseUser.delete();
        } catch (deleteErr) {
          console.warn('Không thể xóa Firebase user:', deleteErr);
        }
        throw err;
      }

      // Tạo user object và set current user
      const user: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || email,
        fullName: fullName,
        username,
        role: 'user',
        token: firebaseUser.refreshToken || ''
      };
      this.setCurrentUser(user);
      return user;
    } catch (error: any) {
      console.error('Register error:', error);
      return null;
    }
  }

  /**
   * Simple signup using Firebase Auth (email/password).
   * Creates a Firestore `userCredentials` document if missing.
   */
  async signUpSimple(email: string, password: string, fullName?: string): Promise<User | null> {
    try {
      // ✅ Kiểm tra email đã tồn tại chưa
      const emailExists = await this.checkEmailExists(email);
      if (emailExists) {
        throw new Error('Email này đã được đăng ký.');
      }

      const credential = await createUserWithEmailAndPassword(firebaseAuth, email, password);
      const firebaseUser = credential.user;

      // Set display name
      try {
        await updateProfile(firebaseUser, { displayName: fullName || '' });
      } catch (err) {
        console.warn('Could not set displayName after signup:', err);
      }

      const name = fullName || firebaseUser.displayName || email.split('@')[0];

      try {
        await this.firebaseService.createUserCredentials({
          uid: firebaseUser.uid,
          username: name,
          email: firebaseUser.email || email,
          passwordHash: this.encryptPassword(password),
          role: 'user',
          fullName: name
        } as any);
      } catch (err) {
        console.warn('Could not create userCredentials after signup:', err);
        // Xóa user Firebase nếu không tạo được Firestore doc
        try {
          await firebaseUser.delete();
        } catch (deleteErr) {
          console.warn('Không thể xóa Firebase user:', deleteErr);
        }
      }

      const user: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || email,
        fullName: name,
        username: name,
        role: 'user',
        token: firebaseUser.refreshToken || ''
      };
      this.setCurrentUser(user);
      return user;
    } catch (error: any) {
      console.error('Simple signup error:', error);
      return null;
    }
  }

  /**
   * Simple signin using Firebase Auth (email/password).
   * Syncs `userCredentials` if missing and returns the `User`.
   */
  async signInSimple(email: string, password: string): Promise<User | null> {
    try {
      const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
      const firebaseUser = credential.user;

      // Try to find credentials by uid
      let creds = await this.firebaseService.getUserCredentialsByUid(firebaseUser.uid);
      // Fallback: try to find by email
      if (!creds) {
        creds = await this.firebaseService.getUserCredentialsByEmail(firebaseUser.email || email);
      }

      const username = creds?.username || firebaseUser.displayName || '';
      const fullName = firebaseUser.displayName || creds?.fullName || (firebaseUser.email || email).split('@')[0];
      const role: 'user' | 'admin' = creds && creds.role === 'admin' ? 'admin' : 'user';

      // Ensure credentials exist for admin UI
      if (!creds) {
        try {
          await this.firebaseService.createUserCredentials({
            uid: firebaseUser.uid,
            username,
            email: firebaseUser.email || email,
            passwordHash: '',
            role
          } as any);
        } catch (err) {
          console.warn('Could not create userCredentials after signin:', err);
        }
      }

      const user: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || email,
        fullName,
        username,
        role,
        token: firebaseUser.refreshToken || ''
      };
      this.setCurrentUser(user);
      return user;
    } catch (error: any) {
      console.error('Simple signin error:', error);
      return null;
    }
  }

  /**
   * Logout: sign out from Firebase and reset theme to light mode.
   */
  logout(): Observable<void> {
    return from(
      signOut(firebaseAuth).then(() => {
        this.currentUserSubject.next(null);
        localStorage.removeItem(this.STORAGE_KEY);
        // Reset theme to light mode on logout
        this.themeService.setTheme('light');
      })
    );
  }

  /**
   * Cập nhật quyền (role) cho user bằng username
   */
  async updateUserRole(username: string, role: 'user' | 'admin'): Promise<void> {
    await this.firebaseService.updateUserRoleByUsername(username, role);
  }

  /**
   * Ví dụ: Gán quyền admin cho tài khoản 'CT070221'
   */
  async makeCT070221Admin(): Promise<void> {
    await this.updateUserRole('CT070221', 'admin');
    console.log('Đã gán quyền admin cho tài khoản CT070221!');
  }

  /**
   * Đăng nhập bằng Google
   */
  async loginWithGoogle(): Promise<User | null> {
    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(firebaseAuth, provider);
      const firebaseUser = result.user;
      // Lấy user credentials từ Firestore bằng uid (an toàn với security rules)
      let userCredentials = await this.firebaseService.getUserCredentialsByUid(firebaseUser.uid);
      let role: 'user' | 'admin' = 'user';
      if (userCredentials && userCredentials.role === 'admin') {
        role = 'admin';
      }
      const user: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || '',
        fullName: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'User',
        username: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || '',
        role,
        token: firebaseUser.refreshToken || ''
      };
      this.setCurrentUser(user);
      // Nếu chưa có user trong Firestore thì lưu mới
      if (!userCredentials) {
        await this.firebaseService.createUserCredentials({
          uid: firebaseUser.uid,
          username: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || '',
          email: firebaseUser.email || '',
          passwordHash: '',
          role: 'user',
        } as any);
      }
      return user;
    } catch (error: any) {
      // Handle common user-cancelled popup error gracefully
      if (error && (error.code === 'auth/popup-closed-by-user' || error.message?.includes('popup closed by the user'))) {
        console.info('User closed Google login popup.');
        return null;
      }
      console.error('Google login error:', error);
      return null;
    }
  }

  /**
   * Đổi mật khẩu cho người dùng (username/password)
   */
  async changePassword(username: string, oldPassword: string, newPassword: string): Promise<boolean> {
    try {
      // First try to update password via Firebase Auth for the currently signed-in user
      const currentUser = firebaseAuth.currentUser;
      if (currentUser && currentUser.email) {
        // If oldPassword provided, reauthenticate
        if (oldPassword) {
          const cred = EmailAuthProvider.credential(currentUser.email, oldPassword);
          await reauthenticateWithCredential(currentUser, cred);
        }
        // Update password in Firebase Auth
        await updatePassword(currentUser, newPassword);

        // Also update Firestore passwordHash for legacy username flows (store base64)
        try {
          const newHash = this.encryptPassword(newPassword);
          await this.firebaseService.updateUserPassword(username, newHash);
        } catch (err) {
          console.warn('Could not update Firestore passwordHash after changing Auth password:', err);
        }
        return true;
      }

      // Fallback: legacy username/password stored in Firestore
      const credentials = await this.getUserCredentialsByUsername(username);
      if (!credentials) {
        throw new Error('Không tìm thấy tài khoản');
      }

      // Nếu oldPassword rỗng (reset), bỏ qua kiểm tra mật khẩu cũ
      if (oldPassword) {
        const decryptedOldPassword = this.decryptPassword(credentials.passwordHash);
        if (decryptedOldPassword !== oldPassword) {
          return false;
        }
      }

      // Mã hóa mật khẩu mới và cập nhật Firestore
      const newPasswordHash = this.encryptPassword(newPassword);
      await this.firebaseService.updateUserPassword(username, newPasswordHash);
      return true;
    } catch (error) {
      console.error('Change password error:', error);
      return false;
    }
  }
}