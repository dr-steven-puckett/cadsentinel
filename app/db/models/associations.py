from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base  # your shared Base

drawing_projects = Table(
    "drawing_projects",
    Base.metadata,
    Column("drawing_version_id", UUID(as_uuid=True), nullable=False),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False),
)

drawing_customers = Table(
    "drawing_customers",
    Base.metadata,
    Column("drawing_version_id", UUID(as_uuid=True), nullable=False),
    Column(
        "customer_id",
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    ),
)
