import asyncio
from decimal import Decimal
import hashlib

import pytest

from app.config import settings
from app.core.dependencies import CurrentUser
from app.models.billing import BillingAddOnSelection, BillingTransactionRequest, MidtransWebhookRequest
from app.services.billing_service import BillingService


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


def test_get_billing_catalog_contains_business_prices():
    service = BillingService(db=object())

    catalog = service.get_billing_catalog()

    assert catalog.currency == "IDR"
    assert catalog.annual_discount_percent == settings.BILLING_ANNUAL_DISCOUNT_PERCENT

    basic_plan = next(plan for plan in catalog.plans if plan.tier == "basic")
    assert basic_plan.monthly_price == Decimal("499000.00")


class _FakeMidtransResponse:
    status_code = 200
    text = "OK"

    def json(self):
        return {
            "token": "snap-token",
            "redirect_url": "https://midtrans.example/redirect",
        }


class _FakeHttpClient:
    def __init__(self, capture):
        self.capture = capture

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers=None, json=None):
        self.capture["url"] = url
        self.capture["headers"] = headers or {}
        self.capture["json"] = json or {}
        return _FakeMidtransResponse()


class _FakeResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _FakeSelectQuery:
    def __init__(self, db, table: str):
        self.db = db
        self.table = table
        self.filters = {}
        self._single = False

    def eq(self, field: str, value):
        self.filters[field] = value
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self.table == "tenants":
            tenant_id = self.filters.get("id")
            tenant = self.db.tenants.get(tenant_id)
            if not tenant:
                return _FakeResult(data=None)
            return _FakeResult(data=dict(tenant))

        if self.table == "billing_events":
            order_id = self.filters.get("order_id")
            match = next((item for item in self.db.billing_events if item.get("order_id") == order_id), None)
            return _FakeResult(data=dict(match) if match else None)

        return _FakeResult(data=None)


class _FakeUpdateQuery:
    def __init__(self, db, table: str, payload: dict):
        self.db = db
        self.table = table
        self.payload = payload
        self.filters = {}

    def eq(self, field: str, value):
        self.filters[field] = value
        return self

    def execute(self):
        if self.table != "tenants":
            return _FakeResult(data=None)

        tenant_id = self.filters.get("id")
        tenant = self.db.tenants.get(tenant_id)
        if not tenant:
            return _FakeResult(data=None)

        tenant.update(self.payload)
        return _FakeResult(data=[dict(tenant)])


class _FakeInsertQuery:
    def __init__(self, db, table: str, payload: dict):
        self.db = db
        self.table = table
        self.payload = payload

    def execute(self):
        if self.table == "billing_events":
            self.db.billing_events.append(dict(self.payload))
            return _FakeResult(data=[dict(self.payload)])
        return _FakeResult(data=None)


class _FakeTable:
    def __init__(self, db, table: str):
        self.db = db
        self.table = table

    def select(self, _columns: str, count=None):
        _ = count
        return _FakeSelectQuery(self.db, self.table)

    def update(self, payload: dict):
        return _FakeUpdateQuery(self.db, self.table, payload)

    def insert(self, payload: dict):
        return _FakeInsertQuery(self.db, self.table, payload)


class _FakeSupabaseDB:
    def __init__(self, tenants: dict[str, dict]):
        self.tenants = tenants
        self.billing_events: list[dict] = []

    def table(self, table_name: str):
        return _FakeTable(self, table_name)


def _build_signed_webhook(
    order_id: str,
    target_tier: str = "pro",
    custom_field1: str = "tenant-1",
    custom_field3: str | None = None,
) -> MidtransWebhookRequest:
    status_code = "200"
    gross_amount = "100000.00"
    raw = f"{order_id}{status_code}{gross_amount}{settings.MIDTRANS_SERVER_KEY}"
    signature_key = hashlib.sha512(raw.encode("utf-8")).hexdigest()

    return MidtransWebhookRequest(
        order_id=order_id,
        status_code=status_code,
        gross_amount=gross_amount,
        signature_key=signature_key,
        transaction_status="settlement",
        custom_field1=custom_field1,
        custom_field2=target_tier,
        custom_field3=custom_field3,
    )


