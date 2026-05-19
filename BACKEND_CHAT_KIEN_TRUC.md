# Kiến trúc backend chức năng chat

## 1. Tổng quan

Backend chatbot được triển khai bằng FastAPI, chia thành các lớp chính:
- Lớp API: nhận request từ frontend, trả response JSON.
- Lớp pipeline hội thoại: xử lý intent, ngữ cảnh, triệu chứng, mức độ nguy cơ, RAG.
- Lớp model: phân loại intent, truy xuất tri thức (RAG), sinh câu trả lời (Gemini).
- Lớp logic ứng dụng: các hàm xử lý follow-up, topic shift, câu hỏi làm rõ, v.v.

## 2. Các file backend liên quan đến chức năng chat

### 2.1 api_server.py – Cổng API cho frontend

- Khởi tạo server FastAPI cho toàn bộ hệ thống chatbot.
- Cấu hình CORS để web Angular có thể gọi API.
- Sự kiện `@app.on_event("startup")` (`load_models`):
  - Khởi tạo Firestore (nếu có).
  - Import các module logic: `response_layer`, `symptom_extractor`, `risk_estimator`.
  - Load `IntentClassifier` (PhoBERT) từ thư mục `model/intent_model`.
  - Load `Retriever` RAG từ thư mục `rag`/`embeddings`.
  - Kiểm tra kết nối Gemini API (hàm `_get_model` trong `generator/gemini_generator.py`).
  - Gán các model đã load vào module `chatbot.py` và test nhanh pipeline.
- Định nghĩa các endpoint chính:
  - `GET /health`: kiểm tra server sống.
  - `GET /ready`: kiểm tra models đã load xong chưa.
  - `POST /api/chat`: nhận câu hỏi từ frontend, gọi `run_chat_pipeline`, trả về câu trả lời cùng metadata.

### 2.2 chatbot.py – Trái tim của pipeline hội thoại

- Quản lý model và trạng thái hội thoại:
  - Biến toàn cục: `intent_classifier`, `retriever`, `_models_initialized`.
  - Biến trạng thái hội thoại: `conversation_states[session_id]` lưu:
    - `last_intent`: intent lần trước.
    - `last_symptoms`: triệu chứng lần trước.
    - `conversation_history`: lịch sử hội thoại (user, bot).
    - `intent_lock`: khóa intent tạm thời để ổn định chủ đề.
    - `pending_intent`, `pending_from_intent`, `pending_type`: dùng cho flow xác nhận đổi chủ đề.
- Các hàm chính:
  - `_ensure_models_loaded()`: đảm bảo đã có `intent_classifier` và `retriever` (lazy loading).
  - `_get_or_create_state(session_id)`: lấy hoặc khởi tạo state cho mỗi phiên chat.
  - `reset_conversation(session_id)`: xóa toàn bộ state của một phiên.
  - `run_chat_pipeline(user_input, session_id="default", user_id=None)`: pipeline xử lý chat:
    1. Chuẩn hóa input, cập nhật `conversation_history`.
    2. Gọi `intent_classifier.predict_topk()` để lấy top-2 intent.
    3. Dùng `response_layer` để phát hiện follow-up, topic shift, và xử lý intent lock / pending:
       - `is_follow_up`, `is_topic_shift`, `parse_switch_confirm`, `get_intent_label`, `get_intent_category`.
    4. Nếu là câu hỏi triệu chứng, gọi:
       - `extract_symptoms` từ `symptom_extractor`.
       - `estimate_risk` từ `risk_estimator`.
    5. Dùng `Retriever` (RAG) để lấy các đoạn văn/bằng chứng liên quan.
    6. Gọi `generate_medical_answer` trong `generator/gemini_generator.py` để sinh câu trả lời y tế dựa trên:
       - Câu hỏi của user.
       - Triệu chứng đã trích xuất.
       - Mức độ nguy cơ.
       - Các đoạn context từ RAG.
    7. Trả về dict kết quả gồm: `reply`, `intent`, `intent_confidence`, `symptoms`, `risk`, `clarification_needed`, `clarification_question`, `sources`, `stage`.

### 2.3 intent/intent_classifier.py – Phân loại intent người dùng

- Load model phân loại intent (PhoBERT) từ `model/intent_model`.
- Cung cấp hàm chính:
  - `predict_topk(text, k=2) -> List[(intent, confidence)]`.
- Được sử dụng trực tiếp trong `chatbot.py` để xác định ý định chính của câu hỏi.

