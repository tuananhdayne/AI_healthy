import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';

import { ChatUIComponent } from './chat-ui.component';
import { ChatService } from '../services/chat.service';
import { AuthService } from '../services/auth.service';

class ChatServiceStub {
  sendMessage() {
    return of({
      sessionId: 'test',
      reply: 'Xin chào!',
      intent: 'chao_hoi',
      intentConfidence: 0.99,
      symptoms: {},
      risk: 'low',
      clarificationNeeded: false,
      clarificationQuestion: null,
      sources: [],
      stage: 'greeting'
    });
  }

  resetConversation() {
    return of();
  }
}

class AuthServiceStub {
  logout() {
    return of();
  }
}

describe('ChatUIComponent', () => {
  let component: ChatUIComponent;
  let fixture: ComponentFixture<ChatUIComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatUIComponent, RouterTestingModule],
      providers: [
        { provide: ChatService, useClass: ChatServiceStub },
        { provide: AuthService, useClass: AuthServiceStub }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ChatUIComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
