"""ASGI entrypoint for the chatbot backend.

This module imports the existing `api_server` module and exposes the FastAPI
`app` object for use with `uvicorn` or other ASGI servers.

Usage (development):
  uvicorn backend.main:app --reload --port 8000
"""

try:
    # Reuse existing api_server.app to avoid duplicating initialization logic
    from api_server import app  # type: ignore
except Exception:
    # If import fails, create a minimal FastAPI app to avoid import-time errors
    from fastapi import FastAPI

    app = FastAPI()
