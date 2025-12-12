# app/db/models/drawing_chunk.py

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ChunkSource(enum.Enum):
    DIMENSIONS = "dimensions"
    NOTES = "notes"
    JSON = "json"
    SUMMARY = "summary"
    MANUAL = "manual"


class DrawingTextChunk(Base):
    """
    Normalized text chunks associated with a DrawingVersion.

    This is used to:
    - Store pre-tokenized / pre-chunked content for embeddings
    - Tag chunks by source (dimensions, notes, JSON, etc.)
    - Attach metadata about how the chunk was generated
    """

    __tablename__ = "drawing_text_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FK into drawing_versions.id (which is a BigInteger in your core models)
    drawing_version_id = Column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Where this chunk came from
    source_type = Column(
        Enum(ChunkSource, name="chunk_source_enum"),
        nullable=False,
    )

    # The actual text content used for embeddings / search
    content = Column(Text, nullable=False)

    # Optional token count for the chunk
    tokens = Column(Integer, nullable=True)

    # ⚠️ IMPORTANT: 'metadata' is reserved in SQLAlchemy Declarative.
    # Use 'meta' as the Python attribute name but keep the DB column name "metadata".
    meta = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship back to DrawingVersion (add text_chunks relationship on DrawingVersion)
    drawing_version = relationship("DrawingVersion", back_populates="text_chunks")


# Composite index for fast querying by drawing_version_id + source_type
Index(
    "ix_drawing_text_chunks_dv_src",
    DrawingTextChunk.drawing_version_id,
    DrawingTextChunk.source_type,
)
