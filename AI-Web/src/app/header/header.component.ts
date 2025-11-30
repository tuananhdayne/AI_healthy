import { Component, OnInit, OnDestroy } from '@angular/core';
import { AuthService, User } from '../services/auth.service';
import { Router, NavigationEnd } from '@angular/router';
import { filter, Subscription } from 'rxjs';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit, OnDestroy {
  isMenuOpen = false;
  currentUser: User | null = null;
  private routerSubscription?: Subscription;

  constructor(private authService: AuthService, private router: Router) {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });
  }

  ngOnInit(): void {
    // Tự đóng menu khi navigate
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.isMenuOpen = false;
      });
  }

  ngOnDestroy(): void {
    if (this.routerSubscription) {
      this.routerSubscription.unsubscribe();
    }
  }

  toggleMenu(): void {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu(): void {
    this.isMenuOpen = false;
  }

  goToAdmin(): void {
    this.router.navigate(['/admin']);
    this.closeMenu();
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        // navigate to home after logout
        this.router.navigate(['/']);
      },
      error: (err) => {
        console.error('Logout error', err);
        // still navigate home
        this.router.navigate(['/']);
      }
    });
  }
}

