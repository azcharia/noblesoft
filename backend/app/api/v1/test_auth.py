"""
Test Authentication Endpoints
Demonstrates how to use the authentication system
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.core.dependencies import (
    get_current_user,
    get_optional_user,
    require_tier,
    require_admin,
    require_owner,
    CurrentUser
)

router = APIRouter()


@router.get("/me")
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current authenticated user information
    Requires: Valid JWT token
    """
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role
        },
        "tenant": {
            "id": current_user.tenant_id,
            "company_name": current_user.company_name,
            "subscription_tier": current_user.subscription_tier,
            "max_users": current_user.max_users
        }
    }


@router.get("/public-or-private")
async def public_or_private_endpoint(
    current_user: CurrentUser | None = Depends(get_optional_user)
) -> Dict[str, Any]:
    """
    Endpoint that works with or without authentication
    Returns different data based on auth status
    """
    if current_user:
        return {
            "message": f"Hello {current_user.email}!",
            "authenticated": True,
            "tier": current_user.subscription_tier
        }
    return {
        "message": "Hello guest!",
        "authenticated": False
    }


@router.get("/pro-feature")
async def pro_feature(
    current_user: CurrentUser = Depends(require_tier(["pro", "enterprise"]))
) -> Dict[str, Any]:
    """
    Example Pro/Enterprise only feature
    Requires: Pro or Enterprise subscription tier
    """
    return {
        "message": "Welcome to Pro features!",
        "user": current_user.email,
        "tier": current_user.subscription_tier,
        "feature": "This is only accessible to Pro and Enterprise users"
    }


@router.get("/admin-only")
async def admin_only_endpoint(
    current_user: CurrentUser = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Admin/Owner only endpoint
    Requires: Admin or Owner role
    """
    return {
        "message": "Admin access granted",
        "user": current_user.email,
        "role": current_user.role,
        "tenant": current_user.company_name
    }


@router.get("/owner-only")
async def owner_only_endpoint(
    current_user: CurrentUser = Depends(require_owner)
) -> Dict[str, Any]:
    """
    Owner only endpoint
    Requires: Owner role
    """
    return {
        "message": "Owner access granted",
        "user": current_user.email,
        "tenant": current_user.company_name
    }


@router.get("/tier-info")
async def get_tier_info(
    current_user: CurrentUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get subscription tier information and feature access
    """
    from app.config import settings
    
    tier_features = {
        "trial": settings.FEATURES_TRIAL,
        "basic": settings.FEATURES_BASIC,
        "pro": settings.FEATURES_PRO,
        "enterprise": settings.FEATURES_ENTERPRISE
    }
    
    return {
        "current_tier": current_user.subscription_tier,
        "available_features": tier_features.get(current_user.subscription_tier, []),
        "max_users": current_user.max_users,
        "is_trial": current_user.subscription_tier == "trial",
        "trial_end_date": current_user.trial_end_date
    }
