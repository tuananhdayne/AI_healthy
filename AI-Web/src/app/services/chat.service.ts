import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map, timeout, catchError, throwError } from 'rxjs';

import { environment } from '../../environments/environment';

interface ChatResponseApi {
  session_id: string;
  reply: string;
  intent: string | null;
  intent_confidence: number;
  symptoms: Record<string, any>;
  risk: string | null;
  clarification_needed: boolean;
  clarification_question: string | null;
  sources: Array<Record<string, any>>;
  stage: string;
}

export interface ChatResponse {
  sessionId: string;
  reply: string;
  intent: string | null;
  intentConfidence: number;
  symptoms: Record<string, any>;
  risk: string | null;
  clarificationNeeded: boolean;
  clarificationQuestion: string | null;
  sources: Array<Record<string, any>>;
  stage: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly apiBaseUrl = this.normalizeBaseUrl(environment.apiBaseUrl);

  constructor(private http: HttpClient) {}

  sendMessage(message: string, sessionId: string): Observable<ChatResponse> {
    return this.http
      .post<ChatResponseApi>(`${this.apiBaseUrl}/api/chat`, {
        message,
        session_id: sessionId
      })
      .pipe(
        timeout(120000), // 2 phút timeout cho model inference
        map((response) => this.transformResponse(response)),
        catchError((error: any) => {
          let errorMessage = 'Không gửi được tin nhắn. Vui lòng thử lại.';
          
          if (error?.status === 503) {
            errorMessage = 'Models đang tải, vui lòng đợi thêm vài phút và thử lại.';
          } else if (error?.status === 0 || error?.name === 'TimeoutError' || error?.message?.includes('timeout')) {
            errorMessage = 'Request timeout. Models có thể đang xử lý, vui lòng thử lại sau.';
          } else if (error?.error?.detail) {
            errorMessage = error.error.detail;
          } else if (error?.message) {
            errorMessage = error.message;
          }
          
          return throwError(() => ({ message: errorMessage, originalError: error }));
        })
      );
  }

  checkReady(): Observable<{ ready: boolean; status: string }> {
    return this.http
      .get<{ ready: boolean; status: string }>(`${this.apiBaseUrl}/ready`)
      .pipe(
        timeout(5000),
        catchError(() => {
          return throwError(() => ({ ready: false, status: 'Không kết nối được server' }));
        })
      );
  }

  resetConversation(sessionId: string): Observable<void> {
    return this.http.post<void>(`${this.apiBaseUrl}/api/chat/reset`, {
      session_id: sessionId
    });
  }

  private transformResponse(apiResponse: ChatResponseApi): ChatResponse {
    return {
      sessionId: apiResponse.session_id,
      reply: apiResponse.reply,
      intent: apiResponse.intent,
      intentConfidence: apiResponse.intent_confidence,
      symptoms: apiResponse.symptoms || {},
      risk: apiResponse.risk,
      clarificationNeeded: apiResponse.clarification_needed,
      clarificationQuestion: apiResponse.clarification_question,
      sources: apiResponse.sources || [],
      stage: apiResponse.stage
    };
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