### 2.4 rag/retriever.py – Lấy kiến thức theo RAG

- Quản lý:
  - FAISS index các vector embedding.
  - SentenceTransformer dùng để mã hóa câu hỏi.
- Cung cấp API tìm kiếm các đoạn văn y khoa liên quan đến câu hỏi/triệu chứng.
- Được sử dụng trong `chatbot.py` để lấy `sources` (bằng chứng) cho câu trả lời và làm input cho Gemini.

### 2.5 generator/gemini_generator.py – Sinh câu trả lời bằng Gemini

- Cấu hình truy cập Gemini API (hàm `_get_model`).
- Cung cấp các hàm sinh câu trả lời, tiêu biểu:
  - `generate_medical_answer(...)`: sinh câu trả lời y tế cho hội thoại chat.
- Được sử dụng:
  - Trong `chatbot.py` để sinh `reply` cuối cùng cho user.
  - Trong `api_server.py` cho các endpoint gợi ý tập luyện/dinh dưỡng dựa trên profile sức khỏe.

### 2.6 app/response_layer.py – Tầng logic hội thoại

- Chứa các hàm quyết định luồng hội thoại dựa trên ngữ cảnh:
  - `need_more_info(...)`: kiểm tra đã đủ thông tin để tư vấn chưa.
  - `build_clarification_question(...)`: xây dựng câu hỏi làm rõ khi thông tin chưa đủ.
  - `is_follow_up(...)`: nhận diện câu hỏi tiếp nối chủ đề trước.
  - `is_topic_shift(...)`: nhận diện user đổi sang chủ đề mới.
  - `parse_switch_confirm(...)`: phân tích câu trả lời xác nhận khi hệ thống hỏi "giữ hay chuyển chủ đề".
  - `get_intent_label(...)`: chuyển intent code sang nhãn tiếng Việt dễ hiểu.
  - `get_intent_category(...)`: phân loại intent (triệu chứng, tư vấn, khác...).
  - `get_rag_gate_thresholds(...)`: cung cấp ngưỡng quyết định khi nào bật/tắt RAG.
- Được dùng rất nhiều trong `chatbot.py` để:
  - Quyết định giữ intent cũ, đổi intent hay yêu cầu người dùng xác nhận.
  - Quyết định xem có cần hỏi thêm hay đã đủ thông tin để tư vấn.

### 2.7 app/symptom_extractor.py – Trích xuất triệu chứng

- Đầu vào: câu tiếng Việt mô tả triệu chứng.
- Đầu ra: cấu trúc dữ liệu chứa:
  - Danh sách triệu chứng.
  - Thời gian xuất hiện, kéo dài.
  - Mức độ, tần suất, các thuộc tính liên quan.
- Được sử dụng trong `chatbot.py` để bổ sung dữ liệu y khoa cho RAG và Gemini.

### 2.8 app/risk_estimator.py – Ước lượng mức độ nguy cơ

- Nhận đầu vào là `symptoms` đã được trích xuất.
- Ước lượng:
  - Mức độ nguy cơ (nhẹ/vừa/nặng).
  - Gợi ý nên theo dõi tại nhà hay cần đi khám ngay.
- Kết quả được đưa vào response để user hiểu mức độ nghiêm trọng.

### 2.9 Các file app khác

- `app/intent_decider.py`, `app/intent_router.py`, `app/medicine_time_parser.py`:
  - Hỗ trợ thêm cho việc:
    - Ra quyết định intent phức tạp hơn.
    - Phân tuyến logic theo nhóm intent.
    - Phân tích thời gian dùng thuốc (nếu bạn mở rộng chức năng nhắc uống thuốc qua chat).

## 3. Trình tự luồng xử lý khi người dùng chat

### 3.1 Khởi động backend

1. Chạy lệnh (ví dụ):
   - `uvicorn api_server:app --reload --port 8000`
   - Hoặc chạy script `start_backend.bat` nếu đã cấu hình.
2. Khi server khởi động, hàm `load_models()` trong `api_server.py` được gọi:
   - Khởi tạo Firestore (nếu cấu hình).
   - Import `response_layer`, `symptom_extractor`, `risk_estimator`.
   - Load model phân loại intent (`IntentClassifier`).
   - Load RAG Retriever (`Retriever`).
   - Kiểm tra kết nối Gemini API.
   - Gán các model đã load vào module `chatbot.py` và test nhanh `run_chat_pipeline("xin chào", session_id="startup_test")`.

