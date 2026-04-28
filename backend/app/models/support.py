"""Pydantic models for support ticketing and SLA tracking."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


SupportPriority = Literal["p1", "p2", "p3"]
SupportStatus = Literal["open", "in_progress", "resolved", "closed"]


class SupportTicketResponse(BaseModel):
    """Support ticket entity response."""

    id: str
    tenant_id: str
    ticket_number: str
    title: str
    description: Optional[str] = None
    category: str = "general"
    priority: SupportPriority = "p3"
    status: SupportStatus = "open"
    requester_user_id: Optional[str] = None
    assignee_user_id: Optional[str] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    sla_response_deadline: datetime
    sla_resolution_deadline: datetime
    is_sla_response_breached: bool = False
    is_sla_resolution_breached: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportTicketListResponse(BaseModel):
    """Paginated support ticket list response."""

    tickets: list[SupportTicketResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class SupportTicketCreateRequest(BaseModel):
    """Payload to create support ticket."""

    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: str = Field(default="general", min_length=2, max_length=100)
    priority: SupportPriority = "p3"
    assignee_user_id: Optional[str] = None

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Support category cannot be empty")
        return normalized


class SupportTicketUpdateRequest(BaseModel):
    """Payload to update support ticket."""

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    priority: Optional[SupportPriority] = None
    status: Optional[SupportStatus] = None
    assignee_user_id: Optional[str] = None

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Support category cannot be empty")
        return normalized


class SupportTicketAssignRequest(BaseModel):
    """Payload to assign support ticket to a user."""

    assignee_user_id: str = Field(..., min_length=1)


class SupportTicketCommentCreateRequest(BaseModel):
    """Payload to add support ticket comment."""

    content: str = Field(..., min_length=1, max_length=6000)
    is_internal: bool = True


class SupportTicketCommentResponse(BaseModel):
    """Support comment entity response."""

    id: str
    tenant_id: str
    ticket_id: str
    author_user_id: Optional[str] = None
    content: str
    is_internal: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportTicketDetailResponse(BaseModel):
    """Single support ticket detail response with comments."""

    ticket: SupportTicketResponse
    comments: list[SupportTicketCommentResponse]


class SupportOverviewResponse(BaseModel):
    """Support ticket high-level metrics."""

    total_open: int
    total_in_progress: int
    total_resolved: int
    total_closed: int
    sla_response_breached: int
    sla_resolution_breached: int
