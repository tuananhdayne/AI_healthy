# 📚 GIẢI THÍCH CHI TIẾT CHỨC NĂNG CHAT

## 🎯 TỔNG QUAN

Hệ thống chat sử dụng kiến trúc **Frontend (Angular) + Backend (Python FastAPI)** với các công nghệ AI:
- **Intent Classification**: PhoBERT để nhận diện ý định người dùng
- **RAG (Retrieval-Augmented Generation)**: FAISS + SentenceTransformer để tìm kiếm thông tin
- **Text Generation**: Google Gemini API để tạo câu trả lời tự nhiên
- **Firebase Firestore**: Lưu trữ lịch sử chat và session

---

## 🔄 LUỒNG HOẠT ĐỘNG TỔNG THỂ

```
User nhập message
    ↓
Frontend (chat-ui.component.ts)
    ↓
ChatService gửi HTTP POST → Backend API
    ↓
api_server.py (/api/chat)
    ↓
chatbot.py (run_chat_pipeline)
    ↓
[1] Validation
[2] Pending Flow (nếu đang chờ xác nhận)
[3] Intent Classification
[4] Follow-up & Topic Shift Detection
[5] Intent Continuity Guard (giữ intent khi follow-up)
[6] Intent Lock (GPT-like stabilization)
[7] Pending Intent (xác nhận đổi chủ đề khi mơ hồ)
[8] Symptom Extraction & Risk Estimation
[9] RAG Guard (tránh RAG sai chủ đề)
[10] RAG Retrieval với Gate Logic theo loại Intent
[11] Tách bạch USER FACTS và RAG KNOWLEDGE
[12] Generate Answer (Gemini) với prompt tách bạch
    ↓
Trả về response
    ↓
Frontend lưu vào Firebase
    ↓
Hiển thị cho User
```

---

## 📱 PHẦN 1: FRONTEND (Angular)

### 1.1. Component: `chat-ui.component.ts`

#### **Khởi tạo (ngOnInit)**
```typescript
ngOnInit(): void {
  this.checkModelsReady();  // Kiểm tra backend đã sẵn sàng chưa
  this.loadChatSessions();  // Load lịch sử chat từ Firebase
}
```

**Chi tiết:**
- `checkModelsReady()`: Gọi API `/ready` để kiểm tra models đã load xong chưa
- `loadChatSessions()`: Load tất cả sessions từ Firestore và hiển thị sidebar

#### **Gửi tin nhắn (send())**
```typescript
async send() {
  // 1. Validate input
  const text = this.input.trim();
  if (!text || !this.currentChatId || this.isSending) return;

  // 2. Tạo user message object
  const userMessage = { role: 'user' as const, content: text };

  // 3. Lưu vào Firebase TRƯỚC khi gửi request
  await this.saveMessageToFirebase(userMessage, sessionId, user);

  // 4. Hiển thị user message trong UI
  this.messages.push(userMessage);

  // 5. Hiển thị placeholder "HealthyAI đang suy nghĩ..."
  this.messages.push({
    role: 'assistant',
    content: 'HealthyAI đang suy nghĩ...',
    pending: true
  });

  // 6. Gọi API backend
  this.chatService.sendMessage(text, sessionId).subscribe({
    next: async (response) => {
      // 7. Thay thế placeholder bằng response thật
      this.messages[placeholderIndex] = {
        role: 'assistant',
        content: response.reply
      };

      // 8. Lưu assistant message vào Firebase
      await this.saveMessageToFirebase(assistantMessage, sessionId, user, response);
    },
    error: (error) => {
      // Xử lý lỗi và hiển thị thông báo
    }
  });
}
```

**Điểm quan trọng:**
- ✅ Lưu message vào Firebase **TRƯỚC** khi hiển thị để đảm bảo không mất dữ liệu
- ✅ Hiển thị placeholder để UX tốt hơn
- ✅ Kiểm tra duplicate messages để tránh hiển thị trùng lặp
- ✅ Tự động scroll xuống cuối khi có message mới

#### **Tải lại chat session (selectChat())**
```typescript
async selectChat(chat: ChatHistory) {
  // 1. Set current chat ID
  this.currentChatId = chat.id;

  // 2. Load messages từ Firebase (không dùng cache)
  const firebaseMessages = await this.firebaseService.getSessionMessages(chat.sessionId);

  // 3. Convert Firebase format sang ChatMessage format
  const loadedMessages = firebaseMessages
    .map(msg => {
      let role = msg.role || (msg.aiResponse ? 'assistant' : 'user');
      let content = role === 'assistant' 
        ? (msg.aiResponse || msg.text) 
        : msg.text;
      return { role, content };
    })
    .filter(msg => msg.content && msg.content.trim().length > 0);

  // 4. Loại bỏ duplicate messages
  const uniqueMessages = [...];
  
  // 5. Cập nhật UI
  this.messages = uniqueMessages;
}
```

**Điểm quan trọng:**
- ✅ Luôn load từ Firebase để đảm bảo dữ liệu mới nhất
- ✅ Xử lý cả 2 format: `role` field và `aiResponse` field (legacy)
- ✅ Lọc bỏ messages rỗng và duplicate

---

### 1.2. Service: `chat.service.ts`

#### **Gửi message đến backend**
```typescript
sendMessage(message: string, sessionId: string): Observable<ChatResponse> {
  return this.http.post<ChatResponseApi>(`${apiBaseUrl}/api/chat`, {
    message,
    session_id: sessionId
  })
  .pipe(
    timeout(120000),  // 2 phút timeout
    map((response) => this.transformResponse(response)),
    catchError((error) => {
      // Xử lý các loại lỗi:
      // - 503: Models đang tải
      // - Timeout: Request quá lâu
      // - 500: Lỗi server
    })
  );
}
```

**Chi tiết:**
- Timeout 120 giây để đủ thời gian cho AI xử lý
- Transform response từ snake_case (backend) sang camelCase (frontend)
- Xử lý các loại lỗi khác nhau và hiển thị message phù hợp

---

## 🐍 PHẦN 2: BACKEND (Python FastAPI)

### 2.1. API Server: `api_server.py`

