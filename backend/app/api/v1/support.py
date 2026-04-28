"""Operations API endpoints for support ticketing and SLA."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
    require_enterprise_permission,
)
from app.models.support import (
    SupportOverviewResponse,
    SupportTicketAssignRequest,
    SupportTicketCommentCreateRequest,
    SupportTicketCommentResponse,
    SupportTicketCreateRequest,
    SupportTicketDetailResponse,
    SupportTicketListResponse,
    SupportTicketResponse,
    SupportTicketUpdateRequest,
)
from app.services.support_service import SupportService

router = APIRouter()


async def require_enterprise_support_write(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.has_tier(["enterprise"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an active enterprise subscription",
        )
    if not current_user.has_permission("support.write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires permission 'support.write'",
        )
    return current_user


@router.get(
    "/tickets",
    response_model=SupportTicketListResponse,
    summary="List support tickets",
)
async def list_support_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    current_user: CurrentUser = Depends(require_enterprise_permission("support.read")),
):
    service = SupportService()
    try:
        return await service.list_tickets(
            current_user=current_user,
            page=page,
            page_size=page_size,
            status=status_filter,
            priority=priority,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/tickets",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create support ticket",
)
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("support.write")),
):
    service = SupportService()
    try:
        return await service.create_ticket(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/tickets/{ticket_id}",
    response_model=SupportTicketDetailResponse,
    summary="Get support ticket detail",
)
async def get_support_ticket(
    ticket_id: str,
    current_user: CurrentUser = Depends(require_enterprise_permission("support.read")),
):
    service = SupportService()
    try:
        return await service.get_ticket(ticket_id, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/tickets/{ticket_id}",
    response_model=SupportTicketResponse,
    summary="Update support ticket",
)
async def update_support_ticket(
    ticket_id: str,
    payload: SupportTicketUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_support_write),
):
    service = SupportService()
    try:
        # Check if user is trying to change assignee without support.assign permission
        has_assign_permission = current_user.has_permission("support.assign")
        require_assign_check = not has_assign_permission
        
        return await service.update_ticket(ticket_id, payload, current_user, require_assign_check)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        if "insufficient permission" in message.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/tickets/{ticket_id}/assignee",
    response_model=SupportTicketResponse,
    summary="Assign support ticket to a user",
)
async def assign_support_ticket(
    ticket_id: str,
    payload: SupportTicketAssignRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("support.assign")),
):
    service = SupportService()
    try:
        return await service.assign_ticket(ticket_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=SupportTicketCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add support ticket comment",
)
async def add_support_ticket_comment(
    ticket_id: str,
    payload: SupportTicketCommentCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("support.write")),
):
    service = SupportService()
    try:
        return await service.add_comment(ticket_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/overview",
    response_model=SupportOverviewResponse,
    summary="Get support ticket overview metrics",
)
async def get_support_overview(
    current_user: CurrentUser = Depends(require_enterprise_permission("support.read")),
):
    service = SupportService()
    try:
        return await service.get_overview(current_user)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
