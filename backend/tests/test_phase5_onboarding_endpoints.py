from fastapi.testclient import TestClient
import pytest

from app.core.dependencies import CurrentUser, get_current_user
from app.main import app
from app.services.onboarding_service import OnboardingService


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


def test_onboarding_requires_enterprise_tier(override_current_user):
    override_current_user(role="owner", tier="pro")

    response = client.get("/api/v1/operations/onboarding")

    assert response.status_code == 403
    assert "enterprise" in response.json()["detail"].lower()


def test_onboarding_requires_admin_or_owner(override_current_user):
    override_current_user(role="member", tier="enterprise")

    response = client.get("/api/v1/operations/onboarding")

    assert response.status_code == 403


def test_onboarding_list_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="admin", tier="enterprise")

    async def mock_list_items(self, current_user):
        _ = current_user
        return {
            "items": [
                {
                    "id": "onboard-1",
                    "tenant_id": "tenant-1",
                    "code": "company_profile",
                    "title": "Lengkapi Profil Perusahaan",
                    "description": "Isi data legal",
                    "category": "workspace",
                    "is_required": True,
                    "status": "pending",
                    "sort_order": 10,
                    "due_date": None,
                    "completed_at": None,
                    "completed_by": None,
                    "created_at": "2026-04-01T10:00:00Z",
                    "updated_at": "2026-04-01T10:00:00Z",
                }
            ],
            "total": 1,
            "completed": 0,
            "pending": 1,
            "completion_rate": 0,
        }

    monkeypatch.setattr(OnboardingService, "list_items", mock_list_items)

    response = client.get("/api/v1/operations/onboarding")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["code"] == "company_profile"


def test_onboarding_complete_item_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_complete_item(self, item_id, current_user):
        _ = current_user
        return {
            "id": item_id,
            "tenant_id": "tenant-1",
            "code": "company_profile",
            "title": "Lengkapi Profil Perusahaan",
            "description": "Isi data legal",
            "category": "workspace",
            "is_required": True,
            "status": "completed",
            "sort_order": 10,
            "due_date": None,
            "completed_at": "2026-04-01T11:00:00Z",
            "completed_by": "owner-1",
            "created_at": "2026-04-01T10:00:00Z",
            "updated_at": "2026-04-01T11:00:00Z",
        }

    monkeypatch.setattr(OnboardingService, "complete_item", mock_complete_item)

    response = client.post("/api/v1/operations/onboarding/items/onboard-1/complete")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "onboard-1"
    assert payload["status"] == "completed"


def test_onboarding_create_duplicate_returns_400(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_item(self, payload, current_user):
        _ = payload
        _ = current_user
        raise ValueError("Onboarding item with code 'company_profile' already exists")

    monkeypatch.setattr(OnboardingService, "create_item", mock_create_item)

    response = client.post(
        "/api/v1/operations/onboarding/items",
        json={
            "code": "company_profile",
            "title": "Lengkapi Profil Perusahaan",
            "category": "workspace",
        },
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_onboarding_update_item_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test successful onboarding item update."""
    override_current_user(role="admin", tier="enterprise")

    async def mock_update_item(self, item_id, payload, current_user):
        _ = current_user
        return {
            "id": item_id,
            "tenant_id": "tenant-1",
            "code": "company_profile",
            "title": payload.title or "Updated Title",
            "description": payload.description,
            "category": payload.category or "workspace",
            "is_required": payload.is_required if payload.is_required is not None else True,
            "status": payload.status or "pending",
            "sort_order": 10,
            "due_date": payload.due_date,
            "completed_at": None,
            "completed_by": None,
            "created_at": "2026-04-01T10:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
        }

    monkeypatch.setattr(OnboardingService, "update_item", mock_update_item)

    response = client.patch(
        "/api/v1/operations/onboarding/items/onboard-1",
        json={
            "title": "Updated Title",
            "description": "Updated description",
            "category": "team",
            "status": "in_progress",
            "due_date": "2026-05-01",
            "is_required": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "onboard-1"
    assert payload["title"] == "Updated Title"
    assert payload["category"] == "team"
    assert payload["status"] == "in_progress"


def test_onboarding_update_item_partial_fields(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test updating only some fields."""
    override_current_user(role="owner", tier="enterprise")

    async def mock_update_item(self, item_id, payload, current_user):
        _ = current_user
        return {
            "id": item_id,
            "tenant_id": "tenant-1",
            "code": "invite_team",
            "title": "Invite core team",  # Original title
            "description": payload.description,  # Updated field
            "category": "team",
            "is_required": True,
            "status": payload.status or "pending",  # Updated field
            "sort_order": 20,
            "due_date": None,
            "completed_at": None,
            "completed_by": None,
            "created_at": "2026-04-01T10:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
        }

    monkeypatch.setattr(OnboardingService, "update_item", mock_update_item)

    # Only update description and status
    response = client.patch(
        "/api/v1/operations/onboarding/items/onboard-2",
        json={
            "description": "Invite at least 3 team members",
            "status": "in_progress",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["description"] == "Invite at least 3 team members"
    assert payload["status"] == "in_progress"


def test_onboarding_update_item_not_found(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test update fails with 404 when item doesn't exist."""
    override_current_user(role="owner", tier="enterprise")

    async def mock_update_item(self, item_id, payload, current_user):
        _ = item_id
        _ = payload
        _ = current_user
        raise ValueError("Onboarding item not found")

    monkeypatch.setattr(OnboardingService, "update_item", mock_update_item)

    response = client.patch(
        "/api/v1/operations/onboarding/items/nonexistent-item",
        json={
            "title": "Updated Title",
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_onboarding_update_status_to_skipped(monkeypatch: pytest.MonkeyPatch, override_current_user):
    """Test updating status to skipped."""
    override_current_user(role="admin", tier="enterprise")

    async def mock_update_item(self, item_id, payload, current_user):
        _ = current_user
        return {
            "id": item_id,
            "tenant_id": "tenant-1",
            "code": "optional_feature",
            "title": "Configure optional feature",
            "description": None,
            "category": "features",
            "is_required": False,
            "status": "skipped",
            "sort_order": 30,
            "due_date": None,
            "completed_at": None,
            "completed_by": None,
            "created_at": "2026-04-01T10:00:00Z",
            "updated_at": "2026-04-07T13:00:00Z",
        }

    monkeypatch.setattr(OnboardingService, "update_item", mock_update_item)

    response = client.patch(
        "/api/v1/operations/onboarding/items/onboard-3",
        json={
            "status": "skipped",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "skipped"