#### **Khởi động server (load_models)**
```python
@app.on_event("startup")
async def load_models():
    """
    Load tất cả models khi server khởi động:
    1. Firestore initialization
    2. Intent Classifier (PhoBERT)
    3. RAG Retriever (FAISS + SentenceTransformer)
    4. Gemini API connection
    5. Test pipeline
    """
```

**Quy trình:**
1. **Bước 0**: Khởi tạo Firestore (nếu có service account key)
2. **Bước 1**: Import các module cơ bản (symptom_extractor, risk_estimator, ...)
3. **Bước 2**: Load Intent Classifier từ file model PhoBERT
4. **Bước 3**: Load RAG Retriever (FAISS indexes + SentenceTransformer model)
5. **Bước 4**: Kiểm tra Gemini API connection
6. **Bước 5**: Khởi tạo chatbot pipeline và test với câu đơn giản

**Lưu ý:**
- Models được load **một lần** khi server khởi động
- Có logging chi tiết từng bước và thời gian
- Xử lý lỗi MemoryError riêng biệt

#### **Endpoint: `/api/chat`**
```python
@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    # 1. Kiểm tra models đã sẵn sàng
    if not _models_ready:
        raise HTTPException(503, "Models đang tải...")

    # 2. Validate input
    if not payload.message or not payload.message.strip():
        raise HTTPException(400, "message is required")

    # 3. Gọi chatbot pipeline
    session_id = payload.session_id or str(uuid.uuid4())
    response = _run_chat_pipeline(
        payload.message, 
        session_id=session_id,
        user_id=payload.user_id
    )

    # 4. Trả về response
    return response
```

**Lưu ý:**
- Backend **KHÔNG** lưu vào Firestore (frontend đã lưu)
- Tạo session_id mới nếu không có
- Truyền user_id để lấy health profile (nếu cần)

---

### 2.2. Chatbot Pipeline: `chatbot.py`

#### **Hàm chính: `run_chat_pipeline()`**

Đây là **trái tim** của hệ thống chat, xử lý message qua nhiều bước:

---

#### **BƯỚC 1: VALIDATION**

```python
cleaned_input = (user_input or "").strip()
if not cleaned_input:
    return {
        "reply": "Bạn hãy nhập câu hỏi hoặc mô tả triệu chứng cụ thể hơn nhé.",
        "stage": "validation"
    }
```

- Làm sạch input (trim whitespace)
- Kiểm tra input không rỗng

---

#### **BƯỚC 2: INTENT CLASSIFICATION**

```python
intent, intent_conf = intent_classifier.predict_with_conf(cleaned_input)
print(f"🧠 Intent: {intent} | conf={intent_conf:.2f}")
```

**Các intent được hỗ trợ:**
- `bao_dau_bung`: Báo đau bụng
- `bao_dau_dau`: Báo đau đầu
- `bao_ho`: Báo ho
- `bao_met`: Báo mệt mỏi
- `bao_sot`: Báo sốt
- `chao_hoi`: Chào hỏi
- `lo_lang_stress`: Lo lắng, stress
- `nhac_nho_uong_thuoc`: Nhắc nhở uống thuốc
- `tu_van_dinh_duong`: Tư vấn dinh dưỡng
- `tu_van_tap_luyen`: Tư vấn tập luyện
- `other`: Khác
- `unknown`: Không xác định được

**Công nghệ:**
- Model: PhoBERT (Vietnamese BERT)
- Input: Câu hỏi của người dùng
- Output: Intent label + confidence score (0.0 - 1.0)

**Vai trò:**
- Quyết định **chiến lược trả lời** (RAG hay Gemini tự do)
- Confidence >= 0.998 → search RAG theo intent
- Confidence < 0.98 hoặc intent = "other"/"unknown" → dùng Gemini tự do

---

#### **BƯỚC 3: SYMPTOM EXTRACTION**

```python
symptoms = extract_symptoms(cleaned_input)
risk = estimate_risk(symptoms)
```

**Extract symptoms (Rule-based):**
```python
def extract_symptoms(text: str):
    return {
        "location": "trán" | "bụng trên" | ...,
        "duration": "3 ngày" | "2 tuần" | ...,
        "intensity": "âm ỉ" | "nhói" | "dữ dội" | ...,
        "extra": ["buồn nôn", "sốt", ...],
        "danger_signs": ["khó thở", "ngất", ...]
    }
```

**Các trường được extract:**
- **Location**: Vị trí (trán, bụng, ngực, ...)
- **Duration**: Thời gian (ngày, tuần, tháng)
- **Intensity**: Mức độ (âm ỉ, nhói, dữ dội, quặn)
- **Extra**: Triệu chứng phụ (buồn nôn, nôn, chóng mặt, sốt, ...)
- **Danger signs**: Dấu hiệu nguy hiểm (khó thở, ngất, mất ý thức, ...)

**Risk estimation:**
```python
def estimate_risk(symptoms):
    if "danger_signs" in symptoms and symptoms["danger_signs"]:
        return "high"  # Nguy hiểm
    elif symptoms.get("intensity") == "dữ dội":
        return "medium"  # Trung bình
    else:
        return "low"  # Thấp
```

---

#### **BƯỚC 4: LƯU VÀO MEMORY (STATE)**

```python
state = _get_or_create_state(session_id)
# State được khởi tạo với:
# - last_intent: None
# - last_symptoms: None
# - conversation_history: []
# - intent_lock: None  # { "intent": str, "turns": int } | None
# - pending_intent: None  # Intent mới đang chờ xác nhận
# - pending_from_intent: None  # Intent cũ
# - pending_type: None  # "intent_switch_confirm" | None
```

**State lưu trữ:**
- `last_intent`: Intent của câu hỏi trước
- `last_symptoms`: Symptoms của câu hỏi trước
- `last_user_input`: Input của câu hỏi trước
- `conversation_history`: Lịch sử Q&A (tối đa 6 cặp gần nhất)
- `last_clarification_question`: Câu hỏi clarification (nếu có)
- `intent_lock`: Lock intent ổn định 1-2 lượt khi confidence cao
- `pending_intent`: Intent mới đang chờ xác nhận đổi chủ đề
- `pending_from_intent`: Intent cũ (khi đang pending)
- `pending_type`: Loại pending ("intent_switch_confirm" | None)

