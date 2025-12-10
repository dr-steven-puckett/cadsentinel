"""add cadsentinel core schema

Revision ID: 123456789abc
Revises: b2747a985e17   # <- your existing revision, if any
Create Date: 2025-12-08 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "123456789abc"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (safe if already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. drawings
    op.create_table(
        "drawings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("document_id_sha", sa.String(), nullable=False, unique=True),
        sa.Column("part_number", sa.String(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_code", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. drawing_versions
    op.create_table(
        "drawing_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_id",
            sa.BigInteger(),
            sa.ForeignKey("drawings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_label", sa.String(), nullable=True),
        sa.Column("dwg_sha256", sa.String(), nullable=False, unique=True),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_by", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    # Unique index for active version per drawing
    op.create_unique_constraint(
        "uq_drawing_versions_active",
        "drawing_versions",
        ["drawing_id", "is_active"],
        deferrable=False,
        initially="IMMEDIATE",
    )

    # 3. drawing_files
    op.create_table(
        "drawing_files",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_version_id",
            sa.BigInteger(),
            sa.ForeignKey("drawing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_drawing_files_version_type",
        "drawing_files",
        ["drawing_version_id", "file_type"],
    )

    # 4. drawing_summaries
    op.create_table(
        "drawing_summaries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_version_id",
            sa.BigInteger(),
            sa.ForeignKey("drawing_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("structured_summary", postgresql.JSONB(), nullable=False),
        sa.Column("long_form_description", sa.Text(), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. dimensions
    op.create_table(
        "dimensions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_version_id",
            sa.BigInteger(),
            sa.ForeignKey("drawing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("json_index", sa.Integer(), nullable=True),
        sa.Column("dim_type", sa.String(), nullable=False),
        sa.Column("raw_type_code", sa.Integer(), nullable=True),
        sa.Column("layer", sa.String(), nullable=True),
        sa.Column("handle", sa.String(), nullable=True),
        sa.Column("owner_handle", sa.String(), nullable=True),
        sa.Column("dim_text", sa.Text(), nullable=True),
        sa.Column("dim_value", sa.Float(), nullable=True),
        sa.Column("units", sa.String(), nullable=True),
        sa.Column("geometry", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_dimensions_version",
        "dimensions",
        ["drawing_version_id"],
    )
    op.create_index(
        "idx_dimensions_layer",
        "dimensions",
        ["layer"],
    )

    # 6. notes
    op.create_table(
        "notes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_version_id",
            sa.BigInteger(),
            sa.ForeignKey("drawing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("json_index", sa.Integer(), nullable=True),
        sa.Column("note_type", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("layer", sa.String(), nullable=True),
        sa.Column("handle", sa.String(), nullable=True),
        sa.Column("geometry", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_notes_version_type",
        "notes",
        ["drawing_version_id", "note_type"],
    )

    # 7. embeddings
    op.create_table(
        "embeddings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_version_id",
            sa.BigInteger(),
            sa.ForeignKey("drawing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_ref_id", sa.BigInteger(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_embeddings_version_source",
        "embeddings",
        ["drawing_version_id", "source_type"],
    )
    # ivfflat index for vector search (optional, can be added later)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_embeddings_vector_ivfflat
        ON embeddings
        USING ivfflat (embedding vector_l2_ops)
        WITH (lists = 100)
        """
    )

    # 8. engineering_standards
    op.create_table(
        "engineering_standards",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. standard_rules
    op.create_table(
        "standard_rules",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "standard_id",
            sa.BigInteger(),
            sa.ForeignKey("engineering_standards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="warning"),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_standard_rules_code",
        "standard_rules",
        ["standard_id", "rule_code"],
    )

    # 10. standard_violations
    op.create_table(
        "standard_violations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "drawing_version_id",
            sa.BigInteger(),
            sa.ForeignKey("drawing_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            sa.BigInteger(),
            sa.ForeignKey("standard_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dimension_id",
            sa.BigInteger(),
            sa.ForeignKey("dimensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "note_id",
            sa.BigInteger(),
            sa.ForeignKey("notes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dwg_handle", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_standard_violations_version",
        "standard_violations",
        ["drawing_version_id"],
    )
    op.create_index(
        "idx_standard_violations_rule",
        "standard_violations",
        ["rule_id"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("idx_standard_violations_rule", table_name="standard_violations")
    op.drop_index("idx_standard_violations_version", table_name="standard_violations")
    op.drop_table("standard_violations")

    op.drop_constraint("uq_standard_rules_code", "standard_rules", type_="unique")
    op.drop_table("standard_rules")

    op.drop_table("engineering_standards")

    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat")
    op.drop_index("idx_embeddings_version_source", table_name="embeddings")
    op.drop_table("embeddings")

    op.drop_index("idx_notes_version_type", table_name="notes")
    op.drop_table("notes")

    op.drop_index("idx_dimensions_layer", table_name="dimensions")
    op.drop_index("idx_dimensions_version", table_name="dimensions")
    op.drop_table("dimensions")

    op.drop_table("drawing_summaries")

    op.drop_index("idx_drawing_files_version_type", table_name="drawing_files")
    op.drop_table("drawing_files")

    op.drop_constraint("uq_drawing_versions_active", "drawing_versions", type_="unique")
    op.drop_table("drawing_versions")

    op.drop_table("drawings")
