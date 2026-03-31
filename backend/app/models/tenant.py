"""Pydantic models for tenant management endpoints."""
from datetime import datetime
from typing import Literal, Optional

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