**Mục đích:**
- Nhớ ngữ cảnh trong cuộc hội thoại (GPT-like)
- Xử lý follow-up questions với intent continuity
- Tạo conversation history để Gemini hiểu context
- Giữ intent ổn định khi confidence cao (intent lock)
- Xác nhận đổi chủ đề khi mơ hồ (pending intent)

---

#### **BƯỚC 5: PENDING FLOW (Xử lý xác nhận đổi chủ đề)**

```python
if pending_type == "intent_switch_confirm":
    confirm_result = parse_switch_confirm(cleaned_input)
    if confirm_result is True:
        intent = pending_intent  # Xác nhận chuyển
    elif confirm_result is False:
        intent = pending_from_intent  # Giữ chủ đề cũ
    else:
        # Không rõ → hỏi lại, không đổi intent, không RAG
        return response_with_confirmation_question
```

**Khi nào tạo pending:**
- Có `last_intent`
- `intent_new != last_intent`
- `is_follow_up == False`
- `is_topic_shift == False`
- `intent_conf` trong vùng xám: [0.85, 0.97)

**Hành vi:**
- Không RAG, không generate câu trả lời chuyên môn
- Hỏi xác nhận: "Bạn đang muốn hỏi tiếp về {intent_cũ} hay chuyển sang {intent_mới}?"
- Parse câu trả lời: True (chuyển), False (giữ), None (hỏi lại)

---

#### **BƯỚC 6: NHẬN DIỆN FOLLOW-UP & TOPIC SHIFT**

```python
is_follow_up_flag = is_follow_up(cleaned_input)
is_topic_shift_flag = is_topic_shift(cleaned_input)
```

**Follow-up keywords:**
- "vẫn", "vẫn thế", "như trước", "như hôm qua"
- "còn", "còn bị", "còn thấy"
- "kèm", "kèm theo", "thêm"
- "hôm nay", "sau đó"
- "đỡ hơn", "đỡ rồi", "nặng hơn", "tệ hơn"
- "tăng lên", "giảm đi"

**Topic shift keywords:**
- "cho hỏi", "cho mình hỏi", "nhân tiện"
- "đổi chủ đề", "vấn đề khác", "câu hỏi khác"
- "muốn hỏi về", "hỏi thêm về", "xin tư vấn"
- "chuyển sang", "đổi sang"
- "tư vấn dinh dưỡng", "tư vấn tập luyện"

**Lưu ý đặc biệt:**
- "ngoài ra" chỉ là topic shift nếu đi kèm các cụm rõ (cho hỏi, nhân tiện...)

---

#### **BƯỚC 7: INTENT CONTINUITY GUARD (Giữ intent khi follow-up)**

```python
if is_follow_up_flag and last_intent and not is_topic_shift_flag:
    intent = last_intent  # Ưu tiên tuyệt đối giữ intent cũ
    print("✅ Follow-up detected → giữ intent cũ")
elif is_topic_shift_flag and not is_follow_up_flag:
    intent = intent_new  # Cho phép đổi chủ đề
    print("✅ Topic shift rõ → đổi intent")
elif state.get("intent_lock"):
    # Intent lock active → dùng locked intent
    intent = intent_lock["intent"]
    intent_lock["turns"] -= 1
```

**Logic ưu tiên:**
1. **Follow-up** → Giữ intent cũ (ưu tiên tuyệt đối)
2. **Topic shift rõ** → Cho phép đổi intent
3. **Intent lock** → Dùng locked intent (1-2 lượt)
4. **Pending intent** → Tạo pending nếu intent đổi nhưng mơ hồ
5. **Bình thường** → Dùng intent classifier

**Intent lock:**
- Khi `intent_conf >= 0.97` → Set lock với `turns = 2`
- Giữ intent ổn định 1-2 lượt để tránh dao động
- Tự động xóa khi hết lượt hoặc topic shift

---

#### **BƯỚC 6: RISK LAYER (AN TOÀN)**

```python
if risk == "high":
    danger_signs = symptoms.get("danger_signs") or []
    response["reply"] = (
        "⚠️ Mình phát hiện có dấu hiệu nguy hiểm như: "
        + ", ".join(danger_signs)
        + ". Bạn nên đi khám bác sĩ càng sớm càng tốt."
    )
    response["stage"] = "safety"
    return response  # Dừng ngay, không xử lý tiếp
```

**Lưu ý quan trọng:**
- Nếu phát hiện **dấu hiệu nguy hiểm** → trả lời ngay, **không** xử lý tiếp
- Ưu tiên **an toàn** của người dùng

---

#### **BƯỚC 7: CLARIFICATION LAYER**

```python
if need_more_info(cleaned_input, intent):
    question = build_clarification_question(intent)
    response["reply"] = f"Để hiểu rõ hơn, bạn cho mình biết thêm:\n{question}"
    response["clarification_needed"] = True
    response["stage"] = "clarification"
    # Lưu câu hỏi để xử lý câu trả lời tiếp theo
    state["last_clarification_question"] = question
    state["last_user_input_before_clarification"] = cleaned_input
    return response
```
**Khi nào cần clarification:**
- Câu hỏi quá ngắn (<= 2 từ) và không có từ khóa triệu chứng
- Câu hỏi 3-4 từ nhưng không có từ khóa rõ ràng theo intent
- Intent không phải "other"/"unknown" nhưng thông tin không đủ

**Ví dụ:**
- ❌ "đau" → cần hỏi thêm (vị trí, mức độ)
- ✅ "đau đầu ở trán" → không cần hỏi (đã rõ)
- ❌ "mệt" → cần hỏi thêm (từ khi nào, kèm triệu chứng gì)
- ✅ "mệt mỏi 3 ngày kèm chóng mặt" → không cần hỏi (đã rõ)

**Lưu ý:**
- Clarification question được lưu vào state để xử lý câu trả lời tiếp theo
- Sau khi user trả lời clarification, hệ thống sẽ kết hợp thông tin để trả lời chính xác hơn

---

#### **BƯỚC 8: RAG GUARD (Tránh RAG sai chủ đề)**

```python
# Follow-up tuyệt đối không được search_by_intent(intent_new)
if is_follow_up_flag and last_intent:
    rag_intent = last_intent  # Dùng intent cũ cho RAG
    print("🛡️ RAG Guard: Follow-up → dùng intent cũ")
else:
    rag_intent = intent  # Dùng intent hiện tại
```

