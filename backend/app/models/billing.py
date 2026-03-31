"""Pydantic models for billing and Midtrans integration endpoints."""
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


PaidTier = Literal["basic", "pro", "enterprise"]


class BillingTransactionRequest(BaseModel):
    """Request payload to create a Midtrans Snap transaction."""

    target_tier: PaidTier
    amount: Decimal = Field(..., gt=0)
    order_id: Optional[str] = Field(None, min_length=6, max_length=100)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = Field(None, min_length=5, max_length=50)
    notes: Optional[str] = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def _normalize_amount(cls, value: Decimal) -> Decimal:
        return round(value, 2)

    @field_validator("customer_email")
    @classmethod
    def _validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Invalid email format")
        return normalized


class BillingTransactionResponse(BaseModel):
    """Response payload from transaction creation."""

    order_id: str
    token: str
    redirect_url: str
    target_tier: PaidTier
    amount: Decimal


class MidtransWebhookRequest(BaseModel):
    """Inbound Midtrans webhook payload schema (subset)."""

    order_id: str
    status_code: str
    gross_amount: str
    signature_key: str
    transaction_status: str
    fraud_status: Optional[str] = None
    custom_field1: Optional[str] = None
    custom_field2: Optional[str] = None


class MidtransWebhookResponse(BaseModel):
    """Webhook handling result response."""

    accepted: bool
    message: str
    tenant_id: Optional[str] = None
    updated_tier: Optional[str] = None


class BillingStatusResponse(BaseModel):
    """Current billing status for authenticated tenant."""

    tenant_id: str
    company_name: str
    subscription_tier: str
    is_active: bool
    max_users: int
    payment_gateway_customer_id: Optional[str] = None