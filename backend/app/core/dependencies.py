"""
FastAPI Dependency Injection
Provides reusable dependencies for authentication, authorization, and context
"""
from fastapi import Depends, Request
from typing import Dict, Any, Optional
import json
import logging

from app.core.database import get_supabase_admin_client
from app.core.security import (
    extract_token_from_header,
    verify_jwt_token,
    get_user_from_database,
    AuthenticationError,
    AuthorizationError
)

logger = logging.getLogger(__name__)


LEGACY_ROLE_PERMISSION_MAP: dict[str, set[str]] = {
    "owner": {"*"},
    "admin": {
        "users.read",
        "users.invite",
        "users.status",
        "roles.read",
        "permissions.read",
        "branches.read",
        "branches.write",
        "audit.read",
        "products.read",
        "products.write",
        "invoices.read",
        "invoices.write",
        "chat.use",
        "onboarding.read",
        "onboarding.write",
        "support.read",
        "support.write",
        "support.assign",
        "qbr.read",
        "qbr.write",
    },
    "member": {
        "products.read",
        "products.write",
        "invoices.read",
        "invoices.write",
        "chat.use",
    },
}


class CurrentUser:
    """
    Current authenticated user context
    Contains user info, tenant info, and subscription details
    """
    def __init__(self, user_data: Dict[str, Any]):
        self.id: str = user_data["id"]
        self.email: str = user_data["email"]
        self.full_name: Optional[str] = user_data.get("full_name")
        self.role: str = user_data.get("role", "member")
        self.role_id: Optional[str] = user_data.get("role_id")
        self.branch_id: Optional[str] = user_data.get("branch_id")
        self.is_active: bool = user_data.get("is_active", True)

        role_data = user_data.get("roles", {})
        self.role_name: Optional[str] = None
        if isinstance(role_data, dict):
            self.role_name = role_data.get("name")

        raw_permission_codes = user_data.get("permission_codes")
        if isinstance(raw_permission_codes, list):
            self.permission_codes: list[str] = [
                str(item).strip()
                for item in raw_permission_codes
                if isinstance(item, str) and item.strip()
            ]
        else:
            self.permission_codes = sorted(
                LEGACY_ROLE_PERMISSION_MAP.get(self.role, set())
            )
        
        # Tenant information
        tenant = user_data.get("tenants", {})
        self.tenant_id: str = user_data["tenant_id"]
        self.company_name: str = tenant.get("company_name", "")
        self.subscription_tier: str = tenant.get("subscription_tier", "trial")
        self.tenant_is_active: bool = tenant.get("is_active", True)
        self.trial_end_date: Optional[str] = tenant.get("trial_end_date")
        self.max_users: int = tenant.get("max_users", 5)
        self.billing_period: str = tenant.get("billing_period", "monthly")
        active_add_ons = tenant.get("active_add_ons", [])
        self.active_add_ons: list[dict[str, Any]] = active_add_ons if isinstance(active_add_ons, list) else []
    
    def is_owner(self) -> bool:
        """Check if user is tenant owner"""
        return self.role == "owner"
    
    def is_admin(self) -> bool:
        """Check if user is admin or owner"""
        return self.role in ["owner", "admin"]
    
    def has_tier(self, required_tiers: list[str]) -> bool:
        """Check if user's subscription tier is in the required list - bypassed for open-source"""
        return True

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has an explicit or wildcard permission."""
        if self.is_owner():
            return True

        normalized = permission_code.strip().lower()
        if not normalized:
            return False

        permission_set = {code.lower() for code in self.permission_codes}
        if "*" in permission_set or normalized in permission_set:
            return True

        resource_wildcard = f"{normalized.split('.', 1)[0]}.*"
        if resource_wildcard in permission_set:
            return True

        legacy_permissions = LEGACY_ROLE_PERMISSION_MAP.get(self.role, set())
        if "*" in legacy_permissions or normalized in legacy_permissions:
            return True

        return resource_wildcard in legacy_permissions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging"""
        return {
            "user_id": self.id,
            "email": self.email,
            "role": self.role,
            "role_id": self.role_id,
            "branch_id": self.branch_id,
            "tenant_id": self.tenant_id,
            "subscription_tier": self.subscription_tier,
            "permission_count": len(self.permission_codes),
        }


async def get_current_user(
    request: Request,
    authorization: str = Depends(extract_token_from_header)
) -> CurrentUser:
    """
    Dependency to get current authenticated user
    
    Usage:
        @app.get("/protected")
        async def protected_route(current_user: CurrentUser = Depends(get_current_user)):
            return {"user_id": current_user.id}
    
    Args:
        authorization: Authorization header (injected by FastAPI)
    
    Returns:
        CurrentUser object with user and tenant context
    
    Raises:
        AuthenticationError: If authentication fails
    """
    # Extract and verify token
    token = authorization
    payload = verify_jwt_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise AuthenticationError("Invalid token: missing user ID")

    cached_user = getattr(request.state, "user_context", None)
    if isinstance(cached_user, dict) and cached_user.get("id") == user_id:
        user_data = cached_user
    else:
        # Fetch user from database with tenant info
        user_data = await get_user_from_database(user_id)
        request.state.user_context = user_data
        request.state.user_id = user_data.get("id")
        request.state.tenant_id = user_data.get("tenant_id")
        request.state.user_role = user_data.get("role", "member")
        tenant = user_data.get("tenants") or {}
        request.state.subscription_tier = tenant.get("subscription_tier", "trial")
    
    return CurrentUser(user_data)