**Nguyên tắc:**
- Follow-up **tuyệt đối** không được search RAG theo intent mới
- Luôn dùng `last_intent` cho RAG khi follow-up
- Đảm bảo RAG search đúng chủ đề đang được nói tiếp

---

#### **BƯỚC 9: RAG RETRIEVAL với Gate Logic theo loại Intent**

```python
# Phân loại intent
intent_category = get_intent_category(rag_intent)
# "symptom": bao_dau_dau, bao_dau_bung, bao_sot, bao_ho, bao_met_moi
# "advisory": tu_van_dinh_duong, tu_van_tap_luyen
# "no_rag": other, chao_hoi, unknown, lo_lang_stress, nhac_nho_uong_thuoc

strong_threshold, soft_threshold = get_rag_gate_thresholds(intent_category)
# symptom: (0.80, 0.70)
# advisory: (0.75, 0.65)
# no_rag: (1.0, 1.0) - luôn không dùng RAG
```

**RAG Gate Logic theo loại Intent:**

**1️⃣ Intent triệu chứng (symptom) - An toàn cao:**
- `bao_dau_dau`, `bao_dau_bung`, `bao_sot`, `bao_ho`, `bao_met_moi`
- **STRONG RAG** (3-5 đoạn): RAG confidence >= 0.80
- **SOFT RAG** (1-2 đoạn, chỉ tham khảo): 0.70 <= confidence < 0.80
- **NO RAG** → Gemini: confidence < 0.70

**2️⃣ Intent tư vấn (advisory) - Tận dụng RAG nhiều hơn:**
- `tu_van_dinh_duong`, `tu_van_tap_luyen`
- **STRONG RAG** (3-5 đoạn): RAG confidence >= 0.75
- **SOFT RAG** (1-2 đoạn): 0.65 <= confidence < 0.75
- **NO RAG** → Gemini: confidence < 0.65

**3️⃣ Intent không dùng RAG:**
- `other`, `chao_hoi`, `unknown`, `lo_lang_stress`, `nhac_nho_uong_thuoc`
- Luôn Gemini, không search RAG

**Quy trình RAG:**

```python
if intent_category == "no_rag":
    use_rag = False  # Luôn Gemini
elif intent_conf >= 0.97 and rag_intent not in ["other", "unknown"]:
    docs = retriever.search_by_intent(rag_intent, cleaned_input, k=5)
    rag_confidence = docs[0].get("confidence", 0.0)
    
    if rag_confidence >= strong_threshold:
        # STRONG RAG: 3-5 đoạn
        context = "\n".join([d["text"] for d in docs[:5]])
        use_rag = True
        rag_mode = "strong"
    elif rag_confidence >= soft_threshold:
        # SOFT RAG: 1-2 đoạn
        context = "\n".join([d["text"] for d in docs[:2]])
        use_rag = True
        rag_mode = "soft"
    else:
        # NO RAG: Confidence quá thấp
        use_rag = False
        rag_mode = None
```

**Lưu ý:**
- Ngưỡng cao hơn cho intent triệu chứng (an toàn)
- Ngưỡng thấp hơn cho intent tư vấn (tận dụng RAG)
- Quality gate: Kiểm tra confidence của RAG result trước khi dùng

**Công nghệ RAG:**

```python
# Retriever sử dụng:
# - FAISS: Vector database để tìm kiếm nhanh
# - SentenceTransformer: "keepitreal/vietnamese-sbert" để embed text
# - Cosine similarity: Để tính độ tương đồng giữa query và documents

# Quy trình:
# 1. Embed query → vector (768 dimensions)
# 2. Search trong FAISS index → top K documents
# 3. Tính cosine similarity → confidence score
# 4. Trả về documents có confidence cao nhất
```

**Cấu trúc RAG Index:**
- Mỗi intent có index riêng:
  - `bao_dau_bung_index.faiss` + `bao_dau_bung_docs.pkl`
  - `bao_dau_dau_index.faiss` + `bao_dau_dau_docs.pkl`
  - `bao_ho_index.faiss` + `bao_ho_docs.pkl`
  - ...
- Documents được chia nhỏ thành chunks (đoạn văn ngắn)
- Mỗi chunk được embed thành vector và lưu trong FAISS

**Kết quả RAG:**
```python
docs = [
    {
        "text": "Đau đầu có thể do...",
        "cosine": 0.85,  # Cosine similarity
        "confidence": 0.925  # (cosine + 1) / 2
    },
    ...
]
```

---

#### **BƯỚC 9: LẤY HEALTH PROFILE (Nếu có user_id)**

```python
health_profile_context = ""
if user_id:
    profile = get_health_profile(user_id)
    if profile:
        # Tính BMI
        bmi = can_nang / (chieu_cao_m ** 2)
        bmi_category = "hơi gầy" | "cân đối" | "hơi thừa cân" | "thừa cân nhiều"
        
        # Tạo context
        health_profile_context = f"""[PROFILE]
Tuổi: {profile.tuoi}
Giới tính: {gioi_tinh_label}
Chiều cao: {profile.chieuCao} cm
Cân nặng: {profile.canNang} kg
BMI: {bmi:.1f} ({bmi_category})
Mức vận động: {muc_van_dong_label}
[/PROFILE]
"""
```

**Mục đích:**
- Cá nhân hóa câu trả lời dựa trên thông tin sức khỏe của user
- Đặc biệt quan trọng cho intent `tu_van_tap_luyen` và `tu_van_dinh_duong`
- Đảm bảo gợi ý phù hợp với độ tuổi, BMI, mức vận động

**Khi nào sử dụng:**
- Intent là `tu_van_tap_luyen` → dùng health profile để gợi ý bài tập phù hợp
- Intent là `tu_van_dinh_duong` → dùng health profile để gợi ý chế độ ăn
- Intent khác → có thể dùng để thêm context (tùy chọn)

---

#### **BƯỚC 10: XÂY DỰNG CONVERSATION HISTORY**

