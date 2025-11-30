import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { FirebaseService, HealthProfile } from '../services/firebase.service';
import { HealthProfileService, BMIResult, ExerciseSuggestion } from '../services/health-profile.service';

@Component({
  selector: 'app-health-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './health-profile.component.html',
  styleUrls: ['./health-profile.component.scss']
})
export class HealthProfileComponent implements OnInit {
  profile: HealthProfile | null = null;
  bmiResult: BMIResult | null = null;
  exerciseSuggestion: ExerciseSuggestion | null = null;
  isEditing = false;
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  editForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private firebaseService: FirebaseService,
    private healthProfileService: HealthProfileService,
    private router: Router
  ) {
    this.editForm = this.fb.group({
      tuoi: ['', [Validators.required, Validators.min(1), Validators.max(120)]],
      chieuCao: ['', [Validators.required, Validators.min(50), Validators.max(250)]],
      canNang: ['', [Validators.required, Validators.min(10), Validators.max(300)]],
      mucVanDong: ['it', [Validators.required]],
      gioiTinh: ['nam', [Validators.required]]
    });
  }

  async ngOnInit(): Promise<void> {
    await this.loadProfile();
  }

  async loadProfile(): Promise<void> {
    const user = this.authService.getCurrentUser();
    if (!user) {
      this.router.navigate(['/login']);
      return;
    }

    this.isLoading = true;
    try {
      this.profile = await this.firebaseService.getHealthProfile(user.id);
      
      if (this.profile) {
        this.calculateBMIAndSuggestion();
        this.editForm.patchValue(this.profile);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
      this.errorMessage = 'Không thể tải hồ sơ sức khỏe';
    } finally {
      this.isLoading = false;
    }
  }

  async calculateBMIAndSuggestion(): Promise<void> {
    if (!this.profile) return;

    this.bmiResult = this.healthProfileService.calculateBMI(
      this.profile.chieuCao,
      this.profile.canNang
    );

    this.isLoading = true;
    try {
      this.exerciseSuggestion = await this.healthProfileService.generateExerciseSuggestion(
        this.profile,
        this.bmiResult
      );
    } catch (error) {
      console.error('Error generating exercise suggestion:', error);
      // Fallback sẽ được xử lý trong service
    } finally {
      this.isLoading = false;
    }
  }

  startEdit(): void {
    this.isEditing = true;
    if (this.profile) {
      this.editForm.patchValue(this.profile);
    }
  }

  cancelEdit(): void {
    this.isEditing = false;
    this.errorMessage = '';
    this.successMessage = '';
    if (this.profile) {
      this.editForm.patchValue(this.profile);
    }
  }

  async saveProfile(): Promise<void> {
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }

    const user = this.authService.getCurrentUser();
    if (!user) {
      this.errorMessage = 'Vui lòng đăng nhập';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    try {
      const profileData: HealthProfile = {
        tuoi: Number(this.editForm.value.tuoi),
        chieuCao: Number(this.editForm.value.chieuCao),
        canNang: Number(this.editForm.value.canNang),
        mucVanDong: this.editForm.value.mucVanDong,
        gioiTinh: this.editForm.value.gioiTinh
      };

      await this.firebaseService.saveHealthProfile(user.id, profileData);
      this.profile = profileData;
      this.calculateBMIAndSuggestion();
      this.isEditing = false;
      this.successMessage = 'Đã cập nhật hồ sơ thành công!';
      
      setTimeout(() => {
        this.successMessage = '';
      }, 3000);
    } catch (error) {
      console.error('Error saving profile:', error);
      this.errorMessage = 'Có lỗi xảy ra khi lưu hồ sơ. Vui lòng thử lại.';
    } finally {
      this.isLoading = false;
    }
  }

  getMucVanDongLabel(value: string): string {
    return this.healthProfileService.getMucVanDongLabel(value as 'it' | 'vua' | 'nhieu');
  }

  getGioiTinhLabel(value: string): string {
    const labels: { [key: string]: string } = {
      'nam': 'Nam',
      'nu': 'Nữ',
      'khac': 'Khác'
    };
    return labels[value] || value;
  }

  getBMIColor(category: string): string {
    const colors: { [key: string]: string } = {
      'hơi gầy': '#FFA726',
      'cân đối': '#4CAF50',
      'hơi thừa cân': '#FF9800',
      'thừa cân nhiều': '#F44336'
    };
    return colors[category] || '#666';
  }
}

