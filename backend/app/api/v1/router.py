"""
Main API v1 Router
Aggregates all v1 endpoints
"""
from fastapi import APIRouter

# Import sub-routers
from app.api.v1 import (
    chat,
    invoices,
    products,
    tenants,
    users,
)

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    products.router,
    prefix="/products",
    tags=["Products"]
)

api_router.include_router(
    invoices.router,
    prefix="/invoices",
    tags=["Invoices"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["AI Chat"]
)

api_router.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["Tenants"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

# Root endpoint
@api_router.get("/")
async def api_root():
    """API v1 root endpoint"""
    return {
        "message": "NobleSoft API v1",
        "version": "1.0.0",
        "status": "operational",
        "available_endpoints": {
            "products": "/api/v1/products",
            "invoices": "/api/v1/invoices",
            "chat": "/api/v1/chat",
            "tenants": "/api/v1/tenants",
            "users": "/api/v1/users",
            "docs": "/api/docs"
        }
    }
