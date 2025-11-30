import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { Subscription } from 'rxjs';
import { ChatResponse, ChatService } from '../services/chat.service';
import { FirebaseService, ChatSession } from '../services/firebase.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  pending?: boolean;
}

interface ChatHistory {
  id: string;
  sessionId: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: ChatMessage[];
  meta?: ChatResponse;
}

@Component({
  selector: 'app-chat-ui',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-ui.component.html',
  styleUrls: ['./chat-ui.component.scss']
})
export class ChatUIComponent implements OnInit, OnDestroy {
  constructor(
    private authService: AuthService,
    private router: Router,
    private chatService: ChatService,
    private firebaseService: FirebaseService
  ) {}
  @ViewChild('container') containerRef!: ElementRef;

  chatHistories: ChatHistory[] = [];
  currentChatId = '';
  messages: ChatMessage[] = [];
  input = '';
  isAccountMenuOpen = false;
  isSending = false;
  errorMessage = '';
  lastBotMeta?: ChatResponse;
  isCheckingReady = false;
  modelsReady = false;

  private historyCounter = 1;
  private activeRequest?: Subscription;

  ngOnInit(): void {
    this.checkModelsReady();
    this.loadChatSessions();
  }

  checkModelsReady() {
    this.isCheckingReady = true;
    this.chatService.checkReady().subscribe({
      next: (response) => {
        this.modelsReady = response.ready;
        this.isCheckingReady = false;
        if (!response.ready) {
          this.errorMessage = 'Models đang tải, vui lòng đợi...';
        } else {
          this.errorMessage = '';
        }
      },
      error: (error) => {
        console.error('Không kiểm tra được trạng thái models:', error);
        this.isCheckingReady = false;
        this.errorMessage = 'Không kết nối được với server. Vui lòng kiểm tra backend đã chạy chưa.';
      }
    });
  }

  ngOnDestroy(): void {
    this.activeRequest?.unsubscribe();
  }

  // Scroll mượt như ChatGPT
  private scrollToBottom() {
    setTimeout(() => {
      const el = this.containerRef.nativeElement;
      el.scrollTop = el.scrollHeight;
    }, 30);
  }

