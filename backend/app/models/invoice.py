"""
Pydantic Models for Invoice Module
Handles validation for invoice and invoice item CRUD operations
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status enum"""
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"


class InvoiceItemBase(BaseModel):
    """Base schema for invoice line items"""
    product_id: Optional[str] = Field(None, description="Product UUID (optional)")
    description: str = Field(..., min_length=1, max_length=255, description="Item description")
    quantity: int = Field(..., gt=0, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    
    @field_validator('unit_price')
    @classmethod
    def validate_price(cls, v):
        """Ensure price has max 2 decimal places"""
        if v < 0:
            raise ValueError("Price cannot be negative")
        return round(v, 2)


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating invoice items"""
    pass


class InvoiceItemResponse(InvoiceItemBase):
    """Schema for invoice item response"""
    id: str = Field(..., description="Invoice item UUID")
    invoice_id: str = Field(..., description="Parent invoice UUID")
    line_total: Decimal = Field(..., description="Calculated line total (quantity * unit_price)")
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    """Base invoice schema"""
    invoice_number: str = Field(..., min_length=1, max_length=50, description="Unique invoice number")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email")
    customer_phone: Optional[str] = Field(None, max_length=50, description="Customer phone")
    issue_date: date = Field(default_factory=date.today, description="Invoice issue date")
    due_date: Optional[date] = Field(None, description="Payment due date")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator('invoice_number')
    @classmethod
    def validate_invoice_number(cls, v):
        """Ensure invoice number is uppercase and trimmed"""
        return v.strip().upper()
    
    @field_validator('customer_email')
    @classmethod
    def validate_email(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v.lower() if v else None
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Ensure due_date is after issue_date"""
        if self.due_date and self.issue_date and self.due_date < self.issue_date:
            raise ValueError("Due date cannot be before issue date")
        return self


class InvoiceCreate(InvoiceBase):
    """Schema for creating a new invoice with items"""
    items: List[InvoiceItemCreate] = Field(..., min_length=1, description="Invoice line items")
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="Tax amount")
    
    @field_validator('tax_amount')
    @classmethod
    def validate_tax(cls, v):
        """Ensure tax has max 2 decimal places"""
        return round(v, 2)
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        """Ensure at least one item"""
        if not v or len(v) == 0:
            raise ValueError("Invoice must have at least one item")
        return v


class InvoiceUpdate(BaseModel):
    """Schema for updating an existing invoice (all fields optional)"""
    invoice_number: Optional[str] = Field(None, min_length=1, max_length=50)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=50)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_status: Optional[PaymentStatus] = None
    notes: Optional[str] = None
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    
    @field_validator('invoice_number')
    @classmethod
    def validate_invoice_number(cls, v):
        """Ensure invoice number is uppercase and trimmed"""
        return v.strip().upper() if v else None
    
    @field_validator('customer_email')
    @classmethod
    def validate_email(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v.lower() if v else None
    
    @field_validator('tax_amount')
    @classmethod
    def validate_tax(cls, v):
        """Ensure tax has max 2 decimal places"""
        return round(v, 2) if v is not None else None


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response (includes DB-generated fields and items)"""
    id: str = Field(..., description="Invoice UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    tax_amount: Decimal = Field(..., description="Tax amount")
    total_amount: Decimal = Field(..., description="Total amount (subtotal + tax)")
    payment_status: PaymentStatus = Field(..., description="Payment status")
    created_by: Optional[str] = Field(None, description="User UUID who created the invoice")
    created_at: datetime
    updated_at: datetime
    
    # Nested items
    items: List[InvoiceItemResponse] = Field(default_factory=list, description="Invoice line items")
    
    # Computed fields
    is_overdue: bool = Field(default=False, description="Whether invoice is overdue")
    days_until_due: Optional[int] = Field(None, description="Days until due date (negative if overdue)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "invoice_number": "INV-2024-001",
                "customer_name": "PT Maju Jaya",
                "customer_email": "finance@majujaya.co.id",
                "customer_phone": "+62812345678",
                "issue_date": "2024-01-15",
                "due_date": "2024-02-15",
                "subtotal": 50000000.00,
                "tax_amount": 5500000.00,
                "total_amount": 55500000.00,
                "payment_status": "unpaid",
                "notes": "Terima kasih atas kepercayaan Anda",
                "is_overdue": False,
                "days_until_due": 31,
                "created_by": "123e4567-e89b-12d3-a456-426614174002",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174003",
                        "invoice_id": "123e4567-e89b-12d3-a456-426614174000",
                        "product_id": "123e4567-e89b-12d3-a456-426614174004",
                        "description": "Laptop Dell XPS 13",
                        "quantity": 5,
                        "unit_price": 10000000.00,
                        "line_total": 50000000.00,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        },
    )


class InvoiceListResponse(BaseModel):
    """Schema for paginated invoice list"""
    invoices: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class PaymentStatusUpdate(BaseModel):
    """Schema for updating payment status"""
    payment_status: PaymentStatus = Field(..., description="New payment status")
    notes: Optional[str] = Field(None, description="Payment notes")
