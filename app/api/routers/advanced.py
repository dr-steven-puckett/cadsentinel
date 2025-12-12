import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.advanced import (
    BatchChatRequest,
    BatchChatResponse,
    SimilarDrawingsResponse,
    RetrievalHeatmapResponse,
    ExplainDrawingResponse,
    RubricValidationRequest,
    RubricValidationResult,
    AssemblyResponse,
)
from app.services import advanced_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advanced", tags=["advanced"])


@router.post(
    "/batch-chat",
    response_model=BatchChatResponse,
    summary="Multi-drawing batch chat (placeholder)",
)
def batch_chat(
    req: BatchChatRequest,
    db: Session = Depends(get_db),
):
    return advanced_service.batch_chat(db, req)


@router.get(
    "/drawings/{drawing_version_id}/similar",
    response_model=SimilarDrawingsResponse,
    summary="Drawing-to-drawing similarity search (placeholder)",
)
def similar_drawings(
    drawing_version_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return advanced_service.similar_drawings(db, drawing_version_id, limit)


@router.get(
    "/drawings/{drawing_version_id}/heatmap",
    response_model=RetrievalHeatmapResponse,
    summary="Retrieval heatmap visualization (placeholder)",
)
def retrieval_heatmap(
    drawing_version_id: str,
    query: str = Query(...),
    db: Session = Depends(get_db),
):
    return advanced_service.retrieval_heatmap(db, drawing_version_id, query)


@router.get(
    "/drawings/{drawing_version_id}/explain",
    response_model=ExplainDrawingResponse,
    summary="LLM-based explain-my-drawing (placeholder)",
)
def explain_drawing(
    drawing_version_id: str,
    db: Session = Depends(get_db),
):
    return advanced_service.explain_drawing(db, drawing_version_id)


@router.post(
    "/drawings/{drawing_version_id}/rubric",
    response_model=RubricValidationResult,
    summary="Validate drawing against rubric (placeholder)",
)
def validate_rubric(
    drawing_version_id: str,
    req: RubricValidationRequest,
    db: Session = Depends(get_db),
):
    return advanced_service.validate_rubric(db, drawing_version_id, req)


@router.get(
    "/drawings/{drawing_version_id}/assembly",
    response_model=AssemblyResponse,
    summary="Multi-file assembly view (placeholder)",
)
def get_assembly(
    drawing_version_id: str,
    db: Session = Depends(get_db),
):
    return advanced_service.get_assembly(db, drawing_version_id)
