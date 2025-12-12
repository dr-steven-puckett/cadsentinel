# app/api/routers/config_models.py
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.schemas.config_models import ConfigModelsResponse, ProviderConfig
from app.services.security_mode import (
    get_security_mode,
    get_effective_providers,
)
from app.config import get_settings  # ✅ use your existing config module

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/config", tags=["config"])


@router.get(
    "/models",
    response_model=ConfigModelsResponse,
    summary="Get active and available models",
    description=(
        "Return the current security mode and mapping of active chat/embedding "
        "models for OpenAI and Ollama."
    ),
)
def get_models_config() -> ConfigModelsResponse:
    """
    Surface model configuration for the frontend.

    Uses:
    - get_security_mode() to determine 'secure' vs 'not_secure'
    - get_effective_providers() to determine which provider is active
      for chat and embeddings based on the security mode.
    - Settings to expose the configured model names for each provider.
    """
    security_mode = get_security_mode()
    effective = get_effective_providers()

    logger.debug(
        "Config models requested; security_mode=%s effective_providers=%s",
        security_mode,
        effective,
    )

    # Use getattr with safe defaults in case some settings aren't defined yet
    openai_chat_model = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4.1")
    openai_embedding_model = getattr(
        settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    ollama_chat_model = getattr(settings, "OLLAMA_CHAT_MODEL", "llama3.1")
    ollama_embedding_model = getattr(
        settings, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
    )

    return ConfigModelsResponse(
        security_mode=security_mode,
        active_chat_model=effective["chat"],
        active_embedding_model=effective["embedding"],
        openai=ProviderConfig(
            chat=openai_chat_model,
            embedding=openai_embedding_model,
        ),
        ollama=ProviderConfig(
            chat=ollama_chat_model,
            embedding=ollama_embedding_model,
        ),
    )
