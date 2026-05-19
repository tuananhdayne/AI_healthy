"""Backend package for the project.

This package provides a stable import point for ASGI servers and other tooling.
"""

__all__ = ["app"]

from .main import app
