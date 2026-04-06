"""Billing API endpoints with Midtrans integration."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, require_owner
from app.models.billing import (
    BillingCatalogResponse,
    BillingStatusResponse,
    BillingTransactionRequest,
    BillingTransactionResponse,
    MidtransWebhookRequest,
    MidtransWebhookResponse,
)
from app.services.billing_service import BillingService

router = APIRouter()


@router.get(
    "/catalog",
    response_model=BillingCatalogResponse,
    summary="Get billing plans and add-on catalog",
)
async def get_billing_catalog(
    current_user: CurrentUser = Depends(get_current_user),
):
    service = BillingService()
    try:
        _ = current_user
        return service.get_billing_catalog()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/status",
    response_model=BillingStatusResponse,
    summary="Get current billing status",
)
async def get_billing_status(
    current_user: CurrentUser = Depends(get_current_user),
):
    service = BillingService()
    try:
        return await service.get_billing_status(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/midtrans/transaction",
    response_model=BillingTransactionResponse,
    summary="Create Midtrans transaction for plan upgrade",
)
async def create_midtrans_transaction(
    payload: BillingTransactionRequest,
    current_user: CurrentUser = Depends(require_owner),
):
    service = BillingService()
    try:
        return await service.create_midtrans_transaction(payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/midtrans/webhook",
    response_model=MidtransWebhookResponse,
    summary="Handle Midtrans webhook callback",
)
async def midtrans_webhook(payload: MidtransWebhookRequest):
    service = BillingService()
    try:
        return await service.process_midtrans_webhook(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))