import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm: FormGroup;
  showPassword: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';
  showError: boolean = false;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService
  ) {
    this.loginForm = this.fb.group({
      username: ['', [Validators.required, Validators.minLength(3)]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      rememberMe: [false]
    });
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.showError = false;
      this.errorMessage = '';
      
      const username = this.loginForm.get('username')?.value;
      const password = this.loginForm.get('password')?.value;
      const rememberMe = this.loginForm.get('rememberMe')?.value;
      
      // Gọi authService để đăng nhập với username và password mã hóa
      this.authService.loginWithUsername(username, password).then((user) => {
        if (user) {
          // Lưu remember me preference
          if (rememberMe) {
            localStorage.setItem('rememberMe', 'true');
            localStorage.setItem('rememberedUsername', username);
          }
          // Chuyển hướng theo quyền
          if (user.role === 'admin') {
            this.router.navigate(['/admin']);
          } else {
            this.router.navigate(['/chat']);
          }
        } else {
          this.errorMessage = 'Tài khoản hoặc mật khẩu không chính xác. Vui lòng thử lại.';
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
      Object.keys(this.loginForm.controls).forEach(key => {
        this.loginForm.get(key)?.markAsTouched();
      });
    }
  }

  clearError(): void {
    this.showError = false;
    this.errorMessage = '';
  }

  ngOnInit(): void {
    // Kiểm tra remember me
    const rememberMe = localStorage.getItem('rememberMe');
    const rememberedUsername = localStorage.getItem('rememberedUsername');
    if (rememberMe && rememberedUsername) {
      this.loginForm.patchValue({
        username: rememberedUsername,
        rememberMe: true
      });
    }
  }
  loginWithGoogle(): void {
  this.authService.loginWithGoogle().then(user => {
    if (user) {
      if (user.role === 'admin') {
        this.router.navigate(['/admin']);
      } else {
        this.router.navigate(['/chat']);
      }
    } else {
      this.errorMessage = 'Đăng nhập Google thất bại!';
      this.showError = true;
    }
  });
}
}