def test_create_midtrans_transaction_rejects_mismatched_amount(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", "test-server-key")
    service = BillingService(db=object())

    payload = BillingTransactionRequest(
        target_tier="basic",
        billing_period="monthly",
        amount=Decimal("1.00"),
    )

    with pytest.raises(ValueError, match="does not match pricing catalog"):
        asyncio.run(service.create_midtrans_transaction(payload, _build_user()))


def test_create_midtrans_transaction_uses_server_calculated_total(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", "test-server-key")

    capture = {}
    monkeypatch.setattr(
        "app.services.billing_service.httpx.Client",
        lambda timeout: _FakeHttpClient(capture),
    )

    service = BillingService(db=object())
    payload = BillingTransactionRequest(
        target_tier="pro",
        billing_period="annual",
        add_ons=[BillingAddOnSelection(code="ai_agent_pack", quantity=2)],
    )

    response = asyncio.run(service.create_midtrans_transaction(payload, _build_user()))

    expected_line_items = service._build_line_items(
        target_tier="pro",
        billing_period="annual",
        add_ons=[BillingAddOnSelection(code="ai_agent_pack", quantity=2)],
    )
    expected_total = sum((item.subtotal for item in expected_line_items), Decimal("0.00"))

    assert response.amount == expected_total
    assert response.billing_period == "annual"
    assert len(response.line_items) == 2

    assert capture["json"]["transaction_details"]["gross_amount"] == int(expected_total)
    assert capture["json"]["item_details"][0]["id"].startswith("plan-pro")
    assert capture["json"]["item_details"][1]["id"].startswith("addon-ai_agent_pack")


def test_get_billing_status_returns_persisted_period_and_add_ons():
    db = _FakeSupabaseDB(
        tenants={
            "tenant-1": {
                "id": "tenant-1",
                "company_name": "NobleSoft Test",
                "subscription_tier": "pro",
                "is_active": True,
                "max_users": 20,
                "payment_gateway_customer_id": None,
                "billing_period": "annual",
                "active_add_ons": [{"code": "ai_agent_pack", "quantity": 2}],
                "billing_start_date": "2026-03-01T00:00:00+00:00",
                "billing_end_date": "2027-03-01T00:00:00+00:00",
            }
        }
    )
    service = BillingService(db=db)

    status = asyncio.run(service.get_billing_status(_build_user()))

    assert status.billing_period == "annual"
    assert len(status.add_ons) == 1
    assert status.add_ons[0].code == "ai_agent_pack"
    assert status.add_ons[0].quantity == 2
    assert str(status.billing_start_date).startswith("2026-03-01")


def test_process_midtrans_webhook_persists_metadata_and_records_event(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", "test-server-key")
    db = _FakeSupabaseDB(
        tenants={
            "tenant-1": {
                "id": "tenant-1",
                "company_name": "NobleSoft Test",
                "subscription_tier": "basic",
                "is_active": True,
                "max_users": 5,
                "payment_gateway_customer_id": None,
                "billing_period": "monthly",
                "active_add_ons": [],
            }
        }
    )
    service = BillingService(db=db)
    payload = _build_signed_webhook(
        order_id="NSFT_tenant-1_pro_annual_1700000000",
        target_tier="pro",
        custom_field3="period=annual;addons=ai_agent_pack:2,automation_pack:1",
    )

    response = asyncio.run(service.process_midtrans_webhook(payload))

    assert response.accepted is True
    assert response.updated_tier == "pro"
    tenant = db.tenants["tenant-1"]
    assert tenant["subscription_tier"] == "pro"
    assert tenant["billing_period"] == "annual"
    assert tenant["last_billing_event_id"] == payload.order_id
    assert tenant["active_add_ons"] == [
        {"code": "ai_agent_pack", "quantity": 2},
        {"code": "automation_pack", "quantity": 1},
    ]
    assert len(db.billing_events) == 1
    assert db.billing_events[0]["order_id"] == payload.order_id


def test_process_midtrans_webhook_is_idempotent_for_existing_event(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MIDTRANS_SERVER_KEY", "test-server-key")
    db = _FakeSupabaseDB(
        tenants={
            "tenant-1": {
                "id": "tenant-1",
                "company_name": "NobleSoft Test",
                "subscription_tier": "basic",
                "is_active": True,
                "max_users": 5,
                "payment_gateway_customer_id": None,
                "billing_period": "monthly",
                "active_add_ons": [],
            }
        }
    )
    db.billing_events.append(
        {
            "order_id": "NSFT_tenant-1_pro_monthly_1700000000",
            "tenant_id": "tenant-1",
            "updated_tier": "pro",
        }
    )
    service = BillingService(db=db)
    payload = _build_signed_webhook(order_id="NSFT_tenant-1_pro_monthly_1700000000")

    response = asyncio.run(service.process_midtrans_webhook(payload))

    assert response.accepted is True
    assert "already processed" in response.message.lower()
    assert db.tenants["tenant-1"]["subscription_tier"] == "basic"
