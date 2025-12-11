# app/services/drawing_search.py
from __future__ import annotations

from typing import Iterable, List, Tuple

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.db.models import Embedding, Dimension, Note, DrawingFile
from app.api.schemas import (
    VectorSearchRequest,
    HybridSearchRequest,
    ChunkSearchResponse,
    ChunkSearchResult,
)
from app.services.embeddings import embed_texts


# ---------------------------------------------------------
# Helpers: thumbnail + geometry enrichment
# ---------------------------------------------------------

def _load_thumbnails_for_embeddings(
    db: Session,
    embeddings: Iterable[Embedding],
) -> dict[int, str]:
    """
    Map drawing_version_id -> png_thumb file_path.
    """
    dv_ids = {e.drawing_version_id for e in embeddings}
    if not dv_ids:
        return {}

    stmt = select(DrawingFile).where(
        DrawingFile.drawing_version_id.in_(dv_ids),
        DrawingFile.file_type == "png_thumb",
    )

    thumb_map: dict[int, str] = {}
    for df in db.execute(stmt).scalars():
        thumb_map[df.drawing_version_id] = df.file_path
    return thumb_map


def _load_geometry_for_embeddings(
    db: Session,
    embeddings: Iterable[Embedding],
) -> dict[int, dict]:
    """
    Build a mapping: embedding_id -> geometry_index dict.

    For:
      - source_type == "dimension" → use Dimension
      - source_type == "note"      → use Note
      - others: {} or None
    """
    dim_ids: set[int] = set()
    note_ids: set[int] = set()

    for e in embeddings:
        if e.source_ref_id is None:
            continue
        if e.source_type == "dimension":
            dim_ids.add(e.source_ref_id)
        elif e.source_type == "note":
            note_ids.add(e.source_ref_id)

    geom_by_embedding: dict[int, dict] = {}

    if dim_ids:
        stmt = select(Dimension).where(Dimension.id.in_(dim_ids))
        dim_by_id = {d.id: d for d in db.execute(stmt).scalars()}
        for e in embeddings:
            if e.source_type == "dimension" and e.source_ref_id in dim_by_id:
                d = dim_by_id[e.source_ref_id]
                geom_by_embedding[e.id] = {
                    "kind": "dimension",
                    "dimension_id": d.id,
                    "json_index": d.json_index,
                    "layer": d.layer,
                    "handle": d.handle,
                    "owner_handle": d.owner_handle,
                    "geometry": d.geometry,
                    "dim_text": d.dim_text,
                    "dim_value": d.dim_value,
                    "units": d.units,
                }

    if note_ids:
        stmt = select(Note).where(Note.id.in_(note_ids))
        note_by_id = {n.id: n for n in db.execute(stmt).scalars()}
        for e in embeddings:
            if e.source_type == "note" and e.source_ref_id in note_by_id:
                n = note_by_id[e.source_ref_id]
                geom_by_embedding[e.id] = {
                    "kind": "note",
                    "note_id": n.id,
                    "json_index": n.json_index,
                    "layer": n.layer,
                    "handle": n.handle,
                    "geometry": n.geometry,
                }

    return geom_by_embedding


# ---------------------------------------------------------
# Vector search
# ---------------------------------------------------------

