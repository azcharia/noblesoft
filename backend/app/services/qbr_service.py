"""Service layer for QBR cycles, goals, and auto metrics."""
from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.qbr import (
    QBRDashboardResponse,
    QBRGoalCreateRequest,
    QBRGoalListResponse,
    QBRGoalResponse,
    QBRGoalUpdateRequest,
    QBRMetricsSummary,
    QBRCycleCreateRequest,
    QBRCycleListResponse,
    QBRCycleResponse,
    QBRCycleUpdateRequest,
)

logger = logging.getLogger(__name__)


class QBRService:
    """Business logic for QBR planning and metrics."""

    def __init__(self, db: Client | None = None):
        self.db = db or get_supabase_admin_client()

    @staticmethod
    def _to_progress_percentage(target_value: Any, current_value: Any) -> float:
        try:
            target = float(target_value or 0)
            current = float(current_value or 0)
        except Exception:
            return 0.0

        if target <= 0:
            return 0.0

        return round((current / target) * 100, 2)

    def _to_goal_response(self, row: dict[str, Any]) -> QBRGoalResponse:
        payload = dict(row)
        payload["progress_percentage"] = self._to_progress_percentage(
            payload.get("target_value"),
            payload.get("current_value"),
        )
        return QBRGoalResponse(**payload)

    async def list_cycles(
        self,
        current_user: CurrentUser,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> QBRCycleListResponse:
        query = self.db.table("qbr_cycles").select(
            "id, tenant_id, quarter_code, title, start_date, end_date, status, notes, "
            "created_by, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if status:
            query = query.eq("status", status)

        offset = (page - 1) * page_size
        response = query.order("start_date", desc=True).range(offset, offset + page_size - 1).execute()

        cycles = [QBRCycleResponse(**row) for row in (response.data or [])]
        total = response.count or len(cycles)

        return QBRCycleListResponse(
            cycles=cycles,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def create_cycle(
        self,
        payload: QBRCycleCreateRequest,
        current_user: CurrentUser,
    ) -> QBRCycleResponse:
        existing = self.db.table("qbr_cycles").select("id").eq(
            "tenant_id", current_user.tenant_id
        ).eq("quarter_code", payload.quarter_code).execute()

        if existing.data:
            raise ValueError(f"QBR cycle for quarter '{payload.quarter_code}' already exists")

        insert_payload = payload.model_dump()
        insert_payload["tenant_id"] = current_user.tenant_id
        insert_payload["created_by"] = current_user.id

        inserted = self.db.table("qbr_cycles").insert(insert_payload).execute()
        if not inserted.data:
            raise Exception("Failed to create QBR cycle")

        return QBRCycleResponse(**inserted.data[0])

    async def update_cycle(
        self,
        cycle_id: str,
        payload: QBRCycleUpdateRequest,
        current_user: CurrentUser,
    ) -> QBRCycleResponse:
        existing = self.db.table("qbr_cycles").select(
            "id, tenant_id, quarter_code, title, start_date, end_date, status, notes, "
            "created_by, created_at, updated_at"
        ).eq("id", cycle_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            raise ValueError("QBR cycle not found")

        update_data = payload.model_dump(exclude_none=True)
        if not update_data:
            return QBRCycleResponse(**existing.data)

        updated = self.db.table("qbr_cycles").update(update_data).eq(
            "id", cycle_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("QBR cycle not found")

        return QBRCycleResponse(**updated.data[0])

    async def list_goals(
        self,
        current_user: CurrentUser,
        cycle_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> QBRGoalListResponse:
        query = self.db.table("qbr_goals").select(
            "id, tenant_id, cycle_id, title, description, metric_name, unit, target_value, "
            "current_value, owner_user_id, status, due_date, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if cycle_id:
            query = query.eq("cycle_id", cycle_id)

        offset = (page - 1) * page_size
        response = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        goals = [self._to_goal_response(row) for row in (response.data or [])]
        total = response.count or len(goals)

        return QBRGoalListResponse(
            goals=goals,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def create_goal(
        self,
        payload: QBRGoalCreateRequest,
        current_user: CurrentUser,
    ) -> QBRGoalResponse:
        cycle = self.db.table("qbr_cycles").select("id").eq(
            "id", payload.cycle_id
        ).eq("tenant_id", current_user.tenant_id).single().execute()

        if not cycle.data:
            raise ValueError("QBR cycle not found")

        insert_payload = payload.model_dump()
        insert_payload["tenant_id"] = current_user.tenant_id

        inserted = self.db.table("qbr_goals").insert(insert_payload).execute()
        if not inserted.data:
            raise Exception("Failed to create QBR goal")

        return self._to_goal_response(inserted.data[0])

    async def update_goal(
        self,
        goal_id: str,
        payload: QBRGoalUpdateRequest,
        current_user: CurrentUser,
    ) -> QBRGoalResponse:
        existing = self.db.table("qbr_goals").select(
            "id, tenant_id, cycle_id, title, description, metric_name, unit, target_value, "
            "current_value, owner_user_id, status, due_date, created_at, updated_at"
        ).eq("id", goal_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            raise ValueError("QBR goal not found")

        update_data = payload.model_dump(exclude_none=True)

        if "cycle_id" in update_data:
            cycle = self.db.table("qbr_cycles").select("id").eq(
                "id", update_data["cycle_id"]
            ).eq("tenant_id", current_user.tenant_id).single().execute()
            if not cycle.data:
                raise ValueError("QBR cycle not found")

        if not update_data:
            return self._to_goal_response(existing.data)

        updated = self.db.table("qbr_goals").update(update_data).eq(
            "id", goal_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("QBR goal not found")

        return self._to_goal_response(updated.data[0])

    async def get_metrics_summary(self, current_user: CurrentUser) -> QBRMetricsSummary:
        invoices_response = self.db.table("invoices").select(
            "payment_status, total_amount"
        ).eq("tenant_id", current_user.tenant_id).execute()

        invoice_rows = invoices_response.data or []

        paid_revenue = 0.0
        unpaid_invoice_count = 0

        for row in invoice_rows:
            status = str(row.get("payment_status") or "").lower()
            amount = float(row.get("total_amount") or 0)
            if status == "paid":
                paid_revenue += amount
            if status in {"unpaid", "overdue"}:
                unpaid_invoice_count += 1

        products_response = self.db.table("products").select(
            "stock_quantity, low_stock_threshold"
        ).eq("tenant_id", current_user.tenant_id).eq("is_active", True).execute()

        product_rows = products_response.data or []
        total_products = len(product_rows)
        low_stock_products = sum(
            1
            for row in product_rows
            if int(row.get("stock_quantity") or 0) <= int(row.get("low_stock_threshold") or 0)
        )

        return QBRMetricsSummary(
            paid_revenue=round(paid_revenue, 2),
            unpaid_invoice_count=unpaid_invoice_count,
            total_products=total_products,
            low_stock_products=low_stock_products,
        )

    async def get_dashboard(
        self,
        current_user: CurrentUser,
        cycle_id: str | None = None,
    ) -> QBRDashboardResponse:
        cycle_row: dict[str, Any] | None = None

        if cycle_id:
            selected = self.db.table("qbr_cycles").select(
                "id, tenant_id, quarter_code, title, start_date, end_date, status, notes, "
                "created_by, created_at, updated_at"
            ).eq("id", cycle_id).eq("tenant_id", current_user.tenant_id).single().execute()
            cycle_row = selected.data or None
            if cycle_row is None:
                raise ValueError("QBR cycle not found")
        else:
            active = self.db.table("qbr_cycles").select(
                "id, tenant_id, quarter_code, title, start_date, end_date, status, notes, "
                "created_by, created_at, updated_at"
            ).eq("tenant_id", current_user.tenant_id).eq("status", "active").order(
                "start_date", desc=True
            ).range(0, 0).execute()

            if active.data:
                cycle_row = active.data[0]
            else:
                latest = self.db.table("qbr_cycles").select(
                    "id, tenant_id, quarter_code, title, start_date, end_date, status, notes, "
                    "created_by, created_at, updated_at"
                ).eq("tenant_id", current_user.tenant_id).order("start_date", desc=True).range(0, 0).execute()
                if latest.data:
                    cycle_row = latest.data[0]

        goals: list[QBRGoalResponse] = []
        if cycle_row:
            goals_response = await self.list_goals(
                current_user=current_user,
                cycle_id=str(cycle_row.get("id")),
                page=1,
                page_size=200,
            )
            goals = goals_response.goals

        metrics = await self.get_metrics_summary(current_user)

        return QBRDashboardResponse(
            cycle=QBRCycleResponse(**cycle_row) if cycle_row else None,
            goals=goals,
            metrics=metrics,
        )
