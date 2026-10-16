"""Pydantic schemas and enums for DOKA DMS."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CUSTOMER = "customer"


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class ReportType(str, Enum):
    ACCESS_LOG = "access_log"
    DOCUMENT_ACTIVITY = "document_activity"
    COMPLIANCE = "compliance"
    AUDIT_TRAIL = "audit_trail"


class ReportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    JSON = "json"


class RuleConditionSchema(BaseModel):
    field: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Any] = None


class RuleActionSchema(BaseModel):
    type: str
    target: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class RuleCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    condition: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    priority: int = 0
    logic: str = "AND"


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    logic: Optional[str] = None


class RuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    condition: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool
    priority: int
    logic: str
    created_at: Optional[datetime] = None
    last_triggered: Optional[datetime] = None

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "general"
    file_pattern: Optional[str] = "*.*"
    destination_folder: Optional[str] = "Organized"
    steps: Optional[List[Dict[str, Any]]] = None


class FolderPermissionCreate(BaseModel):
    folder_path: str
    role: str = "staff"
    permission: PermissionLevel = PermissionLevel.READ


class FolderPermissionResponse(BaseModel):
    id: int = 0
    folder_path: str
    role: str
    permission: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserFolderPermissionAssign(BaseModel):
    user_id: int
    folder_path: str
    permission: PermissionLevel = PermissionLevel.READ


class UserFolderPermissionRemove(BaseModel):
    user_id: int
    folder_path: str


class UserFolderPermissionsResponse(BaseModel):
    user_id: int
    username: str
    permissions: List[FolderPermissionResponse] = []


class FolderAccessCheck(BaseModel):
    folder_path: str
    action: PermissionLevel = PermissionLevel.READ


class FolderAccessResponse(BaseModel):
    has_access: bool
    folder_path: str
    action: str
    reason: Optional[str] = None