```python
# Lấy lịch sử hội thoại từ state (tối đa 5 cặp Q&A gần nhất)
complete_history = [(q, a) for q, a in state["conversation_history"] if a is not None]

# Xây dựng conversation history string
conversation_history = None
if last_clarification_question:
    # Có clarification question trước đó
    conversation_history = f"""
Lịch sử cuộc trò chuyện:
👤 Người dùng: "{last_user_input_before_clarification}"
🤖 Bạn: "{last_clarification_question}"

👉 Bây giờ người dùng trả lời: "{cleaned_input}"
"""
elif complete_history:
    # Có lịch sử Q&A từ các lần trước
    conversation_history = "Lịch sử cuộc trò chuyện trước đó:\n"
    for q, a in complete_history[-5:]:
        conversation_history += f"\n👤 Người dùng: {q}\n🤖 Bạn: {a}\n"
    conversation_history += f"\n👉 Bây giờ người dùng hỏi: \"{cleaned_input}\""
```

**Mục đích:**
- Giúp Gemini **nhớ ngữ cảnh** trong cuộc hội thoại
- Xử lý follow-up questions ("vẫn thế", "đỡ hơn rồi")
- Đảm bảo câu trả lời nhất quán và liên kết với câu hỏi trước

**Lưu trữ:**
- Tối đa **6 cặp Q&A** (để không tốn quá nhiều token)
- Tự động xóa cặp cũ nhất khi vượt quá giới hạn
- Mỗi cặp = (user_input, bot_reply)

---

#### **BƯỚC 11: NGUYÊN TẮC TÁCH BẠCH USER FACTS VÀ RAG KNOWLEDGE**

**🔒 Nguyên tắc cốt lõi:**

1. **USER FACTS (Thông tin từ người dùng):**
   - CHỈ sử dụng những gì người dùng NÓI TRỰC TIẾP
   - KHÔNG tự suy ra, KHÔNG giả định, KHÔNG thêm triệu chứng mà người dùng chưa nói
   - Ví dụ: User nói "tôi đau ở rốn" → CHỈ biết đau ở rốn, KHÔNG suy ra đầy hơi, chướng bụng, ăn cay...

2. **RAG KNOWLEDGE (Kiến thức tham khảo):**
   - Đây là KIẾN THỨC Y TẾ THAM KHẢO từ database, KHÔNG phải bệnh sử của người dùng
   - Dùng để GIẢI THÍCH, HƯỚNG DẪN, nhưng KHÔNG GÁN cho người dùng
   - Ví dụ đúng: "Đau bụng ở vùng rốn thường có thể liên quan đến các vấn đề tiêu hóa. Một số nguyên nhân thường gặp bao gồm..."
   - Ví dụ SAI: "Dựa trên những triệu chứng bạn đã chia sẻ như đầy hơi, chướng bụng..." (nếu user chưa nói)

3. **TUYỆT ĐỐI KHÔNG:**
   - ❌ Nói "Dựa trên những triệu chứng bạn đã chia sẻ như..." khi triệu chứng đó KHÔNG có trong user input
   - ❌ Nói "Có thể thấy bạn đang gặp..." về triệu chứng mà user chưa nói
   - ❌ Tự suy ra nguyên nhân cụ thể (ăn cay, căng thẳng...) nếu user chưa nói
   - ❌ Gán các triệu chứng từ RAG knowledge cho user

**Cấu trúc prompt:**
```
============================================================
KIẾN THỨC Y TẾ THAM KHẢO (RAG KNOWLEDGE):
============================================================
⚠️ QUAN TRỌNG: Đây là KIẾN THỨC Y TẾ THAM KHẢO từ database, 
KHÔNG phải bệnh sử của người dùng.
Chỉ dùng để GIẢI THÍCH và HƯỚNG DẪN. 
KHÔNG được gán các triệu chứng/nhận định trong kiến thức này cho người dùng.
============================================================
{context từ RAG}
============================================================

============================================================
THÔNG TIN TỪ NGƯỜI DÙNG (USER FACTS - CHỈ NHỮNG GÌ HỌ NÓI TRỰC TIẾP):
============================================================
⚠️ QUAN TRỌNG: CHỈ sử dụng những gì người dùng nói trong phần này. 
KHÔNG tự suy ra thêm triệu chứng hoặc nguyên nhân.
============================================================
{user_question}
============================================================
```

---

#### **BƯỚC 12: PHÂN TẦNG TRẢ LỜI (Response Layer)**

```python
# Generate answer với RAG hoặc Gemini
if use_rag and context:
    # Dùng RAG với context
    rag_confidence = docs[0].get("confidence", 0.0) if docs else 0.0
    if rag_mode == "strong":
        # STRONG RAG: Ưu tiên sử dụng RAG context
        response["reply"] = generate_medical_answer(
            context=context,
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up_flag,
            use_rag_priority=True
        )
        response["stage"] = "rag_high_confidence"
    elif rag_mode == "soft":
        # SOFT RAG: Chỉ tham khảo, không ưu tiên
        response["reply"] = generate_medical_answer(
            context=context,
            user_question=cleaned_input,
            intent=intent,
            conversation_history=conversation_history,
            is_follow_up=is_follow_up_flag,
            use_rag_priority=False  # Không ưu tiên, chỉ tham khảo
        )
        response["stage"] = "rag_soft_confidence"
else:
    # Không có RAG → dùng Gemini tự do
    response["reply"] = generate_medical_answer(
        context="",
        user_question=cleaned_input,
        intent=intent,
        conversation_history=conversation_history,
        is_follow_up=is_follow_up_flag,
        use_rag_priority=False
    )
    response["stage"] = "gemini_fallback"
```

**Logic phân tầng:**

1. **STRONG RAG** (rag_mode="strong", use_rag_priority=True):
   - RAG confidence >= threshold (0.80 cho symptom, 0.75 cho advisory)
   - Dùng 3-5 đoạn từ RAG
   - Gemini được yêu cầu **ưu tiên** sử dụng context này
   - Stage: `rag_high_confidence`

2. **SOFT RAG** (rag_mode="soft", use_rag_priority=False):
   - RAG confidence trong khoảng [soft_threshold, strong_threshold)
   - Dùng 1-2 đoạn từ RAG (chỉ tham khảo)
   - Gemini không ưu tiên RAG, chỉ tham khảo
   - Stage: `rag_soft_confidence`

