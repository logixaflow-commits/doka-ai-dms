"""SQLAlchemy ORM models for DOKA Personal Local Edition."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """User account model for Local Authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=True)
    role = Column(String(40), default="staff", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, server_default=func.now())

    folder_permissions = relationship("UserFolderMapping", back_populates="user", foreign_keys="UserFolderMapping.user_id")


class Document(Base):
    """Document metadata and indexing record."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/octet-stream")
    sha256_hash = Column(String(64), nullable=True, index=True)
    status = Column(String(50), default="imported", index=True)
    ocr_text = Column(Text, nullable=True)
    extracted_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, server_default=func.now())


class SOPTemplate(Base):
    """Standard Operating Procedure template for file organization rules."""
    __tablename__ = "sop_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    file_pattern = Column(String(120), nullable=False)
    destination_folder = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())


class FolderPermission(Base):
    """Folder-level permission configuration."""
    __tablename__ = "folder_permissions"

    id = Column(Integer, primary_key=True, index=True)
    folder_path = Column(String(255), unique=True, nullable=False)
    role = Column(String(20), nullable=False, default="staff")
    permission = Column(String(20), nullable=False, default="read")
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user_mappings = relationship("UserFolderMapping", back_populates="folder_permission")


class UserFolderMapping(Base):
    """Mapping between users and folder permissions."""
    __tablename__ = "user_folder_mappings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("folder_permissions.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="folder_permissions", foreign_keys=[user_id])
    folder_permission = relationship("FolderPermission", back_populates="user_mappings")


class AutomationRule(Base):
    """Automation rule for document workflows."""
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    condition = Column(JSON, nullable=False)
    actions = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False, index=True)
    logic = Column(String(10), default="AND")
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_triggered = Column(DateTime(timezone=True), nullable=True)

    execution_logs = relationship("RuleExecutionLog", back_populates="rule")


class RuleExecutionLog(Base):
    """Audit log for automated rule executions."""
    __tablename__ = "rule_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("automation_rules.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    executed = Column(Boolean, nullable=False)
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_now, server_default=func.now())

    rule = relationship("AutomationRule", back_populates="execution_logs")
    document = relationship("Document")


class DocumentVersion(Base):
    """Document version history."""
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)
    file_size = Column(BigInteger, default=0, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=_now, server_default=func.now())
    comment = Column(Text, nullable=True)

    document = relationship("Document")


class AuditLog(Base):
    """Immutable audit trail for file actions, imports, and reviews."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(80), nullable=False, index=True)
    resource_type = Column(String(80), nullable=False, default="document")
    resource_id = Column(String(120), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_now, server_default=func.now())

    document = relationship("Document")


class OCRBatchJobRecord(Base):
    """Durable state for background PDF OCR jobs.

    The worker process may restart while OCR is running, so progress must not
    live only in a process-local dictionary.
    """

    __tablename__ = "ocr_batch_jobs"

    job_id = Column(String(64), primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False)
    status = Column(String(20), nullable=False, default="queued", index=True)
    total_pages = Column(Integer, nullable=False, default=0)
    current_page = Column(Integer, nullable=False, default=0)
    percent = Column(Float, nullable=False, default=0.0)
    worker_id = Column(String(100), nullable=True)
    heartbeat_at = Column(Float, nullable=True)
    started_at = Column(Float, nullable=False)
    completed_at = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    pages_text = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, server_default=func.now())
