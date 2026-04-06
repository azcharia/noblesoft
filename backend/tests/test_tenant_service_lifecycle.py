from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.dependencies import CurrentUser
from app.services.tenant_service import TenantService


class FakeUsersQuery:
    def __init__(self, db: "FakeDB"):
        self.db = db
        self._operation = "select"
        self._filters: dict[str, object] = {}
        self._single = False
        self._count_mode: str | None = None
        self._update_payload: dict[str, object] = {}

    def select(self, _columns: str, count: str | None = None):
        self._operation = "select"
        self._count_mode = count
        return self

    def eq(self, key: str, value: object):
        self._filters[key] = value
        return self

    def single(self):
        self._single = True
        return self

    def update(self, payload: dict[str, object]):
        self._operation = "update"
        self._update_payload = payload
        return self

    def execute(self):
        filtered = [
            row for row in self.db.users
            if all(row.get(key) == value for key, value in self._filters.items())
        ]

        if self._operation == "select":
            data = filtered[0].copy() if (self._single and filtered) else (
                None if self._single else [row.copy() for row in filtered]
            )
            count = len(filtered) if self._count_mode == "exact" else None
            return SimpleNamespace(data=data, count=count)

        updated: list[dict[str, object]] = []
        for row in self.db.users:
            if all(row.get(key) == value for key, value in self._filters.items()):
                row.update(self._update_payload)
                updated.append(row.copy())

        return SimpleNamespace(data=updated, count=None)


class FakeDB:
    def __init__(self, users: list[dict[str, object]]):
        self.users = users

    def table(self, table_name: str):
        if table_name != "users":
            raise AssertionError(f"Unexpected table access: {table_name}")
        return FakeUsersQuery(self)


def _current_user(role: str = "owner", max_users: int = 5) -> CurrentUser:
    return CurrentUser(
        {
            "id": "actor-1",
            "email": "actor@noblesoft.test",
            "full_name": "Actor",
            "role": role,
            "is_active": True,
            "tenant_id": "tenant-1",
            "tenants": {
                "company_name": "NobleSoft",
                "subscription_tier": "pro",
                "is_active": True,
                "trial_end_date": None,
                "max_users": max_users,
            },
        }
    )


def test_reactivate_user_not_found_returns_false():
    service = TenantService(db=FakeDB(users=[]))

    result = asyncio.run(service.reactivate_tenant_user("missing-user", _current_user()))

    assert result.user_id == "missing-user"
    assert result.reactivated is False


def test_reactivate_owner_requires_owner_role():
    users = [
        {
            "id": "owner-2",
            "tenant_id": "tenant-1",
            "role": "owner",
            "is_active": False,
        }
    ]
    service = TenantService(db=FakeDB(users=users))

    with pytest.raises(PermissionError, match="Only owner can reactivate owner accounts"):
        asyncio.run(service.reactivate_tenant_user("owner-2", _current_user(role="admin")))


def test_reactivate_user_enforces_seat_limit():
    users = [
        {
            "id": "member-inactive",
            "tenant_id": "tenant-1",
            "role": "member",
            "is_active": False,
        },
        {
            "id": "member-active",
            "tenant_id": "tenant-1",
            "role": "member",
            "is_active": True,
        },
    ]
    service = TenantService(db=FakeDB(users=users))

    with pytest.raises(ValueError, match="Tenant user limit has been reached"):
        asyncio.run(service.reactivate_tenant_user("member-inactive", _current_user(max_users=1)))


def test_reactivate_user_updates_active_flag_when_capacity_available():
    users = [
        {
            "id": "member-inactive",
            "tenant_id": "tenant-1",
            "role": "member",
            "is_active": False,
        },
        {
            "id": "member-active",
            "tenant_id": "tenant-1",
            "role": "member",
            "is_active": True,
        },
    ]
    fake_db = FakeDB(users=users)
    service = TenantService(db=fake_db)

    result = asyncio.run(service.reactivate_tenant_user("member-inactive", _current_user(max_users=3)))

    assert result.reactivated is True
    updated = next(row for row in fake_db.users if row["id"] == "member-inactive")
    assert updated["is_active"] is True
    assert isinstance(datetime.fromisoformat(updated["updated_at"]), datetime)


def test_reactivate_user_is_idempotent_when_already_active():
    users = [
        {
            "id": "member-active",
            "tenant_id": "tenant-1",
            "role": "member",
            "is_active": True,
        }
    ]
    service = TenantService(db=FakeDB(users=users))

    result = asyncio.run(service.reactivate_tenant_user("member-active", _current_user(max_users=1)))

    assert result.reactivated is True
