import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-change-pass2',
  templateUrl: './change-pass2.component.html',
  styleUrls: ['./change-pass2.component.scss']
})
export class ChangePass2Component {
  changePassForm: FormGroup;
  errorMsg: string = '';
  successMsg: string = '';
  constructor(private fb: FormBuilder, private auth: AuthService, private router: Router) {
    this.changePassForm = this.fb.group({
      newPassword: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]]
    });
  }

  onSubmit() {
    this.errorMsg = '';
    this.successMsg = '';
    if (this.changePassForm.invalid) {
      this.errorMsg = 'Vui lòng nhập đủ thông tin.';
      return;
    }
    const { newPassword, confirmPassword } = this.changePassForm.value;
    if (newPassword !== confirmPassword) {
      this.errorMsg = 'Mật khẩu xác nhận không khớp.';
      return;
    }
    if (newPassword.length < 6) {
      this.errorMsg = 'Mật khẩu phải từ 6 ký tự trở lên.';
      return;
    }
    const username = localStorage.getItem('resetUsername') || '';
    this.auth.changePassword(username, '', newPassword).then(() => {
      this.successMsg = 'Đổi mật khẩu thành công! Vui lòng đăng nhập lại.';
      setTimeout(() => {
        this.router.navigate(['/login']);
      }, 2000);
    }).catch(err => {
      this.errorMsg = 'Đổi mật khẩu thất bại.';
    });
  }
}
