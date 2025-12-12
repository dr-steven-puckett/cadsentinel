# app/services/bom_service.py
from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.schemas.bom import BomResponse

logger = logging.getLogger(__name__)

# NOTE:
# This is a NON-PERSISTENT placeholder implementation.
# It does NOT read from the database yet.
# It only returns stub responses so the API and frontend can be wired up.


def get_bom_for_drawing(
    db: Session, drawing_version_id: str
) -> BomResponse:
    """
    Placeholder for BOM extraction.

    Currently:
    - Does NOT query any tables.
    - Returns an empty 'items' list and status 'not_implemented'.

    Later:
    - Populate BomItem rows from the drawing (e.g., title block, BOM table).
    - Query and return those rows here.
    """
    logger.debug("BOM requested for drawing_version_id=%s", drawing_version_id)
    return BomResponse(items=[], status="not_implemented")
