"""Add durable storage for optional external API integrations.

Revision ID: 0004_external_api_integrations
Revises: 0003_ocr_batch_jobs
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_external_api_integrations"
down_revision: str | Sequence[str] | None = "0003_ocr_batch_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_api_providers",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("auth_type", sa.String(length=30), nullable=False),
        sa.Column("auth_config", sa.Text(), nullable=False),
        sa.Column("endpoints", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("webhook_secret", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_external_api_providers_name", "external_api_providers", ["name"], unique=True)
    op.create_index("ix_external_api_providers_provider_type", "external_api_providers", ["provider_type"])
    op.create_index("ix_external_api_providers_enabled", "external_api_providers", ["enabled"])

    op.create_table(
        "external_api_logs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("request", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["external_api_providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_api_logs_provider_id", "external_api_logs", ["provider_id"])
    op.create_index("ix_external_api_logs_document_id", "external_api_logs", ["document_id"])
    op.create_index("ix_external_api_logs_timestamp", "external_api_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_external_api_logs_timestamp", table_name="external_api_logs")
    op.drop_index("ix_external_api_logs_document_id", table_name="external_api_logs")
    op.drop_index("ix_external_api_logs_provider_id", table_name="external_api_logs")
    op.drop_table("external_api_logs")
    op.drop_index("ix_external_api_providers_enabled", table_name="external_api_providers")
    op.drop_index("ix_external_api_providers_provider_type", table_name="external_api_providers")
    op.drop_index("ix_external_api_providers_name", table_name="external_api_providers")
    op.drop_table("external_api_providers")
