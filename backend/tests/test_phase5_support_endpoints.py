from fastapi.testclient import TestClient
import pytest

from app.core.dependencies import CurrentUser, get_current_user
from app.main import app
from app.services.support_service import SupportService


client = TestClient(app)


def _build_user(role: str = "owner", subscription_tier: str = "enterprise") -> CurrentUser:
    return CurrentUser(
        {
            "id": "owner-1",
            "email": "owner@noblesoft.test",
            "full_name": "Owner User",
            "role": role,
            "is_active": True,
            "tenant_id": "tenant-1",
            "tenants": {
                "company_name": "NobleSoft Test",
                "subscription_tier": subscription_tier,
                "is_active": True,
                "trial_end_date": None,
                "max_users": 20,
            },
        }
    )


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@pytest.fixture
def override_current_user():
    def _override(role: str = "owner", tier: str = "enterprise"):
        async def _dependency() -> CurrentUser:
            return _build_user(role=role, subscription_tier=tier)

        app.dependency_overrides[get_current_user] = _dependency

    return _override


def test_support_requires_enterprise_tier(override_current_user):
    override_current_user(role="owner", tier="pro")

    response = client.get("/api/v1/operations/support/tickets")

    assert response.status_code == 403
    assert "enterprise" in response.json()["detail"].lower()


def test_support_requires_admin_or_owner(override_current_user):
    override_current_user(role="member", tier="enterprise")

    response = client.get("/api/v1/operations/support/tickets")

    assert response.status_code == 403


