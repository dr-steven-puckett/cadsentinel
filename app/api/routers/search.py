'''
1. Metadata Search
   Search drawings by:
      part number
      title
      description
      project code
      revision
      note text
      dimension text/value
      layer
      handle

2. Vector Search (pgvector)
   Query across embeddings for:
      dimension text
      notes
      summaries

3. Hybrid Search
   Combine vector similarity + trigram keyword similarity.

4. Search Router
'''
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func, String
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    Drawing,
    Dimension,
    Note,
)
# New: structured search schemas + services
from app.api.schemas import (
    VectorSearchRequest,
    HybridSearchRequest,
    ChunkSearchResponse,
)

from app.services.drawing_search import (
    vector_search_embeddings,
    hybrid_search_embeddings,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# ---------------------------------------------------------------------------
# 1. METADATA SEARCH  (relational LIKE search)
# ---------------------------------------------------------------------------

@router.get("/metadata")
def metadata_search(
    q: str = Query(..., description="Search text for metadata fields"),
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Search across drawing metadata, notes, dimensions.
    NOT vector search — purely relational/LIKE operations.
    """

    search_str = f"%{q.lower()}%"

    # Drawings by metadata
    drawings = (
        db.query(Drawing)
        .filter(
            or_(
                func.lower(Drawing.part_number).like(search_str),
                func.lower(Drawing.title).like(search_str),
                func.lower(Drawing.description).like(search_str),
                func.lower(Drawing.project_code).like(search_str),
            )
        )
        .limit(limit)
        .all()
    )

    # Notes
    note_hits = (
        db.query(Note)
        .filter(func.lower(Note.text).like(search_str))
        .limit(limit)
        .all()
    )

    # Dimensions (text OR numeric value)
    dim_hits = (
        db.query(Dimension)
        .filter(
            or_(
                func.lower(Dimension.dim_text).like(search_str),
                # cast numeric dim_value to text so we can LIKE it
                func.cast(Dimension.dim_value, String).like(search_str.replace("%", "")),
            )
        )
        .limit(limit)
        .all()
    )

    return {
        "query": q,
        "drawings": [d.id for d in drawings],
        "note_hits": [
            {"id": n.id, "text": n.text, "version": n.drawing_version_id}
            for n in note_hits
        ],
        "dimension_hits": [
            {
                "id": d.id,
                "text": d.dim_text,
                "value": d.dim_value,
                "version": d.drawing_version_id,
            }
            for d in dim_hits
        ],
    }


# ---------------------------------------------------------------------------
# 2. VECTOR / SEMANTIC SEARCH (pgvector cosine)
# ---------------------------------------------------------------------------

@router.post("/vector", response_model=ChunkSearchResponse)
async def search_vector(
    payload: VectorSearchRequest,
    db: Session = Depends(get_db),
) -> ChunkSearchResponse:
    """
    Vector / semantic search across all embeddings.

    Features:
      - pgvector cosine similarity
      - Filters by drawing_version_id and source_types
      - Returns matched text, source_type, drawing_version_id,
        geometry/index info, similarity score, and thumbnail URL.
    """
    try:
        return await vector_search_embeddings(db, payload)
    except NotImplementedError as e:
        # embed_texts() not wired yet
        logger.exception("embed_texts() not implemented")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 3. HYBRID SEARCH (vector + trigram keyword)
# ---------------------------------------------------------------------------

@router.post("/hybrid", response_model=ChunkSearchResponse)
async def search_hybrid(
    payload: HybridSearchRequest,
    db: Session = Depends(get_db),
) -> ChunkSearchResponse:
    """
    Hybrid search combining:
      - vector similarity (pgvector cosine)
      - keyword/trigram similarity on content (pg_trgm)

    Uses a fused score:
        fused = alpha * vector_score + (1 - alpha) * keyword_score
    """
    try:
        return await hybrid_search_embeddings(db, payload)
    except NotImplementedError as e:
        logger.exception("embed_texts() not implemented")
        raise HTTPException(status_code=500, detail=str(e))
