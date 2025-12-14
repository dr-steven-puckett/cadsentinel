from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.standards import (
    StandardsUploadResponse,
    StandardsListResponse,
    StandardListItem,
    StandardDetailResponse,
)
from app.services import standards_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/standards", tags=["standards"])


def _file_url(standard_id: UUID) -> str:
    return f"/api/v1/standards/{standard_id}/file"


@router.post("/upload", response_model=StandardsUploadResponse, status_code=201)
async def upload_standard(
    file: UploadFile = File(...),
    name: str | None = Query(default=None, description="Optional human-friendly name; defaults to filename"),
    db: Session = Depends(get_db),
) -> StandardsUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    storage_dir = standards_service.resolve_storage_dir()
    safe_name = Path(file.filename).name
    out_path = storage_dir / safe_name

    # Avoid overwrite: if exists, append suffix
    if out_path.exists():
        stem = out_path.stem
        suffix = out_path.suffix
        i = 2
        while True:
            candidate = storage_dir / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                out_path = candidate
                break
            i += 1

    try:
        content = await file.read()
        out_path.write_bytes(content)
    except Exception as e:
        logger.exception("Failed saving standards PDF")
        raise HTTPException(status_code=500, detail=f"Failed saving file: {e}")

    doc = standards_service.create_standard(
        db,
        name=(name.strip() if name else out_path.name),
        filename=out_path.name,
        storage_path=str(out_path),
        summary=None,  # placeholder for later summarizer/extractor
    )

    return StandardsUploadResponse(
        standard_id=doc.id,
        filename=doc.filename,
        name=doc.name,
        summary=doc.summary,
        extracted_rules=doc.rules_json or {},
        embedding_stats=doc.embedding_stats or {},
        file_url=_file_url(doc.id),
    )


@router.get("", response_model=StandardsListResponse)
def list_standards(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> StandardsListResponse:
    items, total = standards_service.list_standards(db, limit=limit, offset=offset)
    return StandardsListResponse(
        items=[
            StandardListItem(
                id=x.id,
                name=x.name,
                filename=x.filename,
                created_at=x.created_at,
                summary=x.summary,
                file_url=_file_url(x.id),
            )
            for x in items
        ],
        total=total,
    )


@router.get("/{standard_id}", response_model=StandardDetailResponse)
def get_standard(standard_id: UUID, db: Session = Depends(get_db)) -> StandardDetailResponse:
    doc = standards_service.get_standard(db, standard_id=standard_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Standard not found")

    return StandardDetailResponse(
        id=doc.id,
        name=doc.name,
        filename=doc.filename,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        storage_path=doc.storage_path,
        summary=doc.summary,
        extracted_rules=doc.rules_json or {},
        embedding_stats=doc.embedding_stats or {},
        file_url=_file_url(doc.id),
    )


@router.get("/{standard_id}/file")
def download_standard_pdf(standard_id: UUID, db: Session = Depends(get_db)):
    doc = standards_service.get_standard(db, standard_id=standard_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Standard not found")
    path = Path(doc.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=doc.filename,
    )


@router.delete("/{standard_id}", status_code=204)
def delete_standard(standard_id: UUID, db: Session = Depends(get_db)) -> None:
    doc = standards_service.get_standard(db, standard_id=standard_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Standard not found")

    # Delete DB row first (or after file—either is OK; this way is simpler)
    try:
        deleted = standards_service.delete_standard(db, standard_id=standard_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Standard not found")

    # Best-effort file cleanup
    try:
        path = Path(deleted.storage_path)
        if path.exists():
            path.unlink()
    except Exception:
        logger.warning("Failed to delete standard file from disk", exc_info=True)
