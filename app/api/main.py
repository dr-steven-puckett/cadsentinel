# app/api/main.py

from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import setup_logging

# Initialize settings and logging once at import time
settings = get_settings()
setup_logging()

app = FastAPI(
    title="CadSentinel DWG Pipeline",
    version="0.1.0",
    description="Backend service for DWG → JSON → embeddings and drawing analysis.",
)


@app.get("/health", tags=["system"])
def health_check():
    """
    Simple health check endpoint to verify that the app is running
    and configuration can be loaded.
    """
    return {
        "status": "ok",
        "app": "cadsentinel",
        "log_level": settings.log_level,
    }


# Routers will be included in later phases:
# from app.api.routers import ingest, drawings, search, chat, standards
# app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
# app.include_router(drawings.router, prefix="/drawings", tags=["drawings"])
# app.include_router(search.router, prefix="/search", tags=["search"])
# app.include_router(chat.router, prefix="/chat", tags=["chat"])
# app.include_router(standards.router, prefix="/standards", tags=["standards"])
