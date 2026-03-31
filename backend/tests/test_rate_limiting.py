from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.core import middleware as middleware_module
from app.core.rate_limiter import rate_limiter
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


def _mock_user(subscription_tier: str = "pro") -> dict:
    return {
        "id": "user-rate-limit",
        "email": "owner@noblesoft.test",
        "full_name": "Owner Test",
        "role": "owner",
        "is_active": True,
        "tenant_id": "tenant-rate-limit",
        "tenants": {
            "id": "tenant-rate-limit",
            "company_name": "NobleSoft Test",
            "subscription_tier": subscription_tier,
            "is_active": True,
            "trial_end_date": None,
            "max_users": 20,
        },
    }


def _mock_token_payload() -> dict:
    return {
        "sub": "user-rate-limit",
        "email": "owner@noblesoft.test",
        "aud": "authenticated",
    }


def test_rate_limit_headers_present(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PRO", 5)

    def fake_verify_jwt_token(token: str):
        return _mock_token_payload()

    async def fake_get_user_from_database(user_id: str):
        return _mock_user("pro")

    monkeypatch.setattr(middleware_module, "verify_jwt_token", fake_verify_jwt_token)
    monkeypatch.setattr(middleware_module, "get_user_from_database", fake_get_user_from_database)

    response = client.get("/api/v1/", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"
    assert int(response.headers["X-RateLimit-Reset"]) >= 1


def test_rate_limit_returns_429_when_exceeded(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PRO", 2)

    def fake_verify_jwt_token(token: str):
        return _mock_token_payload()

    async def fake_get_user_from_database(user_id: str):
        return _mock_user("pro")

    monkeypatch.setattr(middleware_module, "verify_jwt_token", fake_verify_jwt_token)
    monkeypatch.setattr(middleware_module, "get_user_from_database", fake_get_user_from_database)

    headers = {"Authorization": "Bearer test-token"}

    first = client.get("/api/v1/", headers=headers)
    second = client.get("/api/v1/", headers=headers)
    third = client.get("/api/v1/", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Rate limit exceeded" in third.json()["detail"]
    assert third.headers["X-RateLimit-Limit"] == "2"
    assert third.headers["X-RateLimit-Remaining"] == "0"
    assert int(third.headers["Retry-After"]) >= 1