from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core.dependencies import CurrentUser, get_current_user
from app.services.product_service import ProductService
from app.services.invoice_service import InvoiceService
from app.services.ai_agent_service import AIAgentService


client = TestClient(app)


def _build_user(subscription_tier: str = "pro") -> CurrentUser:
    return CurrentUser(
        {
            "id": "user-1",
            "email": "owner@noblesoft.test",
            "full_name": "Owner User",
            "role": "owner",
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
    def _override(tier: str = "pro"):
        async def _dependency() -> CurrentUser:
            return _build_user(tier)

        app.dependency_overrides[get_current_user] = _dependency

    return _override


def _mock_product_response() -> dict:
    return {
        "id": "prod-1",
        "tenant_id": "tenant-1",
        "sku": "PROD-001",
        "name": "Laptop Test",
        "description": "Test product",
        "category": "Electronics",
        "unit_price": 15000000.0,
        "stock_quantity": 10,
        "low_stock_threshold": 5,
        "is_active": True,
        "is_low_stock": False,
        "created_by": "user-1",
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
    }


def _mock_invoice_response() -> dict:
    return {
        "id": "inv-1",
        "tenant_id": "tenant-1",
        "invoice_number": "INV-001",
        "customer_name": "PT Test",
        "customer_email": "finance@pttest.co.id",
        "customer_phone": "+628123456789",
        "issue_date": "2026-03-01",
        "due_date": "2026-03-15",
        "subtotal": 1000000.0,
        "tax_amount": 110000.0,
        "total_amount": 1110000.0,
        "payment_status": "unpaid",
        "notes": "test invoice",
        "created_by": "user-1",
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-01T10:00:00Z",
        "items": [
            {
                "id": "item-1",
                "invoice_id": "inv-1",
                "product_id": "prod-1",
                "description": "Laptop Test",
                "quantity": 1,
                "unit_price": 1000000.0,
                "line_total": 1000000.0,
                "created_at": "2026-03-01T10:00:00Z",
            }
        ],
        "is_overdue": False,
        "days_until_due": 14,
    }


def test_products_list_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("pro")

    async def mock_list_products(self, current_user, page=1, page_size=50, category=None, is_active=None, search=None, low_stock_only=False):
        return {
            "products": [_mock_product_response()],
            "total": 1,
            "page": page,
            "page_size": page_size,
            "has_more": False,
        }

    monkeypatch.setattr(ProductService, "list_products", mock_list_products)

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["products"][0]["sku"] == "PROD-001"


def test_products_create_maps_value_error_to_400(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("pro")

    async def mock_create_product(self, product_data, current_user):
        raise ValueError("duplicate sku")

    monkeypatch.setattr(ProductService, "create_product", mock_create_product)

    response = client.post(
        "/api/v1/products",
        json={
            "sku": "prod-001",
            "name": "Laptop Test",
            "description": "Test product",
            "category": "Electronics",
            "unit_price": 15000000,
            "stock_quantity": 10,
            "low_stock_threshold": 5,
            "is_active": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "duplicate sku"


def test_invoices_delete_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("pro")

    async def mock_delete_invoice(self, invoice_id, current_user):
        return True

    monkeypatch.setattr(InvoiceService, "delete_invoice", mock_delete_invoice)

    response = client.delete("/api/v1/invoices/inv-1")

    assert response.status_code == 204
    assert response.text == ""


def test_chat_send_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("pro")

    async def mock_process_chat_message(self, query, current_user, conversation_history=None):
        return {
            "response": "Stok aman.",
            "sources": [{"type": "inventory", "content": "stok produk"}],
            "retrieved_count": 1,
            "user_context": {"tenant_id": "tenant-1"},
            "error": None,
        }

    monkeypatch.setattr(AIAgentService, "process_chat_message", mock_process_chat_message)

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Bagaimana stok hari ini?",
            "conversation_history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "Stok aman."
    assert payload["retrieved_count"] == 1


def test_chat_suggestions_forbidden_for_basic_tier(override_current_user):
    override_current_user("basic")

    response = client.get("/api/v1/chat/suggestions")

    assert response.status_code == 403
    assert "requires" in response.json()["detail"].lower()


def test_invoices_get_success(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("pro")

    async def mock_get_invoice(self, invoice_id, current_user):
        return _mock_invoice_response()

    monkeypatch.setattr(InvoiceService, "get_invoice", mock_get_invoice)

    response = client.get("/api/v1/invoices/inv-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["invoice_number"] == "INV-001"
    assert payload["items"][0]["description"] == "Laptop Test"
