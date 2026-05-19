# Backend package

This package exposes an ASGI application for the chatbot backend.

Run development server:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Notes:
- The existing `api_server.py` implements the full FastAPI app and startup logic.
- `backend.main` imports and re-exports `api_server.app` to provide a clean package entrypoint.
