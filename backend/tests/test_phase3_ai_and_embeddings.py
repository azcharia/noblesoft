import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.dependencies import CurrentUser
from app.models.invoice import InvoiceCreate, PaymentStatus
from app.models.product import ProductCreate
from app.services.ai_agent_service import AIAgentService
from app.services.invoice_service import InvoiceService
from app.services.product_service import ProductService


def _build_user(role: str = "owner", subscription_tier: str = "enterprise") -> CurrentUser:
    return CurrentUser(
        {
            "id": "user-1",
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


def test_parse_function_call_supports_code_fence_json():
    service = AIAgentService.__new__(AIAgentService)
    response = """```json
    {
      "function": "create_product",
      "parameters": {
        "sku": "prd-001",
        "name": "Laptop",
        "price": 15000000,
        "stock": 10,
        "unit_price": 15000000
      }
    }
    ```"""

    parsed = service._parse_function_call(response)

    assert parsed is not None
    assert parsed["function"] == "create_product"
    assert parsed["parameters"]["unit_price"] == 15000000
    assert parsed["parameters"]["stock_quantity"] == 10


def test_process_with_function_calling_executes_function(monkeypatch: pytest.MonkeyPatch):
    service = AIAgentService.__new__(AIAgentService)

    class FakeRAG:
        async def query_with_rag(self, query, tenant_id, top_k):
            return {
                "response": "unused",
                "sources": [{"content": "Product: Laptop"}],
                "retrieved_count": 1,
            }

    class FakeGroq:
        async def chat_completion_async(self, messages):
            return '{"function":"check_stock","parameters":{"product_name":"Laptop"}}'

    async def fake_execute(function_call, current_user):
        return {"message": "stok ditemukan", "success": True}

    service.rag_engine = FakeRAG()
    service.groq_client = FakeGroq()
    monkeypatch.setattr(service, "_execute_function", fake_execute)

    result = asyncio.run(service.process_with_function_calling("cek stok laptop", _build_user()))

    assert result["response"] == "stok ditemukan"
    assert result["function_executed"] == "check_stock"


def test_execute_function_create_invoice_success(monkeypatch: pytest.MonkeyPatch):
    service = AIAgentService.__new__(AIAgentService)

    class FakeInvoiceResult:
        invoice_number = "INV-AI-1"
        total_amount = 200000

        def model_dump(self):
            return {"invoice_number": self.invoice_number, "total_amount": self.total_amount}

    async def fake_create_invoice(self, invoice_data, current_user):
        assert isinstance(invoice_data, InvoiceCreate)
        return FakeInvoiceResult()

    monkeypatch.setattr(InvoiceService, "create_invoice", fake_create_invoice)

    function_call = {
        "function": "create_invoice",
        "parameters": {
            "customer_name": "PT Maju",
            "items": [
                {
                    "description": "Laptop Pro",
                    "quantity": 1,
                    "unit_price": 200000,
                }
            ],
        },
    }

    result = asyncio.run(service._execute_function(function_call, _build_user()))

    assert result["success"] is True
    assert "berhasil dibuat" in result["message"]


def test_execute_function_get_invoice_status_by_id(monkeypatch: pytest.MonkeyPatch):
    service = AIAgentService.__new__(AIAgentService)

    class FakeInvoice:
        invoice_number = "INV-001"
        payment_status = PaymentStatus.PAID
        total_amount = 123000

        def model_dump(self):
            return {
                "invoice_number": self.invoice_number,
                "payment_status": self.payment_status.value,
                "total_amount": self.total_amount,
            }

    async def fake_get_invoice(self, invoice_id, current_user):
        return FakeInvoice()

    monkeypatch.setattr(InvoiceService, "get_invoice", fake_get_invoice)

    result = asyncio.run(
        service._execute_function(
            {"function": "get_invoice_status", "parameters": {"invoice_id": "inv-1"}},
            _build_user(),
        )
    )

    assert result["success"] is True
    assert "INV-001" in result["message"]
    assert "PAID" in result["message"]


def test_get_suggested_questions_data_aware(monkeypatch: pytest.MonkeyPatch):
    service = AIAgentService.__new__(AIAgentService)

    class FakeQuery:
        def __init__(self, table_name, db):
            self.table_name = table_name
            self.db = db

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            if self.table_name == "products":
                return SimpleNamespace(
                    data=[
                        {"id": "p1", "name": "Laptop", "stock_quantity": 3, "low_stock_threshold": 5},
                        {"id": "p2", "name": "Monitor", "stock_quantity": 20, "low_stock_threshold": 5},
                    ],
                    count=2,
                )
            return SimpleNamespace(
                data=[
                    {
                        "id": "i1",
                        "invoice_number": "INV-1",
                        "customer_name": "PT Maju",
                        "total_amount": 500000,
                        "payment_status": "unpaid",
                    }
                ],
                count=1,
            )

    class FakeDB:
        def table(self, table_name):
            return FakeQuery(table_name, self)

    def fake_get_db():
        return FakeDB()

    from app.services import ai_agent_service as ai_agent_module

    monkeypatch.setattr(ai_agent_module, "get_supabase_admin_client", fake_get_db)

    suggestions = asyncio.run(service.get_suggested_questions(_build_user()))

    assert len(suggestions) >= 5
    assert any("stok" in s.lower() for s in suggestions)
    assert any("invoice" in s.lower() for s in suggestions)


def test_create_product_triggers_embedding_sync(monkeypatch: pytest.MonkeyPatch):
    db = MagicMock()

    select_chain = MagicMock()
    select_chain.eq.return_value = select_chain
    select_chain.execute.return_value = SimpleNamespace(data=[])

    insert_chain = MagicMock()
    insert_chain.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "prod-1",
                "tenant_id": "tenant-1",
                "sku": "PRD-001",
                "name": "Laptop",
                "description": None,
                "category": None,
                "unit_price": 100000,
                "stock_quantity": 10,
                "low_stock_threshold": 5,
                "is_active": True,
                "created_by": "user-1",
                "created_at": "2026-03-01T10:00:00Z",
                "updated_at": "2026-03-01T10:00:00Z",
            }
        ]
    )

    table_products = MagicMock()
    table_products.select.return_value = select_chain
    table_products.insert.return_value = insert_chain
    db.table.return_value = table_products

    service = ProductService(db=db)
    called = {"synced": False}

    async def fake_sync(product, tenant_id):
        called["synced"] = True

    monkeypatch.setattr(service, "_sync_product_embedding", fake_sync)

    payload = ProductCreate(
        sku="prd-001",
        name="Laptop",
        unit_price=100000,
        stock_quantity=10,
        low_stock_threshold=5,
    )
    asyncio.run(service.create_product(payload, _build_user()))

    assert called["synced"] is True


