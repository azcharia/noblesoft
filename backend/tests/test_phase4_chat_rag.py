import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import CurrentUser, get_current_user
from app.main import app
from app.ai.rag_engine import RAGEngine
from app.services.ai_agent_service import AIAgentService
from app.config import settings


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


def test_process_chat_message_forwards_conversation_history():
    service = AIAgentService.__new__(AIAgentService)
    captured = {"history": None}

    class FakeRAG:
        async def query_with_rag(self, query, tenant_id, top_k, conversation_history=None):
            captured["history"] = conversation_history
            return {
                "response": "Ringkasan stok tersedia.",
                "sources": [],
                "retrieved_count": 0,
            }

    service.rag_engine = FakeRAG()

    history = [
        {"role": "user", "content": "Halo"},
        {"role": "assistant", "content": "Halo, ada yang bisa saya bantu?"},
    ]

    result = asyncio.run(
        service.process_chat_message(
            query="Tampilkan ringkasan stok",
            current_user=_build_user("pro"),
            conversation_history=history,
        )
    )

    assert captured["history"] == history
    assert result["response"] == "Ringkasan stok tersedia."
    assert result["user_context"]["tenant_id"] == "tenant-1"


def test_process_with_function_calling_forwards_history_to_rag():
    service = AIAgentService.__new__(AIAgentService)
    captured = {"history": None}

    class FakeRAG:
        async def query_with_rag(self, query, tenant_id, top_k, conversation_history=None):
            captured["history"] = conversation_history
            return {
                "response": "unused",
                "sources": [{"content": "Product: Laptop"}],
                "retrieved_count": 1,
            }

    class FakeGroq:
        async def chat_completion_async(self, messages):
            return "Tidak perlu action."

    service.rag_engine = FakeRAG()
    service.groq_client = FakeGroq()

    history = [{"role": "user", "content": "Sebelumnya kita bahas laptop"}]
    result = asyncio.run(
        service.process_with_function_calling(
            query="Lanjutkan analisis",
            current_user=_build_user("enterprise"),
            conversation_history=history,
        )
    )

    assert captured["history"] == history
    assert result["response"] == "Tidak perlu action."
    assert result["retrieved_count"] == 1


def test_process_chat_message_routes_web_intent_to_tavily(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TAVILY_ENABLED", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test-key")

    service = AIAgentService.__new__(AIAgentService)
    captured = {"query": None}

    class FakeRAG:
        async def query_with_rag(self, query, tenant_id, top_k, conversation_history=None):
            raise AssertionError("RAG should not run for explicit web intent")

    class FakeTavily:
        async def search_async(
            self,
            query,
            topic="general",
            time_range=None,
            max_results=None,
            search_depth="basic",
        ):
            captured["query"] = query
            return {
                "sources": [
                    {
                        "type": "web",
                        "content": "Tavily source: berita pajak terbaru (https://example.com)",
                        "metadata": {
                            "title": "Berita Pajak",
                            "url": "https://example.com",
                        },
                    }
                ],
                "tool_calls": [{"name": "tavily_search"}],
            }

    class FakeGroq:
        async def chat_completion_async(self, messages, temperature=None, max_tokens=None):
            return "Ringkasan web terbaru tersedia."

    service.rag_engine = FakeRAG()
    service.tavily_client = FakeTavily()
    service.groq_client = FakeGroq()

    result = asyncio.run(
        service.process_chat_message(
            query="Cari di internet regulasi pajak terbaru hari ini",
            current_user=_build_user("pro"),
        )
    )

    assert result["assistant_mode"] == "tavily"
    assert result["response"] == "Ringkasan web terbaru tersedia."
    assert result["retrieved_count"] == 0
    assert result["tool_calls"][0]["name"] == "tavily_search"
    assert "regulasi pajak" in captured["query"]


