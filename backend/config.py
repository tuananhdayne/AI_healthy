"""Backend configuration helper.

Loads configuration from environment variables and provides defaults.
"""
from typing import List
import os


def get_allowed_origins() -> List[str]:
    value = os.environ.get("ALLOWED_ORIGINS")
    if not value:
        return ["*"]
    return [o.strip() for o in value.split(",") if o.strip()]


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)
