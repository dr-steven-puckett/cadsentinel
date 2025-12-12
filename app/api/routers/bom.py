import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.bom import BomResponse
from app.services import bom_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drawings", tags=["bom"])


@router.get(
    "/{drawing_version_id}/bom",
    response_model=BomResponse,
    summary="Get bill of materials for drawing (placeholder)",
)
def get_bom(
    drawing_version_id: str,
    db: Session = Depends(get_db),
):
    return bom_service.get_bom_for_drawing(db, drawing_version_id)
