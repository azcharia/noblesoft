"""Pydantic models for tenant management endpoints."""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SubscriptionTier = Literal["trial", "basic", "pro", "enterprise"]


class TenantResponse(BaseModel):
    """Tenant profile returned by management endpoints."""

    id: str
    company_name: str
    subscription_tier: SubscriptionTier
    trial_start_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    is_active: bool = True
    max_users: int = 5
    payment_gateway_customer_id: Optional[str] = None
    billing_period: Literal["monthly", "annual"] = "monthly"
    active_add_ons: list[dict[str, Any]] = Field(default_factory=list)
    billing_start_date: Optional[datetime] = None
    billing_end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUpdate(BaseModel):
    """Editable tenant properties."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    max_users: Optional[int] = Field(None, ge=1, le=5000)


class SubscriptionUpdateRequest(BaseModel):
    """Request payload for owner-driven subscription update."""

    subscription_tier: SubscriptionTier = Field(
        ..., description="Target subscription tier"
    )


class SubscriptionUpdateResponse(BaseModel):
    """Response after a subscription update operation."""

    tenant: TenantResponse
    previous_tier: SubscriptionTier
    updated_tier: SubscriptionTier


class TenantRegisterRequest(BaseModel):
    """Request payload for registering a new tenant store and owner account."""

    company_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=255)


class TenantRegisterResponse(BaseModel):
    """Response returned after successful tenant registration."""

    tenant_id: str
    company_name: str
    user_id: str
    email: str
    message: str


class TenantAISettingsResponse(BaseModel):
    """AI settings returned by management endpoints."""

    tenant_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str = "llama-3.1-8b-instant"
    temperature: float = 0.2
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantAISettingsUpdate(BaseModel):
    """Request payload for updating tenant-specific AI settings."""

    api_key: Optional[str] = Field(None, max_length=255)
    base_url: Optional[str] = Field(None, max_length=512)
    model_name: Optional[str] = Field(None, max_length=100)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)