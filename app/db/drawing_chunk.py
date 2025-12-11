# app/db/models/drawing_chunk.py

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from pgvector.sqlalchemy import Vector  # you likely already use this

from app.db.base_class import Base  # your usual Base

class ChunkSourceType(str, enum.Enum):
    NOTE = "note"
    DIMENSION = "dimension"
    SUMMARY = "summary"
    OTHER = "other"  # for future use

class DrawingTextChunk(Base):
    __tablename__ = "drawing_text_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    drawing_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # NOTE / DIMENSION / SUMMARY / OTHER
    source_type: Mapped[ChunkSourceType] = mapped_column(
        Enum(ChunkSourceType, name="chunk_source_type"),
        nullable=False,
        index=True,
    )

    # Raw human-readable text to show in UI
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional machine-friendly structure (for dims/notes)
    # e.g., {"dim_type": "diameter", "value": 12.5, "units": "mm", "tolerance": "+/-0.1"}
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Where in the JSON/geometry this came from (so we can highlight)
    # e.g., {"layer": "DIM", "entity_index": 123, "handle": "4F", "geometry_path": [...]} 
    geometry_index: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Embedding vector from ETL pipeline (L2-normalized)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(dim=1536),  # adjust to your model
        nullable=True,
    )

    # Thumbnail URL for quick preview (you can also store on DrawingVersion)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    drawing_version = relationship("DrawingVersion", back_populates="text_chunks")


# In app/db/models/drawing_version.py, add:
# text_chunks = relationship("DrawingTextChunk", back_populates="drawing_version", cascade="all, delete-orphan")

# Indexes for speed
Index(
    "ix_drawing_text_chunks_dv_src",
    DrawingTextChunk.drawing_version_id,
    DrawingTextChunk.source_type,
)
# Optional trigram/text index added in migration (see below)
