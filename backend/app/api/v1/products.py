"""
Product API Endpoints
RESTful API for product/inventory management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from app.core.dependencies import get_current_user, CurrentUser
from app.services.product_service import ProductService
from app.models.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    StockAdjustment
)

router = APIRouter()


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product"
)
async def create_product(
    product_data: ProductCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a new product in the inventory.
    
    - **sku**: Unique stock keeping unit (will be converted to uppercase)
    - **name**: Product name
    - **unit_price**: Price per unit
    - **stock_quantity**: Initial stock quantity
    
    Requires authentication.
    """
    service = ProductService()
    try:
        product = await service.create_product(product_data, current_user)
        return product
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
    response_model=ProductListResponse,
    summary="List all products"
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, SKU, or description"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    List products with pagination and filters.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    - **category**: Filter by product category
    - **is_active**: Filter by active status
    - **search**: Search in name, SKU, or description
    - **low_stock_only**: Show only products below low stock threshold
    
    Requires authentication.
    """
    service = ProductService()
    try:
        result = await service.list_products(
            current_user=current_user,
            page=page,
            page_size=page_size,
            category=category,
            is_active=is_active,
            search=search,
            low_stock_only=low_stock_only
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID"
)
async def get_product(
    product_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a single product by ID.
    
    Requires authentication. Only returns products from the user's tenant.
    """
    service = ProductService()
    product = await service.get_product(product_id, current_user)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product"
)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update an existing product.
    
    All fields are optional. Only provided fields will be updated.
    
    Requires authentication.
    """
    service = ProductService()
    try:
        product = await service.update_product(product_id, product_data, current_user)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        
        return product
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


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product"
)
async def delete_product(
    product_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete a product (soft delete - sets is_active to False).
    
    Requires authentication.
    """
    service = ProductService()
    try:
        deleted = await service.delete_product(product_id, current_user)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/{product_id}/adjust-stock",
    response_model=ProductResponse,
    summary="Adjust product stock"
)
async def adjust_stock(
    product_id: str,
    adjustment: StockAdjustment,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Adjust product stock quantity.
    
    - **adjustment**: Positive to add stock, negative to subtract
    - **reason**: Optional reason for the adjustment
    
    Example: {"adjustment": 10, "reason": "Restocked from supplier"}
    
    Requires authentication.
    """
    service = ProductService()
    try:
        product = await service.adjust_stock(product_id, adjustment, current_user)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        
        return product
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
