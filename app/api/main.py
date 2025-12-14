from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import configure_logging
from app.config import get_settings

from app.api.routers import ingest
from app.api.routers import drawings
from app.api.routers import search as search_routes
from app.api.routers import chat as chat_routes
from app.api.routers import config as config_routes

# New routers for extended API layer
from app.api.routers import artifacts as artifacts_routes
from app.api.routers import config_models as config_models_routes
from app.api.routers import standards as standards_routes
from app.api.routers import projects as projects_routes
from app.api.routers import customers as customers_routes
from app.api.routers import compliance as compliance_routes
from app.api.routers import bom as bom_routes
from app.api.routers import advanced as advanced_routes
from app.api.routers import customers as customers_router
from app.api.routers import standards as standards_router


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
    allow_origins=["*"],  # TODO: tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (all mounted under /api/v1)
# ---------------------------------------------------------------------------

# Existing core functionality
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(drawings.router, prefix="/api/v1")        # /api/v1/drawings/...
app.include_router(search_routes.router, prefix="/api/v1")   # /api/v1/search/...
app.include_router(chat_routes.router, prefix="/api/v1")     # /api/v1/chat/...
app.include_router(config_routes.router, prefix="/api/v1")   # /api/v1/config/...

# New API surface for frontend
app.include_router(artifacts_routes.router, prefix="/api/v1")
app.include_router(config_models_routes.router, prefix="/api/v1")
app.include_router(standards_routes.router, prefix="/api/v1")
app.include_router(projects_routes.router, prefix="/api/v1")
app.include_router(customers_routes.router, prefix="/api/v1")
app.include_router(compliance_routes.router, prefix="/api/v1")
app.include_router(bom_routes.router, prefix="/api/v1")
app.include_router(advanced_routes.router, prefix="/api/v1")
app.include_router(customers_router.router, prefix="/api/v1")
app.include_router(standards_router.router, prefix="/api/v1")

@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """
    Simple health check endpoint for monitoring / readiness probes.
    """
    return {"status": "ok"}
