# Kiến trúc tổng quan

Repository chứa 3 phần chính:

- Frontend: `AI-Web/` (Angular app, riêng biệt).
- Backend: nhiều script Python tại root (ví dụ `chatbot.py`, `api_server.py`, `firestore_service.py`).
- Data & Models: `model/`, `embeddings/`, `data/`, `data_train/`.

Khuyến nghị nhanh:

1. Bảo mật: Xóa `serviceAccountKey.json` khỏi git history và lưu trữ bí mật bằng secret manager; thêm vào `.gitignore` (đã có).
2. Di chuyển mã backend vào package Python chuẩn, ví dụ `backend/` hoặc `src/app/`, với `__init__.py` và entrypoint (ASGI/CLI).
3. Di chuyển scripts tiện ích vào `scripts/` để root gọn.
4. Lưu trữ mô hình/embeddings ngoài git (S3/GCS) hoặc dùng `git-lfs` nếu bắt buộc.
5. Thêm `env.example` (đã có) và hướng dẫn cài đặt nhanh trong `README.md`.
6. Thêm CI để chạy test/lint tự động.

Tiếp theo nên ưu tiên: bảo mật (rotate key), `.gitignore`, và scaffold backend package.
