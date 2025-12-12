import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.compliance import (
    SpellcheckRequest,
    IssuesListResponse,
    IssuesCountResponse,
)
from app.services import compliance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drawings", tags=["spellcheck"])


@router.post(
    "/{drawing_version_id}/spellcheck",
    response_model=IssuesListResponse,
    summary="Run spellcheck/compliance check against standards (placeholder)",
)
def run_spellcheck(
    drawing_version_id: str,
    req: SpellcheckRequest,
    db: Session = Depends(get_db),
):
    return compliance_service.run_spellcheck(db, drawing_version_id, req)


@router.get(
    "/{drawing_version_id}/issues",
    response_model=IssuesListResponse,
    summary="List issues for drawing",
)
def get_issues(
    drawing_version_id: str,
    db: Session = Depends(get_db),
):
    return compliance_service.list_issues(db, drawing_version_id)


@router.get(
    "/{drawing_version_id}/issues/count",
    response_model=IssuesCountResponse,
    summary="Count issues for drawing",
)
def get_issues_count(
    drawing_version_id: str,
    db: Session = Depends(get_db),
):
    return compliance_service.count_issues(db, drawing_version_id)
