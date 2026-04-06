from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core.dependencies import CurrentUser
from app.models.user import TenantUserInviteRequest
from app.services.tenant_service import TenantService


class FakeAuthAdmin:
    def __init__(self, created_user_id: str = 'auth-user-1'):
        self.created_user_id = created_user_id
        self.create_payloads: list[dict] = []
        self.deleted_user_ids: list[str] = []

    def create_user(self, payload: dict):
        self.create_payloads.append(dict(payload))
        return {'user': {'id': self.created_user_id}}

    def delete_user(self, user_id: str):
        self.deleted_user_ids.append(user_id)


class FakeUsersQuery:
    def __init__(self, db: 'FakeDB'):
        self.db = db
        self._operation = 'select'
        self._filters: dict[str, object] = {}
        self._count_mode: str | None = None
        self._insert_payload: dict[str, object] = {}

    def select(self, _columns: str, count: str | None = None):
        self._operation = 'select'
        self._count_mode = count
        return self

    def eq(self, key: str, value: object):
        self._filters[key] = value
        return self

    def insert(self, payload: dict[str, object]):
        self._operation = 'insert'
        self._insert_payload = payload
        return self

    def execute(self):
        if self._operation == 'select':
            filtered = [
                row for row in self.db.users
                if all(row.get(key) == value for key, value in self._filters.items())
            ]
            count = len(filtered) if self._count_mode == 'exact' else None
            return SimpleNamespace(data=[row.copy() for row in filtered], count=count)

        if self.db.fail_insert_user_profile:
            return SimpleNamespace(data=None, count=None)

        row = dict(self._insert_payload)
        row.setdefault('created_at', '2026-03-01T10:00:00Z')
        row.setdefault('updated_at', '2026-03-01T10:00:00Z')
        self.db.users.append(row)
        return SimpleNamespace(data=[row.copy()], count=None)


class FakeDB:
    def __init__(self, users: list[dict[str, object]] | None = None, fail_insert_user_profile: bool = False):
        self.users = users or []
        self.fail_insert_user_profile = fail_insert_user_profile
        self.auth_admin = FakeAuthAdmin()
        self.auth = SimpleNamespace(admin=self.auth_admin)

    def table(self, table_name: str):
        if table_name != 'users':
            raise AssertionError(f'Unexpected table access: {table_name}')
        return FakeUsersQuery(self)


def _current_user(max_users: int = 10) -> CurrentUser:
    return CurrentUser(
        {
            'id': 'owner-1',
            'email': 'owner@noblesoft.test',
            'full_name': 'Owner User',
            'role': 'owner',
            'is_active': True,
            'tenant_id': 'tenant-1',
            'tenants': {
                'company_name': 'NobleSoft',
                'subscription_tier': 'pro',
                'is_active': True,
                'trial_end_date': None,
                'max_users': max_users,
            },
        }
    )


def test_invite_generates_temporary_password_when_not_provided():
    db = FakeDB()
    service = TenantService(db=db)

    payload = TenantUserInviteRequest(
        email='new@noblesoft.test',
        full_name='New User',
        role='member',
    )

    result = asyncio.run(service.invite_tenant_user(payload, _current_user()))

    assert result.user.email == 'new@noblesoft.test'
    assert result.temporary_password is not None
    assert len(result.temporary_password) >= 8
    assert db.auth_admin.create_payloads[0]['password'] == result.temporary_password


def test_invite_uses_custom_temporary_password():
    db = FakeDB()
    service = TenantService(db=db)

    payload = TenantUserInviteRequest(
        email='new@noblesoft.test',
        full_name='New User',
        role='admin',
        temp_password='custom-temp-123',
    )

    result = asyncio.run(service.invite_tenant_user(payload, _current_user()))

    assert result.temporary_password == 'custom-temp-123'
    assert db.auth_admin.create_payloads[0]['password'] == 'custom-temp-123'


def test_invite_hides_temporary_password_when_not_requested():
    db = FakeDB()
    service = TenantService(db=db)

    payload = TenantUserInviteRequest(
        email='new@noblesoft.test',
        full_name='New User',
        role='member',
        include_temporary_password=False,
    )

    result = asyncio.run(service.invite_tenant_user(payload, _current_user()))

    assert result.temporary_password is None
    assert db.auth_admin.create_payloads[0]['password']


def test_invite_rolls_back_auth_user_when_profile_insert_fails():
    db = FakeDB(fail_insert_user_profile=True)
    service = TenantService(db=db)

    payload = TenantUserInviteRequest(
        email='new@noblesoft.test',
        full_name='New User',
        role='member',
    )

    with pytest.raises(Exception, match='Failed to create user profile in database'):
        asyncio.run(service.invite_tenant_user(payload, _current_user()))

    assert db.auth_admin.deleted_user_ids == ['auth-user-1']