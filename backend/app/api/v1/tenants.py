"""Tenant management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, require_owner
from app.models.tenant import (
    SubscriptionUpdateRequest,
    SubscriptionUpdateResponse,
    TenantResponse,
    TenantUpdate,
    TenantRegisterRequest,
    TenantRegisterResponse,
    TenantAISettingsResponse,
    TenantAISettingsUpdate,
)
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get(
    "/current",
    response_model=TenantResponse,
    summary="Get current tenant profile",
)
async def get_current_tenant(
    current_user: CurrentUser = Depends(get_current_user),
):
    service = TenantService()
    try:
        return await service.get_current_tenant(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/current",
    response_model=TenantResponse,
    summary="Update current tenant settings",
)
async def update_current_tenant(
    payload: TenantUpdate,
    current_user: CurrentUser = Depends(require_owner),
):
    service = TenantService()
    try:
        return await service.update_current_tenant(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/current/subscription",
    response_model=SubscriptionUpdateResponse,
    summary="Update tenant subscription tier",
)
async def update_subscription_tier(
    payload: SubscriptionUpdateRequest,
    current_user: CurrentUser = Depends(require_owner),
):
    service = TenantService()
    try:
        return await service.update_subscription_tier(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/register",
    response_model=TenantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant store and owner account",
)
async def register_tenant(payload: TenantRegisterRequest):
    service = TenantService()
    try:
        return await service.register_new_tenant(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/current/ai-settings",
    response_model=TenantAISettingsResponse,
    summary="Get current tenant's AI settings",
)
async def get_tenant_ai_settings(
    current_user: CurrentUser = Depends(get_current_user),
):
    service = TenantService()
    try:
        return await service.get_tenant_ai_settings(current_user)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/current/ai-settings",
    response_model=TenantAISettingsResponse,
    summary="Update current tenant's AI settings",
)
async def update_tenant_ai_settings(
    payload: TenantAISettingsUpdate,
    current_user: CurrentUser = Depends(require_owner),
):
    service = TenantService()
    try:
        return await service.update_tenant_ai_settings(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))