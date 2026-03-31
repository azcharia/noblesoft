"""Pydantic models for tenant-scoped user management."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


UserRole = Literal["owner", "admin", "member"]


class TenantUserResponse(BaseModel):
    """User record returned by tenant user APIs."""

    id: str
    tenant_id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole = "member"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Invalid email format")
        return normalized


class TenantUsersListResponse(BaseModel):
    """Paginated response for tenant members."""

    users: list[TenantUserResponse]
    total: int


class TenantUserInviteRequest(BaseModel):
    """Request payload for inviting a new tenant user."""

    email: str
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: UserRole = "member"
    temp_password: Optional[str] = Field(
        None,
        min_length=8,
        description="Optional temporary password. Auto-generated if omitted.",
    )
    auto_confirm_email: bool = False
    include_temporary_password: bool = True

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Invalid email format")
        return normalized


class TenantUserInviteResponse(BaseModel):
    """Invite result response including created user details."""

    user: TenantUserResponse
    temporary_password: Optional[str] = None


class TenantUserDeactivateResponse(BaseModel):
    """Soft-deactivation response payload."""

    user_id: str
    deactivated: bool