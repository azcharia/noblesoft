"""Pydantic models for governance and branches management."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleResponse(BaseModel):
    """Role configuration entity."""

    id: str
    tenant_id: str
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    """Paginated role list response."""

    roles: list[RoleResponse]
    total: int


class RoleCreateRequest(BaseModel):
    """Payload to create a custom role."""

    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    copy_from_role_id: Optional[str] = None

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Role code cannot be empty")
        return normalized


class RoleUpdateRequest(BaseModel):
    """Payload to update a role."""

    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class RoleDeleteResponse(BaseModel):
    """Response payload for role deletion."""

    role_id: str
    deleted: bool


class PermissionResponse(BaseModel):
    """Permission definition row."""

    id: str
    code: str
    name: str
    resource: str
    action: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RolePermissionRow(BaseModel):
    """Permission matrix row for a role."""

    role_id: str
    role_code: str
    permission_codes: list[str]


class RolePermissionMatrixResponse(BaseModel):
    """Full permission matrix response."""

    roles: list[RolePermissionRow]
    permissions: list[PermissionResponse]


class RolePermissionUpdateRequest(BaseModel):
    """Payload to replace permissions for a role."""

    permission_codes: list[str] = Field(default_factory=list)


class BranchResponse(BaseModel):
    """Branch entity response."""

    id: str
    tenant_id: str
    code: str
    name: str
    location: Optional[str] = None
    manager_user_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BranchListResponse(BaseModel):
    """Paginated branch list response."""

    branches: list[BranchResponse]
    total: int


class BranchCreateRequest(BaseModel):
    """Payload to create a branch."""

    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    manager_user_id: Optional[str] = None

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Branch code cannot be empty")
        return normalized


class BranchUpdateRequest(BaseModel):
    """Payload to update a branch."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    manager_user_id: Optional[str] = None
    is_active: Optional[bool] = None


class BranchAssignmentRequest(BaseModel):
    """Payload to assign primary branch to a user."""

    user_id: str
    branch_id: str


class BranchAssignmentResponse(BaseModel):
    """Response for branch assignment operation."""

    user_id: str
    branch_id: str
    updated: bool


class BranchDeleteResponse(BaseModel):
    """Response payload for branch deletion."""

    branch_id: str
    deleted: bool


class AuditLogEntry(BaseModel):
    """Audit trail entry."""

    id: str
    tenant_id: str
    actor_user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    old_values: Optional[dict[str, Any]] = None
    new_values: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""

    logs: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
    has_more: bool
