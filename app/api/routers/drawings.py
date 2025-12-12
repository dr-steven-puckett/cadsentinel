# app/api/routers/drawings.py
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.drawings import DrawingListResponse, DrawingDetail
from app.services import drawing_service
from app.api.schemas import (
    SummarizeDrawingRequest,
    SummarizeDrawingResponse,
)
from app.services.drawing_summarizer import (
    summarize_drawing_with_llm,
    parse_structured_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drawings", tags=["drawings"])


# ---------------------------------------------------------------------------
# 1. List & view drawings
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=DrawingListResponse,
    summary="List drawings",
    description=(
        "List all drawings with optional filters for customer, project, and "
        "text search. Results are paginated."
    ),
)
def list_drawings(
    customer_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = drawing_service.list_drawings(
        db=db,
        customer_id=customer_id,
        project_id=project_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    logger.debug(
        "List drawings returned %s items (total=%s) for customer_id=%s project_id=%s search=%s",
        len(items),
        total,
        customer_id,
        project_id,
        search,
    )

    return DrawingListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{drawing_version_id}",
    response_model=DrawingDetail,
    summary="Get drawing details",
    description=(
        "Return detailed metadata, artifact URLs, summary selection, "
        "dimension/note counts, and contexts for a drawing version."
    ),
)
def get_drawing(
    drawing_version_id: str,
    db: Session = Depends(get_db),
):
    detail = drawing_service.get_drawing_detail(db=db, drawing_version_id=drawing_version_id)
    if not detail:
        logger.warning("Drawing not found: drawing_version_id=%s", drawing_version_id)
        raise HTTPException(status_code=404, detail="Drawing not found")

    logger.debug("Fetched drawing detail for drawing_version_id=%s", drawing_version_id)
    return detail


@router.get(
    "/by-customer/{customer_id}",
    response_model=DrawingListResponse,
    summary="List drawings by customer",
    description="Return all drawings associated with a given customer. Relations may be placeholder for now.",
)
def get_drawings_by_customer(
    customer_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = drawing_service.list_drawings_by_customer(
        db=db,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )
    logger.debug(
        "List drawings by customer_id=%s returned %s items (total=%s)",
        customer_id,
        len(items),
        total,
    )

    return DrawingListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# 2. Summarize drawing (existing functionality)
# ---------------------------------------------------------------------------

@router.post(
    "/summarize",
    response_model=SummarizeDrawingResponse,
    summary="Summarize a drawing with LLM",
    description=(
        "Run LLM-based summarization for a specific drawing/document. "
        "Uses the configured provider (OpenAI/Ollama) under the hood."
    ),
)
async def summarize_drawing_endpoint(
    payload: SummarizeDrawingRequest,
) -> SummarizeDrawingResponse:
    """
    Summarize a drawing using the LLM pipeline.

    The request payload should include the identifiers / context the
    `summarize_drawing_with_llm` service expects (e.g., document_id,
    drawing_version_id, paths, or other metadata).

    Returns a structured summary, a long-form description, and optional
    raw model output for debugging.
    """
    try:
        logger.debug(
            "Summarize drawing requested for document_id=%s",
            getattr(payload, "document_id", None),
        )

        # summary_data is expected to be a dict-like object from the service:
        # {
        #   "structured": ...,
        #   "long_form": ...,
        #   "raw_model_output": ...
        # }
        summary_data = await summarize_drawing_with_llm(payload)

        structured, long_form = parse_structured_summary(summary_data)

        return SummarizeDrawingResponse(
            document_id=payload.document_id,  # field assumed from your existing schema
            structured_summary=structured,
            long_form_description=long_form,
            raw_model_output=summary_data.get("raw_model_output"),
        )

    except FileNotFoundError as e:
        logger.exception("Missing file during summarization")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Summarization failed")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {e}")
