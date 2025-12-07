import logging
import sys
from app.config import get_settings

def setup_logging() -> None:
    settings = get_settings()

    root = logging.getLogger()
    if root.handlers:
        # Avoid adding multiple handlers if called more than once
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