def test_create_invoice_triggers_embedding_sync(monkeypatch: pytest.MonkeyPatch):
    db = MagicMock()

    invoices_select = MagicMock()
    invoices_select.eq.return_value = invoices_select
    invoices_select.execute.return_value = SimpleNamespace(data=[])

    invoices_insert = MagicMock()
    invoices_insert.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "inv-1",
                "tenant_id": "tenant-1",
                "invoice_number": "INV-001",
                "customer_name": "PT Maju",
                "customer_email": None,
                "customer_phone": None,
                "issue_date": date.today().isoformat(),
                "due_date": None,
                "subtotal": 100000,
                "tax_amount": 0,
                "total_amount": 100000,
                "payment_status": "unpaid",
                "notes": None,
                "created_by": "user-1",
                "created_at": "2026-03-01T10:00:00Z",
                "updated_at": "2026-03-01T10:00:00Z",
            }
        ]
    )

    invoice_items_insert = MagicMock()
    invoice_items_insert.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "item-1",
                "invoice_id": "inv-1",
                "product_id": None,
                "description": "Laptop",
                "quantity": 1,
                "unit_price": 100000,
                "line_total": 100000,
                "created_at": "2026-03-01T10:00:00Z",
            }
        ]
    )

    invoices_table = MagicMock()
    invoices_table.select.return_value = invoices_select
    invoices_table.insert.return_value = invoices_insert

    invoice_items_table = MagicMock()
    invoice_items_table.insert.return_value = invoice_items_insert

    def fake_table(name):
        if name == "invoices":
            return invoices_table
        if name == "invoice_items":
            return invoice_items_table
        return MagicMock()

    db.table.side_effect = fake_table

    service = InvoiceService(db=db)
    called = {"synced": False}

    async def fake_sync(invoice, tenant_id, items=None):
        called["synced"] = True

    monkeypatch.setattr(service, "_sync_invoice_embedding", fake_sync)

    payload = InvoiceCreate(
        invoice_number="inv-001",
        customer_name="PT Maju",
        issue_date=date.today(),
        items=[
            {
                "description": "Laptop",
                "quantity": 1,
                "unit_price": 100000,
            }
        ],
    )

    asyncio.run(service.create_invoice(payload, _build_user()))

    assert called["synced"] is True