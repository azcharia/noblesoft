# API Testing Guide

## Quick Start

1. From repo root, start backend API:

	```powershell
	cd backend
	.\venv\Scripts\uvicorn.exe app.main:app --reload
	```

2. Open API docs:

	- Swagger UI: http://localhost:8000/api/docs
	- OpenAPI JSON: http://localhost:8000/api/openapi.json

3. Authorize with JWT in Swagger:

	```text
	Bearer <your-jwt-token>
	```

4. Run automated checks when needed:

	```powershell
	cd ..
	powershell -ExecutionPolicy Bypass -File .\preflight.ps1
	```

## Pre-Audit Verification Sequence

Gunakan urutan ini secara konsisten untuk semua audit QA agar hasil staging dan production dapat dibandingkan dengan metode yang sama.

### Step 0 - Cross-Environment SQL Healthcheck (Staging -> Production)

1. Buka Supabase SQL Editor untuk **staging**.
2. Jalankan isi file `supabase_phase5_healthcheck.sql`.
3. Simpan output tabel hasil (section/check_id/status/details).
4. Ulangi langkah yang sama di **production**.
5. Bandingkan output staging vs production untuk mendeteksi schema drift.

Pass/Fail:
- PASS: tidak ada row `status = FAIL` pada check `severity = critical`.
- WARN: boleh lanjut hanya jika tidak ada critical FAIL.
- FAIL: stop audit, lakukan remediation schema terlebih dahulu.

### Step 1 - Backend Schema Probe (Application-Level)

```powershell
cd backend
.\venv\Scripts\python.exe scripts\check_phase5_schema.py
```

Pass/Fail:
- Exit `0`: PASS.
- Exit `2`: WARN (credential placeholder/missing), boleh lanjut untuk mode lokal.
- Exit `1`: FAIL, wajib perbaiki schema dulu.

### Step 2 - Backend Phase 5 Targeted Tests

```powershell
cd backend
$env:PYTHONPATH='.'
.\venv\Scripts\pytest.exe tests\test_phase5_support_endpoints.py tests\test_phase5_support_service_sla.py tests\test_phase5_qbr_endpoints.py tests\test_phase5_qbr_service_metrics.py tests\test_phase5_onboarding_endpoints.py -v --tb=short
```

Pass/Fail:
- PASS: semua test file Phase 5 lulus.
- FAIL: perbaiki issue sesuai domain (Support/QBR/Onboarding), lalu rerun Step 2.

### Step 3 - Frontend Quality and Tests

```powershell
cd frontend
npm run type-check
npm run lint
npm run test:run
```

Pass/Fail:
- PASS: type-check 0 error, lint 0 error, tests lulus.
- FAIL: perbaiki dulu, lalu ulang Step 3.

### Step 4 - Full Integrated Gate

```powershell
cd ..
powershell -ExecutionPolicy Bypass -File .\preflight.ps1
```

Pass/Fail:
- PASS: seluruh tahap preflight lulus (compile, schema probe, backend tests, frontend lint, frontend type-check).
- FAIL: perbaiki tahap yang gagal lalu rerun preflight.

### Required QA Artifacts

Simpan artefak berikut untuk audit package:
1. Output SQL healthcheck di staging.
2. Output SQL healthcheck di production.
3. Output `check_phase5_schema.py`.
4. Output pytest Phase 5 targeted.
5. Output frontend checks (`type-check`, `lint`, `test:run`).
6. Output preflight final.

Gunakan penamaan artefak berisi timestamp dan environment (contoh: `schema-healthcheck-staging-YYYYMMDD-HHMM.txt`).

## Getting JWT Token

1. Login through frontend (recommended) and reuse session token.
2. Or use Supabase auth flow for a test user and copy access token.
3. Ensure token user belongs to the target tenant and has expected role/permissions.

## Endpoint Coverage

### Core APIs

- Products: `GET/POST /api/v1/products/`, `GET/PATCH/DELETE /api/v1/products/{id}`, `POST /api/v1/products/{id}/adjust-stock`
- Invoices: `GET/POST /api/v1/invoices/`, `GET/PATCH/DELETE /api/v1/invoices/{id}`, `PATCH /api/v1/invoices/{id}/payment-status`
- Tenants: `GET/PATCH /api/v1/tenants/current`, `POST /api/v1/tenants/current/subscription`
- Users: `GET /api/v1/users/`, `POST /api/v1/users/invite`, `DELETE /api/v1/users/{id}`
- Billing: `GET /api/v1/billing/status`, `POST /api/v1/billing/midtrans/transaction`, `POST /api/v1/billing/midtrans/webhook`
- Chat: `POST /api/v1/chat/`, `GET /api/v1/chat/suggestions`, `POST /api/v1/chat/function-call`
- Governance: role, branch, permission matrix, audit log endpoints under `/api/v1/governance/*`

### Operations: Onboarding

- `GET /api/v1/operations/onboarding`
- `POST /api/v1/operations/onboarding/items`
- `PATCH /api/v1/operations/onboarding/items/{item_id}`
- `POST /api/v1/operations/onboarding/items/{item_id}/complete`

