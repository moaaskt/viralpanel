"""add metadata_json to scripts

Revision ID: 002
Revises: 001
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable metadata_json column to scripts table."""
    op.add_column("scripts", sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove metadata_json column from scripts table."""
    op.drop_column("scripts", "metadata_json")