def test_process_chat_message_web_intent_returns_safe_message_when_tavily_sources_empty(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TAVILY_ENABLED", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test-key")

    service = AIAgentService.__new__(AIAgentService)

    class FakeRAG:
        async def query_with_rag(self, query, tenant_id, top_k, conversation_history=None):
            raise AssertionError("RAG should not run for explicit web intent")

    class EmptyTavily:
        async def search_async(
            self,
            query,
            topic="general",
            time_range=None,
            max_results=None,
            search_depth="basic",
        ):
            return {
                "sources": [],
                "tool_calls": [{"name": "tavily_search", "query": query}],
            }

    class FakeGroq:
        async def chat_completion_async(self, messages, temperature=None, max_tokens=None):
            raise AssertionError("Groq should not run when Tavily returns no sources")

    service.rag_engine = FakeRAG()
    service.tavily_client = EmptyTavily()
    service.groq_client = FakeGroq()

    result = asyncio.run(
        service.process_chat_message(
            query="Cari di internet berita AI terbaru",
            current_user=_build_user("pro"),
        )
    )

    assert result["assistant_mode"] == "tavily"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["type"] == "audit_tool"
    assert result["tool_calls"][0]["name"] == "tavily_search"
    assert "belum menemukan sumber web tepercaya" in result["response"].lower()


def test_process_chat_message_falls_back_to_rag_when_tavily_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TAVILY_ENABLED", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test-key")

    service = AIAgentService.__new__(AIAgentService)

    class FakeRAG:
        async def query_with_rag(self, query, tenant_id, top_k, conversation_history=None):
            return {
                "response": "Fallback ke data internal berhasil.",
                "sources": [],
                "retrieved_count": 0,
            }

    class FailingTavily:
        async def search_async(
            self,
            query,
            topic="general",
            time_range=None,
            max_results=None,
            search_depth="basic",
        ):
            raise RuntimeError("tavily unavailable")

    service.rag_engine = FakeRAG()
    service.tavily_client = FailingTavily()

    result = asyncio.run(
        service.process_chat_message(
            query="Search web berita teknologi terbaru",
            current_user=_build_user("pro"),
        )
    )

    assert result["assistant_mode"] == "rag_fallback"
    assert result["response"] == "Fallback ke data internal berhasil."
    assert result["tool_calls"] == []


def test_process_chat_message_runs_hybrid_parallel_for_mixed_intent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TAVILY_ENABLED", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test-key")
    monkeypatch.setattr(settings, "ORCHESTRATION_ENABLED", True)
    monkeypatch.setattr(settings, "ORCHESTRATION_ENABLE_HYBRID_FOR_MIXED_INTENT", True)
    monkeypatch.setattr(settings, "ORCHESTRATION_ENTERPRISE_ONLY", False)

    service = AIAgentService.__new__(AIAgentService)

    async def fake_manager_worker(self, query, current_user, conversation_history=None):
        return {
            "response": "Data internal: stok laptop tersedia 40 unit.",
            "sources": [{"type": "product", "content": "Laptop 40 unit", "metadata": {}}],
            "retrieved_count": 1,
            "manager_result_summary": {
                "status": "success",
                "retrieved_count": 1,
                "source_count": 1,
            },
        }

    async def fake_auditor_worker(self, query, current_user, conversation_history=None):
        return {
            "response": "Audit web: tren harga laptop naik 3% minggu ini.",
            "sources": [{"type": "audit_tool", "content": "tavily_search", "metadata": {}}],
            "tool_calls": [{"name": "tavily_search"}],
            "auditor_result_summary": {
                "status": "success",
                "tool_count": 1,
                "source_count": 1,
            },
        }

    async def fake_reconcile(self, query, manager_response, auditor_response, conversation_history=None):
        assert "stok laptop" in manager_response.lower()
        assert "tren harga" in auditor_response.lower()
        return "Final: stok internal aman, tetapi tren harga eksternal sedang naik."

    monkeypatch.setattr(AIAgentService, "_execute_manager_worker", fake_manager_worker)
    monkeypatch.setattr(AIAgentService, "_execute_auditor_worker", fake_auditor_worker)
    monkeypatch.setattr(AIAgentService, "_reconcile_worker_outputs", fake_reconcile)

    result = asyncio.run(
        service.process_chat_message(
            query="Bandingkan stok laptop internal dengan tren harga laptop di web",
            current_user=_build_user("enterprise"),
        )
    )

    assert result["assistant_mode"] == "hybrid_parallel"
    assert result["orchestration_mode"] == "hybrid_parallel"
    assert result["response"].startswith("Final:")
    assert len(result["tool_calls"]) == 1
    assert result["manager_result_summary"]["status"] == "success"
    assert result["auditor_result_summary"]["status"] == "success"


