"""
Security & Authentication Utilities
JWT validation, token parsing, and user authentication
"""
from fastapi import HTTPException, status, Header
from typing import Optional, Dict, Any
import jwt
from jwt import PyJWKClient
from datetime import datetime, timezone
import logging

from app.config import settings
from app.core.database import get_supabase_admin_client

logger = logging.getLogger(__name__)

_jwks_client: Optional[PyJWKClient] = None


def _legacy_permission_codes(role: str) -> list[str]:
    role_map: dict[str, set[str]] = {
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
    return sorted(role_map.get(role, set()))


def _resolve_governance_context(
    db,
    user_id: str,
    tenant_id: str,
    legacy_role: str,
) -> Dict[str, Any]:
    """
    Resolve governance metadata with graceful fallback when migration is not yet applied.
    """
    context: Dict[str, Any] = {
        "role_id": None,
        "branch_id": None,
        "permission_codes": _legacy_permission_codes(legacy_role),
        "roles": None,
    }

    try:
        user_extension = db.table("users").select(
            "role_id, branch_id"
        ).eq("id", user_id).single().execute()
        extension_data = user_extension.data or {}
        context["role_id"] = extension_data.get("role_id")
        context["branch_id"] = extension_data.get("branch_id")
    except Exception as exc:
        logger.debug("Governance user extensions unavailable: %s", exc)
        return context

    role_id = context.get("role_id")
    if not role_id:
        return context

    try:
        role_response = db.table("roles").select(
            "id, tenant_id, code, name, is_active"
        ).eq("id", role_id).eq("tenant_id", tenant_id).single().execute()
        role_data = role_response.data or None
        if role_data:
            context["roles"] = role_data

        permission_response = db.table("role_permissions").select(
            "permissions(code)"
        ).eq("role_id", role_id).execute()

        permission_codes: list[str] = []
        for row in (permission_response.data or []):
            permission_obj = row.get("permissions") or {}
            permission_code = permission_obj.get("code") if isinstance(permission_obj, dict) else None
            if isinstance(permission_code, str) and permission_code.strip():
                permission_codes.append(permission_code.strip())

        if permission_codes:
            context["permission_codes"] = sorted(set(permission_codes))
    except Exception as exc:
        logger.debug("Governance role/permissions unavailable: %s", exc)

    return context


def _get_jwks_client() -> PyJWKClient:
    """Lazily initialize JWKS client for Supabase asymmetric JWT verification."""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


class AuthenticationError(HTTPException):
    """Custom exception for authentication failures"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Custom exception for authorization failures"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def extract_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract JWT token from Authorization header
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
    
    Returns:
        JWT token string
    
    Raises:
        AuthenticationError: If token is missing or malformed
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")
    
    parts = authorization.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format. Expected: Bearer <token>")
    
    return parts[1]


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode Supabase JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload containing user_id, email, role, etc.
    
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
        token_alg = unverified_header.get("alg", settings.JWT_ALGORITHM)

        # Supabase can issue either symmetric (HS256) or asymmetric (ES256/RS256) tokens.
        # Keep HS verification for local/dev compatibility and use JWKS for asymmetric keys.
        if token_alg.startswith("HS"):
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[token_alg],
                audience="authenticated",
                options={"verify_iat": False},
            )
        else:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[token_alg],
                audience="authenticated",
                issuer=f"{settings.SUPABASE_URL}/auth/v1",
                options={"verify_iat": False},
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Token has expired")
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"JWT verification error: {str(e)}")
        raise AuthenticationError("Token verification failed")


def get_user_id_from_token(token: str) -> str:
    """
    Extract user_id (sub claim) from JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        User UUID string
    """
    payload = verify_jwt_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise AuthenticationError("Token missing user ID (sub claim)")
    
    return user_id


async def get_user_from_database(user_id: str) -> Dict[str, Any]:
    """
    Fetch user details from database including tenant information
    
    Args:
        user_id: User UUID
    
    Returns:
        User object with tenant_id, role, subscription_tier, etc.
    
    Raises:
        AuthenticationError: If user not found or inactive
    """
    try:
        db = get_supabase_admin_client()
        
        # Query user with tenant information (using admin client to bypass RLS)
        response = db.table("users").select(
            "id, email, full_name, role, is_active, tenant_id, "
            "tenants(id, company_name, subscription_tier, is_active, trial_end_date, max_users)"
        ).eq("id", user_id).single().execute()
        
        if not response.data:
            raise AuthenticationError("User not found")
        
        user = response.data
        
        # Check if user is active
        if not user.get("is_active"):
            raise AuthenticationError("User account is inactive")
        
        # Check if tenant is active
        tenant = user.get("tenants")
        if not tenant or not tenant.get("is_active"):
            raise AuthenticationError("Tenant account is inactive")
        
        # Check trial expiration
        if tenant.get("subscription_tier") == "trial":
            trial_end = tenant.get("trial_end_date")
            if trial_end:
                trial_end_dt = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
                if trial_end_dt < datetime.now(timezone.utc):
                    raise AuthenticationError("Trial period has expired")

        governance_context = _resolve_governance_context(
            db=db,
            user_id=user_id,
            tenant_id=str(user.get("tenant_id") or ""),
            legacy_role=str(user.get("role") or "member"),
        )
        user.update(governance_context)
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error fetching user: {str(e)}")
        raise AuthenticationError("Failed to authenticate user")


def check_feature_access(subscription_tier: str, feature: str) -> bool:
    """
    Check if a subscription tier has access to a specific feature - bypassed for open source
    
    Args:
        subscription_tier: Tier name (trial, basic, pro, enterprise)
        feature: Feature name to check
    
    Returns:
        True if feature is accessible, False otherwise
    """
    return True


def require_feature(feature: str, user_tier: str):
    """
    Raise exception if user's tier doesn't have access to feature
    
    Args:
        feature: Feature name
        user_tier: User's subscription tier
    
    Raises:
        AuthorizationError: If feature not accessible
    """
    if not check_feature_access(user_tier, feature):
        raise AuthorizationError(
            f"Feature '{feature}' requires a higher subscription tier. "
            f"Current tier: {user_tier}"
        )
