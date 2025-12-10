# app/db/models.py

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, DOUBLE_PRECISION

from sqlalchemy.orm import relationship, Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from .base import Base


# =========================================================
# 1. Core drawing + versions
# =========================================================

class Drawing(Base):
    __tablename__ = "drawings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Stable identifier for the logical drawing / part
    document_id_sha: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Optional human-friendly identifiers
    part_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    versions: Mapped[List["DrawingVersion"]] = relationship(
        "DrawingVersion",
        back_populates="drawing",
        cascade="all, delete-orphan",
    )


class DrawingVersion(Base):
    __tablename__ = "drawing_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawings.id", ondelete="CASCADE"),
        nullable=False,
    )

    revision_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Hash of specific DWG bytes
    dwg_sha256: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    source_filename: Mapped[str] = mapped_column(Text, nullable=False)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    ingested_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    drawing: Mapped["Drawing"] = relationship(
        "Drawing",
        back_populates="versions",
    )

    files: Mapped[List["DrawingFile"]] = relationship(
        "DrawingFile",
        back_populates="drawing_version",
        cascade="all, delete-orphan",
    )

    summary: Mapped[Optional["DrawingSummary"]] = relationship(
        "DrawingSummary",
        back_populates="drawing_version",
        uselist=False,
        cascade="all, delete-orphan",
    )

    dimensions: Mapped[List["Dimension"]] = relationship(
        "Dimension",
        back_populates="drawing_version",
        cascade="all, delete-orphan",
    )

    notes: Mapped[List["Note"]] = relationship(
        "Note",
        back_populates="drawing_version",
        cascade="all, delete-orphan",
    )

    embeddings: Mapped[List["Embedding"]] = relationship(
        "Embedding",
        back_populates="drawing_version",
        cascade="all, delete-orphan",
    )

    violations: Mapped[List["StandardViolation"]] = relationship(
        "StandardViolation",
        back_populates="drawing_version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Only one active version per drawing
        UniqueConstraint(
            "drawing_id",
            "is_active",
            name="uq_drawing_versions_active",
            deferrable=False,
            initially="IMMEDIATE",
        ),
    )


# =========================================================
# 2. File paths per version
# =========================================================

class DrawingFile(Base):
    __tablename__ = "drawing_files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "dwg" | "dxf" | "json" | "pdf" | "png_full" | "png_thumb"
    file_type: Mapped[str] = mapped_column(String, nullable=False)

    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    drawing_version: Mapped["DrawingVersion"] = relationship(
        "DrawingVersion",
        back_populates="files",
    )


Index(
    "idx_drawing_files_version_type",
    DrawingFile.drawing_version_id,
    DrawingFile.file_type,
)


# =========================================================
# 3. LLM multimodal summary per version
# =========================================================

class DrawingSummary(Base):
    __tablename__ = "drawing_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one summary per version
    )

    structured_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    long_form_description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    drawing_version: Mapped["DrawingVersion"] = relationship(
        "DrawingVersion",
        back_populates="summary",
    )


# =========================================================
# 4. Dimensions (from C++ JSON `dimensions[]`)
# =========================================================

class Dimension(Base):
    __tablename__ = "dimensions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    json_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    dim_type: Mapped[str] = mapped_column(String, nullable=False)
    raw_type_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    layer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    dim_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dim_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


    # If you’d like explicit type (recommended):
    # dim_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    units: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    geometry: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    drawing_version: Mapped["DrawingVersion"] = relationship(
        "DrawingVersion",
        back_populates="dimensions",
    )

    violations: Mapped[List["StandardViolation"]] = relationship(
        "StandardViolation",
        back_populates="dimension",
    )


Index("idx_dimensions_version", Dimension.drawing_version_id)
Index("idx_dimensions_layer", Dimension.layer)


# =========================================================
# 5. Notes (tolerance, GD&T, general text)
# =========================================================

class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    json_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # "tolerance" | "gdandt" | "general"
    note_type: Mapped[str] = mapped_column(String, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    layer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    geometry: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    drawing_version: Mapped["DrawingVersion"] = relationship(
        "DrawingVersion",
        back_populates="notes",
    )

    violations: Mapped[List["StandardViolation"]] = relationship(
        "StandardViolation",
        back_populates="note",
    )


Index("idx_notes_version_type", Note.drawing_version_id, Note.note_type)


# =========================================================
# 6. Single embeddings table (Option A)
# =========================================================

class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "summary" | "dimension" | "note" | "gdandt" | ...
    source_type: Mapped[str] = mapped_column(String, nullable=False)

    # ID in drawing_summaries / dimensions / notes etc.
    source_ref_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Match dimension to your embedding model (e.g., vector(1536))
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    drawing_version: Mapped["DrawingVersion"] = relationship(
        "DrawingVersion",
        back_populates="embeddings",
    )


Index(
    "idx_embeddings_version_source",
    Embedding.drawing_version_id,
    Embedding.source_type,
)

# Note: ivfflat index on embedding will be created in Alembic migration
# using op.execute(...).


# =========================================================
# 7. Standards + rules + violations
# =========================================================

class EngineeringStandard(Base):
    __tablename__ = "engineering_standards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # FIXED: renamed attribute to avoid conflict with SQLAlchemy Declarative
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",  # DB column name
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    rules: Mapped[List["StandardRule"]] = relationship(
        "StandardRule",
        back_populates="standard",
        cascade="all, delete-orphan",
    )



class StandardRule(Base):
    __tablename__ = "standard_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    standard_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("engineering_standards.id", ondelete="CASCADE"),
        nullable=False,
    )

    rule_code: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # "dimension" | "note" | "drawing"
    scope: Mapped[str] = mapped_column(String, nullable=False)

    # "info" | "warning" | "error"
    severity: Mapped[str] = mapped_column(String, nullable=False, default="warning")

    config: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    standard: Mapped["EngineeringStandard"] = relationship(
        "EngineeringStandard",
        back_populates="rules",
    )

    violations: Mapped[List["StandardViolation"]] = relationship(
        "StandardViolation",
        back_populates="rule",
    )

    __table_args__ = (
        UniqueConstraint(
            "standard_id",
            "rule_code",
            name="uq_standard_rules_code",
        ),
    )


class StandardViolation(Base):
    __tablename__ = "standard_violations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    drawing_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    rule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("standard_rules.id", ondelete="CASCADE"),
        nullable=False,
    )

    dimension_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("dimensions.id", ondelete="SET NULL"),
        nullable=True,
    )

    note_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("notes.id", ondelete="SET NULL"),
        nullable=True,
    )

    dwg_handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="open")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    drawing_version: Mapped["DrawingVersion"] = relationship(
        "DrawingVersion",
        back_populates="violations",
    )

    rule: Mapped["StandardRule"] = relationship(
        "StandardRule",
        back_populates="violations",
    )

    dimension: Mapped[Optional["Dimension"]] = relationship(
        "Dimension",
        back_populates="violations",
    )

    note: Mapped[Optional["Note"]] = relationship(
        "Note",
        back_populates="violations",
    )


Index("idx_standard_violations_version", StandardViolation.drawing_version_id)
Index("idx_standard_violations_rule", StandardViolation.rule_id)
