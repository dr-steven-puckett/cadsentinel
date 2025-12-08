from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base

EMBEDDING_DIM = 3072  # adjust if you choose a different embedding model


class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)

    original_filename = Column(String, nullable=True)

    ingested_path = Column(String, nullable=False)
    dxf_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    png_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    json_path = Column(String, nullable=True)

    dwg_version = Column(String, nullable=True)
    schema_version = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks = relationship(
        "DrawingChunk",
        back_populates="drawing",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DrawingChunk(Base):
    __tablename__ = "drawing_chunks"

    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(
        Integer,
        ForeignKey("drawings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_type = Column(String(50), nullable=False, index=True)
    label = Column(String, nullable=True)
    source_ref = Column(String, nullable=True)

    text = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)

    # NOTE: attribute name cannot be "metadata" (reserved by SQLAlchemy),
    # but we still name the column "metadata" in the database.
    extra_metadata = Column(
        "metadata",  # actual DB column name
        JSONB,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    drawing = relationship("Drawing", back_populates="chunks")

