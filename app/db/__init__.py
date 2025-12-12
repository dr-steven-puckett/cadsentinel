# app/db/__init__.py

from .base import Base
from .session import SessionLocal, get_db  # optional, but convenient
from . import models  # noqa: F401  # ensure models are imported so Base.metadata is populated

__all__ = [
    "Base",
    "SessionLocal",
    "get_db",
    "models",
]
