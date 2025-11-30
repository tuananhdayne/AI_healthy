
import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { FirebaseService } from '../services/firebase.service';

@Component({
  selector: 'app-miss-pass',
  templateUrl: './miss-pass.component.html',
  styleUrls: ['./miss-pass.component.scss']
})
export class MissPassComponent {
  forgotPasswordForm: FormGroup;
  isLoading: boolean = false;
  errorMessage: string = '';
  showError: boolean = false;
  successMessage: string = '';
  showSuccess: boolean = false;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private firebaseService: FirebaseService
  ) {
    this.forgotPasswordForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      username: ['', [Validators.required]],
      pinCode: ['', [Validators.required, Validators.pattern(/^[0-9]{6}$/)]],
    });
  }

  async onSubmit(): Promise<void> {
    if (this.forgotPasswordForm.valid) {
      this.isLoading = true;
      this.showError = false;
      this.showSuccess = false;
      this.errorMessage = '';
      this.successMessage = '';

      const email = this.forgotPasswordForm.get('email')?.value;
      // Kiểm tra thông tin với Firebase
      const username = this.forgotPasswordForm.get('username')?.value;
      const pinCode = this.forgotPasswordForm.get('pinCode')?.value;
      try {
        const user = await this.firebaseService.getUserCredentialsByUsername(username);
        if (!user) {
          throw new Error('Không tìm thấy tài khoản với tên đăng nhập này');
        }
        
        // Kiểm tra email
        if (user.email !== email) {
          throw new Error('Email không khớp với tài khoản');
        }
        
        // Bắt buộc phải có và khớp PIN
        if (!user.pinCode || user.pinCode === '') {
          throw new Error('Tài khoản chưa có mã PIN. Vui lòng liên hệ admin.');
        }
        
        if (user.pinCode !== pinCode) {
          throw new Error('Mã PIN không đúng');
        }
        
        // Lưu username vào localStorage để dùng cho bước đổi mật khẩu
        localStorage.setItem('resetUsername', username);
        this.successMessage = `Thông tin hợp lệ. Vui lòng đặt lại mật khẩu mới.`;
        this.showSuccess = true;
        setTimeout(() => {
          this.router.navigate(['/change-password-2']);
        }, 1000);
      } catch (err: any) {
        this.errorMessage = err.message || 'Thông tin không hợp lệ.';
        this.showError = true;
      }
      this.isLoading = false;
    } else {
      Object.keys(this.forgotPasswordForm.controls).forEach(key => {
        this.forgotPasswordForm.get(key)?.markAsTouched();
      });
    }
  }

  clearError(): void {
    this.showError = false;
    this.errorMessage = '';
  }

  onPinCodeKeyPress(event: KeyboardEvent): void {
    const charCode = event.which ? event.which : event.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
      event.preventDefault();
    }
  }
}