  async send() {
    const text = this.input.trim();
    if (!text || !this.currentChatId || this.isSending) {
      return;
    }

    const currentHistory = this.chatHistories.find((chat) => chat.id === this.currentChatId);
    if (!currentHistory) {
      return;
    }

    const user = this.authService.getCurrentUser();
    if (!user) {
      this.errorMessage = 'Vui lòng đăng nhập';
      return;
    }

    // Tạo user message
    const userMessage = { role: 'user' as const, content: text };
    
    // Lưu vào Firebase TRƯỚC với error handling
    try {
      await this.saveMessageToFirebase(userMessage, currentHistory.sessionId, user);
      console.log('✅ User message saved to Firebase:', text.substring(0, 50));
    } catch (error) {
      console.error('❌ Error saving user message to Firebase:', error);
      // Vẫn tiếp tục hiển thị message trong UI dù lưu Firebase thất bại
    }
    
    // Push vào UI - chỉ push một lần, kiểm tra duplicate
    const lastMessage = this.messages[this.messages.length - 1];
    const isDuplicate = lastMessage && 
                        lastMessage.role === 'user' && 
                        lastMessage.content === text;
    
    if (!isDuplicate) {
      this.messages.push(userMessage);
      // Đồng bộ với currentHistory.messages
      if (currentHistory.messages.length < this.messages.length) {
        currentHistory.messages.push(userMessage);
      }
    }

    this.updateHistoryPreview(text, currentHistory);
    this.input = '';
    this.errorMessage = '';
    this.lastBotMeta = undefined;
    this.scrollToBottom();

    this.isSending = true;
    const placeholderIndex =
      this.messages.push({
        role: 'assistant',
        content: 'HealthyAI đang suy nghĩ...',
        pending: true
      }) - 1;

    this.activeRequest?.unsubscribe();
    this.activeRequest = this.chatService.sendMessage(text, currentHistory.sessionId).subscribe({
      next: async (response) => {
        const assistantMessage = {
          role: 'assistant' as const,
          content: response.reply
        };
        
        // Lưu assistant message vào Firebase với error handling
        try {
          await this.saveMessageToFirebase(assistantMessage, currentHistory.sessionId, user, response);
          console.log('✅ Assistant message saved to Firebase');
        } catch (error) {
          console.error('❌ Error saving assistant message to Firebase:', error);
          // Vẫn tiếp tục hiển thị message trong UI
        }
        
        // Update UI - đảm bảo không duplicate
        // Kiểm tra xem placeholder có còn tồn tại không
        if (placeholderIndex < this.messages.length && this.messages[placeholderIndex]?.pending) {
          // Thay thế placeholder bằng message thật
          this.messages[placeholderIndex] = assistantMessage;
          
          // Đồng bộ với currentHistory.messages
          if (placeholderIndex < currentHistory.messages.length && currentHistory.messages[placeholderIndex]?.pending) {
            currentHistory.messages[placeholderIndex] = assistantMessage;
          } else if (placeholderIndex < currentHistory.messages.length) {
            // Nếu không phải pending, update trực tiếp
            currentHistory.messages[placeholderIndex] = assistantMessage;
          } else {
            // Nếu index vượt quá, push mới
            currentHistory.messages.push(assistantMessage);
          }
        } else {
          // Nếu placeholder không còn, kiểm tra xem message đã tồn tại chưa
          const lastMessage = this.messages[this.messages.length - 1];
          const isDuplicate = lastMessage && 
                              lastMessage.role === 'assistant' && 
                              lastMessage.content === assistantMessage.content;
          
          if (!isDuplicate) {
            this.messages.push(assistantMessage);
            // Đồng bộ với currentHistory.messages
            const lastHistoryMessage = currentHistory.messages[currentHistory.messages.length - 1];
            const isHistoryDuplicate = lastHistoryMessage && 
                                       lastHistoryMessage.role === 'assistant' && 
                                       lastHistoryMessage.content === assistantMessage.content;
            if (!isHistoryDuplicate) {
              currentHistory.messages.push(assistantMessage);
            }
          }
        }
        
        currentHistory.meta = response;
        this.lastBotMeta = response;
        this.updateHistoryPreview(response.reply, currentHistory);
        
        // Cập nhật session trong Firebase
        try {
          await this.saveSessionToFirebase(currentHistory, user);
        } catch (error) {
          console.error('❌ Error saving session to Firebase:', error);
        }
        
        this.isSending = false;
        this.scrollToBottom();
      },
      error: async (error: any) => {
        console.error('Chat API error:', error);
        const errorMsg = error?.message || 'Xin lỗi, hệ thống đang bận. Bạn thử gửi lại sau nhé.';
        const errorMessage = {
          role: 'assistant' as const,
          content: errorMsg
        };
        
        // Update UI
        if (this.messages[placeholderIndex] && this.messages[placeholderIndex].pending) {
          this.messages[placeholderIndex] = errorMessage;
        } else {
          this.messages.push(errorMessage);
        }
        
        // Lưu error message vào Firebase với error handling
        try {
          await this.saveMessageToFirebase(errorMessage, currentHistory.sessionId, user);
        } catch (firebaseError) {
          console.error('❌ Error saving error message to Firebase:', firebaseError);
        }
        
        this.errorMessage = errorMsg;
        this.isSending = false;
        this.scrollToBottom();
        
        // Nếu là lỗi models chưa ready, tự động check lại sau 10s
        if (error?.originalError?.status === 503) {
          setTimeout(() => this.checkModelsReady(), 10000);
        }
      }
    });
  }

  async startNewChat() {
    this.activeRequest?.unsubscribe();
    this.isSending = false;
    const newId = this.generateChatId();
    const initialMessage: ChatMessage = {
      role: 'assistant',
      content: 'Xin chào! Tôi là HealthyAI. Bạn cần hỗ trợ gì hôm nay?'
    };

    const newHistory: ChatHistory = {
      id: newId,
      sessionId: newId,
      title: 'Cuộc trò chuyện mới',
      lastMessage: initialMessage.content,
      timestamp: new Date(),
      messages: [initialMessage]
    };

    this.chatHistories = [newHistory, ...this.chatHistories];
    this.currentChatId = newHistory.id;
    this.messages = newHistory.messages;
    this.input = '';
    this.lastBotMeta = undefined;
    this.errorMessage = '';

    // Lưu session mới vào Firebase
    const user = this.authService.getCurrentUser();
    if (user) {
      await this.saveSessionToFirebase(newHistory, user);
    }

    this.scrollToBottom();
  }

