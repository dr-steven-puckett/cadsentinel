# app/services/embeddings.py
import math
from typing import Sequence, List

EMBEDDING_DIM = 1536

async def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    # SUPER DUMMY: deterministic but nonsense embeddings – for testing only
    vectors: List[List[float]] = []
    for i, t in enumerate(texts):
        v = [0.0] * EMBEDDING_DIM
        v[i % EMBEDDING_DIM] = 1.0
        vectors.append(v)
    return vectors
