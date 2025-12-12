import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

IssueStatusEnum = Enum("open", "resolved", "ignored", name="issue_status_enum")
IssueSeverityEnum = Enum("info", "warning", "error", name="issue_severity_enum")


class DrawingIssue(Base):
    __tablename__ = "drawing_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drawing_version_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # FK to your DrawingVersion
    standard_id = Column(UUID(as_uuid=True), ForeignKey("standard_documents.id"), nullable=True)
    code = Column(String(128), nullable=True)  # e.g., "ASTM-ABC-001"
    message = Column(String(1024), nullable=False)
    severity = Column(IssueSeverityEnum, nullable=False, default="warning")
    location = Column(JSON, nullable=True)  # {"entity_type": "DIMENSION", "index": 123}
    status = Column(IssueStatusEnum, nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
