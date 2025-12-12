import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class BomItem(Base):
    __tablename__ = "bom_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drawing_version_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # FK to your drawing version
    item_number = Column(Integer, nullable=True)
    part_number = Column(String(255), nullable=True)
    description = Column(String(1024), nullable=True)
    quantity = Column(Integer, nullable=True)
    unit = Column(String(64), nullable=True)
    notes = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