def test_process_chat_message_hybrid_falls_back_to_manager_when_auditor_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "TAVILY_ENABLED", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test-key")
    monkeypatch.setattr(settings, "ORCHESTRATION_ENABLED", True)
    monkeypatch.setattr(settings, "ORCHESTRATION_ENABLE_HYBRID_FOR_MIXED_INTENT", True)
    monkeypatch.setattr(settings, "ORCHESTRATION_ENTERPRISE_ONLY", False)

    service = AIAgentService.__new__(AIAgentService)

    async def fake_manager_worker(self, query, current_user, conversation_history=None):
        return {
            "response": "Manager fallback: data internal tetap tersedia.",
            "sources": [],
            "retrieved_count": 0,
            "manager_result_summary": {"status": "success"},
        }

    async def failing_auditor_worker(self, query, current_user, conversation_history=None):
        raise RuntimeError("auditor failed")

    monkeypatch.setattr(AIAgentService, "_execute_manager_worker", fake_manager_worker)
    monkeypatch.setattr(AIAgentService, "_execute_auditor_worker", failing_auditor_worker)

    result = asyncio.run(
        service.process_chat_message(
            query="Cek stok internal dan validasi tren market web",
            current_user=_build_user("enterprise"),
        )
    )

    assert result["assistant_mode"] == "hybrid_parallel_fallback_manager"
    assert result["orchestration_mode"] == "hybrid_parallel"
    assert result["response"].startswith("Manager fallback")
    assert result["tool_calls"] == []
    assert result["auditor_result_summary"]["status"] == "failed"


def test_rag_engine_generate_response_includes_conversation_history():
    engine = RAGEngine.__new__(RAGEngine)
    captured = {"messages": []}

    class FakeGroq:
        async def chat_completion_async(self, messages):
            captured["messages"] = messages
            return "OK"

    engine.groq_client = FakeGroq()

    history = [
        {"role": "user", "content": "Tolong cek invoice"},
        {"role": "assistant", "content": "Baik, saya cek invoice terbaru."},
    ]

    response = asyncio.run(
        engine._generate_response(
            query="Yang belum lunas berapa?",
            context="[Document 1 - INVOICE]\nInvoice: INV-001 | Status: UNPAID",
            conversation_history=history,
        )
    )

    assert response == "OK"
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1] == history[0]
    assert captured["messages"][2] == history[1]
    assert captured["messages"][-1]["role"] == "user"
    assert "Yang belum lunas berapa?" in captured["messages"][-1]["content"]


def test_chat_endpoint_forwards_history_to_service(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("pro")
    captured = {"history": None}

    def mock_init(self):
        return None

    async def mock_process_chat_message(self, query, current_user, conversation_history=None):
        captured["history"] = conversation_history
        return {
            "response": "Siap, ini rangkuman.",
            "sources": [],
            "retrieved_count": 0,
            "error": None,
        }

    monkeypatch.setattr(AIAgentService, "__init__", mock_init)
    monkeypatch.setattr(AIAgentService, "process_chat_message", mock_process_chat_message)

    payload_history = [
        {"role": "user", "content": "Pertanyaan sebelumnya"},
        {"role": "assistant", "content": "Jawaban sebelumnya"},
    ]
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Lanjutkan pembahasan",
            "conversation_history": payload_history,
        },
    )

    assert response.status_code == 200
    assert captured["history"] == payload_history


def test_chat_function_call_requires_enterprise(override_current_user):
    override_current_user("pro")

    response = client.post(
        "/api/v1/chat/function-call",
        json={"message": "Buatkan invoice baru"},
    )

    assert response.status_code == 403


