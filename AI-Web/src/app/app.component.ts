import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd, Event } from '@angular/router';
import { filter } from 'rxjs/operators';
import { NotificationService } from './services/notification.service';
import { AuthService } from './services/auth.service';
import { FirebaseService } from './services/firebase.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'gia-dien-web';
  showFooter = true;
  showHealthProfileSetup = false;

  constructor(
    private router: Router,
    private notificationService: NotificationService,
    private authService: AuthService,
    private firebaseService: FirebaseService
  ) {
    this.router.events
      .pipe(filter((event: Event) => event instanceof NavigationEnd))
      .subscribe((event: Event) => {
        if (event instanceof NavigationEnd) {
          const currentUrl = event.urlAfterRedirects || (event as NavigationEnd).url;
          // Ẩn footer khi ở trang chat để tối ưu không gian trò chuyện
          this.showFooter = !currentUrl.startsWith('/chat');
        }
      });
  }

  async ngOnInit(): Promise<void> {
    // Khởi động notification service nếu user đã đăng nhập
    this.authService.currentUser$.subscribe(async user => {
      if (user) {
        this.notificationService.start();
        // Kiểm tra xem user đã có health profile chưa
        await this.checkHealthProfile(user.id);
      } else {
        this.notificationService.stop();
        this.showHealthProfileSetup = false;
      }
    });
  }

  async checkHealthProfile(userId: string): Promise<void> {
    try {
      const hasProfile = await this.firebaseService.hasHealthProfile(userId);
      // Chỉ hiện popup nếu user chưa có profile và không đang ở trang health-profile
      const currentUrl = this.router.url;
      if (!hasProfile && !currentUrl.includes('/health-profile')) {
        // Đợi 1 giây để đảm bảo UI đã render
        setTimeout(() => {
          this.showHealthProfileSetup = true;
        }, 1000);
      }
    } catch (error) {
      console.error('Error checking health profile:', error);
    }
  }

  onProfileSaved(): void {
    this.showHealthProfileSetup = false;
  }

  ngOnDestroy(): void {
    this.notificationService.stop();
  }
}

