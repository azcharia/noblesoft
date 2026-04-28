"""Operations API endpoints for QBR cycles, goals, and metrics dashboard."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    CurrentUser,
    require_enterprise_permission,
)
from app.models.qbr import (
    QBRDashboardResponse,
    QBRGoalCreateRequest,
    QBRGoalListResponse,
    QBRGoalResponse,
    QBRGoalUpdateRequest,
    QBRCycleCreateRequest,
    QBRCycleListResponse,
    QBRCycleResponse,
    QBRCycleUpdateRequest,
)
from app.services.qbr_service import QBRService

router = APIRouter()


@router.get(
    "/cycles",
    response_model=QBRCycleListResponse,
    summary="List QBR cycles",
)
async def list_qbr_cycles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.read")),
):
    service = QBRService()
    try:
        return await service.list_cycles(
            current_user=current_user,
            page=page,
            page_size=page_size,
            status=status_filter,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/cycles",
    response_model=QBRCycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create QBR cycle",
)
async def create_qbr_cycle(
    payload: QBRCycleCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.write")),
):
    service = QBRService()
    try:
        return await service.create_cycle(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/cycles/{cycle_id}",
    response_model=QBRCycleResponse,
    summary="Update QBR cycle",
)
async def update_qbr_cycle(
    cycle_id: str,
    payload: QBRCycleUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.write")),
):
    service = QBRService()
    try:
        return await service.update_cycle(cycle_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/goals",
    response_model=QBRGoalListResponse,
    summary="List QBR goals",
)
async def list_qbr_goals(
    cycle_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.read")),
):
    service = QBRService()
    try:
        return await service.list_goals(
            current_user=current_user,
            cycle_id=cycle_id,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/goals",
    response_model=QBRGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create QBR goal",
)
async def create_qbr_goal(
    payload: QBRGoalCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.write")),
):
    service = QBRService()
    try:
        return await service.create_goal(payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/goals/{goal_id}",
    response_model=QBRGoalResponse,
    summary="Update QBR goal",
)
async def update_qbr_goal(
    goal_id: str,
    payload: QBRGoalUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.write")),
):
    service = QBRService()
    try:
        return await service.update_goal(goal_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/dashboard",
    response_model=QBRDashboardResponse,
    summary="Get QBR dashboard",
)
async def get_qbr_dashboard(
    cycle_id: str | None = Query(None),
    current_user: CurrentUser = Depends(require_enterprise_permission("qbr.read")),
):
    service = QBRService()
    try:
        return await service.get_dashboard(current_user, cycle_id=cycle_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