def test_chat_function_call_forwards_history(monkeypatch: pytest.MonkeyPatch, override_current_user):
    override_current_user("enterprise")
    captured = {"history": None}

    def mock_init(self):
        return None

    async def mock_process_with_function_calling(self, query, current_user, conversation_history=None):
        captured["history"] = conversation_history
        return {
            "response": "Invoice berhasil dibuat.",
            "sources": [],
            "retrieved_count": 0,
            "error": None,
        }

    monkeypatch.setattr(AIAgentService, "__init__", mock_init)
    monkeypatch.setattr(AIAgentService, "process_with_function_calling", mock_process_with_function_calling)

    payload_history = [{"role": "user", "content": "Customer: PT Maju"}]
    response = client.post(
        "/api/v1/chat/function-call",
        json={
            "message": "Buat invoice untuk customer tadi",
            "conversation_history": payload_history,
        },
    )

    assert response.status_code == 200
    assert captured["history"] == payload_history
    assert response.json()["response"] == "Invoice berhasil dibuat."


def test_resolve_rag_top_k_scales_by_intent():
    service = AIAgentService.__new__(AIAgentService)

    invoice_top_k = service._resolve_rag_top_k("Berapa invoice unpaid saat ini?")
    product_top_k = service._resolve_rag_top_k("Cek stok laptop terbaru")
    mixed_top_k = service._resolve_rag_top_k("Bandingkan invoice unpaid dengan stok laptop di web")

    assert invoice_top_k >= 14
    assert product_top_k >= 12
    assert mixed_top_k >= 18


def test_execute_manager_worker_uses_dynamic_top_k(monkeypatch: pytest.MonkeyPatch):
    service = AIAgentService.__new__(AIAgentService)
    captured = {"top_k": None}

    async def fake_query_rag(self, query, tenant_id, top_k, conversation_history=None):
        captured["top_k"] = top_k
        return {
            "response": "ok",
            "sources": [],
            "retrieved_count": 0,
        }

    monkeypatch.setattr(AIAgentService, "_query_rag", fake_query_rag)

    result = asyncio.run(
        service._execute_manager_worker(
            query="Berapa invoice unpaid minggu ini?",
            current_user=_build_user("pro"),
        )
    )

    assert result["response"] == "ok"
    assert captured["top_k"] is not None
    assert captured["top_k"] >= 14


def test_rag_engine_retrieve_documents_merges_sparse_vector_results(monkeypatch: pytest.MonkeyPatch):
    engine = RAGEngine.__new__(RAGEngine)

    class FakeRPCResult:
        def __init__(self, data):
            self.data = data

    class FakeRPCQuery:
        def __init__(self, data):
            self._data = data

        def execute(self):
            return FakeRPCResult(self._data)

    class FakeDB:
        def rpc(self, fn_name, payload):
            assert fn_name == "match_documents"
            assert payload["match_count"] == 5
            return FakeRPCQuery(
                [
                    {
                        "document_type": "product",
                        "content": "Product: Produk A",
                        "metadata": {"product_id": "prod-a"},
                    },
                    {
                        "document_type": "invoice",
                        "content": "Invoice: INV-001",
                        "metadata": {"invoice_id": "inv-001"},
                    },
                ]
            )

    async def fake_fallback(self, tenant_id, limit, query_text="", existing_docs=None):
        base_docs = list(existing_docs or [])
        assert len(base_docs) == 2
        return base_docs + [
            {
                "document_type": "product",
                "content": "Product: Produk B",
                "metadata": {"product_id": "prod-b"},
            },
            {
                "document_type": "invoice",
                "content": "Invoice: INV-002",
                "metadata": {"invoice_id": "inv-002"},
            },
            {
                "document_type": "invoice",
                "content": "Invoice: INV-003",
                "metadata": {"invoice_id": "inv-003"},
            },
        ]

    monkeypatch.setattr("app.core.database.get_supabase_admin_client", lambda: FakeDB())
    monkeypatch.setattr(RAGEngine, "_fallback_retrieve", fake_fallback)

    docs = asyncio.run(
        engine._retrieve_documents(
            query_embedding=[0.1, 0.2, 0.3],
            tenant_id="tenant-1",
            top_k=5,
            query_text="Berapa invoice unpaid",
        )
    )

    assert len(docs) == 5
    assert docs[0]["content"] == "Product: Produk A"
    assert docs[-1]["content"] == "Invoice: INV-003"


