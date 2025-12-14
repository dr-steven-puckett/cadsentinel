from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models.standards import StandardDocument

logger = logging.getLogger(__name__)

DEFAULT_STANDARDS_DIR = Path("ingested/standards")  # relative to project root


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def list_standards(db: Session, *, limit: int = 100, offset: int = 0) -> tuple[list[StandardDocument], int]:
    stmt = select(StandardDocument).order_by(StandardDocument.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count()).select_from(StandardDocument)
    items = list(db.execute(stmt).scalars().all())
    total = int(db.execute(count_stmt).scalar_one())
    return items, total


def get_standard(db: Session, *, standard_id: UUID) -> Optional[StandardDocument]:
    stmt = select(StandardDocument).where(StandardDocument.id == standard_id)
    return db.execute(stmt).scalars().first()


def create_standard(
    db: Session,
    *,
    name: str,
    filename: str,
    storage_path: str,
    summary: str | None = None,
) -> StandardDocument:
    doc = StandardDocument(
        name=name.strip(),
        filename=filename,
        storage_path=storage_path,
        summary=summary,
        rules_json=None,          # placeholder
        embedding_stats=None,     # placeholder
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_standard(db: Session, *, standard_id: UUID) -> StandardDocument:
    doc = get_standard(db, standard_id=standard_id)
    if not doc:
        raise KeyError("Standard not found.")
    db.delete(doc)
    db.commit()
    return doc


def resolve_storage_dir() -> Path:
    # If you later add settings like settings.standards_dir, switch to that here.
    base = Path.cwd()
    path = base / DEFAULT_STANDARDS_DIR
    _ensure_dir(path)
    return path
