# app/api/routers/drawings.py
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

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


@router.post("/summarize", response_model=SummarizeDrawingResponse)
async def summarize_drawing_endpoint(
    payload: SummarizeDrawingRequest,
) -> SummarizeDrawingResponse:
    """
    Trigger an LLM-based summarization for a drawing.

    For now the caller must pass document_id, json_path, and pdf_path in the body.
    Later we can look these up from the DB by document_id alone.
    """
    try:
        json_path = Path(payload.json_path)
        pdf_path = Path(payload.pdf_path)

        summary_data = summarize_drawing_with_llm(
            document_id=payload.document_id,
            json_path=json_path,
            pdf_path=pdf_path,
        )

        structured = parse_structured_summary(summary_data)
        long_form = summary_data.get("long_form_description", "")

        return SummarizeDrawingResponse(
            document_id=payload.document_id,
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
