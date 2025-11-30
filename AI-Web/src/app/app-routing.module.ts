import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { RegisterComponent } from './register/register.component';
import { ChatUIComponent } from './chat-ui/chat-ui.component';
import { SettingsComponent } from './settings/settings.component';
import { MissPassComponent } from './miss-pass/miss-pass.component';
import { LandingComponent } from './landing/landing.component';
import { AdminComponent } from './admin/admin.component';
import { ChangePassComponent } from './change-pass/change-pass.component';
import { ChangePass2Component } from './change-pass2/change-pass2.component';
import { AdminGuard } from './guards/admin.guard';
import { MedicineReminderComponent } from './medicine-reminder/medicine-reminder.component';
import { HealthProfileComponent } from './health-profile/health-profile.component';

const routes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'chat', component: ChatUIComponent },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'settings', component: SettingsComponent },
  { path: 'medicine-reminder', component: MedicineReminderComponent },
  { path: 'health-profile', component: HealthProfileComponent },
  { path: 'change-password', component: ChangePassComponent },
  { path: 'admin', component: AdminComponent, canActivate: [AdminGuard] },
  { path: 'forgot-password', component: MissPassComponent },
  { path: 'change-password-2', component: ChangePass2Component }
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {
      anchorScrolling: 'enabled',
      scrollPositionRestoration: 'enabled'
    })
  ],
  exports: [RouterModule]
})
export class AppRoutingModule { }
