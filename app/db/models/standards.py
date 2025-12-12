import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base



class StandardDocument(Base):
    __tablename__ = "standard_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=False)  # path on disk or object store key
    summary = Column(Text, nullable=True)
    rules_json = Column(JSON, nullable=True)  # extracted rules, placeholder
    embedding_stats = Column(JSON, nullable=True)  # {"chunks": int, "dim": int, ...}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
