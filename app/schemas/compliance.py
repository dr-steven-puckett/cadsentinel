from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SpellcheckRequest(BaseModel):
    standards: List[str] = []
    include_gdt: bool = True


class IssueItem(BaseModel):
    issue_id: str
    standard_id: Optional[str] = None
    code: Optional[str] = None
    message: str
    severity: str
    location: Dict[str, Any] | None = None
    status: str
    created_at: datetime


class IssuesListResponse(BaseModel):
    drawing_version_id: str
    issues_found: int
    issues: List[IssueItem]


class IssuesCountResponse(BaseModel):
    drawing_version_id: str
    count: int
