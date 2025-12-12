from __future__ import annotations

from typing import Sequence, List

import httpx
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.security_mode import get_effective_providers

settings = get_settings()

# Determine current embedding model name based on security mode (OpenAI vs Ollama)
def get_current_embedding_model_name() -> str:
    providers = get_effective_providers()
    provider = providers["embedding"].lower()

    if provider == "openai":
        # Standard OpenAI embedding model
        return settings.openai_embedding_model
    elif provider == "ollama":
        # Local model name for Ollama; fallback string if not set
        return settings.ollama_embedding_model or "ollama-embedding"
    else:
        return "unknown"


# Backwards-compatible constant used by ETL when inserting Embedding.model_name
EMBEDDING_MODEL: str = get_current_embedding_model_name()

# Embedding dimension: use settings if defined, else default to 1536
EMBEDDING_DIM: int = getattr(settings, "embedding_dim", 1536)

# Single shared OpenAI client (uses OPENAI_API_KEY env var or settings)
_openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_EMBEDDING_MODEL = settings.openai_embedding_model


async def _embed_openai(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []

    inputs: List[str] = [str(t) for t in texts]

    resp = await _openai_client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=inputs,
    )

    vectors: List[List[float]] = [d.embedding for d in resp.data]

    # Optional sanity check
    if vectors and len(vectors[0]) != EMBEDDING_DIM:
        # You could log or enforce here
        pass

    return vectors


async def _embed_ollama(texts: Sequence[str]) -> List[List[float]]:
    """
    Use Ollama's /api/embeddings endpoint.

    This assumes Ollama's HTTP API is running and accessible via OLLAMA_BASE_URL,
    and that OLLAMA_EMBEDDING_MODEL is set in the environment.
    """
    if not texts:
        return []

    if not settings.ollama_base_url or not settings.ollama_embedding_model:
        raise RuntimeError(
            "Ollama embedding provider selected but OLLAMA_BASE_URL or "
            "OLLAMA_EMBEDDING_MODEL is not configured."
        )

    vectors: List[List[float]] = []

    async with httpx.AsyncClient(base_url=str(settings.ollama_base_url)) as client:
        for t in texts:
            payload = {
                "model": settings.ollama_embedding_model,
                "prompt": str(t),
            }
            resp = await client.post("/api/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Typical Ollama response shape: {"embedding": [...], "num_tokens": N}
            emb = data.get("embedding")
            if not isinstance(emb, list):
                raise RuntimeError("Unexpected Ollama embeddings response format.")
            vectors.append(emb)

    return vectors


async def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """
    Get embeddings for a batch of texts using the provider implied by the
    current security mode:

      - secure     → Ollama
      - not_secure → OpenAI
    """
    providers = get_effective_providers()
    provider = providers["embedding"].lower()

    if provider == "openai":
        return await _embed_openai(texts)
    elif provider == "ollama":
        return await _embed_ollama(texts)
    else:
        raise RuntimeError(f"Unsupported embedding provider: {provider!r}")
