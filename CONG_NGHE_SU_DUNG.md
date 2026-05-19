## 1.3. Các công nghệ được sử dụng

### 1.3.1. Ngôn ngữ Python
Python là ngôn ngữ lập trình bậc cao, đa năng, được sử dụng rộng rãi trong lĩnh vực trí tuệ nhân tạo, học máy, xử lý dữ liệu lớn và phát triển web. Trong hệ thống chatbot sức khỏe, Python đóng vai trò là ngôn ngữ chính cho toàn bộ backend, bao gồm xây dựng API, xử lý hội thoại, huấn luyện và triển khai mô hình AI.

**Ứng dụng thực tế trong hệ thống:**
- Xây dựng các module AI như phân loại ý định (intent), truy xuất thông tin (retriever), sinh câu trả lời (generator)
- Phát triển API backend với FastAPI
- Tích hợp với các dịch vụ cloud như Google Gemini, Firebase
- Xử lý dữ liệu, huấn luyện mô hình với Pandas, Scikit-learn, PyTorch

**Ưu điểm:**
- Cộng đồng lớn, nhiều thư viện AI/ML mạnh mẽ (PyTorch, Transformers, Pandas, NumPy…)
- Cú pháp rõ ràng, dễ đọc, dễ bảo trì, dễ mở rộng
- Tích hợp tốt với các framework web hiện đại (FastAPI, Flask)
- Được sử dụng rộng rãi trong nghiên cứu và công nghiệp, dễ tuyển dụng nhân sự

**Nhược điểm:**
- Hiệu năng xử lý thấp hơn các ngôn ngữ biên dịch như C++/Java, không phù hợp cho các tác vụ real-time yêu cầu tốc độ cực cao
- Gặp hạn chế về đa luồng do GIL (Global Interpreter Lock)
- Quản lý bộ nhớ kém hơn các ngôn ngữ thấp cấp

**So sánh:**
- Python vượt trội về AI/ML so với PHP, Ruby, nhưng kém hơn Java/C++ về hiệu năng xử lý

---

### 1.3.2. Angular (TypeScript)
Angular là framework front-end mạnh mẽ do Google phát triển, sử dụng TypeScript làm ngôn ngữ chính. Angular hỗ trợ xây dựng các ứng dụng web động, có cấu trúc rõ ràng, dễ mở rộng. Trong hệ thống, Angular được dùng để xây dựng giao diện người dùng, kết nối realtime với backend và Firebase.

**Ứng dụng thực tế trong hệ thống:**
- Xây dựng giao diện chat, quản lý lịch sử hội thoại, nhắc nhở uống thuốc
- Tích hợp xác thực người dùng, realtime database với Firebase
- Kết nối API backend để gửi/nhận dữ liệu hội thoại

**Ưu điểm:**
- Kiến trúc component rõ ràng, dễ bảo trì, mở rộng, phù hợp cho dự án lớn
- Hỗ trợ TypeScript giúp phát hiện lỗi sớm, code an toàn hơn, dễ refactor
- Cộng đồng lớn, nhiều tài nguyên, tài liệu, nhiều thư viện UI hỗ trợ
- Tích hợp tốt với các dịch vụ Firebase, REST API, hỗ trợ PWA

**Nhược điểm:**
- Độ phức tạp cao, đường cong học tập lớn với người mới
- Bundle lớn, thời gian khởi tạo dự án lâu hơn React/Vue
- Cấu hình ban đầu phức tạp hơn các framework nhẹ

**So sánh:**
- Angular mạnh về enterprise, quản lý state tốt hơn Vue, nhưng học khó hơn React

---

### 1.3.3. FastAPI
FastAPI là framework Python hiện đại dùng để xây dựng API RESTful, nổi bật với tốc độ xử lý nhanh, hỗ trợ async/await, tự động sinh tài liệu API (Swagger, OpenAPI). Trong hệ thống, FastAPI là nền tảng cho toàn bộ backend, cung cấp các endpoint phục vụ giao tiếp giữa frontend và các module AI.

**Ứng dụng thực tế trong hệ thống:**
- Xây dựng các endpoint như /chat, /reminder, /train, /health-check
- Tích hợp xác thực, kiểm tra dữ liệu đầu vào với Pydantic
- Tự động sinh tài liệu API giúp frontend và tester dễ dàng tích hợp

**Ưu điểm:**
- Hiệu năng cao, hỗ trợ bất đồng bộ (asynchronous), phù hợp cho các hệ thống AI cần xử lý song song nhiều request
- Tự động sinh tài liệu API, dễ kiểm thử, tiết kiệm thời gian phát triển
- Tích hợp tốt với Pydantic cho kiểm tra dữ liệu đầu vào, giảm lỗi runtime
- Cộng đồng phát triển đang tăng trưởng mạnh, nhiều ví dụ thực tế

