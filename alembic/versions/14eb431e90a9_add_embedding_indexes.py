"""add embedding indexes

Revision ID: 14eb431e90a9
Revises: ad64b9caba1a
Create Date: 2025-12-10 15:50:43.085632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# alembic/versions/20251210_add_embedding_indexes.py

# revision identifiers, used by Alembic.
revision = '14eb431e90a9'
down_revision = 'ad64b9caba1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension exists (in case it's not created elsewhere)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # IVFFLAT index for vector cosine similarity on embeddings.embedding
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_embeddings_embedding_ivfflat
        ON embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    )

    # Trigram full-text-ish search for embeddings.content
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_embeddings_content_trgm
        ON embeddings
        USING gin (content gin_trgm_ops);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_content_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_embedding_ivfflat;")
