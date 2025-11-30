import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, from } from 'rxjs';
import { environment } from '../../environments/environment';
import { FirebaseService } from './firebase.service';

export interface MedicineReminder {
  id?: string;
  user_id: string;
  user_email: string;
  medicine_name: string;
  time: string; // Format: "HH:MM"
  repeat_type: 'daily' | 'weekly' | 'once';
  weekday?: number; // 0-6 cho weekly (0=Monday)
  start_date?: string;
  end_date?: string;
  notes?: string;
  created_at?: string;
  is_active?: boolean;
  next_reminder_time?: string;
  last_sent?: string;
}

@Injectable({
  providedIn: 'root'
})
export class MedicineReminderService {
  private readonly apiBaseUrl = this.normalizeBaseUrl(environment.apiBaseUrl);
  private useFirebaseDirectly = true; // Ưu tiên dùng Firestore trực tiếp

  constructor(
    private http: HttpClient,
    private firebaseService: FirebaseService
  ) {}

  createReminder(reminder: Omit<MedicineReminder, 'id' | 'created_at'>): Observable<MedicineReminder> {
    // Ưu tiên lưu trực tiếp vào Firestore (giống chat messages)
    if (this.useFirebaseDirectly) {
      return from(
        this.firebaseService.saveMedicineReminder({
          user_id: reminder.user_id,
          user_email: reminder.user_email,
          medicine_name: reminder.medicine_name,
          time: reminder.time,
          repeat_type: reminder.repeat_type,
          weekday: reminder.weekday,
          start_date: reminder.start_date,
          end_date: reminder.end_date,
          notes: reminder.notes,
          is_active: reminder.is_active !== undefined ? reminder.is_active : true
        }).then(id => ({
          ...reminder,
          id,
          created_at: new Date().toISOString()
        } as MedicineReminder))
      );
    }
    
    // Fallback: gọi API backend
    return this.http.post<MedicineReminder>(
      `${this.apiBaseUrl}/api/medicine-reminders`,
      reminder
    );
  }

  getReminders(userId: string): Observable<MedicineReminder[]> {
    // Ưu tiên lấy trực tiếp từ Firestore
    if (this.useFirebaseDirectly) {
      return from(
        this.firebaseService.getMedicineReminders(userId).then(reminders => 
          reminders.map(r => ({
            id: r.id,
            user_id: r.user_id,
            user_email: r.user_email,
            medicine_name: r.medicine_name,
            time: r.time,
            repeat_type: r.repeat_type,
            weekday: r.weekday,
            start_date: r.start_date,
            end_date: r.end_date,
            notes: r.notes,
            created_at: r.created_at instanceof Date ? r.created_at.toISOString() : (typeof r.created_at === 'string' ? r.created_at : new Date().toISOString()),
            is_active: r.is_active,
            next_reminder_time: r.next_reminder_time,
            last_sent: r.last_sent
          } as MedicineReminder))
        )
      );
    }
    
    // Fallback: gọi API backend
    return this.http.get<MedicineReminder[]>(
      `${this.apiBaseUrl}/api/medicine-reminders/${userId}`
    );
  }

  deleteReminder(reminderId: string): Observable<{ status: string; id: string }> {
    // Ưu tiên xóa trực tiếp từ Firestore
    if (this.useFirebaseDirectly) {
      return from(
        this.firebaseService.deleteMedicineReminder(reminderId).then(() => ({
          status: 'deleted',
          id: reminderId
        }))
      );
    }
    
    // Fallback: gọi API backend
    return this.http.delete<{ status: string; id: string }>(
      `${this.apiBaseUrl}/api/medicine-reminders/${reminderId}`
    );
  }

  private normalizeBaseUrl(url?: string): string {
    if (!url) {
      return window.location.origin;
    }

    if (url.startsWith('/')) {
      return `${window.location.origin}${url}`.replace(/\/$/, '');
    }

    return url.replace(/\/$/, '');
  }
}

