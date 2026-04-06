"""Service layer for governance roles, permissions, branches, and audit logs."""
from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.governance import (
    AuditLogEntry,
    AuditLogListResponse,
    BranchAssignmentResponse,
    BranchCreateRequest,
    BranchDeleteResponse,
    BranchListResponse,
    BranchResponse,
    BranchUpdateRequest,
    PermissionResponse,
    RoleCreateRequest,
    RoleDeleteResponse,
    RoleListResponse,
    RolePermissionMatrixResponse,
    RolePermissionRow,
    RolePermissionUpdateRequest,
    RoleResponse,
    RoleUpdateRequest,
)

logger = logging.getLogger(__name__)


class GovernanceService:
    """Business logic for governance management flows."""

    def __init__(self, db: Client | None = None):
        self.db = db or get_supabase_admin_client()

    async def list_roles(
        self,
        current_user: CurrentUser,
        include_inactive: bool = False,
    ) -> RoleListResponse:
        query = self.db.table("roles").select(
            "id, tenant_id, code, name, description, is_system, is_active, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if not include_inactive:
            query = query.eq("is_active", True)

        response = query.order("code").execute()
        roles = [RoleResponse(**row) for row in (response.data or [])]

        return RoleListResponse(
            roles=roles,
            total=response.count or len(roles),
        )

    async def create_role(
        self,
        payload: RoleCreateRequest,
        current_user: CurrentUser,
    ) -> RoleResponse:
        existing = self.db.table("roles").select("id").eq(
            "tenant_id", current_user.tenant_id
        ).eq("code", payload.code).execute()
        if existing.data:
            raise ValueError(f"Role with code '{payload.code}' already exists")

        source_permission_ids: list[str] = []
        if payload.copy_from_role_id:
            source_role = self.db.table("roles").select("id").eq(
                "id", payload.copy_from_role_id
            ).eq("tenant_id", current_user.tenant_id).single().execute()
            if not source_role.data:
                raise ValueError("Source role for permission copy was not found")

            copied_permissions = self.db.table("role_permissions").select(
                "permission_id"
            ).eq("role_id", payload.copy_from_role_id).execute()
            source_permission_ids = [
                str(row["permission_id"])
                for row in (copied_permissions.data or [])
                if row.get("permission_id")
            ]

        insert_payload = {
            "tenant_id": current_user.tenant_id,
            "code": payload.code,
            "name": payload.name.strip(),
            "description": payload.description,
            "is_system": False,
            "is_active": True,
        }

        inserted = self.db.table("roles").insert(insert_payload).execute()
        if not inserted.data:
            raise Exception("Failed to create role")

        role = RoleResponse(**inserted.data[0])

        if source_permission_ids:
            role_permission_rows = [
                {
                    "role_id": role.id,
                    "permission_id": permission_id,
                }
                for permission_id in source_permission_ids
            ]
            self.db.table("role_permissions").insert(role_permission_rows).execute()

        return role

    async def update_role(
        self,
        role_id: str,
        payload: RoleUpdateRequest,
        current_user: CurrentUser,
    ) -> RoleResponse:
        existing = self.db.table("roles").select(
            "id, tenant_id, code, name, description, is_system, is_active, created_at, updated_at"
        ).eq("id", role_id).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            raise ValueError("Role not found")

        role = RoleResponse(**existing.data)
        update_data = payload.model_dump(exclude_none=True)

        if not update_data:
            return role

        if role.is_system and role.code in {"owner", "admin", "member"}:
            if "is_active" in update_data and update_data["is_active"] is False:
                raise ValueError("Default system roles cannot be deactivated")

        updated = self.db.table("roles").update(update_data).eq(
            "id", role_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("Role not found")

        return RoleResponse(**updated.data[0])

    async def delete_role(
        self,
        role_id: str,
        current_user: CurrentUser,
    ) -> RoleDeleteResponse:
        existing = self.db.table("roles").select("id, code, is_system").eq(
            "id", role_id
        ).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            return RoleDeleteResponse(role_id=role_id, deleted=False)

        code = str(existing.data.get("code") or "")
        is_system = bool(existing.data.get("is_system"))
        if is_system or code in {"owner", "admin", "member"}:
            raise ValueError("Default roles cannot be deleted")

        active_usage = self.db.table("users").select(
            "id", count="exact"
        ).eq("tenant_id", current_user.tenant_id).eq("role_id", role_id).execute()

        usage_count = active_usage.count or len(active_usage.data or [])
        if usage_count > 0:
            raise ValueError("Role is still assigned to users")

        deleted = self.db.table("roles").delete().eq("id", role_id).eq(
            "tenant_id", current_user.tenant_id
        ).execute()

        return RoleDeleteResponse(
            role_id=role_id,
            deleted=bool(deleted.data),
        )

    async def list_permissions(self) -> list[PermissionResponse]:
        response = self.db.table("permissions").select(
            "id, code, name, resource, action, description"
        ).order("resource").order("action").execute()

        return [PermissionResponse(**row) for row in (response.data or [])]

    async def get_permission_matrix(
        self,
        current_user: CurrentUser,
        include_inactive_roles: bool = False,
    ) -> RolePermissionMatrixResponse:
        role_query = self.db.table("roles").select(
            "id, code, is_active"
        ).eq("tenant_id", current_user.tenant_id)

        if not include_inactive_roles:
            role_query = role_query.eq("is_active", True)

        roles_response = role_query.order("code").execute()
        roles_data = roles_response.data or []
        role_ids = [str(row["id"]) for row in roles_data if row.get("id")]

        permissions = await self.list_permissions()

        role_permission_rows: list[dict[str, Any]] = []
        if role_ids:
            role_permission_response = self.db.table("role_permissions").select(
                "role_id, permissions(code)"
            ).in_("role_id", role_ids).execute()
            role_permission_rows = role_permission_response.data or []

        permission_map: dict[str, list[str]] = {role_id: [] for role_id in role_ids}
        for row in role_permission_rows:
            role_id = str(row.get("role_id") or "")
            permission_obj = row.get("permissions") or {}
            permission_code = permission_obj.get("code") if isinstance(permission_obj, dict) else None
            if role_id and isinstance(permission_code, str):
                permission_map.setdefault(role_id, []).append(permission_code)

        matrix_roles = [
            RolePermissionRow(
                role_id=str(role_data["id"]),
                role_code=str(role_data["code"]),
                permission_codes=sorted(set(permission_map.get(str(role_data["id"]), []))),
            )
            for role_data in roles_data
            if role_data.get("id") and role_data.get("code")
        ]

        return RolePermissionMatrixResponse(
            roles=matrix_roles,
            permissions=permissions,
        )

    async def replace_role_permissions(
        self,
        role_id: str,
        payload: RolePermissionUpdateRequest,
        current_user: CurrentUser,
    ) -> RolePermissionRow:
        role_response = self.db.table("roles").select("id, code").eq(
            "id", role_id
        ).eq("tenant_id", current_user.tenant_id).single().execute()

        if not role_response.data:
            raise ValueError("Role not found")

        requested_codes = sorted(set(payload.permission_codes))
        permission_ids: list[str] = []

        if requested_codes:
            permission_rows = self.db.table("permissions").select("id, code").in_(
                "code", requested_codes
            ).execute().data or []

            found_codes = {str(row.get("code")) for row in permission_rows if row.get("code")}
            missing_codes = sorted(set(requested_codes) - found_codes)
            if missing_codes:
                raise ValueError(f"Unknown permission codes: {', '.join(missing_codes)}")

            permission_ids = [str(row["id"]) for row in permission_rows if row.get("id")]

        self.db.table("role_permissions").delete().eq("role_id", role_id).execute()

        if permission_ids:
            insert_rows = [
                {
                    "role_id": role_id,
                    "permission_id": permission_id,
                }
                for permission_id in permission_ids
            ]
            self.db.table("role_permissions").insert(insert_rows).execute()

        return RolePermissionRow(
            role_id=str(role_response.data["id"]),
            role_code=str(role_response.data["code"]),
            permission_codes=requested_codes,
        )

    async def list_branches(
        self,
        current_user: CurrentUser,
        include_inactive: bool = False,
    ) -> BranchListResponse:
        query = self.db.table("branches").select(
            "id, tenant_id, code, name, location, manager_user_id, is_active, created_at, updated_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if not include_inactive:
            query = query.eq("is_active", True)

        response = query.order("code").execute()
        branches = [BranchResponse(**row) for row in (response.data or [])]

        return BranchListResponse(
            branches=branches,
            total=response.count or len(branches),
        )

    async def create_branch(
        self,
        payload: BranchCreateRequest,
        current_user: CurrentUser,
    ) -> BranchResponse:
        existing = self.db.table("branches").select("id").eq(
            "tenant_id", current_user.tenant_id
        ).eq("code", payload.code).execute()

        if existing.data:
            raise ValueError(f"Branch with code '{payload.code}' already exists")

        insert_payload = {
            "tenant_id": current_user.tenant_id,
            "code": payload.code,
            "name": payload.name.strip(),
            "location": payload.location,
            "manager_user_id": payload.manager_user_id,
            "is_active": True,
        }

        inserted = self.db.table("branches").insert(insert_payload).execute()
        if not inserted.data:
            raise Exception("Failed to create branch")

        return BranchResponse(**inserted.data[0])

    async def update_branch(
        self,
        branch_id: str,
        payload: BranchUpdateRequest,
        current_user: CurrentUser,
    ) -> BranchResponse:
        update_data = payload.model_dump(exclude_none=True)

        if not update_data:
            existing = self.db.table("branches").select(
                "id, tenant_id, code, name, location, manager_user_id, is_active, created_at, updated_at"
            ).eq("id", branch_id).eq("tenant_id", current_user.tenant_id).single().execute()
            if not existing.data:
                raise ValueError("Branch not found")
            return BranchResponse(**existing.data)

        updated = self.db.table("branches").update(update_data).eq(
            "id", branch_id
        ).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("Branch not found")

        return BranchResponse(**updated.data[0])

    async def delete_branch(
        self,
        branch_id: str,
        current_user: CurrentUser,
    ) -> BranchDeleteResponse:
        existing = self.db.table("branches").select("id, is_active").eq(
            "id", branch_id
        ).eq("tenant_id", current_user.tenant_id).single().execute()

        if not existing.data:
            return BranchDeleteResponse(branch_id=branch_id, deleted=False)

        is_active = bool(existing.data.get("is_active", True))
        if is_active:
            raise ValueError("Branch must be deactivated before permanent deletion")

        deleted = self.db.table("branches").delete().eq("id", branch_id).eq(
            "tenant_id", current_user.tenant_id
        ).execute()

        return BranchDeleteResponse(
            branch_id=branch_id,
            deleted=bool(deleted.data),
        )

    async def assign_user_primary_branch(
        self,
        user_id: str,
        branch_id: str,
        current_user: CurrentUser,
    ) -> BranchAssignmentResponse:
        branch = self.db.table("branches").select("id, is_active").eq(
            "id", branch_id
        ).eq("tenant_id", current_user.tenant_id).single().execute()

        if not branch.data:
            raise ValueError("Branch not found")

        if not bool(branch.data.get("is_active", True)):
            raise ValueError("Cannot assign inactive branch")

        updated = self.db.table("users").update({
            "branch_id": branch_id,
        }).eq("id", user_id).eq("tenant_id", current_user.tenant_id).execute()

        if not updated.data:
            raise ValueError("User not found")

        return BranchAssignmentResponse(
            user_id=user_id,
            branch_id=branch_id,
            updated=True,
        )

    async def list_audit_logs(
        self,
        current_user: CurrentUser,
        page: int = 1,
        page_size: int = 50,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> AuditLogListResponse:
        query = self.db.table("audit_logs").select(
            "id, tenant_id, actor_user_id, action, resource_type, resource_id, "
            "old_values, new_values, metadata, created_at",
            count="exact",
        ).eq("tenant_id", current_user.tenant_id)

        if action:
            query = query.eq("action", action.lower())

        if resource_type:
            query = query.eq("resource_type", resource_type)

        safe_page = max(1, page)
        safe_page_size = min(max(1, page_size), 200)
        offset = (safe_page - 1) * safe_page_size

        response = query.order(
            "created_at", desc=True
        ).range(offset, offset + safe_page_size - 1).execute()

        logs = [AuditLogEntry(**row) for row in (response.data or [])]
        total = response.count or len(logs)

        return AuditLogListResponse(
            logs=logs,
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            has_more=(offset + safe_page_size) < total,
        )
