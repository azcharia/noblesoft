"""
NobleSoft FastAPI Application Entry Point
Handles CORS, middleware, and API router registration
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
import logging
import time

from app.core.middleware import TenantContextMiddleware
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DOC_PATH_PREFIXES = ("/api/docs", "/api/redoc", "/api/openapi.json")


def _json_safe_validation_errors(errors: list[dict]) -> list[dict]:
    """Convert non-serializable objects in validation errors into strings."""
    safe_errors = []
    for error in errors:
        safe_error = dict(error)
        ctx = safe_error.get("ctx")
        if isinstance(ctx, dict):
            safe_ctx = {}
            for key, value in ctx.items():
                safe_ctx[key] = str(value) if isinstance(value, Exception) else value
            safe_error["ctx"] = safe_ctx
        safe_errors.append(safe_error)
    return safe_errors


def _resolve_csp() -> str:
    if settings.ENVIRONMENT == "production":
        return settings.SECURITY_CSP_PROD
    return settings.SECURITY_CSP_DEV

# ============================================
# Lifespan Events
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown lifecycle events."""
    logger.info("🚀 NobleSoft API starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    # Initialize AI services, database connections, etc.
    yield
    logger.info("🛑 NobleSoft API shutting down...")
    # Cleanup resources, close connections, etc.


# Initialize FastAPI app
app = FastAPI(
    title="NobleSoft API",
    description="B2B SaaS Enterprise AI Operating System for Indonesian UMKM",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ============================================
# CORS Configuration
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # Frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
        "X-Process-Time",
    ],
)

# ============================================
# Custom Middleware
# ============================================
# Add tenant context middleware
app.add_middleware(TenantContextMiddleware)

# Security headers and HTTPS enforcement middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    if settings.ENVIRONMENT == "production" and settings.ENFORCE_HTTPS:
        forwarded_proto = request.headers.get("x-forwarded-proto")
        request_scheme = forwarded_proto or request.url.scheme
        if request_scheme != "https":
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=308)

    response = await call_next(request)

    if settings.SECURITY_HEADERS_ENABLED:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = settings.SECURITY_REFERRER_POLICY
        response.headers["Permissions-Policy"] = settings.SECURITY_PERMISSIONS_POLICY
        response.headers["X-Frame-Options"] = settings.SECURITY_FRAME_OPTIONS

        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = settings.SECURITY_HSTS

        is_docs_path = any(
            request.url.path.startswith(prefix) for prefix in DOC_PATH_PREFIXES
        )
        if not is_docs_path:
            csp = _resolve_csp()
            if csp:
                response.headers["Content-Security-Policy"] = csp

    return response

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to track request duration"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ============================================
# Exception Handlers
# ============================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": _json_safe_validation_errors(exc.errors()),
            "message": "Validation error occurred"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

# ============================================
# Health Check Endpoints
# ============================================
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "NobleSoft API",
        "version": "1.0.0"
    }

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to NobleSoft API",
        "docs": "/api/docs",
        "health": "/health"
    }

# ============================================
# API Router Registration
# ============================================
from app.api.v1.router import api_router
# Include main API router
app.include_router(api_router, prefix="/api/v1")

if settings.ENVIRONMENT != "production":
    from app.api.v1 import test_auth

    app.include_router(test_auth.router, prefix="/api/v1/test", tags=["Test Auth"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
