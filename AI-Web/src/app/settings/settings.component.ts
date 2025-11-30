import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { SettingsService, AppSettings } from '../services/settings.service';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/auth.service';
import { ThemeService, Theme } from '../services/theme.service';
import { Router } from '@angular/router';
import { FirebaseService } from '../services/firebase.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsComponent implements OnInit {
  settingsForm: FormGroup;
  userInfoForm: FormGroup;
  pinForm: FormGroup;
  currentTheme: Theme = 'light';
  navItems = [
    'Chung',
    'Thông báo',
    'Tài khoản'
  ];
  active = 'Chung';
  currentUser: any = null;
  userCredentials: any = null;
  isLoadingUserInfo = false;
  isLoadingPin = false;
  userInfoMessage = '';
  userInfoError = '';
  pinMessage = '';
  pinError = '';

  constructor(
    private fb: FormBuilder, 
    private settingsService: SettingsService,
    private authService: AuthService, 
    private router: Router, 
    private themeService: ThemeService,
    private firebaseService: FirebaseService
  ) {
      this.settingsForm = this.fb.group({
        theme: ['light'],
        notifications: [true],
        pushNotifications: [false],
        aiModel: ['gpt-4'],
        apiKey: [''],
        language: ['auto']
      });

    this.userInfoForm = this.fb.group({
      fullName: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', [Validators.pattern(/^[0-9]{10,11}$/)]]
    });

    this.pinForm = this.fb.group({
      currentPin: ['', [Validators.required, Validators.pattern(/^[0-9]{6}$/)]],
      newPin: ['', [Validators.required, Validators.pattern(/^[0-9]{6}$/)]],
      confirmPin: ['', [Validators.required, Validators.pattern(/^[0-9]{6}$/)]]
    }, {
      validators: this.pinMatchValidator
    });
  }

  async ngOnInit(): Promise<void> {
    // Load từ localStorage trước
    const s: AppSettings = this.settingsService.getSettings();
    
    // Load pushNotifications từ localStorage riêng nếu có
    const pushNotifications = localStorage.getItem('pushNotifications');
    if (pushNotifications) {
      s.pushNotifications = JSON.parse(pushNotifications);
    }
    
    this.settingsForm.patchValue(s);
    
    // Load từ Firebase nếu user đã đăng nhập
    this.currentUser = this.authService.getCurrentUser();
    if (this.currentUser) {
      try {
        const firebaseSettings = await this.firebaseService.getSettings(this.currentUser.id);
        if (firebaseSettings) {
          // Merge với localStorage settings
          this.settingsForm.patchValue({
            theme: firebaseSettings.theme,
            notifications: firebaseSettings.notifications,
            aiModel: firebaseSettings.aiModel,
            apiKey: firebaseSettings.apiKey || '',
            pushNotifications: s.pushNotifications || false
          });
        }

        // Load user credentials để hiển thị thông tin
        if (this.currentUser.username) {
          try {
            this.userCredentials = await this.firebaseService.getUserCredentialsByUsername(this.currentUser.username);
            if (this.userCredentials) {
              this.userInfoForm.patchValue({
                fullName: this.userCredentials.fullName || this.currentUser.fullName || '',
                email: this.userCredentials.email || this.currentUser.email || '',
                phone: this.userCredentials.phone || ''
              });
            }
          } catch (credError) {
            console.error('Error loading user credentials:', credError);
            // Fallback to currentUser data
            this.userInfoForm.patchValue({
              fullName: this.currentUser.fullName || '',
              email: this.currentUser.email || '',
              phone: ''
            });
          }
        } else {
          // Google login - chỉ hiển thị thông tin, không cho chỉnh sửa
          this.userInfoForm.patchValue({
            fullName: this.currentUser.fullName || '',
            email: this.currentUser.email || '',
            phone: ''
          });
          this.userInfoForm.disable(); // Disable form cho Google login
        }
      } catch (error) {
        console.error('Error loading settings from Firebase:', error);
      }
    }
    
    this.currentTheme = this.themeService.getCurrentTheme();
    this.themeService.theme$.subscribe(theme => {
      this.currentTheme = theme;
      this.settingsForm.patchValue({ theme }, { emitEvent: false });
    });
    // Apply theme immediately when user changes the select/radio
    this.settingsForm.get('theme')?.valueChanges.subscribe((val: Theme) => {
      if (val === 'light' || val === 'dark') {
        this.themeService.setTheme(val);
      }
    });
  }

  pinMatchValidator(form: FormGroup) {
    const newPin = form.get('newPin');
    const confirmPin = form.get('confirmPin');
    if (newPin && confirmPin && newPin.value !== confirmPin.value) {
      confirmPin.setErrors({ pinMismatch: true });
      return { pinMismatch: true };
    }
    return null;
  }

  onPinCodeKeyPress(event: KeyboardEvent): void {
    const charCode = event.which ? event.which : event.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
      event.preventDefault();
    }
  }

  onPinInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    // Khi có giá trị, áp dụng letter-spacing, khi rỗng thì để placeholder hiển thị bình thường
    if (input.value.length > 0) {
      input.style.letterSpacing = '4px';
      input.style.textAlign = 'center';
    } else {
      input.style.letterSpacing = 'normal';
      input.style.textAlign = 'left';
    }
  }

  setActive(item: string) {
    this.active = item;
  }

  getNavIcon(item: string): string {
    const icons: { [key: string]: string } = {
      'Chung': '⚙️',
      'Thông báo': '🔔',
      'Tài khoản': '👤'
    };
    return icons[item] || '⚙️';
  }

  getHeaderDescription(item: string): string {
    const descriptions: { [key: string]: string } = {
      'Chung': 'Tùy chỉnh giao diện và ngôn ngữ',
      'Thông báo': 'Quản lý thông báo và nhắc nhở',
      'Tài khoản': 'Thông tin cá nhân và bảo mật'
    };
    return descriptions[item] || '';
  }

  onNotificationChange(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    this.settingsForm.patchValue({ notifications: checked });
  }

  async onPushNotificationChange(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    this.settingsForm.patchValue({ pushNotifications: checked });
    
    if (checked) {
      // Yêu cầu quyền thông báo
      if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          console.log('Push notification permission granted');
        } else {
          alert('Bạn cần cho phép thông báo để nhận nhắc nhở uống thuốc.');
          this.settingsForm.patchValue({ pushNotifications: false });
        }
      }
    }
  }

  logout() {
    this.authService.logout().subscribe({
      next: () => {
        console.log('User logged out');
        try { this.router.navigate(['/']); } catch(e) {}
      },
      error: (err: any) => {
        console.error('Logout failed', err);
      }
    });
  }

  async save(): Promise<void> {
    const val: AppSettings = this.settingsForm.value;
    const theme = this.settingsForm.get('theme')?.value as Theme;
    if (theme && (theme === 'light' || theme === 'dark')) {
      this.themeService.setTheme(theme);
    }
    
    // Lưu vào localStorage (bao gồm pushNotifications)
    this.settingsService.saveSettings(val);
    
    // Lưu vào Firebase nếu user đã đăng nhập
    const user = this.authService.getCurrentUser();
    if (user) {
      try {
        await this.firebaseService.saveSettings(user.id, {
          userId: user.id,
          theme: val.theme,
          language: 'vi',
          notifications: val.notifications,
          aiModel: val.aiModel,
          apiKey: val.apiKey || '',
          accent: 'default',
          voice: 'default'
        });
        
        // Lưu pushNotifications vào localStorage riêng để không bị mất
        localStorage.setItem('pushNotifications', JSON.stringify(val.pushNotifications || false));
      } catch (error) {
        console.error('Error saving settings to Firebase:', error);
      }
    }
    
    // feedback đơn giản
    alert('Cài đặt đã được lưu.');
  }

  reset(): void {
    this.settingsService.resetDefaults();
    this.settingsForm.patchValue(this.settingsService.getSettings());
  }

  goToChangePassword(): void {
    this.router.navigate(['/change-password']);
  }

  async saveUserInfo(): Promise<void> {
    if (this.userInfoForm.invalid || !this.currentUser?.username) {
      this.userInfoError = 'Vui lòng điền đầy đủ thông tin hợp lệ';
      return;
    }

    this.isLoadingUserInfo = true;
    this.userInfoError = '';
    this.userInfoMessage = '';

    try {
      const { fullName, email, phone } = this.userInfoForm.value;
      await this.firebaseService.updateUserInfoByUsername(this.currentUser.username, {
        fullName,
        email,
        phone
      });

      // Cập nhật currentUser
      const updatedUser = {
        ...this.currentUser,
        fullName,
        email
      };
      this.authService.setCurrentUser(updatedUser);

      this.userInfoMessage = 'Đã cập nhật thông tin thành công!';
      setTimeout(() => {
        this.userInfoMessage = '';
      }, 3000);
    } catch (error) {
      this.userInfoError = 'Có lỗi xảy ra khi cập nhật thông tin';
      console.error('Error updating user info:', error);
    } finally {
      this.isLoadingUserInfo = false;
    }
  }

  async savePin(): Promise<void> {
    if (this.pinForm.invalid || !this.currentUser?.username) {
      this.pinError = 'Vui lòng điền đầy đủ thông tin hợp lệ';
      return;
    }

    this.isLoadingPin = true;
    this.pinError = '';
    this.pinMessage = '';

    try {
      const { currentPin, newPin } = this.pinForm.value;

      // Kiểm tra PIN hiện tại
      if (!this.userCredentials) {
        this.userCredentials = await this.firebaseService.getUserCredentialsByUsername(this.currentUser.username);
      }

      if (!this.userCredentials?.pinCode || this.userCredentials.pinCode !== currentPin) {
        this.pinError = 'Mã PIN hiện tại không đúng';
        this.isLoadingPin = false;
        return;
      }

      // Cập nhật PIN mới
      await this.firebaseService.updateUserPinByUsername(this.currentUser.username, newPin);

      // Cập nhật local credentials
      this.userCredentials.pinCode = newPin;

      this.pinMessage = 'Đã cập nhật mã PIN thành công!';
      this.pinForm.reset();
      setTimeout(() => {
        this.pinMessage = '';
      }, 3000);
    } catch (error) {
      this.pinError = 'Có lỗi xảy ra khi cập nhật mã PIN';
      console.error('Error updating PIN:', error);
    } finally {
      this.isLoadingPin = false;
    }
  }
}