async def vector_search_embeddings(
    db: Session,
    req: VectorSearchRequest,
) -> ChunkSearchResponse:
    """
    Vector / semantic search over the embeddings table using pgvector cosine similarity.
    """
    # 1) Get query embedding
    [query_vec] = await embed_texts([req.query_text])

    # 2) Build base query
    sim_expr = 1.0 - Embedding.embedding.cosine_distance(query_vec)

    stmt = (
        select(Embedding, sim_expr.label("similarity"))
        .where(Embedding.embedding.is_not(None))
    )

    filters = []
    if req.filters:
        if req.filters.drawing_version_id is not None:
            filters.append(Embedding.drawing_version_id == req.filters.drawing_version_id)
        if req.filters.source_types:
            filters.append(Embedding.source_type.in_(req.filters.source_types))

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Embedding.embedding.cosine_distance(query_vec).asc())
    stmt = stmt.limit(req.top_k)

    rows = db.execute(stmt).all()
    embeddings: List[Embedding] = [row[0] for row in rows]

    # 3) Thumbnail + geometry enrichment
    thumb_map = _load_thumbnails_for_embeddings(db, embeddings)
    geom_map = _load_geometry_for_embeddings(db, embeddings)

    results: List[ChunkSearchResult] = []
    for emb, similarity in rows:
        sim_val = float(similarity)
        if req.score_threshold is not None and sim_val < req.score_threshold:
            continue

        results.append(
            ChunkSearchResult(
                id=emb.id,
                matched_text=emb.content,
                source_type=emb.source_type,
                drawing_version_id=emb.drawing_version_id,
                source_ref_id=emb.source_ref_id,
                similarity_score=sim_val,
                thumbnail_url=thumb_map.get(emb.drawing_version_id),
                geometry_index=geom_map.get(emb.id),
                metadata=None,  # reserved for future metadata column
            )
        )

    return ChunkSearchResponse(
        results=results,
        total_returned=len(results),
        mode="vector",
    )


# ---------------------------------------------------------
# Hybrid search (vector + keyword/trigram)
# ---------------------------------------------------------

async def hybrid_search_embeddings(
    db: Session,
    req: HybridSearchRequest,
) -> ChunkSearchResponse:
    """
    Hybrid search combining:
      - vector similarity (pgvector cosine)
      - keyword/trigram similarity on content (pg_trgm similarity())
    """
    [query_vec] = await embed_texts([req.query_text])
    sim_expr = 1.0 - Embedding.embedding.cosine_distance(query_vec)

    # pg_trgm similarity(content, query_text) — requires pg_trgm extension
    trigram_expr = func.similarity(Embedding.content, req.query_text)

    stmt = (
        select(
            Embedding,
            sim_expr.label("vector_score"),
            trigram_expr.label("keyword_score"),
        )
        .where(Embedding.embedding.is_not(None))
    )

    filters = []
    if req.filters:
        if req.filters.drawing_version_id is not None:
            filters.append(Embedding.drawing_version_id == req.filters.drawing_version_id)
        if req.filters.source_types:
            filters.append(Embedding.source_type.in_(req.filters.source_types))

    if filters:
        stmt = stmt.where(and_(*filters))

    # Grab extra candidates, then fuse-sort in Python
    stmt = stmt.limit(req.top_k * 3)

    rows = db.execute(stmt).all()
    embeddings: List[Embedding] = [row[0] for row in rows]

    thumb_map = _load_thumbnails_for_embeddings(db, embeddings)
    geom_map = _load_geometry_for_embeddings(db, embeddings)

    fused_results: List[Tuple[ChunkSearchResult, float]] = []

    for emb, vector_score, keyword_score in rows:
        v = float(vector_score)
        k = float(keyword_score or 0.0)
        fused = req.alpha * v + (1.0 - req.alpha) * k

        if req.score_threshold is not None and fused < req.score_threshold:
            continue

        result = ChunkSearchResult(
            id=emb.id,
            matched_text=emb.content,
            source_type=emb.source_type,
            drawing_version_id=emb.drawing_version_id,
            source_ref_id=emb.source_ref_id,
            similarity_score=fused,
            thumbnail_url=thumb_map.get(emb.drawing_version_id),
            geometry_index=geom_map.get(emb.id),
            metadata=None,
        )
        fused_results.append((result, fused))

    # Sort by fused score descending and truncate
    fused_results.sort(key=lambda x: x[1], reverse=True)
    final_results = [r for (r, _) in fused_results[: req.top_k]]

    return ChunkSearchResponse(
        results=final_results,
        total_returned=len(final_results),
        mode="hybrid",
    )
