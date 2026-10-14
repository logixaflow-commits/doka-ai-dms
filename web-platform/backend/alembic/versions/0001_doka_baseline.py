"""Initial baseline schema for Doka AI DMS

Revision ID: 0001_doka_baseline
Revises: 
Create Date: 2026-10-14 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_doka_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are dynamically managed by Base.metadata.create_all; 
    # This migration serves as the certified baseline for future schema changes.
    pass


def downgrade() -> None:
    pass
