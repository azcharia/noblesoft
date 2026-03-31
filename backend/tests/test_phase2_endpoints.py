from fastapi.testclient import TestClient
import pytest

from app.core.dependencies import CurrentUser, get_current_user
from app.main import app
from app.services.billing_service import BillingService
from app.services.tenant_service import TenantService


client = TestClient(app)


def _build_user(role: str = "owner", subscription_tier: str = "pro") -> CurrentUser:
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
    def _override(role: str = "owner", tier: str = "pro"):
        async def _dependency() -> CurrentUser:
            return _build_user(role=role, subscription_tier=tier)

        app.dependency_overrides[get_current_user] = _dependency

    return _override


def _tenant_payload(subscription_tier: str = "pro") -> dict:
    return {
        "id": "tenant-1",
        "company_name": "NobleSoft Test",
        "subscription_tier": subscription_tier,
        "trial_start_date": None,
        "trial_end_date": None,
        "is_active": True,
        "max_users": 20,
        "payment_gateway_customer_id": None,
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
    }


def _user_payload() -> dict:
    return {
        "id": "user-2",
        "tenant_id": "tenant-1",
        "email": "member@noblesoft.test",
        "full_name": "Member User",
        "role": "member",
        "is_active": True,
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
    }


def test_get_current_tenant_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("owner")

    async def mock_get_current_tenant(self, current_user):
        return _tenant_payload("pro")

    monkeypatch.setattr(TenantService, "get_current_tenant", mock_get_current_tenant)

    response = client.get("/api/v1/tenants/current")

    assert response.status_code == 200
    assert response.json()["company_name"] == "NobleSoft Test"


def test_update_current_tenant_requires_owner(override_current_user):
    override_current_user("member")

    response = client.patch(
        "/api/v1/tenants/current",
        json={"company_name": "Renamed Company"},
    )

    assert response.status_code == 403


def test_update_subscription_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("owner", "basic")

    async def mock_update_subscription_tier(self, payload, current_user):
        return {
            "tenant": _tenant_payload("pro"),
            "previous_tier": "basic",
            "updated_tier": "pro",
        }

    monkeypatch.setattr(TenantService, "update_subscription_tier", mock_update_subscription_tier)

    response = client.post(
        "/api/v1/tenants/current/subscription",
        json={"subscription_tier": "pro"},
    )

    assert response.status_code == 200
    assert response.json()["updated_tier"] == "pro"


def test_list_users_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("admin")

    async def mock_list_tenant_users(self, current_user, include_inactive=False):
        return {
            "users": [_user_payload()],
            "total": 1,
        }

    monkeypatch.setattr(TenantService, "list_tenant_users", mock_list_tenant_users)

    response = client.get("/api/v1/users")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["users"][0]["email"] == "member@noblesoft.test"


def test_invite_user_forbidden_for_member(override_current_user):
    override_current_user("member")

    response = client.post(
        "/api/v1/users/invite",
        json={
            "email": "new@noblesoft.test",
            "full_name": "New User",
            "role": "member",
        },
    )

    assert response.status_code == 403


def test_invite_user_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("admin")

    async def mock_invite_tenant_user(self, payload, current_user):
        return {
            "user": _user_payload(),
            "temporary_password": "temp-pass-123",
        }

    monkeypatch.setattr(TenantService, "invite_tenant_user", mock_invite_tenant_user)

    response = client.post(
        "/api/v1/users/invite",
        json={
            "email": "new@noblesoft.test",
            "full_name": "New User",
            "role": "member",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["temporary_password"] == "temp-pass-123"


def test_deactivate_user_not_found(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("admin")

    async def mock_deactivate_tenant_user(self, user_id, current_user):
        return {"user_id": user_id, "deactivated": False}

    monkeypatch.setattr(TenantService, "deactivate_tenant_user", mock_deactivate_tenant_user)

    response = client.delete("/api/v1/users/unknown-user")

    assert response.status_code == 404


def test_billing_status_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("owner")

    async def mock_get_billing_status(self, current_user):
        return {
            "tenant_id": "tenant-1",
            "company_name": "NobleSoft Test",
            "subscription_tier": "pro",
            "is_active": True,
            "max_users": 20,
            "payment_gateway_customer_id": None,
        }

    monkeypatch.setattr(BillingService, "get_billing_status", mock_get_billing_status)

    response = client.get("/api/v1/billing/status")

    assert response.status_code == 200
    assert response.json()["subscription_tier"] == "pro"


def test_create_midtrans_transaction_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("owner")

    async def mock_create_midtrans_transaction(self, payload, current_user):
        return {
            "order_id": "NSFT_tenant-1_pro_12345",
            "token": "snap-token",
            "redirect_url": "https://midtrans.example/redirect",
            "target_tier": "pro",
            "amount": "100000.00",
        }

    monkeypatch.setattr(BillingService, "create_midtrans_transaction", mock_create_midtrans_transaction)

    response = client.post(
        "/api/v1/billing/midtrans/transaction",
        json={
            "target_tier": "pro",
            "amount": 100000,
            "customer_email": "owner@noblesoft.test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token"] == "snap-token"


def test_midtrans_webhook_invalid_signature(monkeypatch: pytest.MonkeyPatch):
    async def mock_process_midtrans_webhook(self, payload):
        raise ValueError("Invalid Midtrans webhook signature")

    monkeypatch.setattr(BillingService, "process_midtrans_webhook", mock_process_midtrans_webhook)

    response = client.post(
        "/api/v1/billing/midtrans/webhook",
        json={
            "order_id": "NSFT_tenant-1_pro_12345",
            "status_code": "200",
            "gross_amount": "100000.00",
            "signature_key": "invalid-signature",
            "transaction_status": "settlement",
        },
    )

    assert response.status_code == 400
    assert "Invalid Midtrans webhook signature" in response.json()["detail"]