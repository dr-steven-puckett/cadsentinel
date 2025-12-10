"""add cadsentinel core schema

Revision ID: ad64b9caba1a
Revises: 454307bfeba0
Create Date: 2025-12-09 19:39:10.190733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad64b9caba1a'
down_revision: Union[str, Sequence[str], None] = '454307bfeba0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
