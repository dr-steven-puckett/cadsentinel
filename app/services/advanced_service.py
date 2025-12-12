import logging
from sqlalchemy.orm import Session

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

logger = logging.getLogger(__name__)


def batch_chat(
    db: Session, req: BatchChatRequest
) -> BatchChatResponse:
    logger.debug(
        "Batch chat requested for drawings=%s message_len=%s",
        req.drawing_version_ids,
        len(req.message),
    )
    # Placeholder
    return BatchChatResponse(
        reply="Multi-drawing chat is not yet implemented.",
        used_drawings=req.drawing_version_ids,
        trace={"status": "not_implemented"},
    )


def similar_drawings(
    db: Session, drawing_version_id: str, limit: int
) -> SimilarDrawingsResponse:
    logger.debug("Similar drawings requested for %s", drawing_version_id)
    return SimilarDrawingsResponse(
        query_drawing_version_id=drawing_version_id,
        items=[],
    )


def retrieval_heatmap(
    db: Session, drawing_version_id: str, query: str
) -> RetrievalHeatmapResponse:
    logger.debug("Retrieval heatmap requested for %s query=%s", drawing_version_id, query)
    return RetrievalHeatmapResponse(
        drawing_version_id=drawing_version_id,
        query=query,
        regions=[],
    )


def explain_drawing(
    db: Session, drawing_version_id: str
) -> ExplainDrawingResponse:
    logger.debug("Explain drawing requested for %s", drawing_version_id)
    return ExplainDrawingResponse(
        drawing_version_id=drawing_version_id,
        explanation="Explain-my-drawing is not yet implemented.",
        sections={},
    )


def validate_rubric(
    db: Session,
    drawing_version_id: str,
    req: RubricValidationRequest,
) -> RubricValidationResult:
    logger.debug(
        "Rubric validation requested for %s rubric=%s strict=%s",
        drawing_version_id,
        req.rubric_id,
        req.strict,
    )
    return RubricValidationResult(
        rubric_id=req.rubric_id,
        passed=False,
        score=0.0,
        messages=["Rubric validation is not yet implemented."],
    )


def get_assembly(
    db: Session, drawing_version_id: str
) -> AssemblyResponse:
    logger.debug("Assembly requested for %s", drawing_version_id)
    return AssemblyResponse(
        assembly_id=drawing_version_id,
        items=[],
        status="not_implemented",
    )