### Operations: Support

- `GET /api/v1/operations/support/tickets`
- `POST /api/v1/operations/support/tickets`
- `GET /api/v1/operations/support/tickets/{ticket_id}`
- `PATCH /api/v1/operations/support/tickets/{ticket_id}`
- `PATCH /api/v1/operations/support/tickets/{ticket_id}/assignee`
- `POST /api/v1/operations/support/tickets/{ticket_id}/comments`
- `GET /api/v1/operations/support/overview`

### Operations: QBR

- `GET /api/v1/operations/qbr/cycles`
- `POST /api/v1/operations/qbr/cycles`
- `PATCH /api/v1/operations/qbr/cycles/{cycle_id}`
- `GET /api/v1/operations/qbr/goals`
- `POST /api/v1/operations/qbr/goals`
- `PATCH /api/v1/operations/qbr/goals/{goal_id}`
- `GET /api/v1/operations/qbr/dashboard`

## Auth, Tier, and Permission Rules

1. Enterprise operations require enterprise subscription.
2. Operations endpoints require role `owner` or `admin`.
3. Most operations endpoints use `require_enterprise_permission(<code>)`.
4. Governance endpoints require enterprise admin (`owner` or `admin`).
5. Rate limiter can return `429` for tier-specific limit breaches.

### Operations Permission Matrix

| Domain | Endpoint | Permission | Notes |
| --- | --- | --- | --- |
| Onboarding | `GET /api/v1/operations/onboarding` | `onboarding.read` | List checklist and progress metrics |
| Onboarding | `POST /api/v1/operations/onboarding/items` | `onboarding.write` | Create checklist item |
| Onboarding | `PATCH /api/v1/operations/onboarding/items/{item_id}` | `onboarding.write` | Update checklist item fields |
| Onboarding | `POST /api/v1/operations/onboarding/items/{item_id}/complete` | `onboarding.write` | Mark checklist item completed |
| Support | `GET /api/v1/operations/support/tickets` | `support.read` | List tickets with filters |
| Support | `POST /api/v1/operations/support/tickets` | `support.write` | Create support ticket |
| Support | `GET /api/v1/operations/support/tickets/{ticket_id}` | `support.read` | Retrieve ticket detail + comments |
| Support | `PATCH /api/v1/operations/support/tickets/{ticket_id}` | `support.write` and conditional `support.assign` | Non-assignment updates allowed with `support.write`; if payload includes `assignee_user_id`, `support.assign` is required |
| Support | `PATCH /api/v1/operations/support/tickets/{ticket_id}/assignee` | `support.assign` | Dedicated assignment endpoint |
| Support | `POST /api/v1/operations/support/tickets/{ticket_id}/comments` | `support.write` | Add support ticket comment |
| Support | `GET /api/v1/operations/support/overview` | `support.read` | Fetch support metrics and SLA summary |
| QBR | `GET /api/v1/operations/qbr/cycles` | `qbr.read` | List cycles |
| QBR | `POST /api/v1/operations/qbr/cycles` | `qbr.write` | Create cycle |
| QBR | `PATCH /api/v1/operations/qbr/cycles/{cycle_id}` | `qbr.write` | Update cycle |
| QBR | `GET /api/v1/operations/qbr/goals` | `qbr.read` | List goals |
| QBR | `POST /api/v1/operations/qbr/goals` | `qbr.write` | Create goal |
| QBR | `PATCH /api/v1/operations/qbr/goals/{goal_id}` | `qbr.write` | Update goal |
| QBR | `GET /api/v1/operations/qbr/dashboard` | `qbr.read` | Dashboard with cycle, goals, and metrics |

### Support Assignment Decision Rule

1. `PATCH /api/v1/operations/support/tickets/{ticket_id}`:
	- If payload does NOT include `assignee_user_id`, `support.write` is enough.
	- If payload includes `assignee_user_id`, caller also needs `support.assign`.
2. `PATCH /api/v1/operations/support/tickets/{ticket_id}/assignee` always requires `support.assign`.

## Operations Request/Response Examples

### Support: Create Ticket (201)

```http
POST /api/v1/operations/support/tickets
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"title": "Payment webhook delayed",
	"description": "Need investigation",
	"category": "billing",
	"priority": "p1"
}
```

```json
{
	"id": "ticket-1",
	"tenant_id": "tenant-1",
	"ticket_number": "SUP-20260406-0001",
	"title": "Payment webhook delayed",
	"description": "Need investigation",
	"category": "billing",
	"priority": "p1",
	"status": "open",
	"requester_user_id": "owner-1",
	"assignee_user_id": null,
	"first_response_at": null,
	"resolved_at": null,
	"sla_response_deadline": "2026-04-06T09:00:00Z",
	"sla_resolution_deadline": "2026-04-06T16:00:00Z",
	"is_sla_response_breached": false,
	"is_sla_resolution_breached": false,
	"created_at": "2026-04-06T08:00:00Z",
	"updated_at": "2026-04-06T08:00:00Z"
}
```

### Support: Assign Ticket via Dedicated Endpoint (200)

