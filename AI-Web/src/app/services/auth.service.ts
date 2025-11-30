import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, from } from 'rxjs';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  Auth,
  UserCredential,
  GoogleAuthProvider,
  signInWithPopup
} from 'firebase/auth';
import { firebaseAuth } from '../../environments/firebase.config';
import { FirebaseService } from './firebase.service';
import { ThemeService } from './theme.service';

export interface User {
  id: string;
  email: string;
  fullName: string;
  username: string;
  role: 'user' | 'admin'; // 'user' or 'admin'
  token?: string;
}

export interface UserCredentials {
  id?: string;
  uid: string;
  username: string;
  email: string;
  passwordHash: string;
  role?: 'user' | 'admin';
  createdAt?: any;
  updatedAt?: any;
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
        // Nếu đã có user từ localStorage (username/password) thì không ghi đè
        if (!this.currentUserSubject.value) {
          const user: User = {
            id: firebaseUser.uid,
            email: firebaseUser.email || '',
            fullName: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'User',
            username: firebaseUser.displayName || '',
            role: 'user',
            token: firebaseUser.refreshToken || ''
          };
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
      // Lấy credentials từ Firestore
      const credentials = await this.getUserCredentialsByUsername(username);
      
      if (!credentials) {
        throw new Error('Tài khoản không tồn tại');
      }

      // Kiểm tra mật khẩu
      const decryptedPassword = this.decryptPassword(credentials.passwordHash);
      if (decryptedPassword !== password) {
        throw new Error('Mật khẩu không chính xác');
      }

      // Tạo user object
      const user: User = {
        id: credentials.uid,
        email: credentials.email,
        fullName: credentials.email.split('@')[0],
        username: credentials.username,
        role: credentials.role === 'admin' ? 'admin' : 'user',
        token: ''
      };
      this.setCurrentUser(user);
      return user;
    } catch (error) {
      console.error('Login error:', error);
      return null;
    }
  }

  /**
   * Simulate login (for demo purposes).
   * In a real app, call your backend API here.
   */
  login(email: string, password: string, role: 'user' | 'admin' = 'user'): Observable<User> {
    return from(
      signInWithEmailAndPassword(firebaseAuth, email, password).then((credential) => {
        const user: User = {
          id: credential.user.uid,
          email: credential.user.email || '',
          fullName: credential.user.displayName || email.split('@')[0],
          username: credential.user.displayName || '',
          role,
          token: credential.user.refreshToken || ''
        };
        this.setCurrentUser(user);
        return user;
      })
    );
  }

  /**
   * Đăng ký tài khoản mới với username, email, password mã hóa
   */
  async registerWithUsername(
    username: string, 
    email: string, 
    password: string, 
    additionalInfo?: { fullName?: string; phone?: string; pinCode?: string }
  ): Promise<User | null> {
    try {
      // Kiểm tra tên tài khoản đã tồn tại
      const usernameExists = await this.checkUsernameExists(username);
      if (usernameExists) {
        throw new Error('Tên tài khoản đã tồn tại. Vui lòng chọn tên khác.');
      }

      // Tạo document credentials mã hóa trong Firestore
      const passwordHash = this.encryptPassword(password);
      const uid = 'user_' + Date.now(); // Tạo ID duy nhất

      // Lấy thông tin từ additionalInfo
      const fullName = additionalInfo?.fullName || email.split('@')[0];
      const phone = additionalInfo?.phone || '';
      const pinCode = additionalInfo?.pinCode || '';

      await this.firebaseService.createUserCredentials({
        uid,
        username,
        email,
        passwordHash,
        role: 'user', // Mặc định là user
        pinCode: pinCode || undefined,
        fullName: fullName || undefined,
        phone: phone || undefined
      });

      // Tạo user object
      const user: User = {
        id: uid,
        email,
        fullName: fullName,
        username,
        role: 'user',
        token: ''
      };
      this.setCurrentUser(user);
      return user;
    } catch (error) {
      console.error('Register error:', error);
      return null;
    }
  }

  /**
   * Register a new user with Firebase Authentication.
   */
  register(email: string, password: string, fullName: string): Observable<User> {
    return from(
      createUserWithEmailAndPassword(firebaseAuth, email, password).then((credential) => {
        const user: User = {
          id: credential.user.uid,
          email: credential.user.email || '',
          fullName: fullName || email.split('@')[0],
          username: '',
          role: 'user',
          token: credential.user.refreshToken || ''
        };
        this.setCurrentUser(user);
        return user;
      })
    );
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
      // Lấy user từ Firestore bằng email
      let userCredentials = await this.firebaseService.getUserCredentialsByEmail(firebaseUser.email || '');
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
    } catch (error) {
      console.error('Google login error:', error);
      return null;
    }
  }

  /**
   * Đổi mật khẩu cho người dùng (username/password)
   */
  async changePassword(username: string, oldPassword: string, newPassword: string): Promise<boolean> {
    try {
      // Lấy credentials từ Firestore
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

      // Mã hóa mật khẩu mới
      const newPasswordHash = this.encryptPassword(newPassword);
      // Cập nhật mật khẩu trong Firestore
      await this.firebaseService.updateUserPassword(username, newPasswordHash);
      return true;
    } catch (error) {
      console.error('Change password error:', error);
      return false;
    }
  }
}