async def get_optional_user(
    request: Request
) -> Optional[CurrentUser]:
    """
    Dependency to get current user if authenticated, None otherwise
    Useful for endpoints that work with or without authentication
    
    Usage:
        @app.get("/public-or-private")
        async def route(user: Optional[CurrentUser] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello guest"}
    """
    try:
        authorization = request.headers.get("authorization")
        if not authorization:
            return None
        
        token = extract_token_from_header(authorization)
        payload = verify_jwt_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None

        cached_user = getattr(request.state, "user_context", None)
        if isinstance(cached_user, dict) and cached_user.get("id") == user_id:
            user_data = cached_user
        else:
            user_data = await get_user_from_database(user_id)
            request.state.user_context = user_data

        return CurrentUser(user_data)
    
    except Exception as e:
        logger.debug(f"Optional auth failed: {str(e)}")
        return None


def get_tenant_id(current_user: CurrentUser = Depends(get_current_user)) -> str:
    """
    Dependency to extract tenant_id from current user
    
    Usage:
        @app.get("/tenant-data")
        async def route(tenant_id: str = Depends(get_tenant_id)):
            return {"tenant_id": tenant_id}
    """
    return current_user.tenant_id


def get_subscription_tier(current_user: CurrentUser = Depends(get_current_user)) -> str:
    """
    Dependency to extract subscription tier from current user
    
    Usage:
        @app.get("/tier-info")
        async def route(tier: str = Depends(get_subscription_tier)):
            return {"tier": tier}
    """
    return current_user.subscription_tier


def require_role(allowed_roles: list[str]):
    """
    Dependency factory to require specific user roles
    
    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            current_user: CurrentUser = Depends(require_role(["owner", "admin"]))
        ):
            ...
    
    Args:
        allowed_roles: List of allowed roles (e.g., ["owner", "admin"])
    
    Returns:
        Dependency function that validates role
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"This action requires one of the following roles: {', '.join(allowed_roles)}. "
                f"Your role: {current_user.role}"
            )
        return current_user
    
    return role_checker


def require_tier(allowed_tiers: list[str]):
    """
    Dependency factory to require specific subscription tiers
    
    Usage:
        @app.post("/ai/chat")
        async def ai_chat(
            message: str,
            current_user: CurrentUser = Depends(require_tier(["pro", "enterprise"]))
        ):
            ...
    
    Args:
        allowed_tiers: List of allowed tiers (e.g., ["pro", "enterprise"])
    
    Returns:
        Dependency function that validates subscription tier
    """
    async def tier_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        # Bypassed for open-source
        return current_user
    
    return tier_checker


def _extract_add_on_codes(raw_add_ons: Any) -> set[str]:
    candidate = raw_add_ons
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except Exception:
            return set()

    if not isinstance(candidate, list):
        return set()

    codes: set[str] = set()
    for item in candidate:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if isinstance(code, str) and code.strip():
            codes.add(code.strip())
    return codes


def require_add_on(required_add_on: str):
    """Dependency factory to require a purchased add-on for a feature."""

    async def add_on_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        # Bypassed for open-source
        return current_user

    return add_on_checker


def require_owner(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Dependency to require tenant owner role
    
    Usage:
        @app.post("/tenant/settings")
        async def update_settings(
            settings: dict,
            current_user: CurrentUser = Depends(require_owner)
        ):
            ...
    """
    if not current_user.is_owner():
        raise AuthorizationError("This action requires tenant owner privileges")
    return current_user


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Dependency to require admin or owner role
    
    Usage:
        @app.post("/users/invite")
        async def invite_user(
            email: str,
            current_user: CurrentUser = Depends(require_admin)
        ):
            ...
    """
    if not current_user.is_admin():
        raise AuthorizationError("This action requires admin or owner privileges")
    return current_user


def require_enterprise_admin(
    current_user: CurrentUser = Depends(require_admin),
) -> CurrentUser:
    """Require both enterprise tier and admin privileges - bypassed for open-source."""
    return current_user


def require_enterprise_permission(permission_code: str):
    """Dependency factory requiring enterprise admin and explicit permission."""

    async def enterprise_permission_checker(
        current_user: CurrentUser = Depends(require_enterprise_admin),
    ) -> CurrentUser:
        if not current_user.has_permission(permission_code):
            raise AuthorizationError(
                f"This action requires permission '{permission_code}'"
            )
        return current_user

    return enterprise_permission_checker


def require_permission(permission_code: str):
    """Dependency factory for permission-based authorization checks."""

    async def permission_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_permission(permission_code):
            raise AuthorizationError(
                f"This action requires permission '{permission_code}'"
            )
        return current_user

    return permission_checker