3. **Gemini Fallback** (use_rag=False):
   - Không có context từ RAG hoặc confidence quá thấp
   - Gemini tự do sử dụng kiến thức của nó
   - Stage: `gemini_fallback`

**Safety layer (bổ sung):**
```python
if risk == "high" or (intent_conf < 0.5):
    safety_message = "⚠️ Tôi khuyên bạn nên đi gặp bác sĩ..."
    response["reply"] = safety_message + response["reply"]
    response["stage"] = "safety_recommendation"
```

---

#### **BƯỚC 13: GENERATE ANSWER (Gemini API)**

**Hàm `generate_medical_answer()` xây dựng prompt với tách bạch rõ ràng:**

1. **System Instruction** (với nguyên tắc tách bạch):
   - 🔒 NGUYÊN TẮC CỐT LÕI - TÁCH BẠCH THÔNG TIN
   - USER FACTS: CHỈ sử dụng những gì người dùng NÓI TRỰC TIẾP
   - RAG KNOWLEDGE: Dùng để GIẢI THÍCH, KHÔNG GÁN cho user
   - TUYỆT ĐỐI KHÔNG: Tự suy ra triệu chứng, gán RAG cho user

2. **Cấu trúc prompt:**
   ```
   ============================================================
   LỊCH SỬ CUỘC TRÒ CHUYỆN TRƯỚC ĐÓ:
   ============================================================
   {conversation_history}
   ============================================================
   
   ============================================================
   KIẾN THỨC Y TẾ THAM KHẢO (RAG KNOWLEDGE):
   ============================================================
   ⚠️ QUAN TRỌNG: Đây là KIẾN THỨC Y TẾ THAM KHẢO từ database, 
   KHÔNG phải bệnh sử của người dùng.
   ============================================================
   {context từ RAG}
   ============================================================
   
   ============================================================
   THÔNG TIN TỪ NGƯỜI DÙNG (USER FACTS):
   ============================================================
   ⚠️ QUAN TRỌNG: CHỈ sử dụng những gì người dùng nói trong phần này.
   KHÔNG tự suy ra thêm triệu chứng hoặc nguyên nhân.
   ============================================================
   {user_question}
   ============================================================
   ```

3. **Generation Config:**
```python
generation_config = genai.types.GenerationConfig(
    temperature=0.7,  # Cân bằng giữa sáng tạo và chính xác
    top_p=0.9,  # Tập trung vào tokens có xác suất cao
    top_k=40,  # Chọn từ top 40 tokens
    max_output_tokens=2048  # Tối đa 2048 tokens
)
```

4. **Model:**
- Sử dụng `gemini-2.5-flash` (nhanh, quota tốt: 15 RPM, 250K TPM)
- Có thể đổi sang `gemini-2.5-pro` (chất lượng cao hơn nhưng chậm hơn)

