"""Persist batch OCR job progress across process restarts.

Revision ID: 0003_ocr_batch_jobs
Revises: 0002_brain_soul
Create Date: 2026-10-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ocr_batch_jobs"
down_revision: str | Sequence[str] | None = "0002_brain_soul"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_batch_jobs",
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("heartbeat_at", sa.Float(), nullable=True),
        sa.Column("started_at", sa.Float(), nullable=False),
        sa.Column("completed_at", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("pages_text", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_ocr_batch_jobs_document_id", "ocr_batch_jobs", ["document_id"])
    op.create_index("ix_ocr_batch_jobs_status", "ocr_batch_jobs", ["status"])
    op.create_index("ix_ocr_batch_jobs_created_at", "ocr_batch_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ocr_batch_jobs_created_at", table_name="ocr_batch_jobs")
    op.drop_index("ix_ocr_batch_jobs_status", table_name="ocr_batch_jobs")
    op.drop_index("ix_ocr_batch_jobs_document_id", table_name="ocr_batch_jobs")
    op.drop_table("ocr_batch_jobs")