def test_rag_engine_retrieve_documents_dedupes_vector_rows_before_sparse_check(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = RAGEngine.__new__(RAGEngine)

    class FakeRPCResult:
        def __init__(self, data):
            self.data = data

    class FakeRPCQuery:
        def __init__(self, data):
            self._data = data

        def execute(self):
            return FakeRPCResult(self._data)

    class FakeDB:
        def rpc(self, fn_name, payload):
            assert fn_name == "match_documents"
            assert payload["match_count"] == 5
            return FakeRPCQuery(
                [
                    {
                        "document_type": "product",
                        "content": "Product: Produk A",
                        "metadata": {"product_id": "prod-a"},
                    },
                    {
                        "document_type": "product",
                        "content": "Product: Produk A",
                        "metadata": {"product_id": "prod-a"},
                    },
                    {
                        "document_type": "product",
                        "content": "Product: Produk B",
                        "metadata": {"product_id": "prod-b"},
                    },
                    {
                        "document_type": "product",
                        "content": "Product: Produk A",
                        "metadata": {"product_id": "prod-a"},
                    },
                    {
                        "document_type": "product",
                        "content": "Product: Produk B",
                        "metadata": {"product_id": "prod-b"},
                    },
                ]
            )

    async def fake_fallback(self, tenant_id, limit, query_text="", existing_docs=None):
        base_docs = list(existing_docs or [])
        # Deduped existing docs should only contain A and B before fallback enriches.
        assert [doc["metadata"]["product_id"] for doc in base_docs] == ["prod-a", "prod-b"]
        return base_docs + [
            {
                "document_type": "product",
                "content": "Product: Produk C",
                "metadata": {"product_id": "prod-c"},
            },
            {
                "document_type": "product",
                "content": "Product: Produk D",
                "metadata": {"product_id": "prod-d"},
            },
            {
                "document_type": "product",
                "content": "Product: Produk E",
                "metadata": {"product_id": "prod-e"},
            },
        ]

    monkeypatch.setattr("app.core.database.get_supabase_admin_client", lambda: FakeDB())
    monkeypatch.setattr(RAGEngine, "_fallback_retrieve", fake_fallback)

    docs = asyncio.run(
        engine._retrieve_documents(
            query_embedding=[0.1, 0.2, 0.3],
            tenant_id="tenant-1",
            top_k=5,
            query_text="Berapa total produk aktif",
        )
    )

    assert len(docs) == 5
    assert docs[0]["metadata"]["product_id"] == "prod-a"
    assert docs[-1]["metadata"]["product_id"] == "prod-e"


def test_build_live_product_summary_doc_has_deterministic_counts():
    engine = RAGEngine.__new__(RAGEngine)

    summary_doc = engine._build_live_product_summary_doc(
        [
            {
                "id": "prod-1",
                "stock_quantity": 10,
                "low_stock_threshold": 5,
            },
            {
                "id": "prod-2",
                "stock_quantity": 0,
                "low_stock_threshold": 2,
            },
            {
                "id": "prod-3",
                "stock_quantity": 1,
                "low_stock_threshold": 3,
            },
        ]
    )

    assert summary_doc is not None
    assert summary_doc["document_type"] == "product_summary"
    assert summary_doc["metadata"]["total_active_products"] == 3
    assert summary_doc["metadata"]["in_stock_products"] == 2
    assert summary_doc["metadata"]["out_of_stock_products"] == 1
    assert summary_doc["metadata"]["low_stock_products"] == 2
    assert summary_doc["metadata"]["total_stock_units"] == 11


def test_build_live_invoice_summary_doc_has_deterministic_counts():
    engine = RAGEngine.__new__(RAGEngine)

    summary_doc = engine._build_live_invoice_summary_doc(
        [
            {"payment_status": "paid", "total_amount": 100000},
            {"payment_status": "unpaid", "total_amount": 250000},
            {"payment_status": "partial", "total_amount": 50000},
            {"payment_status": "overdue", "total_amount": 75000},
        ]
    )

    assert summary_doc is not None
    assert summary_doc["document_type"] == "invoice_summary"
    assert summary_doc["metadata"]["total_invoices"] == 4
    assert summary_doc["metadata"]["unpaid_or_overdue_invoices"] == 3
    assert summary_doc["metadata"]["paid_invoices"] == 1
    assert summary_doc["metadata"]["total_invoice_amount"] == 475000.0