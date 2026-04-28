"""Phase 5 schema probe for Enterprise Operations modules.

Exit codes:
- 0: schema looks ready
- 1: schema check failed
- 2: check skipped (missing/placeholder Supabase credentials)
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import Client, create_client


REQUIRED_TABLES = (
    "onboarding_items",
    "support_tickets",
    "support_ticket_comments",
    "qbr_cycles",
    "qbr_goals",
)

REQUIRED_PERMISSION_CODES = (
    "onboarding.read",
    "onboarding.write",
    "support.read",
    "support.write",
    "support.assign",
    "qbr.read",
    "qbr.write",
)

REQUIRED_ROLE_CODES = ("owner", "admin")

PLACEHOLDER_MARKERS = (
    "your-",
    "your_",
    "example",
    "changeme",
    "replace",
    "placeholder",
)


def _load_backend_env() -> None:
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(scripts_dir)
    env_path = os.path.join(backend_dir, ".env")
    load_dotenv(env_path, override=False)


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _create_admin_client() -> tuple[Client | None, str | None]:
    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    service_role_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    if not supabase_url or not service_role_key:
        return None, "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY is missing"

    if _is_placeholder(supabase_url) or _is_placeholder(service_role_key):
        return None, "Supabase credentials still look like placeholder values"

    try:
        return create_client(supabase_url, service_role_key), None
    except Exception as exc:  # pragma: no cover
        return None, f"Failed to initialize Supabase client: {exc}"


def _table_exists(client: Client, table_name: str) -> tuple[bool, str | None]:
    try:
        client.table(table_name).select("id", count="exact").limit(1).execute()
        return True, None
    except Exception as exc:
        return False, str(exc)


def _fetch_codes(client: Client, table_name: str) -> tuple[set[str], str | None]:
    try:
        response = client.table(table_name).select("code").limit(5000).execute()
        data = response.data or []
        codes = {
            str(row.get("code"))
            for row in data
            if row.get("code") is not None
        }
        return codes, None
    except Exception as exc:
        return set(), str(exc)


def _check_support_assign_binding(client: Client) -> tuple[bool, str | None]:
    try:
        permissions_response = client.table("permissions").select("id,code").limit(5000).execute()
        roles_response = client.table("roles").select("id,code").limit(5000).execute()
        role_permissions_response = client.table("role_permissions").select("role_id,permission_id").limit(10000).execute()
    except Exception as exc:
        return False, str(exc)

    permission_rows = permissions_response.data or []
    role_rows = roles_response.data or []
    role_permission_rows = role_permissions_response.data or []

    support_assign_permission_id = None
    for row in permission_rows:
        if row.get("code") == "support.assign":
            support_assign_permission_id = row.get("id")
            break

    if not support_assign_permission_id:
        return False, "Permission support.assign is missing"

    allowed_role_ids = {
        row.get("id")
        for row in role_rows
        if row.get("code") in REQUIRED_ROLE_CODES
    }
    if not allowed_role_ids:
        return False, "Owner/Admin roles are missing"

    for row in role_permission_rows:
        if (
            row.get("permission_id") == support_assign_permission_id
            and row.get("role_id") in allowed_role_ids
        ):
            return True, None

    return False, "No role_permissions binding found for support.assign and owner/admin roles"


def main() -> int:
    _load_backend_env()

    client, skip_reason = _create_admin_client()
    if client is None:
        print(f"[SCHEMA PROBE] SKIPPED: {skip_reason}")
        return 2

    failures: list[str] = []

    for table_name in REQUIRED_TABLES:
        exists, reason = _table_exists(client, table_name)
        if not exists:
            failures.append(f"missing table '{table_name}': {reason}")

    permission_codes, permission_error = _fetch_codes(client, "permissions")
    if permission_error:
        failures.append(f"failed to read permissions table: {permission_error}")
    else:
        missing_permissions = sorted(
            code for code in REQUIRED_PERMISSION_CODES if code not in permission_codes
        )
        if missing_permissions:
            failures.append(
                "missing permission codes: " + ", ".join(missing_permissions)
            )

    role_codes, role_error = _fetch_codes(client, "roles")
    if role_error:
        failures.append(f"failed to read roles table: {role_error}")
    else:
        missing_roles = sorted(
            role_code for role_code in REQUIRED_ROLE_CODES if role_code not in role_codes
        )
        if missing_roles:
            failures.append("missing role codes: " + ", ".join(missing_roles))

    binding_ok, binding_error = _check_support_assign_binding(client)
    if not binding_ok:
        failures.append(binding_error or "support.assign binding check failed")

    if failures:
        print("[SCHEMA PROBE] FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("[SCHEMA PROBE] OK: Phase 5 operations schema is ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
