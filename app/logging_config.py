# app/logging_config.py

import logging
import sys

from app.config import get_settings


def setup_logging() -> None:
    """
    Configure application-wide logging.

    - Uses LOG_LEVEL from settings (default INFO).
    - Logs to stdout with timestamps and logger names.
    - Idempotent: if handlers already exist, it does nothing.
    """
    settings = get_settings()

    root_logger = logging.getLogger()

    # Avoid duplicate handlers if called multiple times
    if root_logger.handlers:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    # Optional: quiet some noisy third-party loggers if needed later
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

