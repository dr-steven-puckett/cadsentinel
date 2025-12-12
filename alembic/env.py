from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# ---------------------------------------------------------
# Make sure /mnt/cadsentinel is on sys.path so `import app` works
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401 - import models so Base.metadata is populated

# This is the Alembic Config object, which provides access
# to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load app settings (DATABASE_URL from .env, etc.)
settings = get_settings()

# Use your application's metadata for autogenerate support
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Control which DB objects Alembic considers when autogenerating migrations.

    We explicitly IGNORE a few manually-managed indexes on the `embeddings` table
    that are created outside of SQLAlchemy (e.g., pgvector / trigram indexes):

      - idx_embeddings_vector_ivfflat
      - ix_embeddings_content_trgm
      - ix_embeddings_embedding_ivfflat
    """
    if type_ == "index" and name in (
        "idx_embeddings_vector_ivfflat",
        "ix_embeddings_content_trgm",
        "ix_embeddings_embedding_ivfflat",
    ):
        # Don't treat these as schema diffs (keep them as-is in the DB)
        return False

    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Uses the app's DATABASE_URL directly.
    """
    url = settings.database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,  # <- ignore special indexes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Uses SQLAlchemy's create_engine with the app's DATABASE_URL.
    """
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,  # <- ignore special indexes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
