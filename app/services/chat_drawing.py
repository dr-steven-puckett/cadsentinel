# app/services/chat_drawing.py
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from openai import AsyncOpenAI

from app.db.models import (
    Embedding,
    Dimension,
    Note,
    Drawing,
    DrawingVersion,
    DrawingFile,
)
from app.api.schemas import (
    ChatDrawingRequest,
    ChatDrawingResponse,
    RetrievedContextItem,
)
from app.services.embeddings import embed_texts


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

async def _top_embeddings_for_type(
    db: Session,
    drawing_version_id: int,
    query_vec: list[float],
    source_type: str,
    limit: int,
) -> List[Tuple[Embedding, float]]:
    """
    Return top-N Embedding rows for a given drawing_version_id and source_type,
    with their cosine similarity score.
    """
    if limit <= 0:
        return []

    sim_expr = 1.0 - Embedding.embedding.cosine_distance(query_vec)

    stmt = (
        select(Embedding, sim_expr.label("similarity"))
        .where(
            and_(
                Embedding.embedding.is_not(None),
                Embedding.drawing_version_id == drawing_version_id,
                Embedding.source_type == source_type,
            )
        )
        .order_by(Embedding.embedding.cosine_distance(query_vec).asc())
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    return [(row[0], float(row[1])) for row in rows]


def _build_retrieved_items(
    db: Session,
    pairs: List[Tuple[Embedding, float]],
) -> List[RetrievedContextItem]:
    """
    Turn (Embedding, similarity) pairs into RetrievedContextItem objects,
    enriching with geometry + thumbnail.
    """
    if not pairs:
        return []

    embeddings = [e for (e, _) in pairs]

    # Thumbnail by drawing_version_id
    dv_ids = {e.drawing_version_id for e in embeddings}
    thumb_map: dict[int, str] = {}
    if dv_ids:
        stmt = select(DrawingFile).where(
            DrawingFile.drawing_version_id.in_(dv_ids),
            DrawingFile.file_type == "png_thumb",
        )
        for df in db.execute(stmt).scalars():
            thumb_map[df.drawing_version_id] = df.file_path

    # Geometry by type
    dim_ids = {e.source_ref_id for e in embeddings if e.source_type == "dimension" and e.source_ref_id is not None}
    note_ids = {e.source_ref_id for e in embeddings if e.source_type == "note" and e.source_ref_id is not None}

    dim_by_id: dict[int, Dimension] = {}
    note_by_id: dict[int, Note] = {}

    if dim_ids:
        stmt = select(Dimension).where(Dimension.id.in_(dim_ids))
        dim_by_id = {d.id: d for d in db.execute(stmt).scalars()}

    if note_ids:
        stmt = select(Note).where(Note.id.in_(note_ids))
        note_by_id = {n.id: n for n in db.execute(stmt).scalars()}

    items: List[RetrievedContextItem] = []

    for emb, sim in pairs:
        geometry_index = None

        if emb.source_type == "dimension" and emb.source_ref_id in dim_by_id:
            d = dim_by_id[emb.source_ref_id]
            geometry_index = {
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
        elif emb.source_type == "note" and emb.source_ref_id in note_by_id:
            n = note_by_id[emb.source_ref_id]
            geometry_index = {
                "kind": "note",
                "note_id": n.id,
                "json_index": n.json_index,
                "layer": n.layer,
                "handle": n.handle,
                "geometry": n.geometry,
            }

        items.append(
            RetrievedContextItem(
                chunk_id=emb.id,
                source_type=emb.source_type,
                drawing_version_id=emb.drawing_version_id,
                source_ref_id=emb.source_ref_id,
                matched_text=emb.content,
                similarity_score=sim,
                geometry_index=geometry_index,
                thumbnail_url=thumb_map.get(emb.drawing_version_id),
            )
        )

    return items


def _resolve_drawing_version_id(
    db: Session,
    req: ChatDrawingRequest,
) -> tuple[int, str | None]:
    """
    Resolve which drawing_version_id to use from the request.
    Priority:
      1. explicit drawing_version_id
      2. document_id (hash) → latest DrawingVersion for that document
    """
    if req.drawing_version_id is not None:
        dv = db.get(DrawingVersion, req.drawing_version_id)
        if not dv:
            raise ValueError(f"drawing_version_id={req.drawing_version_id} not found")
        # Try to fetch document_id from related Drawing if available
        document_id: str | None = None
        if dv.drawing_id is not None:
            drawing = db.get(Drawing, dv.drawing_id)
            if drawing and getattr(drawing, "document_id", None):
                document_id = drawing.document_id
        return dv.id, document_id

    if req.document_id:
        # Adjust this filter to whatever field stores your hash/document_id
        stmt = (
            select(DrawingVersion)
            .join(Drawing, DrawingVersion.drawing_id == Drawing.id)
            .where(Drawing.document_id == req.document_id)
            .order_by(DrawingVersion.created_at.desc())
        )
        dv = db.execute(stmt).scalars().first()
        if not dv:
            raise ValueError(f"No drawing version found for document_id={req.document_id!r}")
        return dv.id, req.document_id

    raise ValueError("Either drawing_version_id or document_id must be provided.")


def _build_context_text(
    summaries: List[RetrievedContextItem],
    notes: List[RetrievedContextItem],
    dims: List[RetrievedContextItem],
) -> str:
    """
    Render retrieved chunks into a single context text blob for the LLM.
    """
    lines: List[str] = []

    if summaries:
        lines.append("=== STRUCTURED / SUMMARY CONTEXT ===")
        for s in summaries:
            lines.append(f"- [summary #{s.chunk_id}] {s.matched_text}")

    if notes:
        lines.append("\n=== NOTES / ANNOTATIONS ===")
        for n in notes:
            lines.append(f"- [note #{n.chunk_id}] {n.matched_text}")

    if dims:
        lines.append("\n=== DIMENSIONS ===")
        for d in dims:
            # Show both text and value if available
            gi = d.geometry_index or {}
            dim_text = gi.get("dim_text") or d.matched_text
            dim_value = gi.get("dim_value")
            if dim_value is not None:
                lines.append(f"- [dim #{d.chunk_id}] {dim_text} = {dim_value}")
            else:
                lines.append(f"- [dim #{d.chunk_id}] {dim_text}")

    return "\n".join(lines)


def _build_system_prompt() -> str:
    """
    System prompt optimized for mechanical drawings, GD&T, and standards-aware reasoning.
    """
    return (
        "You are an expert mechanical design and manufacturing engineer, "
        "specializing in interpreting AutoCAD mechanical drawings, GD&T, tolerances, "
        "hydraulic cylinder design, threads, and machining/manufacturing processes.\n\n"
        "You are helping a user analyze a single engineering drawing. You will be given:\n"
        "- A user question.\n"
        "- Retrieved context chunks: summaries, notes, and dimensions.\n\n"
        "Guidelines:\n"
        "1. Base your answer strictly on the provided context. If critical information "
        "   is missing, say what is missing instead of guessing.\n"
        "2. When discussing dimensions, refer to them clearly (e.g., 'the 1.750 PROD DIA').\n"
        "3. Explain GD&T or tolerances in practical, manufacturing-aware terms.\n"
        "4. If you suspect standards issues (ASME Y14.5, thread callouts, etc.), explain why.\n"
        "5. Be concise but technically clear. Use bullets and short paragraphs.\n"
    )


# ---------------------------------------------------------
# Main entry: chat_with_drawing
# ---------------------------------------------------------

async def chat_with_drawing(
    db: Session,
    req: ChatDrawingRequest,
) -> ChatDrawingResponse:
    """
    Orchestrates retrieval + LLM call for /chat/drawing.
    """
    # 1) Resolve drawing_version_id + document_id
    drawing_version_id, document_id = _resolve_drawing_version_id(db, req)

    # 2) Embed user_message
    [query_vec] = await embed_texts([req.user_message])

    # 3) Retrieve chunks by type
    summary_pairs = await _top_embeddings_for_type(
        db, drawing_version_id, query_vec, "summary", req.max_summary_chunks
    )
    note_pairs = await _top_embeddings_for_type(
        db, drawing_version_id, query_vec, "note", req.max_note_chunks
    )
    dim_pairs = await _top_embeddings_for_type(
        db, drawing_version_id, query_vec, "dimension", req.max_dimension_chunks
    )

    summary_items = _build_retrieved_items(db, summary_pairs)
    note_items = _build_retrieved_items(db, note_pairs)
    dim_items = _build_retrieved_items(db, dim_pairs)

    # 4) Build context text for the LLM
    context_text = _build_context_text(summary_items, note_items, dim_items)

    # 5) Call OpenAI (ChatGPT-5.1 or equivalent)
    client = AsyncOpenAI()  # uses OPENAI_API_KEY env var

    system_prompt = _build_system_prompt()

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": (
                f"User question:\n{req.user_message}\n\n"
                "Drawing context (summaries, notes, dimensions):\n"
                f"{context_text}"
            ),
        },
    ]

    completion = await client.chat.completions.create(
        model="gpt-4.1",  # or "gpt-5.1" when available in your API account
        messages=messages,
        temperature=0.2,
    )

    assistant_reply = completion.choices[0].message.content or ""

    # 6) Aggregate all context items into one list
    all_items: List[RetrievedContextItem] = []
    all_items.extend(summary_items)
    all_items.extend(note_items)
    all_items.extend(dim_items)

    open_in_documents_url = f"/documents/{drawing_version_id}"

    return ChatDrawingResponse(
        assistant_reply=assistant_reply,
        drawing_version_id=drawing_version_id,
        document_id=document_id,
        contexts=all_items,
        open_in_documents_url=open_in_documents_url,
    )
