"""Service layer for tenant onboarding checklist."""
from __future__ import annotations

import logging
from datetime import timezone, datetime
from typing import Any

from supabase import Client

from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.onboarding import (
    OnboardingChecklistResponse,
    OnboardingItemCreateRequest,
    OnboardingItemResponse,
    OnboardingItemUpdateRequest,
)

logger = logging.getLogger(__name__)


class OnboardingService:
    """Business logic for onboarding checklist lifecycle."""

    def __init__(self, db: Client | None = None):
        self.db = db or get_supabase_admin_client()

    async def list_items(self, current_user: CurrentUser) -> OnboardingChecklistResponse:
        response = self.db.table("onboarding_items").select(
            "id, tenant_id, code, title, description, category, is_required, status, "
            "sort_order, due_date, completed_at, completed_by, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id).order("sort_order").order("created_at").execute()

        items = [OnboardingItemResponse(**row) for row in (response.data or [])]
        total = response.count or len(items)
        completed = sum(1 for item in items if item.status == "completed")
        pending = max(total - completed, 0)
        completion_rate = round((completed / total) * 100, 2) if total > 0 else 0.0

        return OnboardingChecklistResponse(
            items=items,
            total=total,
            completed=completed,
            pending=pending,
            completion_rate=completion_rate,
        )

    async def create_item(
        self,
        payload: OnboardingItemCreateRequest,
        current_user: CurrentUser,
    ) -> OnboardingItemResponse:
        existing = self.db.table("onboarding_items").select("id").eq(
            "tenant_id", current_user.tenant_id
        ).eq("code", payload.code).execute()

        if existing.data:
            raise ValueError(f"Onboarding item with code '{payload.code}' already exists")

        insert_payload: dict[str, Any] = payload.model_dump()
        insert_payload["tenant_id"] = current_user.tenant_id

        if payload.status == "completed":
            insert_payload["completed_at"] = datetime.now(timezone.utc).isoformat()
            insert_payload["completed_by"] = current_user.id

        inserted = self.db.table("onboarding_items").insert(insert_payload).execute()
        if not inserted.data:
            raise Exception("Failed to create onboarding item")

        return OnboardingItemResponse(**inserted.data[0])

    async def update_item(
        self,
        item_id: str,
        payload: OnboardingItemUpdateRequest,
        current_user: CurrentUser,
    ) -> OnboardingItemResponse:
        existing = self.db.table("onboarding_items").select(
            "id, tenant_id, code, title, description, category, is_required, status, "
            "sort_order, due_date, completed_at, completed_by, created_at, updated_at"
        ).eq("id", item_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            raise ValueError("Onboarding item not found")

        update_data: dict[str, Any] = payload.model_dump(exclude_none=True)

        if not update_data:
            return OnboardingItemResponse(**existing.data)

        current_status = str(existing.data.get("status") or "pending")
        next_status = str(update_data.get("status") or current_status)

        if next_status == "completed" and current_status != "completed":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            update_data["completed_by"] = current_user.id
        elif next_status != "completed" and current_status == "completed":
            update_data["completed_at"] = None
            update_data["completed_by"] = None

        updated = self.db.table("onboarding_items").update(update_data).eq(
            "id", item_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("Onboarding item not found")

        return OnboardingItemResponse(**updated.data[0])

    async def complete_item(self, item_id: str, current_user: CurrentUser) -> OnboardingItemResponse:
        updated = self.db.table("onboarding_items").update(
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_by": current_user.id,
            }
        ).eq("id", item_id).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("Onboarding item not found")

        return OnboardingItemResponse(**updated.data[0])
