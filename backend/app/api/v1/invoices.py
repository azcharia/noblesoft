"""
Invoice API Endpoints
RESTful API for invoice management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from app.core.dependencies import get_current_user, CurrentUser
from app.services.invoice_service import InvoiceService
from app.models.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceListResponse,
    PaymentStatus,
    PaymentStatusUpdate
)

router = APIRouter()


@router.post(
    "/",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new invoice"
)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a new invoice with line items.
    
    - **invoice_number**: Unique invoice number (will be converted to uppercase)
    - **customer_name**: Customer name
    - **items**: List of invoice line items (at least one required)
    - **tax_amount**: Tax amount (optional, default: 0)
    
    The system will automatically calculate:
    - Subtotal (sum of all line items)
    - Total amount (subtotal + tax)
    - Line totals for each item
    
    Requires authentication.
    """
    service = InvoiceService()
    try:
        invoice = await service.create_invoice(invoice_data, current_user)
        return invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=InvoiceListResponse,
    summary="List all invoices"
)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    customer_name: Optional[str] = Query(None, description="Filter by customer name"),
    overdue_only: bool = Query(False, description="Show only overdue invoices"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    List invoices with pagination and filters.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    - **payment_status**: Filter by payment status (unpaid, partial, paid, overdue)
    - **customer_name**: Filter by customer name (partial match)
    - **overdue_only**: Show only overdue invoices
    
    Each invoice includes:
    - All invoice details
    - Line items
    - Computed fields (is_overdue, days_until_due)
    
    Requires authentication.
    """
    service = InvoiceService()
    try:
        result = await service.list_invoices(
            current_user=current_user,
            page=page,
            page_size=page_size,
            payment_status=payment_status,
            customer_name=customer_name,
            overdue_only=overdue_only
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get an invoice by ID"
)
async def get_invoice(
    invoice_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a single invoice by ID with all line items.
    
    Requires authentication. Only returns invoices from the user's tenant.
    """
    service = InvoiceService()
    invoice = await service.get_invoice(invoice_id, current_user)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found"
        )
    
    return invoice


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Update an invoice"
)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update an existing invoice.
    
    All fields are optional. Only provided fields will be updated.
    
    Note: This endpoint updates invoice header information only.
    To update line items, delete and recreate the invoice.
    
    Requires authentication.
    """
    service = InvoiceService()
    try:
        invoice = await service.update_invoice(invoice_id, invoice_data, current_user)
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found"
            )
        
        return invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch(
    "/{invoice_id}/payment-status",
    response_model=InvoiceResponse,
    summary="Update invoice payment status"
)
async def update_payment_status(
    invoice_id: str,
    status_update: PaymentStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update the payment status of an invoice.
    
    - **payment_status**: New payment status (unpaid, partial, paid, overdue)
    - **notes**: Optional notes about the payment
    
    Example: {"payment_status": "paid", "notes": "Paid via bank transfer"}
    
    Requires authentication.
    """
    service = InvoiceService()
    try:
        invoice = await service.update_payment_status(invoice_id, status_update, current_user)
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found"
            )
        
        return invoice
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an invoice"
)
async def delete_invoice(
    invoice_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete an invoice and all its line items.
    
    This is a hard delete and cannot be undone.
    
    Requires authentication.
    """
    service = InvoiceService()
    try:
        deleted = await service.delete_invoice(invoice_id, current_user)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
