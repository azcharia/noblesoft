"""Tenant and tenant-user management service layer."""
from __future__ import annotations

from datetime import datetime
import logging
import secrets
from typing import Any

from supabase import Client

from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.tenant import (
    SubscriptionUpdateRequest,
    SubscriptionUpdateResponse,
    TenantResponse,
    TenantUpdate,
)
from app.models.user import (
    TenantUserDeactivateResponse,
    TenantUserInviteRequest,
    TenantUserInviteResponse,
    TenantUserReactivateResponse,
    TenantUserResponse,
    TenantUsersListResponse,
)

logger = logging.getLogger(__name__)


class TenantService:
    """Service class for tenant metadata and team management operations."""

    def __init__(self, db: Client | None = None):
        self.db = db or get_supabase_admin_client()

    async def get_current_tenant(self, current_user: CurrentUser) -> TenantResponse:
        response = self.db.table("tenants").select(
            "id, company_name, subscription_tier, trial_start_date, trial_end_date, "
            "is_active, max_users, payment_gateway_customer_id, created_at, updated_at"
        ).eq("id", current_user.tenant_id).single().execute()

        if not response.data:
            raise ValueError("Tenant not found")

        return TenantResponse(**response.data)

    async def update_current_tenant(
        self,
        payload: TenantUpdate,
        current_user: CurrentUser,
    ) -> TenantResponse:
        update_dict = payload.model_dump(exclude_none=True)
        if not update_dict:
            return await self.get_current_tenant(current_user)

        response = self.db.table("tenants").update(update_dict).eq(
            "id", current_user.tenant_id
        ).execute()

        if not response.data:
            raise ValueError("Tenant not found")

        return TenantResponse(**response.data[0])

    async def update_subscription_tier(
        self,
        payload: SubscriptionUpdateRequest,
        current_user: CurrentUser,
    ) -> SubscriptionUpdateResponse:
        current_tenant = await self.get_current_tenant(current_user)
        previous_tier = current_tenant.subscription_tier

        response = self.db.table("tenants").update(
            {
                "subscription_tier": payload.subscription_tier,
                "is_active": True,
            }
        ).eq("id", current_user.tenant_id).execute()

        if not response.data:
            raise ValueError("Tenant not found")

        tenant = TenantResponse(**response.data[0])
        return SubscriptionUpdateResponse(
            tenant=tenant,
            previous_tier=previous_tier,
            updated_tier=tenant.subscription_tier,
        )

    async def list_tenant_users(
        self,
        current_user: CurrentUser,
        include_inactive: bool = False,
    ) -> TenantUsersListResponse:
        query = self.db.table("users").select(
            "id, tenant_id, email, full_name, role, role_id, branch_id, is_active, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if not include_inactive:
            query = query.eq("is_active", True)

        response = query.order("created_at").execute()
        users = [TenantUserResponse(**row) for row in (response.data or [])]

        return TenantUsersListResponse(
            users=users,
            total=response.count or len(users),
        )

    async def invite_tenant_user(
        self,
        payload: TenantUserInviteRequest,
        current_user: CurrentUser,
    ) -> TenantUserInviteResponse:
        existing = self.db.table("users").select("id").eq(
            "email", payload.email.lower()
        ).execute()
        if existing.data:
            raise ValueError(f"User with email '{payload.email}' already exists")

        active_count_response = self.db.table("users").select(
            "id", count="exact"
        ).eq("tenant_id", current_user.tenant_id).eq("is_active", True).execute()

        active_count = active_count_response.count or len(active_count_response.data or [])
        if active_count >= current_user.max_users:
            raise ValueError("Tenant user limit has been reached")

        temporary_password = payload.temp_password or secrets.token_urlsafe(12)

        auth_result = self.db.auth.admin.create_user(
            {
                "email": payload.email.lower(),
                "password": temporary_password,
                "email_confirm": payload.auto_confirm_email,
                "user_metadata": {
                    "full_name": payload.full_name,
                    "tenant_id": current_user.tenant_id,
                },
            }
        )

        created_user_id = self._extract_auth_user_id(auth_result)
        if not created_user_id:
            raise Exception("Failed to create auth user for invitation")

        role_id: str | None = None
        try:
            role_lookup = self.db.table("roles").select("id").eq(
                "tenant_id", current_user.tenant_id
            ).eq("code", payload.role).single().execute()
            role_id = (role_lookup.data or {}).get("id")
        except Exception as role_lookup_error:
            logger.debug("Role lookup skipped during invite: %s", role_lookup_error)

        if not role_id and payload.role not in {"owner", "admin", "member"}:
            raise ValueError(f"Role '{payload.role}' not found for this tenant")

        insert_payload = {
            "id": created_user_id,
            "tenant_id": current_user.tenant_id,
            "email": payload.email.lower(),
            "full_name": payload.full_name,
            "role": payload.role,
            "role_id": role_id,
            "is_active": True,
        }

        inserted = self.db.table("users").insert(insert_payload).execute()

        if not inserted.data:
            try:
                self.db.auth.admin.delete_user(created_user_id)
            except Exception as cleanup_error:  # pragma: no cover
                logger.warning("Failed to cleanup auth user %s: %s", created_user_id, cleanup_error)
            raise Exception("Failed to create user profile in database")

        user = TenantUserResponse(**inserted.data[0])

        return TenantUserInviteResponse(
            user=user,
            temporary_password=temporary_password if payload.include_temporary_password else None,
        )

    async def deactivate_tenant_user(
        self,
        user_id: str,
        current_user: CurrentUser,
    ) -> TenantUserDeactivateResponse:
        if user_id == current_user.id:
            raise ValueError("You cannot deactivate your own account")

        target = self.db.table("users").select("id, role").eq("id", user_id).eq(
            "tenant_id", current_user.tenant_id
        ).single().execute()

        if not target.data:
            return TenantUserDeactivateResponse(user_id=user_id, deactivated=False)

        if target.data.get("role") == "owner" and not current_user.is_owner():
            raise PermissionError("Only owner can deactivate owner accounts")

        response = self.db.table("users").update(
            {"is_active": False, "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", user_id).eq("tenant_id", current_user.tenant_id).execute()

        return TenantUserDeactivateResponse(
            user_id=user_id,
            deactivated=bool(response.data),
        )

    async def reactivate_tenant_user(
        self,
        user_id: str,
        current_user: CurrentUser,
    ) -> TenantUserReactivateResponse:
        target = self.db.table("users").select("id, role, is_active").eq("id", user_id).eq(
            "tenant_id", current_user.tenant_id
        ).single().execute()

        if not target.data:
            return TenantUserReactivateResponse(user_id=user_id, reactivated=False)

        if target.data.get("role") == "owner" and not current_user.is_owner():
            raise PermissionError("Only owner can reactivate owner accounts")

        if bool(target.data.get("is_active")):
            return TenantUserReactivateResponse(user_id=user_id, reactivated=True)

        active_count_response = self.db.table("users").select(
            "id", count="exact"
        ).eq("tenant_id", current_user.tenant_id).eq("is_active", True).execute()

        active_count = active_count_response.count or len(active_count_response.data or [])
        if active_count >= current_user.max_users:
            raise ValueError("Tenant user limit has been reached")

        response = self.db.table("users").update(
            {"is_active": True, "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", user_id).eq("tenant_id", current_user.tenant_id).execute()

        return TenantUserReactivateResponse(
            user_id=user_id,
            reactivated=bool(response.data),
        )

    def _extract_auth_user_id(self, auth_result: Any) -> str | None:
        """Extract user id from multiple supabase-py response shapes."""
        if auth_result is None:
            return None

        if isinstance(auth_result, dict):
            user_data = auth_result.get("user")
            if isinstance(user_data, dict) and user_data.get("id"):
                return str(user_data["id"])

            data = auth_result.get("data")
            if isinstance(data, dict):
                nested_user = data.get("user")
                if isinstance(nested_user, dict) and nested_user.get("id"):
                    return str(nested_user["id"])

        user_obj = getattr(auth_result, "user", None)
        if user_obj is not None:
            if isinstance(user_obj, dict):
                user_id = user_obj.get("id")
                return str(user_id) if user_id else None

            user_id = getattr(user_obj, "id", None)
            return str(user_id) if user_id else None

        data_obj = getattr(auth_result, "data", None)
        if isinstance(data_obj, dict):
            nested = data_obj.get("user")
            if isinstance(nested, dict):
                user_id = nested.get("id")
                return str(user_id) if user_id else None

        return None