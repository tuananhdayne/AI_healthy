import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../services/auth.service';
import { MedicineReminderService, MedicineReminder } from '../services/medicine-reminder.service';

@Component({
  selector: 'app-medicine-reminder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './medicine-reminder.component.html',
  styleUrls: ['./medicine-reminder.component.scss']
})
export class MedicineReminderComponent implements OnInit {
  reminders: MedicineReminder[] = [];
  showAddForm = false;
  isEditing = false;
  editingReminder: MedicineReminder | null = null;

  // Form fields
  medicineName = '';
  time = '08:00';
  repeatType: 'daily' | 'weekly' | 'once' = 'daily';
  weekday: number | null = null;
  notes = '';
  startDate = '';
  endDate = '';

  errorMessage = '';
  successMessage = '';

  weekdays = [
    { value: 0, label: 'Thứ 2' },
    { value: 1, label: 'Thứ 3' },
    { value: 2, label: 'Thứ 4' },
    { value: 3, label: 'Thứ 5' },
    { value: 4, label: 'Thứ 6' },
    { value: 5, label: 'Thứ 7' },
    { value: 6, label: 'Chủ nhật' }
  ];

  constructor(
    private authService: AuthService,
    private reminderService: MedicineReminderService
  ) {}

  ngOnInit(): void {
    this.loadReminders();
  }

  loadReminders(): void {
    const user = this.authService.getCurrentUser();
    if (!user) {
      this.errorMessage = 'Vui lòng đăng nhập';
      return;
    }

    this.reminderService.getReminders(user.id).subscribe({
      next: (reminders) => {
        console.log(`📋 Loaded ${reminders.length} reminders from Firestore`);
        this.reminders = reminders;
        this.errorMessage = '';
      },
      error: (error) => {
        console.error('❌ Lỗi khi tải reminders:', error);
        this.errorMessage = 'Không thể tải danh sách nhắc nhở';
      }
    });
  }

  showAddReminderForm(): void {
    this.showAddForm = true;
    this.isEditing = false;
    this.resetForm();
  }

  editReminder(reminder: MedicineReminder): void {
    this.editingReminder = reminder;
    this.isEditing = true;
    this.showAddForm = true;
    this.medicineName = reminder.medicine_name;
    this.time = reminder.time;
    this.repeatType = reminder.repeat_type;
    this.weekday = reminder.weekday || null;
    this.notes = reminder.notes || '';
    this.startDate = reminder.start_date || '';
    this.endDate = reminder.end_date || '';
  }

  cancelForm(): void {
    this.showAddForm = false;
    this.isEditing = false;
    this.editingReminder = null;
    this.resetForm();
  }

  resetForm(): void {
    this.medicineName = '';
    this.time = '08:00';
    this.repeatType = 'daily';
    this.weekday = null;
    this.notes = '';
    this.startDate = '';
    this.endDate = '';
    this.errorMessage = '';
    this.successMessage = '';
  }

  saveReminder(): void {
    if (!this.medicineName.trim()) {
      this.errorMessage = 'Vui lòng nhập tên thuốc';
      return;
    }

    const user = this.authService.getCurrentUser();
    if (!user) {
      this.errorMessage = 'Vui lòng đăng nhập';
      return;
    }

    const reminderData: Omit<MedicineReminder, 'id' | 'created_at'> = {
      user_id: user.id,
      user_email: user.email,
      medicine_name: this.medicineName.trim(),
      time: this.time,
      repeat_type: this.repeatType,
      weekday: this.repeatType === 'weekly' ? (this.weekday ?? undefined) : undefined,
      start_date: this.startDate || undefined,
      end_date: this.endDate || undefined,
      notes: this.notes.trim() || undefined,
      is_active: true
    };

    if (this.isEditing && this.editingReminder?.id) {
      // Update existing - tạm thời xóa và tạo mới (vì chưa có API update)
      this.reminderService.deleteReminder(this.editingReminder.id).subscribe({
        next: () => {
          this.createReminder(reminderData);
        },
        error: (error) => {
          console.error('Lỗi khi xóa reminder cũ:', error);
          this.createReminder(reminderData);
        }
      });
    } else {
      this.createReminder(reminderData);
    }
  }

  private createReminder(reminderData: Omit<MedicineReminder, 'id' | 'created_at'>): void {
    this.reminderService.createReminder(reminderData).subscribe({
      next: () => {
        this.successMessage = 'Đã tạo lịch nhắc nhở thành công!';
        this.errorMessage = '';
        this.loadReminders();
        setTimeout(() => {
          this.cancelForm();
        }, 1500);
      },
      error: (error) => {
        console.error('Lỗi khi tạo reminder:', error);
        this.errorMessage = 'Không thể tạo lịch nhắc nhở. Vui lòng thử lại.';
        this.successMessage = '';
      }
    });
  }

  deleteReminder(reminder: MedicineReminder): void {
    if (!reminder.id) return;

    if (confirm(`Bạn có chắc muốn xóa lịch nhắc nhở "${reminder.medicine_name}"?`)) {
      this.reminderService.deleteReminder(reminder.id).subscribe({
        next: () => {
          this.successMessage = 'Đã xóa lịch nhắc nhở';
          this.loadReminders();
          setTimeout(() => {
            this.successMessage = '';
          }, 2000);
        },
        error: (error) => {
          console.error('Lỗi khi xóa reminder:', error);
          this.errorMessage = 'Không thể xóa lịch nhắc nhở';
        }
      });
    }
  }

  getRepeatTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      daily: 'Hàng ngày',
      weekly: 'Hàng tuần',
      once: 'Một lần'
    };
    return labels[type] || type;
  }

  formatTime(time: string): string {
    return time;
  }
}

