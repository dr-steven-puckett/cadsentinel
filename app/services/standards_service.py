# app/services/standards_service.py
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.schemas.standards import (
    StandardUploadResponse,
    StandardListItem,
    StandardListResponse,
    StandardDetail,
)

logger = logging.getLogger(__name__)

# NOTE:
# This is a NON-PERSISTENT placeholder implementation.
# It does NOT store anything in the database yet.
# It only returns stub responses so the API and frontend can be wired up.


def upload_standard(
    db: Session,  # kept for future compatibility, not used yet
    file_obj,
    filename: str,
) -> StandardUploadResponse:
    """
    Placeholder upload handler for standards.

    Currently:
    - Does NOT persist anything to the database
    - Does NOT store the file on disk
    - Returns a fake standard_id and placeholder summary/rules

    Later:
    - Save PDF to storage
    - Insert a StandardDocument row
    - Run summarization and rule extraction
    """
    standard_id = str(uuid.uuid4())
    logger.debug(
        "Received standards upload filename=%s (placeholder, not persisted) standard_id=%s",
        filename,
        standard_id,
    )

    summary = "Standards processing is not yet implemented."
    extracted_rules: List[Dict[str, Any]] = []
    embedding_stats: Dict[str, Any] = {"status": "not_implemented"}

    return StandardUploadResponse(
        standard_id=standard_id,
        filename=filename,
        summary=summary,
        extracted_rules=extracted_rules,
        embedding_stats=embedding_stats,
    )


def list_standards(db: Session) -> StandardListResponse:
    """
    Placeholder list: always returns an empty list.
    """
    logger.debug("Listing standards (placeholder, always empty)")
    return StandardListResponse(items=[])


def get_standard_detail(db: Session, standard_id: str) -> StandardDetail | None:
    """
    Placeholder detail: always returns None so router returns 404.
    """
    logger.debug("Fetching standard detail standard_id=%s (placeholder, none)", standard_id)
    return None


def delete_standard(db: Session, standard_id: str) -> bool:
    """
    Placeholder delete: always returns False so router returns 404.
    """
    logger.debug("Deleting standard standard_id=%s (placeholder, no-op)", standard_id)
    return False
