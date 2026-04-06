from fastapi.testclient import TestClient
import pytest

from app.core.dependencies import CurrentUser, get_current_user
from app.main import app
from app.models.governance import BranchDeleteResponse
from app.services.governance_service import GovernanceService


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


def _role_payload() -> dict:
    return {
        "id": "role-1",
        "tenant_id": "tenant-1",
        "code": "finance_manager",
        "name": "Finance Manager",
        "description": "Can manage finance approval",
        "is_system": False,
        "is_active": True,
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
    }


def test_governance_roles_requires_enterprise_tier(override_current_user):
    override_current_user(role="owner", tier="pro")

    response = client.get("/api/v1/governance/roles")

    assert response.status_code == 403
    assert "enterprise" in response.json()["detail"].lower()


def test_governance_roles_requires_admin_or_owner(override_current_user):
    override_current_user(role="member", tier="enterprise")

    response = client.get("/api/v1/governance/roles")

    assert response.status_code == 403


def test_list_roles_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="admin", tier="enterprise")

    async def mock_list_roles(self, current_user, include_inactive=False):
        _ = include_inactive
        return {
            "roles": [_role_payload()],
            "total": 1,
        }

    monkeypatch.setattr(GovernanceService, "list_roles", mock_list_roles)

    response = client.get("/api/v1/governance/roles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["roles"][0]["code"] == "finance_manager"


def test_create_role_duplicate_code_returns_400(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_create_role(self, payload, current_user):
        _ = payload
        _ = current_user
        raise ValueError("Role with code 'finance_manager' already exists")

    monkeypatch.setattr(GovernanceService, "create_role", mock_create_role)

    response = client.post(
        "/api/v1/governance/roles",
        json={
            "code": "finance_manager",
            "name": "Finance Manager",
        },
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_audit_logs_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_list_audit_logs(self, current_user, page=1, page_size=50, action=None, resource_type=None):
        _ = current_user
        _ = page
        _ = page_size
        _ = action
        _ = resource_type
        return {
            "logs": [
                {
                    "id": "audit-1",
                    "tenant_id": "tenant-1",
                    "actor_user_id": "owner-1",
                    "action": "update",
                    "resource_type": "roles",
                    "resource_id": "role-1",
                    "old_values": {"name": "Old Name"},
                    "new_values": {"name": "New Name"},
                    "metadata": {"source": "api"},
                    "created_at": "2026-03-01T10:00:00Z",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 50,
            "has_more": False,
        }

    monkeypatch.setattr(GovernanceService, "list_audit_logs", mock_list_audit_logs)

    response = client.get("/api/v1/governance/audit-logs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["logs"][0]["resource_type"] == "roles"


def test_delete_branch_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_delete_branch(self, branch_id, current_user):
        _ = current_user
        return BranchDeleteResponse(
            branch_id=branch_id,
            deleted=True,
        )

    monkeypatch.setattr(GovernanceService, "delete_branch", mock_delete_branch)

    response = client.delete("/api/v1/governance/branches/branch-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["branch_id"] == "branch-1"
    assert payload["deleted"] is True


def test_delete_branch_not_found_returns_404(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_delete_branch(self, branch_id, current_user):
        _ = current_user
        return BranchDeleteResponse(
            branch_id=branch_id,
            deleted=False,
        )

    monkeypatch.setattr(GovernanceService, "delete_branch", mock_delete_branch)

    response = client.delete("/api/v1/governance/branches/missing-branch")

    assert response.status_code == 404


def test_delete_branch_active_returns_400(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user(role="owner", tier="enterprise")

    async def mock_delete_branch(self, branch_id, current_user):
        _ = branch_id
        _ = current_user
        raise ValueError("Branch must be deactivated before permanent deletion")

    monkeypatch.setattr(GovernanceService, "delete_branch", mock_delete_branch)

    response = client.delete("/api/v1/governance/branches/branch-active")

    assert response.status_code == 400
    assert "deactivated" in response.json()["detail"].lower()
