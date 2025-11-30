import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent  } from './login/login.component';
import { RegisterComponent } from './register/register.component';
import { HeaderComponent } from './header/header.component';
import { FooterComponent } from './footer/footer.component';
import { ChatUIComponent } from './chat-ui/chat-ui.component';
import { SettingsComponent } from './settings/settings.component';
import { MissPassComponent } from './miss-pass/miss-pass.component';
import { LandingComponent } from './landing/landing.component';
import { AuthService } from './services/auth.service';
import { FirebaseService } from './services/firebase.service';
import { AdminGuard } from './guards/admin.guard';
import { ChangePass2Component } from './change-pass2/change-pass2.component';
import { HealthProfileSetupComponent } from './health-profile/health-profile-setup.component';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    RegisterComponent,
    HeaderComponent,
    FooterComponent,
    MissPassComponent,
    LandingComponent,
    ChangePass2Component
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    ReactiveFormsModule,
    FormsModule,
    HttpClientModule,
    HealthProfileSetupComponent
  ],
  providers: [AuthService, FirebaseService, AdminGuard],
  bootstrap: [AppComponent]
})
export class AppModule { }
