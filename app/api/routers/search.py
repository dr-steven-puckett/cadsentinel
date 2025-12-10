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

2. Semantic Search (pgvector)
   Query across embeddings for:
   dimension text
   notes
   summaries

3. Hybrid Search
   Combine structured filters + semantic similarity for extremely high-precision engineering drawing retrieval.

4. Search Router
'''
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    Drawing,
    DrawingVersion,
    Dimension,
    Note,
    DrawingSummary,
    Embedding,
)
from app.services.ai_providers import build_embedding_provider
from app.config import get_settings, Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# ---------------------------------------------------------------------------
# 1. METADATA SEARCH
# ---------------------------------------------------------------------------

@router.get("/metadata")
def metadata_search(
    q: str = Query(..., description="Search text for metadata fields"),
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Search across drawing metadata, notes, dimensions, summaries.
    NOT vector search — purely relational/LIKE operations.
    """

    search_str = f"%{q.lower()}%"

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

    # Also search notes & dimensions if needed
    note_hits = (
        db.query(Note)
        .filter(func.lower(Note.text).like(search_str))
        .limit(limit)
        .all()
    )

    dim_hits = (
        db.query(Dimension)
        .filter(
            or_(
                func.lower(Dimension.dim_text).like(search_str),
                func.cast(Dimension.dim_value, String).like(search_str.replace("%", "")),
            )
        )
        .limit(limit)
        .all()
    )

    return {
        "query": q,
        "drawings": [d.id for d in drawings],
        "note_hits": [{"id": n.id, "text": n.text, "version": n.drawing_version_id} for n in note_hits],
        "dimension_hits": [
            {"id": d.id, "text": d.dim_text, "value": d.dim_value, "version": d.drawing_version_id}
            for d in dim_hits
        ],
    }



# ---------------------------------------------------------------------------
# 2. SEMANTIC SEARCH (pgvector)
# ---------------------------------------------------------------------------

@router.get("/semantic")
def semantic_search(
    q: str = Query(..., description="Text to search semantically"),
    top_k: int = 10,
    provider: str = "openai",
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Use embeddings + pgvector to find relevant drawings, notes, dimensions, summaries.
    """
    embedding_provider = build_embedding_provider(settings.ai_provider)
    query_vec = embedding_provider.embed_text(q)

    # VECTOR SEARCH
    results = (
        db.query(
            Embedding,
            func.l2_distance(Embedding.embedding, query_vec).label("distance")
        )
        .order_by("distance")
        .limit(top_k)
        .all()
    )

    formatted = []
    for emb, dist in results:
        formatted.append({
            "embedding_id": emb.id,
            "drawing_version_id": emb.drawing_version_id,
            "source_type": emb.source_type,
            "source_ref_id": emb.source_ref_id,
            "content": emb.content,
            "distance": float(dist),
        })

    return {
        "query": q,
        "results": formatted,
    }



# ---------------------------------------------------------------------------
# 3. HYBRID SEARCH (metadata filters + semantic similarity)
# ---------------------------------------------------------------------------

@router.get("/hybrid")
def hybrid_search(
    semantic_query: str = Query(...),
    part_number: Optional[str] = None,
    project_code: Optional[str] = None,
    max_distance: float = 0.60,
    top_k: int = 10,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Combine metadata filtering + semantic similarity.

    Process:
    1. Find drawings matching metadata filters
    2. Run vector search across those drawing_version_ids only
    """

    # -----------------------------
    # Step 1: metadata filtering
    # -----------------------------
    drawing_filters = []

    if part_number:
        drawing_filters.append(Drawing.part_number == part_number)

    if project_code:
        drawing_filters.append(Drawing.project_code == project_code)

    # base query
    q_drawings = db.query(Drawing)

    if drawing_filters:
        q_drawings = q_drawings.filter(*drawing_filters)

    filtered_drawing_ids = [d.id for d in q_drawings.all()]

    if not filtered_drawing_ids:
        return {
            "semantic_query": semantic_query,
            "message": "No drawings matched metadata filters.",
            "results": [],
        }

    # find versions for these drawings
    version_ids = [
        v.id
        for v in db.query(DrawingVersion)
        .filter(DrawingVersion.drawing_id.in_(filtered_drawing_ids))
        .all()
    ]

    if not version_ids:
        return {
            "semantic_query": semantic_query,
            "message": "No versions present for drawings.",
            "results": [],
        }

    # -----------------------------
    # Step 2: semantic search limited to version_ids
    # -----------------------------
    embedding_provider = build_embedding_provider(settings.ai_provider)
    query_vec = embedding_provider.embed_text(semantic_query)

    results = (
        db.query(
            Embedding,
            func.l2_distance(Embedding.embedding, query_vec).label("distance"),
        )
        .filter(Embedding.drawing_version_id.in_(version_ids))
        .having(func.l2_distance(Embedding.embedding, query_vec) <= max_distance)
        .order_by("distance")
        .limit(top_k)
        .all()
    )

    formatted = []
    for emb, dist in results:
        formatted.append({
            "embedding_id": emb.id,
            "drawing_version_id": emb.drawing_version_id,
            "source_type": emb.source_type,
            "source_ref_id": emb.source_ref_id,
            "content": emb.content,
            "distance": float(dist),
        })

    return {
        "semantic_query": semantic_query,
        "metadata_filters": {
            "part_number": part_number,
            "project_code": project_code,
        },
        "results": formatted,
    }
