"""add cadsentinel core schema

Revision ID: 454307bfeba0
Revises: 8e9ef0bc2b4d
Create Date: 2025-12-09 19:23:35.126222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '454307bfeba0'
down_revision: Union[str, Sequence[str], None] = '8e9ef0bc2b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
