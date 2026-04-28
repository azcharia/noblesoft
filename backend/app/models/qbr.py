"""Pydantic models for QBR cycles, goals, and dashboard metrics."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


QBRCycleStatus = Literal["draft", "active", "completed"]
QBRGoalStatus = Literal["on_track", "at_risk", "off_track", "achieved"]


class QBRCycleResponse(BaseModel):
    """QBR cycle response payload."""

    id: str
    tenant_id: str
    quarter_code: str
    title: Optional[str] = None
    start_date: date
    end_date: date
    status: QBRCycleStatus = "draft"
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QBRCycleListResponse(BaseModel):
    """Paginated QBR cycle list response."""

    cycles: list[QBRCycleResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class QBRCycleCreateRequest(BaseModel):
    """Payload to create QBR cycle."""

    quarter_code: str = Field(..., min_length=6, max_length=10)
    title: Optional[str] = Field(default=None, max_length=255)
    start_date: date
    end_date: date
    status: QBRCycleStatus = "draft"
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("quarter_code")
    @classmethod
    def normalize_quarter_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Quarter code cannot be empty")
        return normalized


class QBRCycleUpdateRequest(BaseModel):
    """Payload to update QBR cycle."""

    title: Optional[str] = Field(default=None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[QBRCycleStatus] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class QBRGoalResponse(BaseModel):
    """QBR goal response payload."""

    id: str
    tenant_id: str
    cycle_id: str
    title: str
    description: Optional[str] = None
    metric_name: Optional[str] = None
    unit: Optional[str] = None
    target_value: float
    current_value: float
    owner_user_id: Optional[str] = None
    status: QBRGoalStatus = "on_track"
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    progress_percentage: float = 0

    model_config = ConfigDict(from_attributes=True)


class QBRGoalListResponse(BaseModel):
    """Paginated QBR goals list response."""

    goals: list[QBRGoalResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class QBRGoalCreateRequest(BaseModel):
    """Payload to create QBR goal."""

    cycle_id: str
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    metric_name: Optional[str] = Field(default=None, max_length=100)
    unit: Optional[str] = Field(default=None, max_length=30)
    target_value: float = Field(...)
    current_value: float = Field(default=0)
    owner_user_id: Optional[str] = None
    status: QBRGoalStatus = "on_track"
    due_date: Optional[date] = None


class QBRGoalUpdateRequest(BaseModel):
    """Payload to update QBR goal."""

    cycle_id: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    metric_name: Optional[str] = Field(default=None, max_length=100)
    unit: Optional[str] = Field(default=None, max_length=30)
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    owner_user_id: Optional[str] = None
    status: Optional[QBRGoalStatus] = None
    due_date: Optional[date] = None


class QBRMetricsSummary(BaseModel):
    """Auto-generated QBR metrics from operational data."""

    paid_revenue: float
    unpaid_invoice_count: int
    total_products: int
    low_stock_products: int


class QBRDashboardResponse(BaseModel):
    """QBR dashboard data including current cycle, goals, and metrics."""

    cycle: Optional[QBRCycleResponse] = None
    goals: list[QBRGoalResponse]
    metrics: QBRMetricsSummary