**Nhược điểm:**
- Cộng đồng nhỏ hơn so với Flask/Django, một số extension chưa đa dạng
- Đôi khi gặp khó khăn khi tích hợp với các hệ thống cũ hoặc các thư viện không hỗ trợ async

**So sánh:**
- FastAPI nhanh hơn Flask, dễ dùng hơn Django cho API thuần, nhưng không mạnh về web template như Django

---

### 1.3.4. Uvicorn (ASGI Server)
Uvicorn là web server ASGI nhẹ, hiệu năng cao, được dùng để chạy ứng dụng FastAPI trong môi trường production hoặc phát triển.

**Ứng dụng thực tế trong hệ thống:**
- Khởi chạy API server cho chatbot: `uvicorn api_server:app --reload --port 8000`
- Tiếp nhận và phân phối request từ frontend đến các endpoint FastAPI

**Ưu điểm:**
- Nhẹ, tốc độ cao, hỗ trợ async tốt
- Cấu hình đơn giản, dễ tích hợp với FastAPI

**Nhược điểm:**
- Khi triển khai production quy mô lớn thường cần kết hợp thêm reverse proxy (Nginx) để tối ưu bảo mật và hiệu năng

---

### 1.3.5. PyTorch và Transformers
PyTorch là thư viện học sâu (deep learning) mã nguồn mở, còn Transformers là bộ thư viện của Hugging Face cung cấp các mô hình ngôn ngữ hiện đại (BERT, PhoBERT, GPT, v.v.). Trong dự án, PyTorch và Transformers là nền tảng để huấn luyện và suy luận mô hình phân loại ý định (intent classifier) dựa trên PhoBERT.

**Ứng dụng thực tế trong hệ thống:**
- Tải và fine-tune mô hình PhoBERT cho tác vụ phân loại intent người dùng
- Suy luận (inference) nhanh trên server khi có câu hỏi mới
- Lưu và nạp lại checkpoint mô hình trong thư mục `model/intent_model`

**Ưu điểm:**
- Hỗ trợ tốt GPU, tối ưu cho bài toán deep learning
- Cộng đồng rất lớn, tài liệu, ví dụ phong phú
- Transformers cung cấp sẵn nhiều mô hình pretrained, dễ fine-tune cho tiếng Việt

**Nhược điểm:**
- Cần tài nguyên phần cứng tốt (RAM, GPU) nếu mô hình lớn
- Độ phức tạp cao hơn so với các thư viện ML truyền thống (Scikit-learn)

---

### 1.3.6. PhoBERT (BERT tiếng Việt)
PhoBERT là mô hình ngôn ngữ tiền huấn luyện (pretrained) dựa trên BERT, tối ưu cho tiếng Việt, được sử dụng để phân loại ý định (intent classification) trong hệ thống. PhoBERT giúp chatbot hiểu chính xác câu hỏi, nhu cầu của người dùng tiếng Việt.

**Ứng dụng thực tế trong hệ thống:**
- Phân loại ý định người dùng: hỏi triệu chứng, tư vấn dinh dưỡng, nhắc nhở uống thuốc...
- Đầu vào cho pipeline RAG và sinh câu trả lời
- Fine-tune trên tập dữ liệu thực tế để tăng độ chính xác

**Ưu điểm:**
- Hiệu quả cao cho các tác vụ NLP tiếng Việt, vượt trội so với các model đa ngôn ngữ
- Có thể fine-tune cho nhiều bài toán khác nhau (intent, sentiment, NER...)
- Được cộng đồng nghiên cứu Việt Nam phát triển và hỗ trợ, nhiều tài liệu tham khảo

**Nhược điểm:**
- Yêu cầu tài nguyên lớn khi huấn luyện và suy luận (RAM, GPU)
- Không tối ưu cho các ngôn ngữ khác ngoài tiếng Việt
- Kích thước model lớn, thời gian load lâu nếu không tối ưu

**So sánh:**
- PhoBERT tốt hơn mBERT, XLM-R cho tiếng Việt, nhưng không dùng được cho tiếng Anh hoặc đa ngôn ngữ

---

### 1.3.7. Sentence-BERT (Vietnamese SBERT)
Sentence-BERT là mô hình embedding câu, giúp chuyển đổi văn bản thành vector ngữ nghĩa, tối ưu cho tiếng Việt. SBERT giúp chatbot hiểu sâu ý nghĩa câu hỏi và tài liệu, tăng độ chính xác khi truy xuất thông tin.

**Ứng dụng thực tế trong hệ thống:**
- Sinh embedding cho câu hỏi người dùng và các đoạn tài liệu y tế
- Làm đầu vào cho FAISS để tìm kiếm semantic
- Hỗ trợ các tác vụ so khớp ngữ nghĩa, phân cụm, phân loại

