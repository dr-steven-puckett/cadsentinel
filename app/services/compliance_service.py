import logging
from typing import List

from sqlalchemy.orm import Session

from app.db.models.issues import DrawingIssue
from app.schemas.compliance import (
    SpellcheckRequest,
    IssueItem,
    IssuesListResponse,
    IssuesCountResponse,
)

logger = logging.getLogger(__name__)


def run_spellcheck(
    db: Session,
    drawing_version_id: str,
    req: SpellcheckRequest,
) -> IssuesListResponse:
    """
    Placeholder implementation: returns zero issues and does not modify DB.
    Later this will:
    - Build LLM prompts using standards
    - Compare drawing JSON / notes / dims to rule set
    - Store issues in DrawingIssue table
    """
    logger.debug(
        "Spellcheck requested for drawing_version_id=%s standards=%s include_gdt=%s",
        drawing_version_id,
        req.standards,
        req.include_gdt,
    )
    return IssuesListResponse(
        drawing_version_id=drawing_version_id,
        issues_found=0,
        issues=[],
    )


def list_issues(
    db: Session,
    drawing_version_id: str,
) -> IssuesListResponse:
    q = (
        db.query(DrawingIssue)
        .filter(DrawingIssue.drawing_version_id == drawing_version_id)
        .order_by(DrawingIssue.created_at.asc())
    )
    issues: List[IssueItem] = [
        IssueItem(
            issue_id=str(i.id),
            standard_id=str(i.standard_id) if i.standard_id else None,
            code=i.code,
            message=i.message,
            severity=i.severity,
            location=i.location,
            status=i.status,
            created_at=i.created_at,
        )
        for i in q.all()
    ]
    return IssuesListResponse(
        drawing_version_id=drawing_version_id,
        issues_found=len(issues),
        issues=issues,
    )


def count_issues(
    db: Session,
    drawing_version_id: str,
) -> IssuesCountResponse:
    count = (
        db.query(DrawingIssue)
        .filter(DrawingIssue.drawing_version_id == drawing_version_id)
        .count()
    )
    return IssuesCountResponse(
        drawing_version_id=drawing_version_id,
        count=count,
    )