5. **Xử lý response:**
- Loại bỏ markdown formatting (**, *, #)
- Giữ lại bullet points (dấu * ở đầu dòng)
- Trả về văn bản thuần túy, tự nhiên

---

#### **BƯỚC 14: CẬP NHẬT CONVERSATION HISTORY**

```python
# Lưu bot reply vào conversation history
if "reply" in response and response["reply"]:
    history_list = state.get("conversation_history", [])
    # Tìm entry cuối cùng (câu hỏi hiện tại) và cập nhật reply
    if history_list and history_list[-1][1] is None:
        history_list[-1] = (history_list[-1][0], response["reply"])
    
    # Giữ tối đa 6 cặp Q&A
    if len(history_list) > 6:
        history_list.pop(0)
    state["conversation_history"] = history_list
```

**Lưu ý:**
- User input đã được lưu ở Bước 4 (với reply = None)
- Giờ cập nhật reply sau khi generate xong
- Tự động xóa cặp cũ nhất khi vượt quá 6 cặp

---

#### **BƯỚC 15: TRẢ VỀ RESPONSE**

```python
return {
    "session_id": session_id,
    "reply": "Câu trả lời từ Gemini...",
    "intent": "bao_dau_dau",
    "intent_confidence": 0.998,
    "symptoms": {...},
    "risk": "low",
    "clarification_needed": False,
    "clarification_question": None,
    "sources": [...],  # RAG documents (nếu có)
    "stage": "rag_high_confidence"
}
```

**Response fields:**
- `session_id`: ID của session hiện tại
- `reply`: Câu trả lời chính (hiển thị cho user)
- `intent`: Intent đã được nhận diện
- `intent_confidence`: Độ tin cậy của intent (0.0 - 1.0)
- `symptoms`: Thông tin triệu chứng đã extract
- `risk`: Mức độ nguy hiểm (low/medium/high)
- `clarification_needed`: Có cần hỏi thêm không
- `clarification_question`: Câu hỏi clarification (nếu có)
- `sources`: Danh sách RAG documents (để hiển thị nguồn tham khảo)
- `stage`: Giai đoạn xử lý (validation/clarification/rag_high_confidence/gemini_fallback/safety)

---

## 🔄 QUAY LẠI FRONTEND

Sau khi nhận được response từ backend:

```typescript
// chat-ui.component.ts - send() method

this.chatService.sendMessage(text, sessionId).subscribe({
  next: async (response) => {
    // 1. Tạo assistant message từ response
    const assistantMessage = {
      role: 'assistant' as const,
      content: response.reply  // Lấy nội dung câu trả lời
    };
    
    // 2. Lưu assistant message vào Firebase (có metadata)
    try {
      await this.saveMessageToFirebase(
        assistantMessage, 
        currentHistory.sessionId, 
        user, 
        response  // Truyền cả response để lưu metadata (intent, risk, sources...)
      );
      console.log('✅ Assistant message saved to Firebase');
    } catch (error) {
      console.error('❌ Error saving assistant message:', error);
      // Vẫn tiếp tục hiển thị message trong UI dù lưu Firebase thất bại
    }
    
    // 3. Cập nhật UI - thay thế placeholder "HealthyAI đang suy nghĩ..."
    if (placeholderIndex < this.messages.length && 
        this.messages[placeholderIndex]?.pending) {
      // Thay thế placeholder bằng message thật
      this.messages[placeholderIndex] = assistantMessage;
      
      // Đồng bộ với currentHistory.messages
      if (placeholderIndex < currentHistory.messages.length) {
        currentHistory.messages[placeholderIndex] = assistantMessage;
      }
    } else {
      // Nếu placeholder không còn, kiểm tra duplicate và push mới
      const lastMessage = this.messages[this.messages.length - 1];
      const isDuplicate = lastMessage && 
                          lastMessage.role === 'assistant' && 
                          lastMessage.content === assistantMessage.content;
      
      if (!isDuplicate) {
        this.messages.push(assistantMessage);
        currentHistory.messages.push(assistantMessage);
      }
    }
    
    // 4. Lưu metadata (intent, risk, sources...) để hiển thị sau này
    currentHistory.meta = response;
    this.lastBotMeta = response;
    
    // 5. Cập nhật preview của session (title, lastMessage, timestamp)
    this.updateHistoryPreview(response.reply, currentHistory);
    
    // 6. Cập nhật session trong Firebase
    try {
      await this.saveSessionToFirebase(currentHistory, user);
    } catch (error) {
      console.error('❌ Error saving session to Firebase:', error);
    }
    
    // 7. Đánh dấu không còn đang gửi và scroll xuống cuối
    this.isSending = false;
    this.scrollToBottom();
  },
  
  error: async (error: any) => {
    console.error('Chat API error:', error);
    
    // Xử lý lỗi và hiển thị thông báo phù hợp
    let errorMsg = error?.message || 
                   'Xin lỗi, hệ thống đang bận. Bạn thử gửi lại sau nhé.';
    
    const errorMessage = {
      role: 'assistant' as const,
      content: errorMsg
    };
    
    // Thay thế placeholder bằng error message
    if (this.messages[placeholderIndex]?.pending) {
      this.messages[placeholderIndex] = errorMessage;
    } else {
      this.messages.push(errorMessage);
    }
    
    // Lưu error message vào Firebase
    try {
      await this.saveMessageToFirebase(
        errorMessage, 
        currentHistory.sessionId, 
        user
      );
    } catch (firebaseError) {
      console.error('❌ Error saving error message to Firebase:', firebaseError);
    }
    
    // Hiển thị error message và dừng loading
    this.errorMessage = errorMsg;
    this.isSending = false;
    this.scrollToBottom();
    
    // Nếu là lỗi models chưa ready (503), tự động check lại sau 10s
    if (error?.originalError?.status === 503) {
      setTimeout(() => this.checkModelsReady(), 10000);
    }
  }
});
```

**Điểm quan trọng trong xử lý response:**
- ✅ Lưu cả user message và assistant message vào Firebase
- ✅ Lưu metadata (intent, risk, sources) để hiển thị sau
- ✅ Xử lý duplicate messages để tránh hiển thị trùng lặp
- ✅ Error handling chi tiết với retry logic
- ✅ Cập nhật session preview (title, lastMessage, timestamp)

---

## 🔥 PHẦN 3: FIREBASE INTEGRATION

### 3.1. Lưu trữ Messages

**Cấu trúc dữ liệu trong Firestore:**
```
chatMessages/
  ├── {messageId}/
      ├── userId: string
      ├── userEmail: string
      ├── sessionId: string
      ├── text: string (nội dung message)
      ├── role: "user" | "assistant"
      ├── aiResponse: string (chỉ có khi role = "assistant")
      ├── metadata: {
      │     intent: string,
      │     intentConfidence: number,
      │     risk: "low" | "medium" | "high",
      │     stage: string,
      │     sources: Array
      │   }
      └── timestamp: Timestamp
```

**Lưu ý:**
- `role` field là **bắt buộc** để phân biệt user/assistant
- `aiResponse` chỉ có khi `role = "assistant"` (legacy support)
- `metadata` chứa thông tin từ backend (intent, risk, sources...)

### 3.2. Lưu trữ Sessions

**Cấu trúc:**
```
chatSessions/
  ├── {sessionId}/
      ├── userId: string
      ├── userEmail: string
      ├── sessionId: string
      ├── title: string
      ├── lastMessage: string
      ├── messageCount: number
      ├── createdAt: Timestamp
      └── updatedAt: Timestamp
```

**Quy trình:**
1. Tạo session mới khi `startNewChat()`
2. Cập nhật `lastMessage`, `updatedAt` mỗi khi có message mới
3. Tự động tạo `title` từ user message đầu tiên

---

## 📊 TÓM TẮT CÁC ĐIỂM QUAN TRỌNG

### ✅ Frontend (Angular)

1. **Lưu trữ:**
   - Lưu message vào Firebase **TRƯỚC** khi hiển thị
   - Luôn load messages từ Firebase khi select session (không dùng cache)
   - Xử lý duplicate messages để tránh trùng lặp

2. **UI/UX:**
   - Hiển thị placeholder "HealthyAI đang suy nghĩ..." khi đợi response
   - Tự động scroll xuống cuối khi có message mới
   - Error handling với retry logic

3. **State Management:**
   - Mỗi chat session có `sessionId` riêng
   - Lưu metadata (intent, risk, sources) để hiển thị sau
   - Cập nhật session preview realtime

### ✅ Backend (Python FastAPI)

1. **Models Loading:**
   - Load **một lần** khi server khởi động (không reload mỗi request)
   - Có logging chi tiết từng bước
   - Xử lý MemoryError riêng biệt

2. **Pipeline Logic:**
   - Intent confidence >= 0.998 → search RAG theo intent (tối ưu nhất)
   - Intent confidence < 0.98 hoặc "other"/"unknown" → dùng Gemini tự do
   - Risk = "high" → trả lời ngay, không xử lý tiếp (ưu tiên an toàn)

3. **Memory & Context:**
   - Lưu conversation history (tối đa 6 cặp Q&A)
   - Xử lý follow-up questions ("vẫn thế", "đỡ hơn rồi")
   - Nhớ clarification questions để kết hợp thông tin

4. **Response Strategy:**
   - RAG high confidence (>= 0.7) → trả lời dựa vào RAG data
   - RAG low confidence → dùng Gemini với RAG context
   - Không có RAG → dùng Gemini tự do

### ✅ Firebase Integration

1. **Architecture:**
   - Frontend lưu trực tiếp vào Firestore (backend không lưu)
   - Tránh duplicate bằng cách chỉ frontend lưu
   - Backend chỉ xử lý logic, không lưu data

2. **Data Structure:**
   - Messages: `chatMessages/{messageId}`
   - Sessions: `chatSessions/{sessionId}`
   - Có metadata đầy đủ để query và hiển thị

---

## 🔍 LUỒNG HOẠT ĐỘNG HOÀN CHỈNH (Chi tiết)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER NHẬP MESSAGE                                         │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. FRONTEND: chat-ui.component.ts → send()                  │
│    - Validate input                                          │
│    - Tạo userMessage object                                 │
│    - Lưu vào Firebase TRƯỚC                                 │
│    - Hiển thị trong UI                                       │
│    - Hiển thị placeholder "HealthyAI đang suy nghĩ..."      │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. FRONTEND: ChatService → sendMessage()                    │
│    - HTTP POST → /api/chat                                  │
│    - Payload: { message, session_id, user_id }             │
│    - Timeout: 120 giây                                      │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. BACKEND: api_server.py → /api/chat                       │
│    - Kiểm tra models đã sẵn sàng                            │
│    - Validate payload                                        │
│    - Gọi run_chat_pipeline()                                │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. BACKEND: chatbot.py → run_chat_pipeline()                │
│    ├─ BƯỚC 1: Validation                                    │
│    ├─ BƯỚC 2: Pending Flow (xử lý xác nhận đổi chủ đề)     │
│    ├─ BƯỚC 3: Intent Classification (PhoBERT)               │
│    ├─ BƯỚC 4: Follow-up & Topic Shift Detection             │
│    ├─ BƯỚC 5: Intent Continuity Guard (giữ intent khi follow-up)│
│    ├─ BƯỚC 6: Intent Lock (GPT-like stabilization)         │
│    ├─ BƯỚC 7: Pending Intent (tạo pending khi mơ hồ)       │
│    ├─ BƯỚC 8: Symptom Extraction & Risk Estimation          │
│    ├─ BƯỚC 9: Risk Layer (nếu high → return ngay)           │
│    ├─ BƯỚC 10: Clarification Layer                         │
│    ├─ BƯỚC 11: RAG Guard (tránh RAG sai chủ đề)            │
│    ├─ BƯỚC 12: RAG Retrieval với Gate Logic theo Intent     │
│    ├─ BƯỚC 13: Lấy Health Profile (nếu có user_id)        │
│    ├─ BƯỚC 14: Xây dựng Conversation History                │
│    ├─ BƯỚC 15: Tách bạch USER FACTS và RAG KNOWLEDGE        │
│    ├─ BƯỚC 16: Generate Answer (Gemini API)                 │
│    └─ BƯỚC 17: Cập nhật Conversation History                │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. BACKEND: Trả về Response                                 │
│    {                                                         │
│      session_id, reply, intent, intent_confidence,          │
│      symptoms, risk, sources, stage, ...                    │
│    }                                                         │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. FRONTEND: Xử lý Response                                 │
│    - Thay placeholder bằng response.reply                   │
│    - Lưu assistant message vào Firebase                     │
│    - Lưu metadata (intent, risk, sources)                   │
│    - Cập nhật session preview                               │
│    - Scroll xuống cuối                                      │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. HIỂN THỊ CHO USER                                        │
│    - Message đã được hiển thị                               │
│    - Metadata có thể hiển thị sau (nếu cần)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 CÁC TÌNH HUỐNG ĐẶC BIỆT

### 1. Models chưa sẵn sàng
- Backend trả về 503 với message "Models đang tải..."
- Frontend hiển thị thông báo và tự động retry sau 10 giây
- User vẫn có thể nhập message (sẽ đợi đến khi models ready)

### 2. Request timeout (120s)
- Frontend hiển thị "Request timeout. Models có thể đang xử lý..."
- User có thể gửi lại message
- Backend vẫn tiếp tục xử lý (có thể response sau)

### 3. Risk = "high"
- Backend trả về ngay, không xử lý tiếp
- Message: "⚠️ Mình phát hiện có dấu hiệu nguy hiểm..."
- Khuyên đi khám bác sĩ ngay

### 4. Clarification needed
- Backend hỏi thêm thông tin
- Lưu câu hỏi vào state
- Câu trả lời tiếp theo sẽ kết hợp với câu hỏi trước

### 5. Duplicate messages
- Frontend kiểm tra duplicate trước khi hiển thị
- So sánh bằng `role + content`
- Tránh hiển thị cùng một message nhiều lần

---

## 📝 KẾT LUẬN

Hệ thống chat được thiết kế với kiến trúc **frontend-backend tách biệt**, sử dụng các công nghệ AI tiên tiến:

1. **PhoBERT**: Nhận diện ý định người dùng chính xác
2. **FAISS + SentenceTransformer**: Tìm kiếm thông tin nhanh và chính xác
3. **Google Gemini API**: Tạo câu trả lời tự nhiên và có ngữ cảnh
4. **Firebase Firestore**: Lưu trữ lịch sử chat đáng tin cậy

**Điểm mạnh:**
- ✅ Pipeline xử lý nhiều lớp (validation → intent → RAG → generation)
- ✅ Intent continuity (GPT-like): Giữ intent khi follow-up, xác nhận khi đổi chủ đề
- ✅ RAG gate logic theo loại intent: Ngưỡng cao cho triệu chứng, thấp hơn cho tư vấn
- ✅ Tách bạch USER FACTS và RAG KNOWLEDGE: Không tự suy ra, không gán RAG cho user
- ✅ RAG Guard: Tránh search sai chủ đề khi follow-up
- ✅ Intent lock: Giữ intent ổn định 1-2 lượt khi confidence cao
- ✅ Ưu tiên an toàn (risk layer)
- ✅ Nhớ ngữ cảnh (conversation history)
- ✅ Xử lý lỗi chi tiết
- ✅ UI/UX tốt (placeholder, auto-scroll, retry)

**Hướng phát triển:**
- Nâng cấp symptom extraction lên AI-based thay vì rule-based
- Thêm nhiều intent hơn
- Cải thiện RAG với fine-tuning
- Thêm voice input/output
- Multi-language support

---

**Tài liệu này giải thích chi tiết cách hoạt động của chức năng chat từ frontend đến backend, bao gồm tất cả các bước xử lý, lưu trữ, và hiển thị.**