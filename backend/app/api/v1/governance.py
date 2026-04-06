"""Governance and branches management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, require_enterprise_admin
from app.models.governance import (
    AuditLogListResponse,
    BranchAssignmentRequest,
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
from app.services.governance_service import GovernanceService

router = APIRouter()


@router.get(
    "/roles",
    response_model=RoleListResponse,
    summary="List tenant roles",
)
async def list_roles(
    include_inactive: bool = Query(False, description="Include inactive roles"),
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.list_roles(current_user, include_inactive=include_inactive)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create custom role",
)
async def create_role(
    payload: RoleCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.create_role(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
)
async def update_role(
    role_id: str,
    payload: RoleUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.update_role(role_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/roles/{role_id}",
    response_model=RoleDeleteResponse,
    summary="Delete custom role",
)
async def delete_role(
    role_id: str,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        result = await service.delete_role(role_id, current_user)
        if not result.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    summary="List permission catalog",
)
async def list_permissions(
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        _ = current_user
        return await service.list_permissions()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/permissions/matrix",
    response_model=RolePermissionMatrixResponse,
    summary="Get role permission matrix",
)
async def get_permission_matrix(
    include_inactive_roles: bool = Query(False),
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.get_permission_matrix(
            current_user,
            include_inactive_roles=include_inactive_roles,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.put(
    "/roles/{role_id}/permissions",
    response_model=RolePermissionRow,
    summary="Replace permissions for role",
)
async def replace_role_permissions(
    role_id: str,
    payload: RolePermissionUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.replace_role_permissions(role_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/branches",
    response_model=BranchListResponse,
    summary="List tenant branches",
)
async def list_branches(
    include_inactive: bool = Query(False, description="Include inactive branches"),
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.list_branches(current_user, include_inactive=include_inactive)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create branch",
)
async def create_branch(
    payload: BranchCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.create_branch(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/branches/{branch_id}",
    response_model=BranchResponse,
    summary="Update branch",
)
async def update_branch(
    branch_id: str,
    payload: BranchUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.update_branch(branch_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/branches/{branch_id}",
    response_model=BranchDeleteResponse,
    summary="Delete inactive branch permanently",
)
async def delete_branch(
    branch_id: str,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        result = await service.delete_branch(branch_id, current_user)
        if not result.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/branches/assign",
    response_model=BranchAssignmentResponse,
    summary="Assign user primary branch",
)
async def assign_branch(
    payload: BranchAssignmentRequest,
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.assign_user_primary_branch(
            user_id=payload.user_id,
            branch_id=payload.branch_id,
            current_user=current_user,
        )
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="List audit logs",
)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    current_user: CurrentUser = Depends(require_enterprise_admin),
):
    service = GovernanceService()
    try:
        return await service.list_audit_logs(
            current_user=current_user,
            page=page,
            page_size=page_size,
            action=action,
            resource_type=resource_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
