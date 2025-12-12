import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base



class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