### 3.2 Frontend kiểm tra server sẵn sàng

- Frontend/web gọi `GET /ready`:
  - Nếu trả về `{"ready": true, ...}` → models đã sẵn sàng, có thể hiển thị giao diện chat cho người dùng.
  - Nếu đang `loading` → hiển thị "Đang tải mô hình, vui lòng đợi".

### 3.3 Người dùng gửi câu hỏi

- Frontend gửi request `POST /api/chat` với JSON:
  - `message`: câu hỏi hoặc mô tả triệu chứng.
  - `session_id`: id phiên chat (nếu muốn giữ ngữ cảnh giữa các lần hỏi). Nếu không gửi, backend tự tạo bằng `uuid4`.
  - `user_id`, `user_email`: dùng để lưu log tại frontend/Firestore (backend không lưu để tránh trùng lặp).

### 3.4 api_server.py chuyển tiếp đến pipeline

- Endpoint `/api/chat` trong `api_server.py`:
  - Kiểm tra `_models_ready` và `_run_chat_pipeline`.
  - Gọi `_run_chat_pipeline(message, session_id=session_id, user_id=user_id)` trỏ tới hàm `run_chat_pipeline` trong `chatbot.py`.

### 3.5 chatbot.py xử lý hội thoại chi tiết

1. Lấy/khởi tạo state phiên chat:
   - `_get_or_create_state(session_id)`.
   - Cập nhật `conversation_history` với câu hỏi mới.
2. Phân loại intent:
   - `intent_classifier.predict_topk(cleaned_input, k=2)` → lấy `intent1, conf1` và `intent2, conf2`.
3. Phân tích ngữ cảnh:
   - `is_follow_up(cleaned_input)`: xem có phải tiếp nối chủ đề cũ không.
   - `is_topic_shift(cleaned_input)`: xem có dấu hiệu đổi chủ đề rõ ràng không.
   - Nếu có trạng thái `pending` (đang chờ xác nhận đổi chủ đề): dùng `parse_switch_confirm` để quyết định giữ hay đổi intent.
4. Áp dụng chiến lược TOP-2, follow-up, topic shift, intent lock:
   - Nếu follow-up → ưu tiên giữ `last_intent`.
   - Nếu topic shift rõ → cho phép đổi sang intent mới.
   - Nếu TOP-2 rất chắc chắn → có thể override chủ đề ngay.
   - Nếu mơ hồ → tạo `pending_intent` và hỏi user xác nhận.
5. Trích xuất triệu chứng và ước lượng nguy cơ (nếu intent thuộc nhóm triệu chứng):
   - `symptoms = extract_symptoms(cleaned_input)`.
   - `risk = estimate_risk(symptoms)`.
6. Gọi RAG Retriever (nếu phù hợp):
   - Dùng `Retriever` để tìm các đoạn văn/bằng chứng y khoa phù hợp với intent và triệu chứng.
7. Sinh câu trả lời bằng Gemini:
   - Gọi `generate_medical_answer(...)` trong `generator/gemini_generator.py`, truyền vào:
     - Câu hỏi gốc của user.
     - Thông tin `symptoms`.
     - Mức `risk`.
     - Danh sách `sources` từ RAG.
   - Nhận về câu trả lời tự nhiên bằng tiếng Việt, an toàn y khoa.
8. Trả về kết quả cho `api_server.py`:
   - Một dict gồm: `reply`, `intent`, `intent_confidence`, `symptoms`, `risk`, `clarification_needed`, `clarification_question`, `sources`, `stage`.

### 3.6 api_server.py trả JSON cho frontend

- `api_server.py` nhận `response` từ `run_chat_pipeline`, gán thêm `session_id` nếu cần.
- Trả JSON về cho frontend qua endpoint `/api/chat`.
- Frontend hiển thị:
  - Câu trả lời `reply`.
  - Có thể hiển thị thêm nguồn tham khảo `sources`, mức nguy cơ `risk`, hoặc câu hỏi làm rõ `clarification_question` nếu có.

---

Tài liệu này mô tả đầy đủ các file backend liên quan đến chức năng chat, vai trò của từng file và trình tự luồng xử lý từ lúc khởi động server đến khi trả lời người dùng. Bạn có thể dùng nguyên văn (hoặc chỉnh sửa nhẹ) cho phần "Thiết kế/kiến trúc backend chatbot" trong báo cáo hoặc tài liệu dự án.