"""
Pydantic Models for Product/Inventory Module
Handles validation for product CRUD operations
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    """Base product schema with common fields"""
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    stock_quantity: int = Field(..., ge=0, description="Current stock quantity")
    low_stock_threshold: int = Field(default=10, ge=0, description="Alert threshold for low stock")
    is_active: bool = Field(default=True, description="Whether product is active")
    
    @field_validator('unit_price')
    @classmethod
    def validate_price(cls, v):
        """Ensure price has max 2 decimal places"""
        if v < 0:
            raise ValueError("Price cannot be negative")
        return round(v, 2)
    
    @field_validator('sku')
    @classmethod
    def validate_sku(cls, v):
        """Ensure SKU is uppercase and trimmed"""
        return v.strip().upper()


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating an existing product (all fields optional)"""
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    @field_validator('unit_price')
    @classmethod
    def validate_price(cls, v):
        """Ensure price has max 2 decimal places"""
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return round(v, 2) if v is not None else None
    
    @field_validator('sku')
    @classmethod
    def validate_sku(cls, v):
        """Ensure SKU is uppercase and trimmed"""
        return v.strip().upper() if v else None


class ProductResponse(ProductBase):
    """Schema for product response (includes DB-generated fields)"""
    id: str = Field(..., description="Product UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    created_by: Optional[str] = Field(None, description="User UUID who created the product")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Computed fields
    is_low_stock: bool = Field(default=False, description="Whether stock is below threshold")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "sku": "PROD-001",
                "name": "Laptop Dell XPS 13",
                "description": "High-performance ultrabook",
                "category": "Electronics",
                "unit_price": 15000000.00,
                "stock_quantity": 25,
                "low_stock_threshold": 10,
                "is_active": True,
                "is_low_stock": False,
                "created_by": "123e4567-e89b-12d3-a456-426614174002",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        },
    )


class ProductListResponse(BaseModel):
    """Schema for paginated product list"""
    products: list[ProductResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class StockAdjustment(BaseModel):
    """Schema for adjusting product stock"""
    adjustment: int = Field(..., description="Stock adjustment (positive to add, negative to subtract)")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for adjustment")
    
    @field_validator('adjustment')
    @classmethod
    def validate_adjustment(cls, v):
        """Ensure adjustment is not zero"""
        if v == 0:
            raise ValueError("Adjustment cannot be zero")
        return v