**Ưu điểm:**
- Sinh embedding chất lượng cao cho tiếng Việt, tăng độ chính xác semantic search
- Tối ưu cho các tác vụ RAG, semantic retrieval
- Có thể fine-tune cho các bài toán đặc thù

**Nhược điểm:**
- Model lớn, cần RAM/CPU đủ mạnh, thời gian encode lâu với batch lớn
- Không tốt cho các ngôn ngữ ngoài phạm vi huấn luyện
- Cần quản lý bộ nhớ khi xử lý dữ liệu lớn

**So sánh:**
- SBERT tốt hơn các phương pháp TF-IDF, BM25 về hiểu ngữ nghĩa, nhưng chậm hơn khi scale lớn

---

### 1.3.8. FAISS
FAISS (Facebook AI Similarity Search) là thư viện mã nguồn mở tối ưu cho tìm kiếm vector, dùng để xây dựng hệ thống truy xuất thông tin (RAG) trong chatbot. FAISS giúp tìm kiếm nhanh các đoạn văn bản liên quan trong cơ sở tri thức y tế.

**Ứng dụng thực tế trong hệ thống:**
- Lưu trữ và tìm kiếm vector embedding của các tài liệu y tế
- Truy xuất top-k đoạn văn bản liên quan đến câu hỏi người dùng
- Kết hợp với Sentence-BERT để tăng độ chính xác semantic search

**Ưu điểm:**
- Tìm kiếm vector nhanh, tối ưu cho CPU, không cần GPU
- Dễ tích hợp với Python, open-source, tài liệu đầy đủ
- Hỗ trợ nhiều loại index (Flat, IVFFlat, HNSW...), mở rộng tốt cho big data

**Nhược điểm:**
- Không hỗ trợ phân tán native (phải tự triển khai nếu muốn scale out)
- Cần hiểu rõ về vector search để tối ưu hiệu năng và bộ nhớ
- Không phù hợp cho các bài toán search phi tuyến tính hoặc dữ liệu phi cấu trúc

**So sánh:**
- FAISS nhanh hơn Annoy, Milvus cho bài toán nhỏ/trung bình, nhưng Milvus mạnh hơn khi cần phân tán lớn

---

### 1.3.9. RAG (Retrieval-Augmented Generation)
RAG là kiến trúc kết hợp giữa truy xuất thông tin (retrieval) và sinh ngôn ngữ tự nhiên (generation), giúp chatbot trả lời chính xác, tự nhiên dựa trên tri thức thực tế. Trong hệ thống, RAG sử dụng Sentence-BERT để chuyển đổi câu hỏi và tài liệu thành vector, FAISS để tìm kiếm các đoạn văn bản liên quan, sau đó kết hợp với Google Gemini để sinh câu trả lời cuối cùng.

**Ứng dụng thực tế trong hệ thống:**
- Khi người dùng đặt câu hỏi, hệ thống sẽ:
  1. Phân loại ý định (PhoBERT)
  2. Dùng SBERT + FAISS để truy xuất top-k đoạn văn bản y tế liên quan
  3. Kết hợp thông tin truy xuất với ngữ cảnh hội thoại, gửi vào Gemini để sinh câu trả lời tự nhiên, chính xác
- Đảm bảo câu trả lời vừa dựa trên tri thức thực tế, vừa linh hoạt, tự nhiên như con người

**Ưu điểm:**
- Kết hợp điểm mạnh của retrieval (chính xác, dựa trên tri thức thực tế) và generation (tự nhiên, linh hoạt)
- Giảm rủi ro "hallucination" của LLM, tăng độ tin cậy cho chatbot y tế
- Dễ mở rộng, cập nhật tri thức mới chỉ cần cập nhật dữ liệu truy xuất

**Nhược điểm:**
- Pipeline phức tạp hơn so với chỉ dùng retrieval hoặc chỉ dùng LLM
- Đòi hỏi tối ưu hóa đồng thời nhiều thành phần (embedding, index, prompt)
- Độ trễ có thể tăng nếu dữ liệu truy xuất lớn hoặc LLM trả lời chậm

**So sánh:**
- RAG vượt trội so với QA truyền thống (chỉ retrieval) về độ tự nhiên, và an toàn hơn so với chỉ dùng LLM về độ chính xác tri thức

---

### 1.3.10. Google Gemini API
Google Gemini là dịch vụ AI tạo sinh (LLM) của Google, được sử dụng để sinh câu trả lời tự nhiên cho chatbot. Gemini giúp chatbot trả lời linh hoạt, tự nhiên, có thể tổng hợp thông tin từ nhiều nguồn.

