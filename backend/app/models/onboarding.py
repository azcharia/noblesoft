"""Pydantic models for onboarding checklist operations."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


OnboardingStatus = Literal["pending", "in_progress", "completed", "skipped"]


class OnboardingItemResponse(BaseModel):
    """Onboarding checklist item response payload."""

    id: str
    tenant_id: str
    code: str
    title: str
    description: Optional[str] = None
    category: str = "general"
    is_required: bool = True
    status: OnboardingStatus = "pending"
    sort_order: int = 0
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingChecklistResponse(BaseModel):
    """Onboarding checklist with summary metrics."""

    items: list[OnboardingItemResponse]
    total: int
    completed: int
    pending: int
    completion_rate: float


class OnboardingItemCreateRequest(BaseModel):
    """Payload to create a new onboarding checklist item."""

    code: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: str = Field(default="general", min_length=2, max_length=100)
    is_required: bool = True
    status: OnboardingStatus = "pending"
    sort_order: int = Field(default=0, ge=0, le=10000)
    due_date: Optional[date] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Onboarding code cannot be empty")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Onboarding category cannot be empty")
        return normalized


class OnboardingItemUpdateRequest(BaseModel):
    """Payload to update onboarding checklist item."""

    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    is_required: Optional[bool] = None
    status: Optional[OnboardingStatus] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=10000)
    due_date: Optional[date] = None

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Onboarding category cannot be empty")
        return normalized
