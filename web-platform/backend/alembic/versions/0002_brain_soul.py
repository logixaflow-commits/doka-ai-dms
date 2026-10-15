"""Add brain soul tables for DOKA AI DMS

Revision ID: 0002_brain_soul
Revises: 0001_doka_baseline
Create Date: 2026-10-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_brain_soul"
down_revision: Union[str, Sequence[str], None] = "0001_doka_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── brain_soul_context (Soul File key-value store) ────────────────────────
    op.create_table(
        "brain_soul_context",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("context_key", sa.String(length=120), nullable=False),
        sa.Column("context_value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("context_key", name="uq_brain_soul_context_key"),
    )
    op.create_index("ix_brain_soul_context_key", "brain_soul_context", ["context_key"], unique=True)
    op.create_index("ix_brain_soul_context_active", "brain_soul_context", ["is_active"])

    # ── brain_soul_syntheses (weekly LLM snapshot) ────────────────────────────
    op.create_table(
        "brain_soul_syntheses",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("period_label", sa.String(length=40), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("topic", sa.String(length=80), nullable=False, server_default="documents"),
        sa.Column("synthesis_text", sa.Text(), nullable=False),
        sa.Column("source_item_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period_label", "topic", name="uq_brain_soul_syntheses_period_topic"),
    )
    op.create_index("ix_brain_soul_syntheses_period", "brain_soul_syntheses", ["period_label"])
    op.create_index("ix_brain_soul_syntheses_topic", "brain_soul_syntheses", ["topic"])
    op.create_index("ix_brain_soul_syntheses_created", "brain_soul_syntheses", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_brain_soul_syntheses_created", table_name="brain_soul_syntheses")
    op.drop_index("ix_brain_soul_syntheses_topic", table_name="brain_soul_syntheses")
    op.drop_index("ix_brain_soul_syntheses_period", table_name="brain_soul_syntheses")
    op.drop_table("brain_soul_syntheses")

    op.drop_index("ix_brain_soul_context_active", table_name="brain_soul_context")
    op.drop_index("ix_brain_soul_context_key", table_name="brain_soul_context")
    op.drop_table("brain_soul_context")