**Ứng dụng thực tế trong hệ thống:**
- Sinh câu trả lời dựa trên ngữ cảnh hội thoại và thông tin truy xuất từ RAG
- Tùy chỉnh prompt để phù hợp với lĩnh vực y tế, đảm bảo an toàn thông tin
- Tối ưu chi phí bằng cách chọn model phù hợp (2.5-flash, 2.0-flash-lite...)

**Ưu điểm:**
- Không cần GPU local, tốc độ phản hồi nhanh, dễ tích hợp qua API
- Chất lượng sinh ngôn ngữ tự nhiên tốt, hỗ trợ tiếng Việt
- Quota miễn phí cao, nhiều lựa chọn model phù hợp nhu cầu
- Có thể cấu hình temperature, top-p, top-k để kiểm soát output

**Nhược điểm:**
- Phụ thuộc vào cloud, cần internet ổn định, có thể bị giới hạn khi hết quota hoặc API thay đổi
- Dữ liệu gửi lên cloud cần đảm bảo bảo mật, tuân thủ quy định y tế
- Không kiểm soát hoàn toàn model như khi dùng LLM local

**So sánh:**
- Gemini nhanh hơn GPT-4 API, chi phí thấp hơn, nhưng ít tính năng nâng cao hơn OpenAI

---

### 1.3.11. Firebase (Firestore)
Firebase là nền tảng BaaS của Google, Firestore là dịch vụ cơ sở dữ liệu realtime, dùng để lưu trữ hội thoại, nhắc nhở uống thuốc, quản lý người dùng.

**Ứng dụng thực tế trong hệ thống:**
- Lưu trữ lịch sử hội thoại, nhắc nhở uống thuốc, thông tin người dùng
- Đồng bộ realtime với frontend Angular
- Tích hợp xác thực, phân quyền, bảo mật dữ liệu

**Ưu điểm:**
- Realtime database, đồng bộ nhanh giữa các client
- Dễ tích hợp với web/mobile, nhiều SDK hỗ trợ
- Có sẵn authentication, security rules, dễ mở rộng
- Hỗ trợ tốt cho các ứng dụng cần realtime, push notification

**Nhược điểm:**
- Chi phí tăng nhanh nếu scale lớn, nhiều người dùng đồng thời
- Một số query phức tạp bị giới hạn, không tối ưu cho analytics lớn
- Phụ thuộc vào hạ tầng Google, khó migrate sang hệ khác

**So sánh:**
- Firestore dễ dùng hơn MongoDB Atlas cho realtime, nhưng không mạnh về query phức tạp như PostgreSQL

---

### 1.3.12. Firebase Admin SDK và Google Auth
Firebase Admin SDK và bộ thư viện Google Auth được sử dụng ở phía backend để kết nối an toàn tới Firestore, xử lý xác thực dịch vụ (service account), đọc/ghi dữ liệu hội thoại và nhắc nhở uống thuốc.

**Ứng dụng thực tế trong hệ thống:**
- Khởi tạo kết nối Firestore từ phía server Python thông qua file service account
- Thao tác CRUD với các collection như `conversations`, `medicine_reminders`, `users`
- Đảm bảo kết nối giữa server và Firebase an toàn, có kiểm soát quyền truy cập

**Ưu điểm:**
- Cung cấp API chính thức, ổn định từ Google
- Tích hợp chặt chẽ với hệ sinh thái Firebase/Google Cloud

**Nhược điểm:**
- Cần quản lý cẩn thận file khóa dịch vụ (serviceAccountKey.json) để tránh lộ thông tin
- Phụ thuộc vào phiên bản thư viện và chính sách bảo mật của Google

---

### 1.3.13. Scheduler nhắc nhở uống thuốc
Hệ thống sử dụng một tiến trình scheduler đơn giản viết bằng Python (kết hợp `time`, `datetime` và thư viện `requests`) để định kỳ gọi API kiểm tra và gửi nhắc nhở uống thuốc.

**Ứng dụng thực tế trong hệ thống:**
- Script `medicine_reminder_scheduler.py` chạy mỗi 60 giây
- Gửi request tới endpoint `/api/medicine-reminders/check` của FastAPI
- Nếu có nhắc nhở đến giờ, server sẽ ghi nhận và gửi thông báo tương ứng (qua Firebase hoặc kênh cấu hình sẵn)

**Ưu điểm:**
- Cách triển khai đơn giản, dễ hiểu, phù hợp với quy mô hệ thống hiện tại
- Dễ thay thế bằng cron job, Windows Task Scheduler hoặc dịch vụ scheduler trên cloud

**Nhược điểm:**
- Chỉ chạy được khi tiến trình Python còn hoạt động; nếu server hoặc máy chủ tắt, scheduler sẽ dừng
- Không tối ưu cho quy mô rất lớn hoặc yêu cầu độ sẵn sàng 24/7, khi đó nên dùng các dịch vụ scheduler chuyên dụng (Cloud Scheduler, Celery Beat, v.v.)

---

