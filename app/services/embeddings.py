# app/services/embeddings.py
from __future__ import annotations

from typing import Sequence, List

from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

# Single shared OpenAI client (uses OPENAI_API_KEY env var)
_client = AsyncOpenAI()

# Must match your pgvector column dimension (Vector(1536))
EMBEDDING_MODEL = getattr(settings, "openai_embedding_model", None) or "text-embedding-3-small"
EMBEDDING_DIM = getattr(settings, "embedding_dim", None) or 1536


async def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """
    Get OpenAI embeddings for a batch of texts.

    - Uses text-embedding-3-small by default (1536-dim).
    - Returns vectors in the same order as `texts`.
    - Safe for both ingestion-time and query-time use.
    """
    if not texts:
        return []

    inputs: List[str] = [str(t) for t in texts]

    resp = await _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=inputs,
    )

    vectors: List[List[float]] = [d.embedding for d in resp.data]

    # Optional sanity check: dimensions should match pgvector column
    if vectors and len(vectors[0]) != EMBEDDING_DIM:
        # You can log or raise here if you want stricter enforcement
        # For now we just trust DB to reject mismatched inserts at ingest time.
        pass

    return vectors
