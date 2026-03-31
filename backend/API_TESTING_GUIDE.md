# API Testing Guide

## Quick Start

1. Start server: `uvicorn app.main:app --reload`
2. Open docs: http://localhost:8000/api/docs
3. Click "Authorize" and enter: `Bearer <your-jwt-token>`
4. Test endpoints interactively!

## Get JWT Token

### Option 1: Supabase Dashboard
1. Go to Authentication → Users
2. Create a test user
3. Use Supabase client to login and get token

### Option 2: Frontend (Phase 5)
Login via Next.js frontend to get token

## Available Endpoints

### Products API
- `POST /api/v1/products/` - Create product
- `GET /api/v1/products/` - List products
- `GET /api/v1/products/{id}` - Get product
- `PATCH /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product
- `POST /api/v1/products/{id}/adjust-stock` - Adjust stock

### Invoices API
- `POST /api/v1/invoices/` - Create invoice
- `GET /api/v1/invoices/` - List invoices
- `GET /api/v1/invoices/{id}` - Get invoice
- `PATCH /api/v1/invoices/{id}` - Update invoice
- `PATCH /api/v1/invoices/{id}/payment-status` - Update status
- `DELETE /api/v1/invoices/{id}` - Delete invoice

### Tenants API
- `GET /api/v1/tenants/current` - Get current tenant profile
- `PATCH /api/v1/tenants/current` - Update tenant settings (owner only)
- `POST /api/v1/tenants/current/subscription` - Update tenant subscription (owner only)

### Users API
- `GET /api/v1/users/` - List tenant users (admin/owner)
- `POST /api/v1/users/invite` - Invite/create tenant user (admin/owner)
- `DELETE /api/v1/users/{id}` - Deactivate tenant user (admin/owner)

### Billing API
- `GET /api/v1/billing/status` - Get current billing status
- `POST /api/v1/billing/midtrans/transaction` - Create Midtrans transaction (owner only)
- `POST /api/v1/billing/midtrans/webhook` - Midtrans webhook callback (public, signature-verified)

## Role & Tier Notes

- Owner-only endpoints use owner role enforcement via dependency checks.
- Admin endpoints can be accessed by owner and admin roles.
- AI chat remains restricted to Pro/Enterprise tiers.
- Middleware now applies per-user tier-based rate limits with `429` response when exceeded.

## Example Requests

See PHASE_3_COMPLETE.md for detailed curl examples!
