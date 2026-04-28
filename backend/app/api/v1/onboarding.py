"""Operations API endpoints for onboarding checklist."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    CurrentUser,
    require_enterprise_permission,
)
from app.models.onboarding import (
    OnboardingChecklistResponse,
    OnboardingItemCreateRequest,
    OnboardingItemResponse,
    OnboardingItemUpdateRequest,
)
from app.services.onboarding_service import OnboardingService

router = APIRouter()


@router.get(
    "",
    response_model=OnboardingChecklistResponse,
    summary="List onboarding checklist and progress",
)
async def list_onboarding(
    current_user: CurrentUser = Depends(require_enterprise_permission("onboarding.read")),
):
    service = OnboardingService()
    try:
        return await service.list_items(current_user)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/items",
    response_model=OnboardingItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create onboarding checklist item",
)
async def create_onboarding_item(
    payload: OnboardingItemCreateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("onboarding.write")),
):
    service = OnboardingService()
    try:
        return await service.create_item(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/items/{item_id}",
    response_model=OnboardingItemResponse,
    summary="Update onboarding checklist item",
)
async def update_onboarding_item(
    item_id: str,
    payload: OnboardingItemUpdateRequest,
    current_user: CurrentUser = Depends(require_enterprise_permission("onboarding.write")),
):
    service = OnboardingService()
    try:
        return await service.update_item(item_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/items/{item_id}/complete",
    response_model=OnboardingItemResponse,
    summary="Mark onboarding checklist item as completed",
)
async def complete_onboarding_item(
    item_id: str,
    current_user: CurrentUser = Depends(require_enterprise_permission("onboarding.write")),
):
    service = OnboardingService()
    try:
        return await service.complete_item(item_id, current_user)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
