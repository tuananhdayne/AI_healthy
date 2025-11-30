import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-change-pass',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './change-pass.component.html',
  styleUrls: ['./change-pass.component.scss']
})
export class ChangePassComponent implements OnInit {
  changePassForm!: FormGroup;
  showOldPassword = false;
  showNewPassword = false;
  showConfirmPassword = false;
  isLoading = false;
  showError = false;
  showSuccess = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  private initializeForm(): void {
    this.changePassForm = this.fb.group(
      {
        oldPassword: ['', [Validators.required, Validators.minLength(6)]],
        newPassword: ['', [Validators.required, Validators.minLength(6)]],
        confirmPassword: ['', [Validators.required, Validators.minLength(6)]]
      },
      { validators: this.passwordMatchValidator }
    );
  }

  private passwordMatchValidator(form: FormGroup) {
    const newPassword = form.get('newPassword');
    const confirmPassword = form.get('confirmPassword');

    if (newPassword && confirmPassword && newPassword.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    return null;
  }

  toggleOldPassword(): void {
    this.showOldPassword = !this.showOldPassword;
  }

  toggleNewPassword(): void {
    this.showNewPassword = !this.showNewPassword;
  }

  toggleConfirmPassword(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  clearError(): void {
    this.showError = false;
    this.errorMessage = '';
  }

  clearSuccess(): void {
    this.showSuccess = false;
    this.successMessage = '';
  }

  async onSubmit(): Promise<void> {
    if (this.changePassForm.valid) {
      this.isLoading = true;
      this.showError = false;
      this.showSuccess = false;
      this.errorMessage = '';
      this.successMessage = '';

      try {
        const currentUser = this.authService.getCurrentUser();
        if (!currentUser) {
          this.showError = true;
          this.errorMessage = 'Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại.';
          this.isLoading = false;
          return;
        }

        // Kiểm tra xem user có đăng nhập bằng Google không (không có username)
        if (!currentUser.username || currentUser.username === '') {
          this.showError = true;
          this.errorMessage = 'Tài khoản đăng nhập bằng Google không thể đổi mật khẩu tại đây.';
          this.isLoading = false;
          return;
        }

        const oldPassword = this.changePassForm.get('oldPassword')?.value;
        const newPassword = this.changePassForm.get('newPassword')?.value;

        // Call the auth service to change password (bắt buộc phải có oldPassword)
        const success = await this.authService.changePassword(currentUser.username, oldPassword, newPassword);

        if (success) {
          this.showSuccess = true;
          this.successMessage = 'Đổi mật khẩu thành công! Vui lòng đăng nhập lại.';
          this.changePassForm.reset();
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 2000);
        } else {
          this.showError = true;
          this.errorMessage = 'Mật khẩu cũ không chính xác. Vui lòng thử lại.';
        }
      } catch (error) {
        this.showError = true;
        this.errorMessage = error instanceof Error ? error.message : 'Có lỗi xảy ra. Vui lòng thử lại.';
      } finally {
        this.isLoading = false;
      }
    }
  }

  goBack(): void {
    this.router.navigate(['/chat']);
  }
}
