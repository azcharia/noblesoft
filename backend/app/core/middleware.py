"""
Custom Middleware for Tenant Context and Request Processing
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
from typing import Callable

from app.config import settings
from app.core.rate_limiter import RateLimitResult, rate_limiter
from app.core.security import verify_jwt_token, get_user_from_database, AuthenticationError

logger = logging.getLogger(__name__)


def _get_tier_limit(subscription_tier: str | None) -> int:
    """Resolve per-minute request limit based on subscription tier."""
    tier = (subscription_tier or "trial").lower()
    if tier == "enterprise":
        return settings.RATE_LIMIT_ENTERPRISE
    if tier == "pro":
        return settings.RATE_LIMIT_PRO
    if tier == "basic":
        return settings.RATE_LIMIT_BASIC
    return settings.RATE_LIMIT_TRIAL


def _rate_headers(rate_limit: RateLimitResult) -> dict[str, str]:
    """Build HTTP headers for rate-limiting visibility."""
    return {
        "X-RateLimit-Limit": str(rate_limit.limit),
        "X-RateLimit-Remaining": str(rate_limit.remaining),
        "X-RateLimit-Reset": str(rate_limit.reset_seconds),
    }


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject tenant context into request state
    Extracts tenant_id and subscription_tier from JWT and makes it available
    throughout the request lifecycle
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and inject tenant context
        """
        # Initialize request state
        request.state.tenant_id = None
        request.state.user_id = None
        request.state.subscription_tier = None
        request.state.user_role = None
        request.state.user_context = None
        request.state.rate_limit = None
        
        # Skip auth for public endpoints
        public_paths = ["/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json", "/api/v1/tenants/register"]
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("authorization")
        
        if authorization:
            try:
                # Extract token
                parts = authorization.split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1]
                    
                    # Verify and decode token
                    payload = verify_jwt_token(token)
                    user_id = payload.get("sub")
                    
                    # Inject user context into request state
                    request.state.user_id = user_id
                    request.state.email = payload.get("email")

                    if user_id:
                        user_data = await get_user_from_database(user_id)
                        request.state.user_context = user_data
                        request.state.tenant_id = user_data.get("tenant_id")
                        request.state.user_role = user_data.get("role", "member")
                        tenant = user_data.get("tenants") or {}
                        request.state.subscription_tier = tenant.get("subscription_tier", "trial")

                        limit = _get_tier_limit(request.state.subscription_tier)
                        rate_key = f"user:{user_id}"
                        request.state.rate_limit = await rate_limiter.consume(rate_key, limit)

                        if not request.state.rate_limit.allowed:
                            headers = _rate_headers(request.state.rate_limit)
                            if request.state.rate_limit.retry_after is not None:
                                headers["Retry-After"] = str(request.state.rate_limit.retry_after)

                            return JSONResponse(
                                status_code=429,
                                content={
                                    "detail": (
                                        "Rate limit exceeded for your subscription tier. "
                                        "Please retry later."
                                    )
                                },
                                headers=headers,
                            )
                    
                    logger.debug(f"Request authenticated: user_id={request.state.user_id}")
            
            except AuthenticationError as e:
                logger.warning(f"Authentication failed: {str(e)}")
                # Don't block request here - let endpoint dependencies handle it
            except Exception as e:
                logger.error(f"Middleware error: {str(e)}")
        
        # Continue processing request
        response = await call_next(request)

        rate_limit: RateLimitResult | None = getattr(request.state, "rate_limit", None)
        if rate_limit:
            for key, value in _rate_headers(rate_limit).items():
                response.headers[key] = value
        
        return response
