"""SQLAlchemy models for DOKA Brain Soul Layer.

These models are registered with the shared Base so that
``Base.metadata.create_all()`` can pick them up in development,
and the Alembic migration 0002_brain_soul.py handles production.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import declarative_base

# Use a standalone Base so these models never conflict with legacy
# enterprise model definitions that may share the name "Base".
Base = declarative_base()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BrainSoulContext(Base):
    """Soul File — operator context key-value store."""

    __tablename__ = "brain_soul_context"
    __table_args__ = (
        UniqueConstraint("context_key", name="uq_brain_soul_context_key"),
    )

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    context_key: str = Column(String(120), nullable=False, index=True, unique=True)
    context_value: str = Column(Text, nullable=False)
    description: str = Column(String(500), nullable=False, default="")
    is_active: bool = Column(Boolean, nullable=False, default=True)
    updated_by: str = Column(String(40), nullable=False, default="system")
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now, server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.context_key,
            "value": self.context_value,
            "description": self.description,
            "is_active": self.is_active,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BrainSoulSynthesis(Base):
    """Weekly LLM knowledge synthesis snapshot."""

    __tablename__ = "brain_soul_syntheses"
    __table_args__ = (
        UniqueConstraint("period_label", "topic", name="uq_brain_soul_syntheses_period_topic"),
    )

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    period_label: str = Column(String(40), nullable=False, index=True)
    period_start: datetime = Column(DateTime(timezone=True), nullable=False)
    period_end: datetime = Column(DateTime(timezone=True), nullable=False)
    topic: str = Column(String(80), nullable=False, default="documents", index=True)
    synthesis_text: str = Column(Text, nullable=False)
    source_item_ids: str = Column(Text, nullable=False, default="[]")   # JSON list
    item_count: int = Column(Integer, nullable=False, default=0)
    provider: str | None = Column(String(120), nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=_now, index=True, server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "period_label": self.period_label,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "topic": self.topic,
            "synthesis_text": self.synthesis_text,
            "source_item_ids": json.loads(self.source_item_ids or "[]"),
            "item_count": self.item_count,
            "provider": self.provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