  async selectChat(chat: ChatHistory) {
    this.currentChatId = chat.id;
    
    // Luôn load messages từ Firebase để đảm bảo có đầy đủ và tránh duplicate
    const user = this.authService.getCurrentUser();
    if (user) {
      try {
        console.log(`🔄 Loading messages for session: ${chat.sessionId}`);
        const firebaseMessages = await this.firebaseService.getSessionMessages(chat.sessionId);
        console.log(`📥 Received ${firebaseMessages.length} messages from Firestore`);
        
        if (firebaseMessages.length > 0) {
          console.log('📋 Raw Firestore messages sample:', firebaseMessages.slice(0, 3).map(m => ({
            id: m.id,
            role: m.role,
            text: m.text?.substring(0, 30),
            aiResponse: m.aiResponse?.substring(0, 30),
            hasRole: !!m.role,
            hasAiResponse: !!m.aiResponse
          })));
          // Convert Firebase messages sang format ChatMessage
          const loadedMessages = firebaseMessages
            .map(msg => {
              // Xác định role: ưu tiên msg.role, nếu không có thì dựa vào aiResponse
              let role: 'user' | 'assistant';
              if (msg.role) {
                role = msg.role;
              } else if (msg.aiResponse) {
                role = 'assistant';
              } else {
                role = 'user'; // Nếu không có aiResponse thì là user message
              }
              
              // Xác định content: user dùng text, assistant dùng aiResponse hoặc text
              let content = '';
              if (role === 'assistant') {
                content = msg.aiResponse || msg.text || '';
              } else {
                // User message: chỉ dùng text, không dùng aiResponse
                content = msg.text || '';
              }
              
              // Debug log cho từng message
              if (!content || content.trim().length === 0) {
                console.warn('⚠️ Empty content message:', { 
                  id: msg.id, 
                  role: msg.role, 
                  text: msg.text?.substring(0, 30), 
                  aiResponse: msg.aiResponse?.substring(0, 30) 
                });
              }
              
              return { role, content };
            })
            .filter(msg => {
              // Lọc bỏ messages rỗng hoặc không có content
              const hasContent = msg.content && msg.content.trim().length > 0;
              if (!hasContent) {
                console.warn('⚠️ Filtered out empty message:', msg);
              }
              return hasContent;
            });
          
          // Loại bỏ duplicate messages dựa trên role và content
          const uniqueMessages: ChatMessage[] = [];
          const seenMessages = new Set<string>();
          
          for (const msg of loadedMessages) {
            const key = `${msg.role}:${msg.content}`;
            if (!seenMessages.has(key)) {
              seenMessages.add(key);
              uniqueMessages.push(msg);
            }
          }
          
          // Cập nhật chat.messages và this.messages - chỉ gán một lần để tránh duplicate
          chat.messages = uniqueMessages;
          // Tạo copy mới để tránh reference issues và trigger change detection
          this.messages = uniqueMessages.map(m => ({ ...m }));
          
          console.log(`✅ Loaded ${uniqueMessages.length} unique messages from Firebase for session ${chat.sessionId}`);
          console.log('📊 Messages breakdown:', {
            user: uniqueMessages.filter(m => m.role === 'user').length,
            assistant: uniqueMessages.filter(m => m.role === 'assistant').length,
            total: uniqueMessages.length
          });
          console.log('📝 Sample messages:', uniqueMessages.slice(0, 5).map(m => ({ 
            role: m.role, 
            content: m.content.substring(0, 50) + (m.content.length > 50 ? '...' : '') 
          })));
          
          // Đảm bảo UI được cập nhật
          setTimeout(() => {
            this.scrollToBottom();
          }, 100);
        } else {
          // Không có messages, dùng default
          const defaultMessage = [{
            role: 'assistant' as const,
            content: 'Xin chào! Tôi là HealthyAI. Bạn cần hỗ trợ gì hôm nay?'
          }];
          chat.messages = defaultMessage;
          this.messages = [...defaultMessage];
        }
      } catch (error) {
        console.error('❌ Error loading messages from Firebase:', error);
        // Fallback về messages hiện có
        this.messages = chat.messages.length > 0 ? [...chat.messages] : [{
          role: 'assistant' as const,
          content: 'Xin chào! Tôi là HealthyAI. Bạn cần hỗ trợ gì hôm nay?'
        }];
      }
    } else {
      // Không có user, dùng messages hiện có
      this.messages = chat.messages.length > 0 ? [...chat.messages] : [{
        role: 'assistant' as const,
        content: 'Xin chào! Tôi là HealthyAI. Bạn cần hỗ trợ gì hôm nay?'
      }];
    }
    
    this.lastBotMeta = chat.meta;
    this.scrollToBottom();
  }

