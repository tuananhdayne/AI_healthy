import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../services/auth.service';
import { FirebaseService, HealthProfile } from '../services/firebase.service';

@Component({
  selector: 'app-health-profile-setup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './health-profile-setup.component.html',
  styleUrls: ['./health-profile-setup.component.scss']
})
export class HealthProfileSetupComponent implements OnInit {
  @Output() profileSaved = new EventEmitter<void>();
  
  setupForm: FormGroup;
  isLoading = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private firebaseService: FirebaseService
  ) {
    this.setupForm = this.fb.group({
      tuoi: ['', [Validators.required, Validators.min(1), Validators.max(120)]],
      chieuCao: ['', [Validators.required, Validators.min(50), Validators.max(250)]],
      canNang: ['', [Validators.required, Validators.min(10), Validators.max(300)]],
      mucVanDong: ['it', [Validators.required]],
      gioiTinh: ['nam', [Validators.required]]
    });
  }

  ngOnInit(): void {
    // Load existing profile if available
    this.loadExistingProfile();
  }

  async loadExistingProfile(): Promise<void> {
    const user = this.authService.getCurrentUser();
    if (!user) return;

    try {
      const profile = await this.firebaseService.getHealthProfile(user.id);
      if (profile) {
        this.setupForm.patchValue(profile);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
    }
  }

  async onSubmit(): Promise<void> {
    if (this.setupForm.invalid) {
      this.setupForm.markAllAsTouched();
      return;
    }

    const user = this.authService.getCurrentUser();
    if (!user) {
      this.errorMessage = 'Vui lòng đăng nhập để lưu hồ sơ';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    try {
      const profileData: HealthProfile = {
        tuoi: Number(this.setupForm.value.tuoi),
        chieuCao: Number(this.setupForm.value.chieuCao),
        canNang: Number(this.setupForm.value.canNang),
        mucVanDong: this.setupForm.value.mucVanDong,
        gioiTinh: this.setupForm.value.gioiTinh
      };

      await this.firebaseService.saveHealthProfile(user.id, profileData);
      this.profileSaved.emit();
    } catch (error) {
      console.error('Error saving profile:', error);
      this.errorMessage = 'Có lỗi xảy ra khi lưu hồ sơ. Vui lòng thử lại.';
    } finally {
      this.isLoading = false;
    }
  }

  getMucVanDongLabel(value: string): string {
    const labels: { [key: string]: string } = {
      'it': 'Ít',
      'vua': 'Vừa',
      'nhieu': 'Nhiều'
    };
    return labels[value] || value;
  }
}

