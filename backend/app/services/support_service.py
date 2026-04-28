"""Service layer for support ticketing and SLA tracking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any
import uuid

from supabase import Client

from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.support import (
    SupportOverviewResponse,
    SupportTicketAssignRequest,
    SupportTicketCommentCreateRequest,
    SupportTicketCommentResponse,
    SupportTicketCreateRequest,
    SupportTicketDetailResponse,
    SupportTicketListResponse,
    SupportTicketResponse,
    SupportTicketUpdateRequest,
)

logger = logging.getLogger(__name__)


SLA_POLICY_HOURS: dict[str, tuple[int, int]] = {
    "p1": (1, 8),
    "p2": (4, 24),
    "p3": (8, 72),
}


class SupportService:
    """Business logic for support tickets."""

    def __init__(self, db: Client | None = None):
        self.db = db or get_supabase_admin_client()

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None

    def _calculate_sla_deadlines(self, priority: str, created_at: datetime) -> tuple[datetime, datetime]:
        normalized = priority.lower().strip()
        response_hours, resolution_hours = SLA_POLICY_HOURS.get(normalized, SLA_POLICY_HOURS["p3"])
        return (
            created_at + timedelta(hours=response_hours),
            created_at + timedelta(hours=resolution_hours),
        )

    def _hydrate_sla_flags(self, ticket: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        first_response_at = self._parse_datetime(ticket.get("first_response_at"))
        resolved_at = self._parse_datetime(ticket.get("resolved_at"))
        response_deadline = self._parse_datetime(ticket.get("sla_response_deadline"))
        resolution_deadline = self._parse_datetime(ticket.get("sla_resolution_deadline"))
        status = str(ticket.get("status") or "open").lower()

        response_breached = bool(ticket.get("is_sla_response_breached"))
        resolution_breached = bool(ticket.get("is_sla_resolution_breached"))

        if not response_breached and response_deadline and first_response_at is None:
            response_breached = now > response_deadline

        if not resolution_breached and resolution_deadline and status not in {"resolved", "closed"} and resolved_at is None:
            resolution_breached = now > resolution_deadline

        ticket["is_sla_response_breached"] = response_breached
        ticket["is_sla_resolution_breached"] = resolution_breached
        return ticket

    def _to_ticket_response(self, ticket: dict[str, Any]) -> SupportTicketResponse:
        hydrated = self._hydrate_sla_flags(dict(ticket))
        return SupportTicketResponse(**hydrated)

    def _generate_ticket_number(self, tenant_id: str) -> str:
        prefix = datetime.now(timezone.utc).strftime("SUP-%Y%m%d")
        for index in range(1, 1000):
            candidate = f"{prefix}-{index:04d}"
            existing = self.db.table("support_tickets").select("id").eq(
                "tenant_id", tenant_id
            ).eq("ticket_number", candidate).execute()
            if not existing.data:
                return candidate
        return f"SUP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    async def list_tickets(
        self,
        current_user: CurrentUser,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        priority: str | None = None,
    ) -> SupportTicketListResponse:
        query = self.db.table("support_tickets").select(
            "id, tenant_id, ticket_number, title, description, category, priority, status, "
            "requester_user_id, assignee_user_id, first_response_at, resolved_at, "
            "sla_response_deadline, sla_resolution_deadline, "
            "is_sla_response_breached, is_sla_resolution_breached, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority.lower())

        offset = (page - 1) * page_size
        response = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        tickets = [self._to_ticket_response(row) for row in (response.data or [])]
        total = response.count or len(tickets)

        return SupportTicketListResponse(
            tickets=tickets,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def get_ticket(self, ticket_id: str, current_user: CurrentUser) -> SupportTicketDetailResponse:
        ticket_response = self.db.table("support_tickets").select(
            "id, tenant_id, ticket_number, title, description, category, priority, status, "
            "requester_user_id, assignee_user_id, first_response_at, resolved_at, "
            "sla_response_deadline, sla_resolution_deadline, "
            "is_sla_response_breached, is_sla_resolution_breached, created_at, updated_at"
        ).eq("id", ticket_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not ticket_response.data:
            raise ValueError("Ticket not found")

        comments_response = self.db.table("support_ticket_comments").select(
            "id, tenant_id, ticket_id, author_user_id, content, is_internal, created_at"
        ).eq("ticket_id", ticket_id).eq("tenant_id", current_user.tenant_id).order("created_at", desc=True).execute()

        return SupportTicketDetailResponse(
            ticket=self._to_ticket_response(ticket_response.data),
            comments=[SupportTicketCommentResponse(**row) for row in (comments_response.data or [])],
        )

    async def create_ticket(
        self,
        payload: SupportTicketCreateRequest,
        current_user: CurrentUser,
    ) -> SupportTicketResponse:
        now = datetime.now(timezone.utc)
        priority = payload.priority.lower()
        response_deadline, resolution_deadline = self._calculate_sla_deadlines(priority, now)

        insert_payload = {
            "tenant_id": current_user.tenant_id,
            "ticket_number": self._generate_ticket_number(current_user.tenant_id),
            "title": payload.title.strip(),
            "description": payload.description,
            "category": payload.category,
            "priority": priority,
            "status": "open",
            "requester_user_id": current_user.id,
            "assignee_user_id": payload.assignee_user_id,
            "sla_response_deadline": response_deadline.isoformat(),
            "sla_resolution_deadline": resolution_deadline.isoformat(),
            "is_sla_response_breached": False,
            "is_sla_resolution_breached": False,
        }

        inserted = self.db.table("support_tickets").insert(insert_payload).execute()
        if not inserted.data:
            raise Exception("Failed to create support ticket")

        return self._to_ticket_response(inserted.data[0])

    async def update_ticket(
        self,
        ticket_id: str,
        payload: SupportTicketUpdateRequest,
        current_user: CurrentUser,
        require_assign_permission: bool = False,
    ) -> SupportTicketResponse:
        existing = self.db.table("support_tickets").select(
            "id, tenant_id, ticket_number, title, description, category, priority, status, "
            "requester_user_id, assignee_user_id, first_response_at, resolved_at, "
            "sla_response_deadline, sla_resolution_deadline, "
            "is_sla_response_breached, is_sla_resolution_breached, created_at, updated_at"
        ).eq("id", ticket_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            raise ValueError("Ticket not found")

        update_data: dict[str, Any] = payload.model_dump(exclude_none=True)

        # Field-level validation for assignee_user_id
        if "assignee_user_id" in update_data and require_assign_permission:
            raise ValueError("Insufficient permission: support.assign required to change assignee")

        if not update_data:
            return self._to_ticket_response(existing.data)

        now = datetime.now(timezone.utc)

        if "priority" in update_data:
            normalized_priority = str(update_data["priority"]).lower()
            update_data["priority"] = normalized_priority
            created_at = self._parse_datetime(existing.data.get("created_at")) or now
            response_deadline, resolution_deadline = self._calculate_sla_deadlines(
                normalized_priority,
                created_at,
            )
            update_data["sla_response_deadline"] = response_deadline.isoformat()
            update_data["sla_resolution_deadline"] = resolution_deadline.isoformat()

        if "status" in update_data:
            next_status = str(update_data["status"]).lower()
            update_data["status"] = next_status
            current_first_response = existing.data.get("first_response_at")

            if next_status in {"in_progress", "resolved", "closed"} and current_first_response is None:
                update_data["first_response_at"] = now.isoformat()

            if next_status in {"resolved", "closed"}:
                update_data["resolved_at"] = now.isoformat()
            elif next_status in {"open", "in_progress"}:
                update_data["resolved_at"] = None

        updated = self.db.table("support_tickets").update(update_data).eq(
            "id", ticket_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("Ticket not found")

        return self._to_ticket_response(updated.data[0])

    async def assign_ticket(
        self,
        ticket_id: str,
        payload: SupportTicketAssignRequest,
        current_user: CurrentUser,
    ) -> SupportTicketResponse:
        """Assign ticket to a user. Requires support.assign permission."""
        existing = self.db.table("support_tickets").select(
            "id, tenant_id"
        ).eq("id", ticket_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            raise ValueError("Ticket not found")

        update_data = {"assignee_user_id": payload.assignee_user_id}

        updated = self.db.table("support_tickets").update(update_data).eq(
            "id", ticket_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("Ticket not found")

        return self._to_ticket_response(updated.data[0])

    async def add_comment(
        self,
        ticket_id: str,
        payload: SupportTicketCommentCreateRequest,
        current_user: CurrentUser,
    ) -> SupportTicketCommentResponse:
        ticket = self.db.table("support_tickets").select("id").eq(
            "id", ticket_id
        ).eq("tenant_id", current_user.tenant_id).single().execute()

        if not ticket.data:
            raise ValueError("Ticket not found")

        inserted = self.db.table("support_ticket_comments").insert(
            {
                "tenant_id": current_user.tenant_id,
                "ticket_id": ticket_id,
                "author_user_id": current_user.id,
                "content": payload.content.strip(),
                "is_internal": payload.is_internal,
            }
        ).execute()

        if not inserted.data:
            raise Exception("Failed to add support ticket comment")

        return SupportTicketCommentResponse(**inserted.data[0])

    async def get_overview(self, current_user: CurrentUser) -> SupportOverviewResponse:
        response = self.db.table("support_tickets").select(
            "status, first_response_at, resolved_at, sla_response_deadline, sla_resolution_deadline, "
            "is_sla_response_breached, is_sla_resolution_breached"
        ).eq("tenant_id", current_user.tenant_id).execute()

        rows = response.data or []

        total_open = 0
        total_in_progress = 0
        total_resolved = 0
        total_closed = 0
        response_breached = 0
        resolution_breached = 0

        for row in rows:
            status = str(row.get("status") or "open").lower()
            if status == "open":
                total_open += 1
            elif status == "in_progress":
                total_in_progress += 1
            elif status == "resolved":
                total_resolved += 1
            elif status == "closed":
                total_closed += 1

            hydrated = self._hydrate_sla_flags(dict(row))
            if hydrated.get("is_sla_response_breached"):
                response_breached += 1
            if hydrated.get("is_sla_resolution_breached"):
                resolution_breached += 1

        return SupportOverviewResponse(
            total_open=total_open,
            total_in_progress=total_in_progress,
            total_resolved=total_resolved,
            total_closed=total_closed,
            sla_response_breached=response_breached,
            sla_resolution_breached=resolution_breached,
        )
