import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.standards import (
    StandardUploadResponse,
    StandardListResponse,
    StandardDetail,
)
from app.services import standards_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/standards", tags=["standards"])


@router.post(
    "/upload",
    response_model=StandardUploadResponse,
    summary="Upload standards PDF",
    description="Upload a standards PDF. Processing (rules, embeddings) is placeholder for now.",
)
async def upload_standard(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    logger.debug("Uploading standard file=%s", file.filename)
    return standards_service.upload_standard(db, file.file, file.filename)


@router.get(
    "",
    response_model=StandardListResponse,
    summary="List standards",
)
def list_standards(db: Session = Depends(get_db)):
    return standards_service.list_standards(db)


@router.get(
    "/{standard_id}",
    response_model=StandardDetail,
    summary="Get standards document details",
)
def get_standard(standard_id: str, db: Session = Depends(get_db)):
    detail = standards_service.get_standard_detail(db, standard_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Standard not found")
    return detail


@router.delete(
    "/{standard_id}",
    status_code=204,
    summary="Delete standards document",
)
def delete_standard(standard_id: str, db: Session = Depends(get_db)):
    ok = standards_service.delete_standard(db, standard_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Standard not found")
    return
