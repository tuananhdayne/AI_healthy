import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  registerForm: FormGroup;
  showPassword: boolean = false;
  showConfirmPassword: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';
  showError: boolean = false;
  successMessage: string = '';
  showSuccess: boolean = false;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService
  ) {
    this.registerForm = this.fb.group({
      username: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(20)]],
      fullName: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', [Validators.required, Validators.pattern(/^[0-9]{10,11}$/)]],
      pinCode: ['', [Validators.required, Validators.pattern(/^[0-9]{6}$/)]],
      confirmPinCode: ['', [Validators.required]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
      dateOfBirth: ['', [Validators.required]],
      agreeTerms: [false, [Validators.requiredTrue]]
    }, {
      validators: [this.passwordMatchValidator, this.pinCodeMatchValidator]
    });
  }

  passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
    const password = control.get('password');
    const confirmPassword = control.get('confirmPassword');
    
    if (!password || !confirmPassword) {
      return null;
    }
    
    return password.value === confirmPassword.value ? null : { passwordMismatch: true };
  }

  pinCodeMatchValidator(control: AbstractControl): ValidationErrors | null {
    const pinCode = control.get('pinCode');
    const confirmPinCode = control.get('confirmPinCode');
    
    if (!pinCode || !confirmPinCode) {
      return null;
    }
    
    return pinCode.value === confirmPinCode.value ? null : { pinCodeMismatch: true };
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
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

  onPinCodeKeyPress(event: KeyboardEvent): void {
    const charCode = event.which ? event.which : event.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
      event.preventDefault();
    }
  }

  onSubmit(): void {
    if (this.registerForm.valid) {
      this.isLoading = true;
      this.showError = false;
      this.showSuccess = false;
      this.errorMessage = '';
      this.successMessage = '';
      
      const username = this.registerForm.get('username')?.value;
      const email = this.registerForm.get('email')?.value;
      const password = this.registerForm.get('password')?.value;
      const fullName = this.registerForm.get('fullName')?.value;
      const phone = this.registerForm.get('phone')?.value;
      const pinCode = this.registerForm.get('pinCode')?.value;
      
      // Gọi authService để đăng ký với tên tài khoản duy nhất và mật khẩu mã hóa
      // Pass thêm fullName, phone, pinCode để lưu vào Firestore
      this.authService.registerWithUsername(username, email, password, { fullName, phone, pinCode }).then((user) => {
        if (user) {
          this.successMessage = 'Đăng ký thành công! Vui lòng đăng nhập.';
          this.showSuccess = true;
          console.log('Register successful:', user);
          
          // Redirect to login sau 2 giây
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 2000);
        } else {
          this.errorMessage = 'Tên tài khoản đã tồn tại hoặc có lỗi xảy ra. Vui lòng thử lại.';
          this.showError = true;
        }
        this.isLoading = false;
      }).catch((error) => {
        this.errorMessage = error.message || 'Có lỗi xảy ra. Vui lòng thử lại.';
        this.showError = true;
        this.isLoading = false;
      });
    } else {
      // Mark all fields as touched to show validation errors
      Object.keys(this.registerForm.controls).forEach(key => {
        this.registerForm.get(key)?.markAsTouched();
      });
    }
  }

  openSettings(): void {
    // Debug logging to verify the click handler runs and whether Router succeeds.
    console.log('[Register] openSettings() called');
    this.router.navigateByUrl('/settings')
      .then(result => {
        console.log('[Register] router.navigateByUrl result =', result);
        if (!result) {
          console.warn('[Register] Router returned false — falling back to full-page navigation');
          window.location.href = '/settings';
        }
      })
      .catch(err => {
        console.error('[Register] Navigation to /settings failed', err);
        // Fallback to full page navigation so user still gets to the settings page
        window.location.href = '/settings';
      });
  }
}