```http
PATCH /api/v1/operations/support/tickets/ticket-1/assignee
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"assignee_user_id": "admin-2"
}
```

```json
{
	"id": "ticket-1",
	"ticket_number": "SUP-20260407-0001",
	"title": "Test ticket",
	"priority": "p2",
	"status": "open",
	"assignee_user_id": "admin-2"
}
```

### Support: Non-Assignment Update with support.write (200)

```http
PATCH /api/v1/operations/support/tickets/ticket-1
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"status": "in_progress",
	"priority": "p2"
}
```

```json
{
	"id": "ticket-1",
	"status": "in_progress",
	"priority": "p2",
	"assignee_user_id": null
}
```

### QBR: Create Cycle (201)

```http
POST /api/v1/operations/qbr/cycles
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"quarter_code": "2026-Q2",
	"title": "Q2 2026 Review",
	"start_date": "2026-04-01",
	"end_date": "2026-06-30",
	"status": "active"
}
```

```json
{
	"id": "cycle-1",
	"tenant_id": "tenant-1",
	"quarter_code": "2026-Q2",
	"title": "Q2 2026 Review",
	"start_date": "2026-04-01",
	"end_date": "2026-06-30",
	"status": "active",
	"notes": null,
	"created_by": "owner-1",
	"created_at": "2026-04-01T08:00:00Z",
	"updated_at": "2026-04-01T08:00:00Z"
}
```

### QBR: Create Goal with Minimal Required Fields (201)

```http
POST /api/v1/operations/qbr/goals
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"cycle_id": "cycle-1",
	"title": "Simple Goal",
	"target_value": 5000000
}
```

```json
{
	"id": "goal-minimal",
	"tenant_id": "tenant-1",
	"cycle_id": "cycle-1",
	"title": "Simple Goal",
	"description": null,
	"metric_name": null,
	"unit": null,
	"target_value": 5000000,
	"current_value": 0,
	"owner_user_id": null,
	"status": "on_track",
	"due_date": null,
	"created_at": "2026-04-07T13:00:00Z",
	"updated_at": "2026-04-07T13:00:00Z",
	"progress_percentage": 0
}
```

### Onboarding: Create Item (201)

```http
POST /api/v1/operations/onboarding/items
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"code": "company_profile",
	"title": "Lengkapi Profil Perusahaan",
	"description": "Isi data legal",
	"category": "workspace",
	"is_required": true,
	"status": "pending",
	"sort_order": 10
}
```

```json
{
	"id": "onboard-1",
	"tenant_id": "tenant-1",
	"code": "company_profile",
	"title": "Lengkapi Profil Perusahaan",
	"description": "Isi data legal",
	"category": "workspace",
	"is_required": true,
	"status": "pending",
	"sort_order": 10,
	"due_date": null,
	"completed_at": null,
	"completed_by": null,
	"created_at": "2026-04-01T10:00:00Z",
	"updated_at": "2026-04-01T10:00:00Z"
}
```

### Onboarding: Update Item (200)

```http
PATCH /api/v1/operations/onboarding/items/onboard-1
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
	"title": "Updated Title",
	"description": "Updated description",
	"category": "team",
	"status": "in_progress",
	"due_date": "2026-05-01",
	"is_required": false
}
```

```json
{
	"id": "onboard-1",
	"code": "company_profile",
	"title": "Updated Title",
	"category": "team",
	"status": "in_progress",
	"due_date": "2026-05-01",
	"is_required": false
}
```

## High-Value Manual Scenarios

1. Support write-only user updates status/title without assignment change.
	- Request: `PATCH /api/v1/operations/support/tickets/{ticket_id}` with status/title only.
	- Expected: `200`.
2. Support write-only user is forbidden when assigning ticket.
	- Request: `PATCH /api/v1/operations/support/tickets/{ticket_id}` with `assignee_user_id` or dedicated `/assignee` endpoint.
	- Expected: `403`.
3. QBR goal creation validates required fields (`cycle_id`, `title`, `target_value`).
	- Request missing `target_value`.
	- Expected: `422`.
4. QBR goal creation fails when `cycle_id` does not exist.
	- Request: `POST /api/v1/operations/qbr/goals` with invalid `cycle_id`.
	- Expected: `404`.
5. Onboarding item update returns `404` for invalid item id.
	- Request: `PATCH /api/v1/operations/onboarding/items/{item_id}` with missing id.
	- Expected: `404`.
6. Governance matrix update persists permission changes and audit logs.

## Automated Verification Commands

### Backend phase-5 targeted checks

```powershell
cd backend
$env:PYTHONPATH='.'
.\venv\Scripts\pytest.exe tests\test_phase5_support_endpoints.py tests\test_phase5_support_service_sla.py tests\test_phase5_qbr_endpoints.py tests\test_phase5_qbr_service_metrics.py tests\test_phase5_onboarding_endpoints.py -v --tb=short
```

### Frontend targeted checks

```powershell
cd frontend
npm run type-check
npm run lint
npm run test:run
```

### Full project gate

```powershell
cd ..
powershell -ExecutionPolicy Bypass -File .\preflight.ps1
```
