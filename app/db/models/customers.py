import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(64), nullable=True, unique=True)
    contact_info = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