  formatDate(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Hôm nay';
    if (days === 1) return 'Hôm qua';
    if (days < 7) return `${days} ngày trước`;
    return date.toLocaleDateString('vi-VN');
  }

  /**
   * Xóa chat session
   */
  async deleteChat(chat: ChatHistory, event: Event) {
    event.stopPropagation(); // Ngăn chặn selectChat khi click delete
    
    if (!confirm(`Bạn có chắc muốn xóa cuộc trò chuyện "${chat.title}"?`)) {
      return;
    }

    const user = this.authService.getCurrentUser();
    if (!user) {
      return;
    }

    try {
      await this.firebaseService.deleteChatSession(chat.sessionId, user.id);
      
      // Xóa khỏi danh sách
      this.chatHistories = this.chatHistories.filter(c => c.id !== chat.id);
      
      // Nếu đang xem chat bị xóa, chuyển sang chat khác hoặc tạo mới
      if (this.currentChatId === chat.id) {
        if (this.chatHistories.length > 0) {
          await this.selectChat(this.chatHistories[0]);
        } else {
          await this.startNewChat();
        }
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
      alert('Không thể xóa cuộc trò chuyện. Vui lòng thử lại.');
    }
  }

  toggleAccountMenu() {
    this.isAccountMenuOpen = !this.isAccountMenuOpen;
  }

  openSettings() {
    console.log('Mở cài đặt');
    this.isAccountMenuOpen = false;
    try { this.router.navigate(['/settings']); } catch (e) {}
  }

  logout() {
    console.log('Đăng xuất');
    this.authService.logout().subscribe({
      next: () => {
        this.isAccountMenuOpen = false;
        try { this.router.navigate(['/']); } catch (e) {}
      },
      error: (err: any) => {
        console.error('Logout failed', err);
        this.isAccountMenuOpen = false;
      }
    });
  }

  private updateHistoryPreview(latestMessage: string, history: ChatHistory) {
    history.lastMessage = latestMessage;
    history.timestamp = new Date();

    const firstUserMessage = history.messages.find((msg) => msg.role === 'user');
    if (firstUserMessage) {
      history.title = this.buildTitleFromMessage(firstUserMessage.content);
    }
  }

  private buildTitleFromMessage(content: string): string {
    if (!content) {
      return 'Cuộc trò chuyện';
    }
    return content.length > 40 ? `${content.substring(0, 37)}...` : content;
  }

  private generateChatId(): string {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return `chat_${Date.now()}`;
  }

  /**
   * Load chat sessions từ Firebase
   */
  private async loadChatSessions() {
    const user = this.authService.getCurrentUser();
    if (!user) {
      // Nếu chưa đăng nhập, vẫn tạo chat mới nhưng không lưu
      this.startNewChat();
      return;
    }

    try {
      const sessions = await this.firebaseService.getChatSessions(user.id);
      
      if (sessions.length > 0) {
        // Convert Firebase sessions sang ChatHistory format
        this.chatHistories = await Promise.all(
          sessions.map(async (session) => {
            const messages = await this.firebaseService.getSessionMessages(session.sessionId);
            return {
              id: session.id || session.sessionId,
              sessionId: session.sessionId,
              title: session.title,
              lastMessage: session.lastMessage,
              timestamp: session.updatedAt instanceof Date ? session.updatedAt : session.updatedAt.toDate(),
              messages: messages.length > 0
                ? messages
                  .map(msg => {
                    // Xác định role: ưu tiên msg.role, nếu không có thì dựa vào aiResponse
                    let role: 'user' | 'assistant';
                    if (msg.role) {
                      role = msg.role;
                    } else if (msg.aiResponse) {
                      role = 'assistant';
                    } else {
                      role = 'user'; // Nếu không có aiResponse thì là user message
                    }
                    
                    // Xác định content: user dùng text, assistant dùng aiResponse hoặc text
                    let content = '';
                    if (role === 'assistant') {
                      content = msg.aiResponse || msg.text || '';
                    } else {
                      content = msg.text || '';
                    }
                    
                    return { role, content };
                  })
                  .filter(msg => msg.content && msg.content.trim().length > 0) // Lọc bỏ messages rỗng
                  .sort((a, b) => {
                    // Đảm bảo thứ tự đúng (theo timestamp nếu có)
                    return 0; // Giữ nguyên thứ tự từ Firestore (đã sort trong getSessionMessages)
                  })
                : [
                    {
                      role: 'assistant' as const,
                      content: 'Xin chào! Tôi là HealthyAI. Bạn cần hỗ trợ gì hôm nay?'
                    }
                  ],
              meta: undefined
            } as ChatHistory;
          })
        );
        
        // Chọn chat đầu tiên (mới nhất)
        if (this.chatHistories.length > 0) {
          await this.selectChat(this.chatHistories[0]);
        }
      } else {
        // Chưa có chat nào, tạo mới
        await this.startNewChat();
      }
    } catch (error) {
      console.error('Error loading chat sessions:', error);
      // Nếu lỗi, vẫn tạo chat mới
      await this.startNewChat();
    }
  }

  /**
   * Lưu message vào Firebase
   */
  private async saveMessageToFirebase(
    message: ChatMessage,
    sessionId: string,
    user: { id: string; email: string },
    metadata?: ChatResponse
  ): Promise<void> {
    try {
      const messageData: any = {
        userId: user.id,
        userEmail: user.email,
        text: message.content, // Luôn lưu text (cho cả user và assistant)
        role: message.role, // QUAN TRỌNG: Phải lưu role để phân biệt
        sessionId: sessionId
      };
      
      // Chỉ thêm aiResponse khi là assistant (không thêm undefined)
      if (message.role === 'assistant') {
        messageData.aiResponse = message.content;
      }
      
      // Chỉ thêm metadata khi có (không thêm undefined)
      if (metadata) {
        const metadataObj: any = {};
        if (metadata.intent) metadataObj.intent = metadata.intent;
        if (metadata.intentConfidence !== undefined) metadataObj.intentConfidence = metadata.intentConfidence;
        if (metadata.risk) metadataObj.risk = metadata.risk;
        if (metadata.stage) metadataObj.stage = metadata.stage;
        if (metadata.sources && metadata.sources.length > 0) metadataObj.sources = metadata.sources;
        
        // Chỉ thêm metadata nếu có ít nhất một field
        if (Object.keys(metadataObj).length > 0) {
          messageData.metadata = metadataObj;
        }
      }
      
      console.log('💾 Saving message to Firebase:', {
        role: messageData.role,
        text: messageData.text.substring(0, 50) + (messageData.text.length > 50 ? '...' : ''),
        hasAiResponse: !!messageData.aiResponse,
        sessionId
      });
      
      const messageId = await this.firebaseService.addChatMessage(messageData);
      console.log('✅ Message saved successfully with ID:', messageId);
    } catch (error) {
      console.error('❌ Error saving message to Firebase:', error);
      // Throw lại để caller có thể xử lý
      throw error;
    }
  }

  /**
   * Lưu session vào Firebase
   */
  private async saveSessionToFirebase(history: ChatHistory, user: { id: string; email: string }) {
    try {
      await this.firebaseService.saveChatSession({
        userId: user.id,
        userEmail: user.email,
        sessionId: history.sessionId,
        title: history.title,
        lastMessage: history.lastMessage,
        messageCount: history.messages.length
      });
    } catch (error) {
      console.error('Error saving session to Firebase:', error);
    }
  }
}
