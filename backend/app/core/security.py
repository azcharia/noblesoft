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
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error fetching user: {str(e)}")
        raise AuthenticationError("Failed to authenticate user")


def check_feature_access(subscription_tier: str, feature: str) -> bool:
    """
    Check if a subscription tier has access to a specific feature
    
    Args:
        subscription_tier: Tier name (trial, basic, pro, enterprise)
        feature: Feature name to check
    
    Returns:
        True if feature is accessible, False otherwise
    """
    tier_features = {
        "trial": settings.FEATURES_TRIAL,
        "basic": settings.FEATURES_BASIC,
        "pro": settings.FEATURES_PRO,
        "enterprise": settings.FEATURES_ENTERPRISE
    }
    
    features = tier_features.get(subscription_tier, [])
    return feature in features


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
