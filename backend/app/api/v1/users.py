"""Tenant user management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, require_admin
from app.models.user import (
    TenantUserDeactivateResponse,
    TenantUserInviteRequest,
    TenantUserInviteResponse,
    TenantUserReactivateResponse,
    TenantUsersListResponse,
)
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get(
    "/",
    response_model=TenantUsersListResponse,
    summary="List tenant users",
)
async def list_users(
    include_inactive: bool = Query(False, description="Include inactive users"),
    current_user: CurrentUser = Depends(require_admin),
):
    service = TenantService()
    try:
        return await service.list_tenant_users(current_user, include_inactive=include_inactive)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/invite",
    response_model=TenantUserInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a tenant user",
)
async def invite_user(
    payload: TenantUserInviteRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    service = TenantService()
    try:
        return await service.invite_tenant_user(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/{user_id}",
    response_model=TenantUserDeactivateResponse,
    summary="Deactivate tenant user",
)
async def deactivate_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_admin),
):
    service = TenantService()
    try:
        result = await service.deactivate_tenant_user(user_id, current_user)
        deactivated = result.deactivated if hasattr(result, "deactivated") else bool(result.get("deactivated"))
        if not deactivated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/{user_id}/reactivate",
    response_model=TenantUserReactivateResponse,
    summary="Reactivate tenant user",
)
async def reactivate_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_admin),
):
    service = TenantService()
    try:
        result = await service.reactivate_tenant_user(user_id, current_user)
        reactivated = result.reactivated if hasattr(result, "reactivated") else bool(result.get("reactivated"))
        if not reactivated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))