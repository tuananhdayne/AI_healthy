import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FirebaseService } from './firebase.service';
import { AuthService } from './auth.service';
import { SettingsService } from './settings.service';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private checkInterval?: number;
  private lastCheckTime = new Date();

  constructor(
    private firebaseService: FirebaseService,
    private authService: AuthService,
    private settingsService: SettingsService,
    private http: HttpClient
  ) {}

  /**
   * Khởi động service kiểm tra và gửi thông báo
   */
  start(): void {
    // Kiểm tra quyền thông báo
    if (!('Notification' in window)) {
      console.warn('Browser does not support notifications');
      return;
    }

    // Request permission nếu chưa có
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Kiểm tra mỗi phút
    this.checkInterval = window.setInterval(() => {
      this.checkAndSendNotifications();
    }, 60000); // 1 phút

    // Kiểm tra ngay lập tức
    this.checkAndSendNotifications();
  }

  /**
   * Dừng service
   */
  stop(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = undefined;
    }
  }

  /**
   * Kiểm tra và gửi thông báo
   */
  private async checkAndSendNotifications(): Promise<void> {
    const user = this.authService.getCurrentUser();
    if (!user) {
      console.log('⏭️ No user, skipping notifications');
      return;
    }

    // Kiểm tra cài đặt
    const settings = this.settingsService.getSettings();
    const pushNotifications = localStorage.getItem('pushNotifications');
    const isPushEnabled = pushNotifications ? JSON.parse(pushNotifications) : false;
    
    if (!settings.notifications && !isPushEnabled) {
      console.log('⏭️ Notifications disabled in settings');
      // Vẫn kiểm tra medicine reminders ngay cả khi notifications bị tắt
      // (có thể gửi qua email hoặc hiển thị trong app)
    }

    // Kiểm tra quyền (chỉ cần cho browser notifications)
    const hasNotificationPermission = Notification.permission === 'granted';
    if (!hasNotificationPermission) {
      console.log('⚠️ Notification permission not granted:', Notification.permission);
      // Vẫn tiếp tục kiểm tra reminders (có thể gửi qua email)
    }

    try {
      const now = new Date();
      console.log('🔄 Checking notifications at:', now.toLocaleTimeString());
      
      // 1. Kiểm tra medicine reminders (luôn kiểm tra, không phụ thuộc vào notification permission)
      await this.checkMedicineReminders(user.id, now);
      
      // 2. Kiểm tra exercise reminders (tập thể dục) - chỉ nếu có permission
      if (hasNotificationPermission) {
        await this.checkExerciseReminders(user.id, now);
        
        // 3. Kiểm tra water reminders (uống nước) - chỉ nếu có permission
        await this.checkWaterReminders(user.id, now);
      }
      
      this.lastCheckTime = now;
    } catch (error) {
      console.error('❌ Error checking notifications:', error);
    }
  }

  /**
   * Kiểm tra và gửi thông báo nhắc uống thuốc
   */
  private async checkMedicineReminders(userId: string, now: Date): Promise<void> {
    try {
      console.log(`🔍 Checking medicine reminders for user: ${userId} at ${now.toLocaleTimeString()}`);
      const reminders = await this.firebaseService.getMedicineReminders(userId);
      console.log(`📋 Found ${reminders.length} active reminders`);
      
      if (reminders.length === 0) {
        console.log('ℹ️ No active reminders found');
        return;
      }
      
      for (const reminder of reminders) {
        if (!reminder.is_active) {
          console.log(`⏭️ Skipping inactive reminder: ${reminder.medicine_name}`);
          continue;
        }
        
        const reminderTime = this.parseTime(reminder.time);
        const currentTime = now.getHours() * 60 + now.getMinutes();
        const reminderMinutes = reminderTime.hour * 60 + reminderTime.minute;
        
        console.log(`⏰ Checking reminder: ${reminder.medicine_name} at ${reminder.time} (${reminderMinutes} minutes)`);
        console.log(`   Current time: ${now.getHours()}:${now.getMinutes()} (${currentTime} minutes)`);
        
        // Kiểm tra xem đã đến giờ chưa (trong vòng 5 phút)
        const diff = Math.abs(currentTime - reminderMinutes);
        console.log(`   Time difference: ${diff} minutes`);
        
        if (diff <= 5 && diff >= 0) {
          // Kiểm tra xem đã gửi thông báo chưa (trong 5 phút vừa rồi)
          const lastSent = reminder.last_sent ? new Date(reminder.last_sent) : null;
          const timeSinceLastSent = lastSent ? (now.getTime() - lastSent.getTime()) / (1000 * 60) : Infinity;
          console.log(`   Last sent: ${lastSent ? lastSent.toLocaleString() : 'never'} (${timeSinceLastSent.toFixed(1)} minutes ago)`);
          
          if (!lastSent || timeSinceLastSent > 5) {
            console.log(`✅ Sending notification for: ${reminder.medicine_name}`);
            
            // Gửi browser notification
            this.sendNotification(
              '🔔 Nhắc nhở uống thuốc',
              `Đã đến giờ uống thuốc: ${reminder.medicine_name} (${reminder.time})`
            );
            
            // Gửi email notification (nếu có email và function đã deploy)
            // Tạm thời tắt để tránh lỗi CORS khi function chưa deploy
            // TODO: Bật lại sau khi deploy Firebase Function
            /*
            const user = this.authService.getCurrentUser();
            if (user && user.email) {
              this.sendEmailReminder(user.email, reminder).catch((err: any) => {
                console.error('❌ Error sending email reminder:', err);
              });
            }
            */
            
            // Cập nhật last_sent và next_reminder_time cho lần tiếp theo
            if (reminder.id) {
              // Tính toán next reminder time dựa trên repeat_type
              let nextReminderTime: Date | null = null;
              
              if (reminder.repeat_type === 'daily') {
                nextReminderTime = new Date(now);
                const [hours, minutes] = reminder.time.split(':').map(Number);
                nextReminderTime.setHours(hours, minutes, 0, 0);
                nextReminderTime.setSeconds(0, 0);
                // Nếu đã qua giờ hôm nay, set cho ngày mai
                if (nextReminderTime.getTime() <= now.getTime()) {
                  nextReminderTime.setDate(nextReminderTime.getDate() + 1);
                }
                console.log(`📅 Daily reminder next time: ${nextReminderTime.toLocaleString()}`);
              } else if (reminder.repeat_type === 'weekly' && reminder.weekday !== undefined) {
                nextReminderTime = new Date(now);
                const [hours, minutes] = reminder.time.split(':').map(Number);
                nextReminderTime.setHours(hours, minutes, 0, 0);
                // Tính ngày tiếp theo trong tuần
                const currentDay = nextReminderTime.getDay();
                const targetDay = reminder.weekday;
                let daysUntilNext = (targetDay - currentDay + 7) % 7;
                if (daysUntilNext === 0 && nextReminderTime <= now) {
                  daysUntilNext = 7; // Nếu đã qua giờ hôm nay, set cho tuần sau
                }
                nextReminderTime.setDate(nextReminderTime.getDate() + daysUntilNext);
              } else if (reminder.repeat_type === 'once') {
                // Một lần thì deactivate sau khi gửi
                await this.firebaseService.updateMedicineReminder(reminder.id, {
                  last_sent: now.toISOString(),
                  is_active: false
                });
                console.log(`💾 Deactivated one-time reminder: ${reminder.id}`);
                continue; // Skip update next_reminder_time
              }
              
              if (nextReminderTime) {
                await this.firebaseService.updateMedicineReminder(reminder.id, {
                  last_sent: now.toISOString(),
                  next_reminder_time: nextReminderTime.toISOString()
                });
              } else {
                await this.firebaseService.updateMedicineReminder(reminder.id, {
                  last_sent: now.toISOString()
                });
              }
              console.log(`💾 Updated last_sent and next_reminder_time for reminder: ${reminder.id}`);
              console.log(`   Next reminder: ${nextReminderTime ? nextReminderTime.toLocaleString() : 'N/A'}`);
            }
          } else {
            console.log(`⏭️ Skipping: notification sent ${timeSinceLastSent.toFixed(1)} minutes ago`);
          }
        } else {
          console.log(`⏭️ Not time yet: ${diff} minutes away`);
        }
      }
    } catch (error) {
      console.error('❌ Error checking medicine reminders:', error);
    }
  }

  /**
   * Kiểm tra và gửi thông báo nhắc tập thể dục
   */
  private async checkExerciseReminders(userId: string, now: Date): Promise<void> {
    // Lấy cài đặt exercise reminders từ Firebase (sẽ tạo sau)
    // Tạm thời: nhắc mỗi 2 giờ từ 6h sáng đến 10h tối
    const hour = now.getHours();
    const minute = now.getMinutes();
    
    if (hour >= 6 && hour < 22) {
      // Kiểm tra xem đã nhắc trong 2 giờ vừa rồi chưa
      const lastExerciseReminder = localStorage.getItem(`exercise_reminder_${userId}`);
      if (!lastExerciseReminder) {
        // Lần đầu tiên trong ngày
        this.sendNotification(
          '💪 Nhắc nhở tập thể dục',
          'Đã đến giờ tập thể dục! Hãy dành ít nhất 15-30 phút để vận động nhé.'
        );
        localStorage.setItem(`exercise_reminder_${userId}`, now.toISOString());
      } else {
        const lastTime = new Date(lastExerciseReminder);
        const hoursSince = (now.getTime() - lastTime.getTime()) / (1000 * 60 * 60);
        if (hoursSince >= 2) {
          this.sendNotification(
            '💪 Nhắc nhở tập thể dục',
            'Đã đến giờ tập thể dục! Hãy dành ít nhất 15-30 phút để vận động nhé.'
          );
          localStorage.setItem(`exercise_reminder_${userId}`, now.toISOString());
        }
      }
    }
  }

  /**
   * Kiểm tra và gửi thông báo nhắc uống nước
   */
  private async checkWaterReminders(userId: string, now: Date): Promise<void> {
    const hour = now.getHours();
    const minute = now.getMinutes();
    
    // Nhắc mỗi giờ từ 7h sáng đến 10h tối
    if (hour >= 7 && hour < 22 && minute === 0) {
      const lastWaterReminder = localStorage.getItem(`water_reminder_${userId}_${hour}`);
      if (!lastWaterReminder) {
        this.sendNotification(
          '💧 Nhắc nhở uống nước',
          'Đã đến giờ uống nước! Hãy uống một ly nước để giữ cơ thể khỏe mạnh nhé.'
        );
        localStorage.setItem(`water_reminder_${userId}_${hour}`, now.toISOString());
      }
    }
  }

  /**
   * Gửi thông báo
   */
  private sendNotification(title: string, body: string): void {
    // Luôn log để debug
    console.log(`📢 Sending notification: ${title} - ${body}`);
    
    if (Notification.permission === 'granted') {
      const pushNotifications = localStorage.getItem('pushNotifications');
      const isPushEnabled = pushNotifications ? JSON.parse(pushNotifications) : false;
      
      if (isPushEnabled) {
        try {
          const notification = new Notification(title, {
            body,
            icon: '/favicon.ico', // Fallback nếu không có icon
            badge: '/favicon.ico',
            tag: 'health-reminder',
            requireInteraction: false
          });
          
          console.log('✅ Browser notification sent');
          
          // Auto close sau 5 giây
          setTimeout(() => {
            notification.close();
          }, 5000);
        } catch (error) {
          console.error('❌ Error creating notification:', error);
        }
      } else {
        console.log('ℹ️ Push notifications disabled in settings, but reminder is logged');
      }
    } else {
      console.log('ℹ️ Notification permission not granted, but reminder is logged');
      // Có thể thêm logic gửi email hoặc hiển thị trong app ở đây
    }
  }

  /**
   * Gửi email nhắc nhở uống thuốc
   */
  private async sendEmailReminder(email: string, reminder: any): Promise<void> {
    try {
      // Kiểm tra cài đặt email notifications
      const settings = this.settingsService.getSettings();
      if (!settings.notifications) {
        console.log('ℹ️ Email notifications disabled in settings');
        return;
      }

      // Gọi Firebase Cloud Function để gửi email
      // URL có thể là: https://us-central1-giadienweb.cloudfunctions.net/sendMedicineReminder
      const functionUrl = 'https://us-central1-giadienweb.cloudfunctions.net/sendMedicineReminder';
      
      const emailData = {
        email: email,
        medicine_name: reminder.medicine_name,
        time: reminder.time,
        message: `Đã đến giờ uống thuốc: ${reminder.medicine_name} (${reminder.time}). ${reminder.notes || ''}`
      };

      console.log(`📧 Sending email reminder to ${email} for ${reminder.medicine_name}`);
      
      // Gọi Firebase Function
      const response = await this.http.post(functionUrl, emailData).toPromise();
      console.log('✅ Email reminder sent successfully:', response);
    } catch (error: any) {
      // Nếu function chưa deploy hoặc lỗi, chỉ log, không throw
      console.warn('⚠️ Could not send email reminder (function may not be deployed):', error.message);
      // Không throw error để không ảnh hưởng đến browser notification
    }
  }

  /**
   * Parse time string (HH:MM) thành object
   */
  private parseTime(timeStr: string): { hour: number; minute: number } {
    const parts = timeStr.split(':');
    return {
      hour: parseInt(parts[0], 10),
      minute: parseInt(parts[1] || '0', 10)
    };
  }
}

