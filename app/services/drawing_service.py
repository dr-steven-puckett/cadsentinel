import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas.drawings import (
    DrawingBase,
    DrawingDetail,
    DrawingFlags,
    DrawingSummarySelection,
    DrawingContextInfo,
)

logger = logging.getLogger(__name__)


def _artifact_url(kind: str, drawing_version_id: str) -> str:
    # All absolute, versioned URLs for the frontend
    return f"/api/v1/artifacts/{drawing_version_id}/{kind}"


def list_drawings(
    db: Session,
    *,
    customer_id: Optional[str],
    project_id: Optional[str],
    search: Optional[str],
    page: int,
    page_size: int,
) -> Tuple[List[DrawingBase], int]:
    """
    Query DB for drawings, apply filters, and map to DrawingBase.
    Currently a stub that you should wire to your drawing models.
    """
    logger.debug(
        "Listing drawings with filters customer_id=%s project_id=%s search=%s page=%s page_size=%s",
        customer_id,
        project_id,
        search,
        page,
        page_size,
    )

    # TODO: Replace with real SQLAlchemy queries into your DWG/DrawingVersion models.
    # Placeholder: empty list
    items: List[DrawingBase] = []
    total = 0
    return items, total


def get_drawing_detail(
    db: Session,
    drawing_version_id: str,
) -> Optional[DrawingDetail]:
    """
    Load a single drawing_version and map to DrawingDetail.
    """
    logger.debug("Fetching drawing detail for drawing_version_id=%s", drawing_version_id)

    # TODO: Query your DrawingVersion model by drawing_version_id.
    # Placeholder: None
    return None


def list_drawings_by_customer(
    db: Session,
    customer_id: str,
    page: int,
    page_size: int,
) -> Tuple[List[DrawingBase], int]:
    logger.debug(
        "Listing drawings for customer_id=%s page=%s page_size=%s",
        customer_id,
        page,
        page_size,
    )

    # TODO: Real DB query
    items: List[DrawingBase] = []
    total = 0
    return items, total
