from fastapi.testclient import TestClient
import pytest

from app.core.dependencies import CurrentUser, get_current_user
from app.main import app
from app.services.qbr_service import QBRService


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


def test_qbr_requires_enterprise_tier(override_current_user):
    override_current_user(role="owner", tier="pro")

    response = client.get("/api/v1/operations/qbr/dashboard")

    assert response.status_code == 403
    assert "enterprise" in response.json()["detail"].lower()


def test_qbr_requires_admin_or_owner(override_current_user):
    override_current_user(role="member", tier="enterprise")

    response = client.get("/api/v1/operations/qbr/dashboard")

    assert response.status_code == 403


def test_qbr_create_cycle_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_cycle(self, payload, current_user):
        _ = payload
        _ = current_user
        return {
            "id": "cycle-1",
            "tenant_id": "tenant-1",
            "quarter_code": "2026-Q2",
            "title": "Q2 2026 Review",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "status": "active",
            "notes": None,
            "created_by": "owner-1",
            "created_at": "2026-04-01T08:00:00Z",
            "updated_at": "2026-04-01T08:00:00Z",
        }

    monkeypatch.setattr(QBRService, "create_cycle", mock_create_cycle)

    response = client.post(
        "/api/v1/operations/qbr/cycles",
        json={
            "quarter_code": "2026-Q2",
            "title": "Q2 2026 Review",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "status": "active",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["quarter_code"] == "2026-Q2"


def test_qbr_create_duplicate_cycle_returns_400(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_cycle(self, payload, current_user):
        _ = payload
        _ = current_user
        raise ValueError("QBR cycle for quarter '2026-Q2' already exists")

    monkeypatch.setattr(QBRService, "create_cycle", mock_create_cycle)

    response = client.post(
        "/api/v1/operations/qbr/cycles",
        json={
            "quarter_code": "2026-Q2",
            "title": "Q2 2026 Review",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "status": "active",
        },
    )

    assert response.status_code == 400


def test_qbr_dashboard_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="admin", tier="enterprise")

    async def mock_get_dashboard(self, current_user, cycle_id=None):
        _ = current_user
        _ = cycle_id
        return {
            "cycle": {
                "id": "cycle-1",
                "tenant_id": "tenant-1",
                "quarter_code": "2026-Q2",
                "title": "Q2 2026 Review",
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "status": "active",
                "notes": None,
                "created_by": "owner-1",
                "created_at": "2026-04-01T08:00:00Z",
                "updated_at": "2026-04-01T08:00:00Z",
            },
            "goals": [
                {
                    "id": "goal-1",
                    "tenant_id": "tenant-1",
                    "cycle_id": "cycle-1",
                    "title": "Increase paid revenue",
                    "description": "Target revenue growth",
                    "metric_name": "paid_revenue",
                    "unit": "IDR",
                    "target_value": 120000000,
                    "current_value": 95000000,
                    "owner_user_id": "owner-1",
                    "status": "on_track",
                    "due_date": "2026-06-30",
                    "created_at": "2026-04-02T08:00:00Z",
                    "updated_at": "2026-04-05T08:00:00Z",
                    "progress_percentage": 79.17,
                }
            ],
            "metrics": {
                "paid_revenue": 95000000,
                "unpaid_invoice_count": 11,
                "total_products": 125,
                "low_stock_products": 14,
            },
        }

    monkeypatch.setattr(QBRService, "get_dashboard", mock_get_dashboard)

    response = client.get("/api/v1/operations/qbr/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cycle"]["quarter_code"] == "2026-Q2"
    assert payload["metrics"]["low_stock_products"] == 14


def test_qbr_create_goal_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test successful goal creation with all required fields."""
    override_current_user(role="admin", tier="enterprise")

    async def mock_create_goal(self, payload, current_user):
        _ = current_user
        return {
            "id": "goal-new",
            "tenant_id": "tenant-1",
            "cycle_id": payload.cycle_id,
            "title": payload.title,
            "description": payload.description,
            "metric_name": payload.metric_name,
            "unit": payload.unit,
            "target_value": payload.target_value,
            "current_value": payload.current_value or 0,
            "owner_user_id": payload.owner_user_id,
            "status": payload.status or "on_track",
            "due_date": payload.due_date,
            "created_at": "2026-04-07T13:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
            "progress_percentage": 0,
        }

    monkeypatch.setattr(QBRService, "create_goal", mock_create_goal)

    response = client.post(
        "/api/v1/operations/qbr/goals",
        json={
            "cycle_id": "cycle-1",
            "title": "Increase Monthly Revenue",
            "description": "Target 100M IDR monthly revenue",
            "metric_name": "monthly_revenue",
            "unit": "IDR",
            "target_value": 100000000,
            "current_value": 0,
            "status": "on_track",
            "due_date": "2026-06-30",
            "owner_user_id": "owner-1",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Increase Monthly Revenue"
    assert payload["target_value"] == 100000000
    assert payload["cycle_id"] == "cycle-1"


def test_qbr_create_goal_minimal_fields(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test goal creation with only required fields (cycle_id, title, target_value)."""
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_goal(self, payload, current_user):
        _ = current_user
        return {
            "id": "goal-minimal",
            "tenant_id": "tenant-1",
            "cycle_id": payload.cycle_id,
            "title": payload.title,
            "description": None,
            "metric_name": None,
            "unit": None,
            "target_value": payload.target_value,
            "current_value": 0,
            "owner_user_id": None,
            "status": "on_track",
            "due_date": None,
            "created_at": "2026-04-07T13:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
            "progress_percentage": 0,
        }

    monkeypatch.setattr(QBRService, "create_goal", mock_create_goal)

    response = client.post(
        "/api/v1/operations/qbr/goals",
        json={
            "cycle_id": "cycle-1",
            "title": "Simple Goal",
            "target_value": 5000000,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Simple Goal"
    assert payload["target_value"] == 5000000


def test_qbr_create_goal_cycle_not_found(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test goal creation fails with 404 when cycle doesn't exist."""
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_goal(self, payload, current_user):
        _ = payload
        _ = current_user
        raise ValueError("QBR cycle not found")

    monkeypatch.setattr(QBRService, "create_goal", mock_create_goal)

    response = client.post(
        "/api/v1/operations/qbr/goals",
        json={
            "cycle_id": "nonexistent-cycle",
            "title": "Test Goal",
            "target_value": 1000000,
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_qbr_create_goal_missing_required_fields(override_current_user):
    """Test goal creation fails with 422 when required fields are missing."""
    override_current_user(role="owner", tier="enterprise")

    # Missing target_value
    response = client.post(
        "/api/v1/operations/qbr/goals",
        json={
            "cycle_id": "cycle-1",
            "title": "Incomplete Goal",
        },
    )

    assert response.status_code == 422

