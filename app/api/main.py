# app/api/main.py
from __future__ import annotations

import logging
from app.logging_config import configure_logging   # ✅ import this


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routers import ingest  # add other routers here as we build them

logger = logging.getLogger(__name__)
# ✅ configure logging BEFORE doing anything else
configure_logging()
settings = get_settings()

app = FastAPI(
    title="CadSentinel DWG Pipeline",
    version="0.1.0",
    description="DWG → DXF/PDF/PNG/JSON → embeddings pipeline for CadSentinel.",
)

# CORS – later we can restrict to your Vercel domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ingest.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """
    Simple health endpoint so Vercel / monitoring can check liveness.
    """
    return {"status": "ok"}

