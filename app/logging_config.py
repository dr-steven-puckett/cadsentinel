# app/logging_config.py
import logging
from pathlib import Path

from app.config import get_settings


def configure_logging() -> None:
    """
    Simple logging setup:

    - Reset any existing handlers on the root logger.
    - Attach a StreamHandler to stdout so logs show in uvicorn's console.
    - Also attach a FileHandler to logs/cadsentinel.log.
    - Use LOG_LEVEL from settings (default INFO).
    """
    settings = get_settings()

    level_name = getattr(settings, "log_level", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)

    root_logger = logging.getLogger()

    # Remove any handlers uvicorn or previous config attached
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "cadsentinel.log", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Optional: prove we configured logging
    root_logger.debug("Logging configured (level=%s)", level_name)