def test_support_list_tickets_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="admin", tier="enterprise")

    async def mock_list_tickets(self, current_user, page=1, page_size=20, status=None, priority=None):
        _ = current_user
        _ = page
        _ = page_size
        _ = status
        _ = priority
        return {
            "tickets": [
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
                    "assignee_user_id": None,
                    "first_response_at": None,
                    "resolved_at": None,
                    "sla_response_deadline": "2026-04-06T09:00:00Z",
                    "sla_resolution_deadline": "2026-04-06T16:00:00Z",
                    "is_sla_response_breached": False,
                    "is_sla_resolution_breached": False,
                    "created_at": "2026-04-06T08:00:00Z",
                    "updated_at": "2026-04-06T08:00:00Z",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "has_more": False,
        }

    monkeypatch.setattr(SupportService, "list_tickets", mock_list_tickets)

    response = client.get("/api/v1/operations/support/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["tickets"][0]["priority"] == "p1"


def test_support_create_ticket_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_ticket(self, payload, current_user):
        _ = payload
        _ = current_user
        return {
            "id": "ticket-1",
            "tenant_id": "tenant-1",
            "ticket_number": "SUP-20260406-0001",
            "title": "Payment webhook delayed",
            "description": "Need investigation",
            "category": "billing",
            "priority": "p1",
            "status": "open",
            "requester_user_id": "owner-1",
            "assignee_user_id": None,
            "first_response_at": None,
            "resolved_at": None,
            "sla_response_deadline": "2026-04-06T09:00:00Z",
            "sla_resolution_deadline": "2026-04-06T16:00:00Z",
            "is_sla_response_breached": False,
            "is_sla_resolution_breached": False,
            "created_at": "2026-04-06T08:00:00Z",
            "updated_at": "2026-04-06T08:00:00Z",
        }

    monkeypatch.setattr(SupportService, "create_ticket", mock_create_ticket)

    response = client.post(
        "/api/v1/operations/support/tickets",
        json={
            "title": "Payment webhook delayed",
            "description": "Need investigation",
            "category": "billing",
            "priority": "p1",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticket_number"].startswith("SUP-")


def test_support_assign_ticket_not_found_returns_404(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_update_ticket(self, ticket_id, payload, current_user, require_assign_permission=False):
        _ = ticket_id
        _ = payload
        _ = current_user
        _ = require_assign_permission
        raise ValueError("Ticket not found")

    monkeypatch.setattr(SupportService, "update_ticket", mock_update_ticket)

    response = client.patch(
        "/api/v1/operations/support/tickets/missing-ticket",
        json={"assignee_user_id": "admin-2"},
    )

    assert response.status_code == 404


def test_support_dedicated_assign_endpoint_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test dedicated /assignee endpoint with support.assign permission"""
    override_current_user(role="admin", tier="enterprise")

    async def mock_assign_ticket(self, ticket_id, payload, current_user):
        _ = current_user
        return {
            "id": ticket_id,
            "tenant_id": "tenant-1",
            "ticket_number": "SUP-20260407-0001",
            "title": "Test ticket",
            "category": "general",
            "priority": "p2",
            "status": "open",
            "assignee_user_id": payload.assignee_user_id,
            "sla_response_deadline": "2026-04-07T16:00:00Z",
            "sla_resolution_deadline": "2026-04-08T12:00:00Z",
            "is_sla_response_breached": False,
            "is_sla_resolution_breached": False,
            "created_at": "2026-04-07T12:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
        }

    monkeypatch.setattr(SupportService, "assign_ticket", mock_assign_ticket)

    response = client.patch(
        "/api/v1/operations/support/tickets/test-ticket-1/assignee",
        json={"assignee_user_id": "user-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assignee_user_id"] == "user-123"


def test_support_assign_forbidden_without_assign_permission(monkeypatch: pytest.MonkeyPatch):
    """Test that assign endpoint requires support.assign permission"""
    # User with only support.write but not support.assign
    def _build_limited_user() -> CurrentUser:
        return CurrentUser(
            {
                "id": "user-1",
                "email": "user@test.com",
                "role": "member",
                "permission_codes": ["support.read", "support.write"],
                "is_active": True,
                "tenant_id": "tenant-1",
                "tenants": {
                    "company_name": "Test Co",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "max_users": 10,
                },
            }
        )

    async def _dependency() -> CurrentUser:
        return _build_limited_user()

    app.dependency_overrides[get_current_user] = _dependency

    response = client.patch(
        "/api/v1/operations/support/tickets/test-ticket-1/assignee",
        json={"assignee_user_id": "user-456"},
    )

    assert response.status_code == 403


def test_support_update_with_assignee_blocked_without_assign_permission(monkeypatch: pytest.MonkeyPatch):
    """Test that updating assignee via general update endpoint is blocked without support.assign permission"""
    # User with only support.write but not support.assign
    def _build_limited_user() -> CurrentUser:
        return CurrentUser(
            {
                "id": "user-1",
                "email": "user@test.com",
                "role": "member",
                "permission_codes": ["support.read", "support.write"],
                "is_active": True,
                "tenant_id": "tenant-1",
                "tenants": {
                    "company_name": "Test Co",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "max_users": 10,
                },
            }
        )

    async def _dependency() -> CurrentUser:
        return _build_limited_user()

    app.dependency_overrides[get_current_user] = _dependency

    async def mock_update_ticket(self, ticket_id, payload, current_user, require_assign_permission=False):
        _ = ticket_id
        _ = current_user
        if require_assign_permission and hasattr(payload, 'assignee_user_id') and payload.assignee_user_id:
            raise ValueError("Insufficient permission: support.assign required to change assignee")
        return {
            "id": ticket_id,
            "tenant_id": "tenant-1",
            "ticket_number": "SUP-20260407-0001",
            "title": "Test ticket",
            "category": "general",
            "priority": "p2",
            "status": "in_progress",
            "assignee_user_id": None,
            "sla_response_deadline": "2026-04-07T16:00:00Z",
            "sla_resolution_deadline": "2026-04-08T12:00:00Z",
            "is_sla_response_breached": False,
            "is_sla_resolution_breached": False,
            "created_at": "2026-04-07T12:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
        }

    monkeypatch.setattr(SupportService, "update_ticket", mock_update_ticket)

    # This should be blocked (403) because payload contains assignee_user_id
    response = client.patch(
        "/api/v1/operations/support/tickets/test-ticket-1",
        json={"assignee_user_id": "user-789", "status": "in_progress"},
    )

    assert response.status_code == 403


def test_support_update_non_assignment_allowed_with_write_permission(monkeypatch: pytest.MonkeyPatch):
    """Test that non-assignment updates work with only support.write permission"""
    # User with only support.write
    def _build_limited_user() -> CurrentUser:
        return CurrentUser(
            {
                "id": "user-1",
                "email": "user@test.com",
                "role": "member",
                "permission_codes": ["support.read", "support.write"],
                "is_active": True,
                "tenant_id": "tenant-1",
                "tenants": {
                    "company_name": "Test Co",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "max_users": 10,
                },
            }
        )

    async def _dependency() -> CurrentUser:
        return _build_limited_user()

    app.dependency_overrides[get_current_user] = _dependency

    async def mock_update_ticket(self, ticket_id, payload, current_user, require_assign_permission=False):
        _ = ticket_id
        _ = current_user
        _ = require_assign_permission
        return {
            "id": ticket_id,
            "tenant_id": "tenant-1",
            "ticket_number": "SUP-20260407-0001",
            "title": "Updated ticket",
            "category": "general",
            "priority": "p2",
            "status": "resolved",
            "assignee_user_id": None,
            "sla_response_deadline": "2026-04-07T16:00:00Z",
            "sla_resolution_deadline": "2026-04-08T12:00:00Z",
            "is_sla_response_breached": False,
            "is_sla_resolution_breached": False,
            "created_at": "2026-04-07T12:00:00Z",
            "updated_at": "2026-04-07T14:00:00Z",
        }

    monkeypatch.setattr(SupportService, "update_ticket", mock_update_ticket)

    # This should succeed - only updating status, not assignee
    response = client.patch(
        "/api/v1/operations/support/tickets/test-ticket-1",
        json={"status": "resolved", "title": "Updated ticket"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["title"] == "Updated ticket"

