from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import configure_logging
from app.config import get_settings
from app.api.routers import ingest, drawings  # ⬅ add drawings
from app.api.routers import search as search_routes

logger = logging.getLogger(__name__)

# Configure logging before anything else
configure_logging()
settings = get_settings()

app = FastAPI(
    title="CadSentinel DWG Pipeline",
    version="0.1.0",
    description="DWG → DXF/PDF/PNG/JSON → embeddings pipeline for CadSentinel.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ingest.router)
app.include_router(drawings.router)  # ⬅ exposes /drawings/summarize
app.include_router(search_routes.router)

@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {"status": "ok"}


