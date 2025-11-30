import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from '../services/auth.service';
import { FirebaseService, UserCredentials } from '../services/firebase.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent implements OnInit {
  activeTab: 'ai' | 'users' | 'analytics' | 'settings' = 'ai';
  aiForm: FormGroup;
  currentAdminUser: any;

  // real users from Firestore (userCredentials)
  aiModels: any[] = [
    { id: 1, name: 'GPT-4', status: 'active', apiKey: 'sk-...', maxTokens: 8000 },
    { id: 2, name: 'GPT-3.5-Turbo', status: 'active', apiKey: 'sk-...', maxTokens: 4000 }
  ];

  users: UserCredentials[] = [];

  analytics: any = {
    totalUsers: 150,
    activeChats: 45,
    totalRequests: 1024,
    avgResponseTime: '1.2s'
  };

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
    , private firebaseService: FirebaseService
  ) {
    this.aiForm = this.fb.group({
      modelName: ['', [Validators.required]],
      apiKey: ['', [Validators.required]],
      maxTokens: ['', [Validators.required, Validators.min(100)]],
      status: ['active']
    });
  }

  ngOnInit(): void {
    this.currentAdminUser = this.authService.getCurrentUser();
    // Load real users from Firestore (userCredentials collection)
    this.loadUsers();
  }

  async loadUsers(): Promise<void> {
    try {
      const result = await this.firebaseService.getAllUserCredentials();
      // Map to UserCredentials and ensure basic fields exist for UI
      this.users = result.map(u => ({ ...u } as UserCredentials));
      console.debug('[Admin] loaded users:', this.users);
      // update analytics
      this.analytics.totalUsers = this.users.length;
    } catch (err) {
      console.error('[Admin] loadUsers error', err);
    }
  }

  setActiveTab(tab: 'ai' | 'users' | 'analytics' | 'settings'): void {
    this.activeTab = tab;
  }

  // AI Management
  addAIModel(): void {
    if (this.aiForm.valid) {
      const newModel = {
        id: this.aiModels.length + 1,
        ...this.aiForm.value
      };
      this.aiModels.push(newModel);
      this.aiForm.reset({ status: 'active' });
      console.log('[Admin] AI Model added:', newModel);
    }
  }

  deleteAIModel(id: number): void {
    this.aiModels = this.aiModels.filter(m => m.id !== id);
    console.log('[Admin] AI Model deleted:', id);
  }

  editAIModel(model: any): void {
    this.aiForm.patchValue({
      modelName: model.name,
      apiKey: model.apiKey,
      maxTokens: model.maxTokens,
      status: model.status
    });
    this.deleteAIModel(model.id);
  }

  // User Management
  // Toggle status locally (UI only) — if you have a backend flag, update accordingly
  toggleUserStatus(userId: string): void {
    const user = this.users.find(u => (u.id === userId) || (u.uid === userId));
    if (user) {
      // Use a local status field if not present
      (user as any).status = (user as any).status === 'inactive' ? 'active' : 'inactive';
      console.log('[Admin] User status toggled:', user);
    }
  }

  async removeUser(userId: string): Promise<void> {
    try {
      await this.firebaseService.deleteUserCredentialsById(userId);
      this.users = this.users.filter(u => (u.id !== userId) && (u.uid !== userId));
      console.log('[Admin] User removed from userCredentials:', userId);
    } catch (err) {
      console.error('[Admin] removeUser error', err);
    }
  }

  async promoteToAdmin(userId: string): Promise<void> {
    try {
      await this.firebaseService.updateUserCredentialsRoleById(userId, 'admin');
      const user = this.users.find(u => (u.id === userId) || (u.uid === userId));
      if (user) user.role = 'admin';
      console.log('[Admin] User promoted to admin (userCredentials):', userId);
    } catch (err) {
      console.error('[Admin] promoteToAdmin error', err);
    }
  }

  async demoteFromAdmin(userId: string): Promise<void> {
    try {
      await this.firebaseService.updateUserCredentialsRoleById(userId, 'user');
      const user = this.users.find(u => (u.id === userId) || (u.uid === userId));
      if (user) user.role = 'user';
      console.log('[Admin] User demoted from admin (userCredentials):', userId);
    } catch (err) {
      console.error('[Admin] demoteFromAdmin error', err);
    }
  }

  // Settings
  saveAdminSettings(): void {
    console.log('[Admin] Settings saved');
    alert('Cài đặt đã được lưu!');
  }

  // Logout
  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        console.log('[Admin] Admin logged out');
        try { this.router.navigate(['/']); } catch(e) {}
      },
      error: (err: any) => {
        console.error('[Admin] Logout failed', err);
      }
    });
  }
}
