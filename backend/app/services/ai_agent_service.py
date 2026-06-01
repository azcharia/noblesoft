"""
AI Agent Service
Orchestrates RAG pipeline and handles chat interactions
"""
import asyncio
from typing import Dict, Any, Optional, List
import logging
import json
import re
import time
from datetime import date, timedelta

from app.core.dependencies import CurrentUser
from app.core.database import get_supabase_admin_client
from app.ai.rag_engine import RAGEngine
from app.ai.tavily_client import TavilySearchClient
from app.ai.groq_client import GroqLLMClient
from app.ai.prompts import (
    MANAGER_RECONCILIATION_PROMPT,
    TAVILY_WEB_ASSISTANT_PROMPT,
    get_function_calling_prompt,
    get_reconciliation_prompt,
    get_web_context_prompt,
)
from app.config import settings

logger = logging.getLogger(__name__)


class AIAgentService:
    """
    AI Agent service for conversational interactions
    Handles RAG queries and future function calling
    """
    
    def __init__(self):
        """Initialize AI agent with RAG engine"""
        self.rag_engine = RAGEngine()
        self.groq_client = GroqLLMClient()
        self.tavily_client = TavilySearchClient()
    
    async def process_chat_message(
        self,
        query: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message using RAG pipeline
        
        Args:
            query: User's message/question
            current_user: Current authenticated user (contains tenant_id)
            conversation_history: Optional previous messages for context
        
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Override Groq client with tenant specific AI Settings (BYOK)
            tenant_groq = await self._resolve_tenant_groq_client(current_user.tenant_id)
            if tenant_groq:
                self.groq_client = tenant_groq

            # Validate subscription tier (bypassed for open source)
            pass
            
            # Log query for analytics
            logger.info(
                f"AI query from user {current_user.id} (tenant: {current_user.tenant_id}): {query}"
            )

            assistant_mode = self._detect_assistant_mode(query, current_user)

            if assistant_mode == "hybrid_parallel":
                result = await self._run_hybrid_parallel_orchestration(
                    query=query,
                    current_user=current_user,
                    conversation_history=conversation_history,
                )
            elif assistant_mode == "tavily":
                try:
                    auditor_result = await self._execute_auditor_worker(
                        query=query,
                        current_user=current_user,
                        conversation_history=conversation_history,
                    )

                    result = {
                        "response": auditor_result["response"],
                        "sources": auditor_result["sources"],
                        "retrieved_count": 0,
                        "assistant_mode": "tavily",
                        "orchestration_mode": "single",
                        "tool_calls": auditor_result["tool_calls"],
                        "manager_result_summary": None,
                        "auditor_result_summary": auditor_result.get("auditor_result_summary"),
                        "reconciliation_notes": None,
                    }
                except Exception as tavily_error:
                    logger.warning(
                        "Tavily mode failed, falling back to RAG for tenant %s: %s",
                        current_user.tenant_id,
                        str(tavily_error),
                    )
                    manager_result = await self._execute_manager_worker(
                        query=query,
                        current_user=current_user,
                        conversation_history=conversation_history,
                    )

                    result = {
                        "response": manager_result["response"],
                        "sources": manager_result["sources"],
                        "retrieved_count": manager_result["retrieved_count"],
                        "assistant_mode": "rag_fallback",
                        "orchestration_mode": "single",
                        "tool_calls": [],
                        "manager_result_summary": manager_result.get("manager_result_summary"),
                        "auditor_result_summary": {
                            "status": "failed",
                            "error": str(tavily_error),
                            "tool_count": 0,
                        },
                        "reconciliation_notes": "Auditor web gagal dijalankan, jawaban menggunakan manager internal.",
                    }
            else:
                # Default path: tenant-scoped RAG for internal business data.
                manager_result = await self._execute_manager_worker(
                    query=query,
                    current_user=current_user,
                    conversation_history=conversation_history,
                )

                result = {
                    "response": manager_result["response"],
                    "sources": manager_result["sources"],
                    "retrieved_count": manager_result["retrieved_count"],
                    "assistant_mode": "rag",
                    "orchestration_mode": "single",
                    "tool_calls": [],
                    "manager_result_summary": manager_result.get("manager_result_summary"),
                    "auditor_result_summary": None,
                    "reconciliation_notes": None,
                }
                if "function_executed" in manager_result:
                    result["function_executed"] = manager_result["function_executed"]
                if "execution_result" in manager_result:
                    result["execution_result"] = manager_result["execution_result"]
            
            # Add user context to response
            result["user_context"] = {
                "tenant_id": current_user.tenant_id,
                "company_name": current_user.company_name,
                "subscription_tier": current_user.subscription_tier
            }
            
            logger.info(
                f"AI response generated for user {current_user.id}, "
                f"mode={result.get('assistant_mode', 'rag')}, "
                f"orchestration={result.get('orchestration_mode', 'single')}, "
                f"retrieved {result.get('retrieved_count', 0)} documents"
            )
            
            return result
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            return {
                "response": (
                    "Maaf, terjadi kesalahan saat memproses pertanyaan Anda. "
                    "Silakan coba lagi atau hubungi support jika masalah berlanjut."
                ),
                "error": str(e),
                "sources": [],
                "assistant_mode": "rag",
                "orchestration_mode": "single",
                "tool_calls": [],
                "manager_result_summary": None,
                "auditor_result_summary": None,
                "reconciliation_notes": None,
            }

    async def _run_hybrid_parallel_orchestration(
        self,
        query: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Run manager (internal) and auditor (web) workers in parallel, then reconcile."""
        timeout_seconds = self._resolve_orchestration_timeout_seconds()
        manager_task = asyncio.create_task(
            self._execute_manager_worker(
                query=query,
                current_user=current_user,
                conversation_history=conversation_history,
            )
        )
        auditor_task = asyncio.create_task(
            self._execute_auditor_worker(
                query=query,
                current_user=current_user,
                conversation_history=conversation_history,
            )
        )

        try:
            manager_result, auditor_result = await asyncio.wait_for(
                asyncio.gather(manager_task, auditor_task, return_exceptions=True),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            for task in (manager_task, auditor_task):
                if not task.done():
                    task.cancel()

            manager_fallback = await self._execute_manager_worker(
                query=query,
                current_user=current_user,
                conversation_history=conversation_history,
            )

            return {
                "response": manager_fallback["response"],
                "sources": manager_fallback["sources"],
                "retrieved_count": manager_fallback["retrieved_count"],
                "assistant_mode": "hybrid_parallel_timeout_fallback",
                "orchestration_mode": "hybrid_parallel",
                "tool_calls": [],
                "manager_result_summary": manager_fallback.get("manager_result_summary"),
                "auditor_result_summary": {
                    "status": "timeout",
                    "tool_count": 0,
                },
                "reconciliation_notes": (
                    "Eksekusi paralel melebihi batas waktu; jawaban menggunakan manager internal."
                ),
            }

        manager_error = manager_result if isinstance(manager_result, Exception) else None
        auditor_error = auditor_result if isinstance(auditor_result, Exception) else None

        if manager_error and auditor_error:
            raise Exception(
                "Manager dan auditor gagal dieksekusi: "
                f"manager={manager_error}, auditor={auditor_error}"
            )

        if manager_error:
            auditor_payload = dict(auditor_result)
            return {
                "response": auditor_payload["response"],
                "sources": auditor_payload["sources"],
                "retrieved_count": 0,
                "assistant_mode": "hybrid_parallel_fallback_auditor",
                "orchestration_mode": "hybrid_parallel",
                "tool_calls": auditor_payload.get("tool_calls", []),
                "manager_result_summary": {
                    "status": "failed",
                    "error": str(manager_error),
                },
                "auditor_result_summary": auditor_payload.get("auditor_result_summary"),
                "reconciliation_notes": (
                    "Manager internal gagal; jawaban menggunakan auditor web sebagai fallback."
                ),
            }

        if auditor_error:
            manager_payload = dict(manager_result)
            return {
                "response": manager_payload["response"],
                "sources": manager_payload["sources"],
                "retrieved_count": manager_payload["retrieved_count"],
                "assistant_mode": "hybrid_parallel_fallback_manager",
                "orchestration_mode": "hybrid_parallel",
                "tool_calls": [],
                "manager_result_summary": manager_payload.get("manager_result_summary"),
                "auditor_result_summary": {
                    "status": "failed",
                    "error": str(auditor_error),
                    "tool_count": 0,
                },
                "reconciliation_notes": (
                    "Auditor web gagal; jawaban menggunakan manager internal sebagai fallback."
                ),
            }

        manager_payload = dict(manager_result)
        auditor_payload = dict(auditor_result)

        merged_response = await self._reconcile_worker_outputs(
            query=query,
            manager_response=manager_payload.get("response", ""),
            auditor_response=auditor_payload.get("response", ""),
            conversation_history=conversation_history,
        )

        merged_sources = self._merge_sources(
            manager_payload.get("sources"),
            auditor_payload.get("sources"),
        )

        return {
            "response": merged_response,
            "sources": merged_sources,
            "retrieved_count": manager_payload.get("retrieved_count", 0),
            "assistant_mode": "hybrid_parallel",
            "orchestration_mode": "hybrid_parallel",
            "tool_calls": auditor_payload.get("tool_calls", []),
            "manager_result_summary": manager_payload.get("manager_result_summary"),
            "auditor_result_summary": auditor_payload.get("auditor_result_summary"),
            "reconciliation_notes": (
                    "Manager internal dan auditor web (Tavily) dijalankan paralel lalu direkonsiliasi "
                "oleh GPT-OSS manager."
            ),
        }

    async def _execute_manager_worker(
        self,
        query: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Manager worker: use internal tenant-scoped RAG + function calling as the main brain path."""
        top_k = self._resolve_rag_top_k(query=query, assistant_mode="rag")
        manager_result = await self._query_rag(
            query=query,
            tenant_id=current_user.tenant_id,
            top_k=top_k,
            conversation_history=conversation_history,
        )

        sources = self._normalize_sources(manager_result.get("sources"))
        retrieved_count = int(manager_result.get("retrieved_count") or len(sources))
        context = "\n".join([str(source.get("content", "")) for source in sources])

        # Step 2: Define available functions
        available_functions = [
            "create_product",
            "create_invoice",
            "update_stock",
            "check_stock",
            "get_invoice_status"
        ]

        if not hasattr(self, "groq_client"):
            # Bypassed or mock test environment where LLM client is not initialized
            response_text = str(manager_result.get("response") or "").strip()
            function_executed = None
            exec_res = None
        else:
            # Step 3: Ask AI to determine if function call is needed
            function_prompt = get_function_calling_prompt(
                query, context, available_functions
            )

            messages = [
                {"role": "system", "content": "You are a function-calling AI assistant."},
                {"role": "user", "content": function_prompt}
            ]

            ai_response = await self.groq_client.chat_completion_async(messages)

            # Step 4: Parse AI response for function calls
            function_call = self._parse_function_call(ai_response)

            if function_call:
                # Step 5: Execute function
                execution_result = await self._execute_function(
                    function_call,
                    current_user
                )
                response_text = execution_result["message"]
                function_executed = function_call["function"]
                exec_res = execution_result
            else:
                response_text = ai_response.strip()
                function_executed = None
                exec_res = None

        result = {
            "response": response_text,
            "sources": sources,
            "retrieved_count": retrieved_count,
            "manager_result_summary": {
                "status": "success",
                "retrieved_count": retrieved_count,
                "source_count": len(sources),
                "top_k_used": top_k,
                "response_preview": self._to_preview(response_text),
            },
        }
        if function_executed:
            result["function_executed"] = function_executed
            result["execution_result"] = exec_res

        return result

    async def _execute_auditor_worker(
        self,
        query: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Auditor worker: use Tavily retrieval for external verification."""
        auditor_result = await self._query_tavily_web(
            query=query,
            current_user=current_user,
            conversation_history=conversation_history,
        )

        response_text = str(auditor_result.get("response") or "").strip()
        tool_calls = self._normalize_tool_calls(auditor_result.get("tool_calls"))
        source_docs = self._merge_sources(
            self._normalize_sources(auditor_result.get("sources")),
            self._build_auditor_sources(tool_calls),
        )

        return {
            "response": response_text,
            "sources": source_docs,
            "tool_calls": tool_calls,
            "auditor_result_summary": {
                "status": "success",
                "tool_count": len(tool_calls),
                "source_count": len(source_docs),
                "response_preview": self._to_preview(response_text),
            },
        }

    async def _reconcile_worker_outputs(
        self,
        query: str,
        manager_response: str,
        auditor_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Use GPT-OSS manager to merge manager and auditor outputs into one final answer."""
        manager_text = manager_response.strip()
        auditor_text = auditor_response.strip()

        if not manager_text:
            return auditor_text
        if not auditor_text:
            return manager_text

        reconciliation_prompt = get_reconciliation_prompt(
            query=query,
            manager_response=manager_text,
            auditor_response=auditor_text,
        )

        messages = [
            {"role": "system", "content": MANAGER_RECONCILIATION_PROMPT},
        ]
        messages.extend(self._prepare_history_messages(conversation_history, max_messages=4))
        messages.append({"role": "user", "content": reconciliation_prompt})

        try:
            merged = await self.groq_client.chat_completion_async(
                messages,
                temperature=0.2,
                max_tokens=1200,
            )
        except TypeError:
            merged = await self.groq_client.chat_completion_async(messages)
        except Exception as error:
            logger.warning("Reconciliation failed, using deterministic merge: %s", str(error))
            merged = ""

        merged_text = str(merged or "").strip()
        if merged_text:
            return merged_text

        return (
            f"{manager_text}\n\n"
            "Catatan audit web:\n"
            f"{auditor_text}"
        )

    def _resolve_orchestration_timeout_seconds(self) -> float:
        """Read and clamp orchestration timeout for safer parallel execution."""
        try:
            timeout_seconds = float(settings.ORCHESTRATION_TIMEOUT_SECONDS)
        except Exception:
            timeout_seconds = 10.0

        if timeout_seconds < 2:
            return 2.0
        if timeout_seconds > 30:
            return 30.0
        return timeout_seconds

    def _normalize_sources(self, sources: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Normalize source documents into list[dict] for API compatibility."""
        if not isinstance(sources, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            normalized.append(source)
        return normalized

    def _normalize_tool_calls(self, tool_calls: Any) -> List[Dict[str, Any]]:
        """Normalize tool call metadata payload."""
        if not isinstance(tool_calls, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            normalized.append(tool_call)
        return normalized

    def _merge_sources(
        self,
        primary_sources: Optional[List[Dict[str, Any]]],
        secondary_sources: Optional[List[Dict[str, Any]]],
        max_items: int = 10,
    ) -> List[Dict[str, Any]]:
        """Merge source lists while keeping order and avoiding duplicate entries."""
        merged: List[Dict[str, Any]] = []
        seen_markers = set()

        for candidate in [
            *(primary_sources or []),
            *(secondary_sources or []),
        ]:
            if not isinstance(candidate, dict):
                continue

            marker = (
                str(candidate.get("type") or ""),
                str(candidate.get("content") or "")[:240],
            )
            if marker in seen_markers:
                continue

            seen_markers.add(marker)
            merged.append(candidate)

            if len(merged) >= max_items:
                break

        return merged

    def _build_auditor_sources(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tool call metadata into source-style records for UI traceability."""
        sources: List[Dict[str, Any]] = []
        for index, tool_call in enumerate(tool_calls, start=1):
            tool_name = str(tool_call.get("name") or "unknown_tool")
            sources.append(
                {
                    "type": "audit_tool",
                    "content": f"Auditor menggunakan tool '{tool_name}' untuk verifikasi web.",
                    "metadata": {
                        "sequence": index,
                        "tool_call": tool_call,
                    },
                }
            )
        return sources

    def _to_preview(self, text: str, limit: int = 180) -> str:
        """Create compact preview text for metadata payloads."""
        cleaned = " ".join((text or "").split())
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[:limit].rstrip()}..."
    
    async def process_with_function_calling(
        self,
        query: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        ADVANCED: Process query with function calling capability
        Allows AI to trigger actions (create invoice, update stock, etc.)
        
        This is a blueprint for Phase 5+ implementation
        
        Args:
            query: User's request
            current_user: Current user context
        
        Returns:
            Dictionary with response and executed actions
        """
        try:
            # Override Groq client with tenant specific AI Settings (BYOK)
            tenant_groq = await self._resolve_tenant_groq_client(current_user.tenant_id)
            if tenant_groq:
                self.groq_client = tenant_groq
            # Step 1: Retrieve relevant context
            top_k = self._resolve_rag_top_k(query=query, assistant_mode="function_calling")
            rag_result = await self._query_rag(
                query=query,
                tenant_id=current_user.tenant_id,
                top_k=top_k,
                conversation_history=conversation_history,
            )
            
            context = "\n".join([
                source["content"] for source in rag_result.get("sources", [])
            ])
            
            # Step 2: Define available functions
            available_functions = [
                "create_product",
                "create_invoice",
                "update_stock",
                "check_stock",
                "get_invoice_status"
            ]
            
            # Step 3: Ask AI to determine if function call is needed
            function_prompt = get_function_calling_prompt(
                query, context, available_functions
            )
            
            messages = [
                {"role": "system", "content": "You are a function-calling AI assistant."},
                {"role": "user", "content": function_prompt}
            ]
            
            ai_response = await self.groq_client.chat_completion_async(messages)
            
            # Step 4: Parse AI response for function calls
            function_call = self._parse_function_call(ai_response)
            
            user_context = {
                "tenant_id": current_user.tenant_id,
                "company_name": current_user.company_name,
                "subscription_tier": current_user.subscription_tier
            }

            if function_call:
                # Step 5: Execute function
                execution_result = await self._execute_function(
                    function_call,
                    current_user
                )
                
                return {
                    "response": execution_result["message"],
                    "function_executed": function_call["function"],
                    "execution_result": execution_result,
                    "sources": rag_result.get("sources", []),
                    "retrieved_count": rag_result.get("retrieved_count", 0),
                    "user_context": user_context,
                    "assistant_mode": "function_calling",
                    "orchestration_mode": "single",
                }
            else:
                # No function call detected: return direct analysis text from model.
                return {
                    "response": ai_response,
                    "sources": rag_result.get("sources", []),
                    "retrieved_count": rag_result.get("retrieved_count", 0),
                    "user_context": user_context,
                    "assistant_mode": "function_calling",
                    "orchestration_mode": "single",
                }
        
        except Exception as e:
            logger.error(f"Function calling error: {str(e)}")
            return {
                "response": f"Error: {str(e)}",
                "error": str(e)
            }
    
    def _parse_function_call(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """
        Parse AI response to extract function call
        
        Args:
            ai_response: AI's response text
        
        Returns:
            Function call dict or None
        """
        try:
            cleaned = ai_response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            candidates: List[str] = [cleaned]
            for match in re.finditer(r"\{[\s\S]*\}", cleaned):
                candidates.append(match.group(0))

            decoder = json.JSONDecoder()
            parsed_objects: List[Dict[str, Any]] = []

            for candidate in candidates:
                candidate = candidate.strip()
                if not candidate:
                    continue

                try:
                    loaded = json.loads(candidate)
                    if isinstance(loaded, dict):
                        parsed_objects.append(loaded)
                        continue
                except Exception:
                    pass

                for idx, ch in enumerate(candidate):
                    if ch != "{":
                        continue
                    try:
                        loaded, _ = decoder.raw_decode(candidate[idx:])
                        if isinstance(loaded, dict):
                            parsed_objects.append(loaded)
                    except Exception:
                        continue

            for obj in parsed_objects:
                normalized = self._normalize_function_call(obj)
                if normalized is not None:
                    return normalized

            return None
        
        except Exception as e:
            logger.warning(f"Failed to parse function call: {str(e)}")
            return None

    async def _query_rag(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Query RAG engine with graceful fallback for legacy call signatures."""
        if conversation_history is None:
            return await self.rag_engine.query_with_rag(
                query=query,
                tenant_id=tenant_id,
                top_k=top_k,
            )

        try:
            return await self.rag_engine.query_with_rag(
                query=query,
                tenant_id=tenant_id,
                top_k=top_k,
                conversation_history=conversation_history,
            )
        except TypeError as exc:
            if "conversation_history" not in str(exc):
                raise
            return await self.rag_engine.query_with_rag(
                query=query,
                tenant_id=tenant_id,
                top_k=top_k,
            )

    async def _query_tavily_web(
        self,
        query: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Query Tavily for web context, then synthesize final answer with GPT-OSS."""
        search_config = self._infer_tavily_search_config(query)
        tavily_result = await self.tavily_client.search_async(
            query=query,
            topic=search_config["topic"],
            time_range=search_config["time_range"],
            max_results=search_config["max_results"],
            search_depth=search_config["search_depth"],
        )

        sources = self._normalize_sources(tavily_result.get("sources"))
        tool_calls = self._normalize_tool_calls(tavily_result.get("tool_calls"))

        if not sources:
            return {
                "response": (
                    "Maaf, saya belum menemukan sumber web tepercaya yang relevan untuk "
                    "pertanyaan ini saat ini. Silakan coba ulang dengan kata kunci yang lebih "
                    "spesifik atau rentang waktu yang lebih luas."
                ),
                "sources": [],
                "retrieved_count": 0,
                "tool_calls": tool_calls,
            }

        web_context = self._build_web_context(sources)

        messages = self._build_tavily_messages(
            query=query,
            web_context=web_context,
            current_user=current_user,
            conversation_history=conversation_history,
        )

        try:
            response_text = await self.groq_client.chat_completion_async(
                messages,
                temperature=0.2,
                max_tokens=1200,
            )
        except TypeError:
            response_text = await self.groq_client.chat_completion_async(messages)

        response_text = str(response_text or "").strip()
        if not response_text:
            response_text = (
                "Maaf, saya belum menemukan temuan web yang cukup untuk menjawab pertanyaan "
                "secara akurat saat ini."
            )

        return {
            "response": response_text,
            "sources": sources,
            "retrieved_count": len(sources),
            "tool_calls": tool_calls,
        }

    def _detect_assistant_mode(self, query: str, current_user: CurrentUser) -> str:
        """Route queries to RAG, Tavily, or hybrid parallel orchestration mode."""
        if not settings.is_tavily_enabled:
            return "rag"

        normalized = query.strip().lower()
        if not normalized:
            return "rag"

        if normalized.startswith("/hybrid "):
            if self._can_use_hybrid_parallel(current_user):
                return "hybrid_parallel"
            return "rag"

        if normalized.startswith("/web "):
            return "tavily"
        if normalized.startswith("/internal "):
            return "rag"

        internal_data_keywords = (
            "stok",
            "stock",
            "inventory",
            "invoice",
            "faktur",
            "produk",
            "product",
            "customer",
            "pelanggan",
            "tenant",
            "dashboard",
            "analytics",
        )

        web_intent_keywords = (
            "cari di web",
            "cari di internet",
            "search web",
            "search internet",
            "web search",
            " web",
            "internet",
            "browser",
            "website",
            "url",
            "link",
            "berita",
            "news",
            "tren",
            "trend",
            "terbaru",
            "update terbaru",
            "regulasi",
            "regulation",
            "kompetitor",
            "competitor",
            "market",
            "pasar",
            "kurs",
        )

        has_internal_intent = any(keyword in normalized for keyword in internal_data_keywords)
        has_web_intent = any(keyword in normalized for keyword in web_intent_keywords)

        if has_web_intent and not has_internal_intent:
            return "tavily"

        if has_internal_intent and not has_web_intent:
            return "rag"

        if has_web_intent and has_internal_intent:
            if (
                settings.ORCHESTRATION_ENABLE_HYBRID_FOR_MIXED_INTENT
                and self._can_use_hybrid_parallel(current_user)
            ):
                return "hybrid_parallel"
            if any(term in normalized for term in ("internet", "web", "website", "browser")):
                return "tavily"
            return "rag"

        # Heuristic for fresh external information requests.
        is_fresh_info_request = bool(
            re.search(r"\b(hari ini|minggu ini|bulan ini|terbaru|update|latest|today|current)\b", normalized)
            and re.search(r"\b(berita|news|regulasi|regulation|kompetitor|competitor|pasar|market)\b", normalized)
        )
        if is_fresh_info_request:
            return "tavily"

        return "rag"

    def _can_use_hybrid_parallel(self, current_user: CurrentUser) -> bool:
        """Check feature gate and user tier for hybrid parallel orchestration."""
        if not settings.is_orchestration_enabled:
            return False

        if settings.ORCHESTRATION_ENTERPRISE_ONLY and current_user.subscription_tier != "enterprise":
            return False

        return True

    def _build_tavily_messages(
        self,
        query: str,
        web_context: str,
        current_user: CurrentUser,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """Build messages payload for Tavily-backed web synthesis mode."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": TAVILY_WEB_ASSISTANT_PROMPT}
        ]

        messages.extend(self._prepare_history_messages(conversation_history))

        context_prompt = get_web_context_prompt(query, web_context)
        user_prompt = (
            "KONTEKS BISNIS USER:\n"
            f"- Perusahaan: {current_user.company_name}\n"
            f"- Tenant ID: {current_user.tenant_id}\n\n"
            f"{context_prompt}"
        )
        messages.append({"role": "user", "content": user_prompt})

        return messages

    def _infer_tavily_search_config(self, query: str) -> Dict[str, Any]:
        """Infer Tavily search parameters from query intent."""
        normalized = query.strip().lower()

        topic = "general"
        if any(term in normalized for term in ("berita", "news")):
            topic = "news"
        elif any(term in normalized for term in ("saham", "stock market", "forex", "kurs")):
            topic = "finance"

        time_range: Optional[str] = None
        if any(term in normalized for term in ("hari ini", "today", "terkini")):
            time_range = "day"
        elif any(term in normalized for term in ("minggu ini", "this week")):
            time_range = "week"
        elif any(term in normalized for term in ("bulan ini", "this month")):
            time_range = "month"
        elif any(term in normalized for term in ("tahun ini", "this year")):
            time_range = "year"

        return {
            "topic": topic,
            "time_range": time_range,
            "max_results": settings.TAVILY_MAX_RESULTS,
            "search_depth": "basic",
        }

    def _build_web_context(self, sources: List[Dict[str, Any]]) -> str:
        """Render Tavily sources into compact context for GPT-OSS synthesis."""
        if not sources:
            return "Tidak ada temuan web yang relevan."

        lines: List[str] = []
        for index, source in enumerate(sources[:8], start=1):
            metadata = source.get("metadata") if isinstance(source, dict) else {}
            if not isinstance(metadata, dict):
                metadata = {}
            title = str(metadata.get("title") or f"Sumber {index}")
            url = str(metadata.get("url") or "")
            content = str(source.get("content") or "")
            compact_content = content[:500]
            if len(content) > 500:
                compact_content = f"{compact_content.rstrip()}..."

            if url:
                lines.append(f"[{index}] {title} | URL: {url}\n{compact_content}")
            else:
                lines.append(f"[{index}] {title}\n{compact_content}")

        return "\n\n".join(lines)

    def _prepare_history_messages(
        self,
        conversation_history: Optional[List[Dict[str, str]]],
        max_messages: int = 6,
    ) -> List[Dict[str, str]]:
        """Normalize chat history into safe LLM message objects."""
        if not conversation_history:
            return []

        normalized_messages: List[Dict[str, str]] = []
        for entry in conversation_history[-max_messages:]:
            if not isinstance(entry, dict):
                continue

            role = str(entry.get("role", "")).strip().lower()
            content = entry.get("content")

            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str):
                continue

            cleaned_content = content.strip()
            if not cleaned_content:
                continue

            normalized_messages.append({"role": role, "content": cleaned_content})

        return normalized_messages

    def _normalize_function_call(self, raw_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize different function-call JSON styles into a strict schema."""
        function_name = raw_obj.get("function") or raw_obj.get("tool") or raw_obj.get("action")
        if not isinstance(function_name, str):
            return None

        parameters = raw_obj.get("parameters")
        if parameters is None:
            parameters = raw_obj.get("args")
        if not isinstance(parameters, dict):
            return None

        normalized: Dict[str, Any] = {
            "function": function_name,
            "parameters": dict(parameters),
        }

        if function_name == "create_product":
            mapping = {
                "price": "unit_price",
                "stock": "stock_quantity",
            }
            for old_key, new_key in mapping.items():
                if old_key in normalized["parameters"] and new_key not in normalized["parameters"]:
                    normalized["parameters"][new_key] = normalized["parameters"].pop(old_key)

        return normalized

    def _resolve_rag_top_k(self, query: str, assistant_mode: str = "rag") -> int:
        """Resolve retrieval depth dynamically so invoice/mixed intents get broader context."""
        normalized = (query or "").strip().lower()
        if not normalized:
            return 8

        invoice_keywords = (
            "invoice",
            "faktur",
            "tagihan",
            "payment",
            "pembayaran",
            "unpaid",
            "overdue",
            "piutang",
            "customer",
        )
        product_keywords = (
            "stok",
            "stock",
            "inventory",
            "produk",
            "product",
            "sku",
            "restock",
            "laptop",
        )
        web_keywords = (
            "web",
            "internet",
            "website",
            "news",
            "berita",
            "market",
            "pasar",
            "trend",
            "tren",
        )

        has_invoice_intent = any(keyword in normalized for keyword in invoice_keywords)
        has_product_intent = any(keyword in normalized for keyword in product_keywords)
        has_web_intent = any(keyword in normalized for keyword in web_keywords)

        if assistant_mode == "function_calling":
            base_top_k = 10
        elif has_invoice_intent and has_product_intent:
            base_top_k = 18
        elif has_invoice_intent:
            base_top_k = 14
        elif has_product_intent:
            base_top_k = 12
        else:
            base_top_k = 10

        if has_web_intent and (has_invoice_intent or has_product_intent):
            base_top_k += 2

        if assistant_mode == "hybrid_parallel":
            base_top_k = max(base_top_k, 16)

        if base_top_k < 6:
            return 6
        if base_top_k > 24:
            return 24
        return base_top_k
    
    async def _execute_function(
        self,
        function_call: Dict[str, Any],
        current_user: CurrentUser
    ) -> Dict[str, Any]:
        """
        Execute a function call
        
        Args:
            function_call: Function name and parameters
            current_user: Current user context
        
        Returns:
            Execution result
        """
        function_name = function_call.get("function")
        parameters = function_call.get("parameters", {})
        
        try:
            # Import services dynamically to avoid circular imports
            from app.services.product_service import ProductService
            from app.services.invoice_service import InvoiceService
            from app.models.product import ProductCreate, StockAdjustment
            from app.models.invoice import InvoiceCreate
            
            # Route to appropriate service
            if function_name == "create_product":
                service = ProductService()
                product_data = ProductCreate(**parameters)
                result = await service.create_product(product_data, current_user)
                return {
                    "success": True,
                    "message": f"Produk '{result.name}' berhasil dibuat dengan SKU {result.sku}",
                    "data": result.model_dump()
                }
            
            elif function_name == "update_stock":
                service = ProductService()
                adjustment = StockAdjustment(**parameters)
                result = await service.adjust_stock(
                    parameters["product_id"],
                    adjustment,
                    current_user
                )
                return {
                    "success": True,
                    "message": f"Stok berhasil diupdate. Stok baru: {result.stock_quantity}",
                    "data": result.model_dump()
                }
            
            elif function_name == "check_stock":
                service = ProductService()
                products = await service.list_products(
                    current_user,
                    search=parameters.get("product_name"),
                    page_size=5
                )
                return {
                    "success": True,
                    "message": f"Ditemukan {len(products['products'])} produk",
                    "data": [p.model_dump() for p in products["products"]]
                }
            
            elif function_name == "create_invoice":
                service = InvoiceService()
                invoice_parameters = dict(parameters)

                if not invoice_parameters.get("invoice_number"):
                    invoice_parameters["invoice_number"] = (
                        f"INV-AI-{int(time.time())}"
                    )

                if not invoice_parameters.get("issue_date"):
                    invoice_parameters["issue_date"] = date.today().isoformat()

                if not invoice_parameters.get("due_date"):
                    invoice_parameters["due_date"] = (
                        date.today() + timedelta(days=14)
                    ).isoformat()

                if "customer_name" not in invoice_parameters:
                    raise ValueError("Parameter 'customer_name' wajib untuk create_invoice")

                if not invoice_parameters.get("items"):
                    raise ValueError("Parameter 'items' wajib dan tidak boleh kosong")

                invoice_data = InvoiceCreate(**invoice_parameters)
                result = await service.create_invoice(invoice_data, current_user)
                return {
                    "success": True,
                    "message": (
                        f"Invoice '{result.invoice_number}' berhasil dibuat "
                        f"dengan total Rp {result.total_amount:,.2f}"
                    ),
                    "data": result.model_dump()
                }
            
            elif function_name == "get_invoice_status":
                service = InvoiceService()
                invoice = None

                invoice_id = parameters.get("invoice_id")
                invoice_number = parameters.get("invoice_number")

                if invoice_id:
                    invoice = await service.get_invoice(str(invoice_id), current_user)
                elif invoice_number:
                    lookup = service.db.table("invoices").select("id").eq(
                        "tenant_id", current_user.tenant_id
                    ).eq("invoice_number", str(invoice_number).strip().upper()).limit(1).execute()
                    if lookup.data:
                        invoice = await service.get_invoice(lookup.data[0]["id"], current_user)

                if not invoice:
                    return {
                        "success": False,
                        "message": "Invoice tidak ditemukan. Mohon cek nomor atau ID invoice.",
                    }

                return {
                    "success": True,
                    "message": (
                        f"Status invoice {invoice.invoice_number}: {invoice.payment_status.value.upper()}. "
                        f"Total Rp {invoice.total_amount:,.2f}."
                    ),
                    "data": invoice.model_dump()
                }
            
            else:
                return {
                    "success": False,
                    "message": f"Fungsi '{function_name}' tidak dikenali"
                }
        
        except Exception as e:
            logger.error(f"Function execution error: {str(e)}")
            return {
                "success": False,
                "message": f"Error executing function: {str(e)}",
                "error": str(e)
            }
    
    async def get_suggested_questions(
        self,
        current_user: CurrentUser
    ) -> List[str]:
        """
        Generate suggested questions based on user's data
        
        Args:
            current_user: Current user context
        
        Returns:
            List of suggested questions
        """
        try:
            db = get_supabase_admin_client()

            products_response = db.table("products").select(
                "id, name, stock_quantity, low_stock_threshold",
                count="exact",
            ).eq("tenant_id", current_user.tenant_id).eq("is_active", True).execute()

            invoices_response = db.table("invoices").select(
                "id, invoice_number, customer_name, total_amount, payment_status",
                count="exact",
            ).eq("tenant_id", current_user.tenant_id).execute()

            products = products_response.data or []
            invoices = invoices_response.data or []

            low_stock_products = [
                p for p in products
                if int(p.get("stock_quantity", 0)) <= int(p.get("low_stock_threshold", 0))
            ]
            unpaid_invoices = [
                inv for inv in invoices
                if str(inv.get("payment_status", "")).lower() in {"unpaid", "overdue", "partial"}
            ]

            suggestions: List[str] = []
            suggestions.append(
                f"Berapa total jenis barang dagangan yang kita miliki saat ini? (Tercatat {len(products)} barang)"
            )

            if low_stock_products:
                suggestions.append(
                    f"Barang apa saja yang stoknya hampir habis dan perlu dibeli lagi? (Ada {len(low_stock_products)} barang)"
                )
            else:
                suggestions.append("Barang apa yang stoknya paling banyak di toko saat ini?")

            suggestions.append(
                f"Ada berapa nota penjualan yang pembayarannya belum lunas? (Ada {len(unpaid_invoices)} nota)"
            )

            if invoices:
                largest_invoice = max(invoices, key=lambda inv: float(inv.get("total_amount") or 0))
                largest_customer = largest_invoice.get("customer_name", "pelanggan")
                suggestions.append(
                    f"Tunjukkan nota penjualan dengan nilai transaksi terbesar atas nama pelanggan {largest_customer}."
                )
            else:
                suggestions.append("Bagaimana rangkuman penjualan toko kita untuk minggu ini?")

            if products:
                first_product = products[0].get("name") or "barang utama"
                suggestions.append(
                    f"Berapa sisa stok barang {first_product} dan kapan harus beli lagi?"
                )
            else:
                suggestions.append("Bagaimana cara mencatat barang dagangan baru ke dalam sistem?")

            # Keep UI compact and deterministic
            return suggestions[:6]

        except Exception as e:
            logger.warning(f"Failed to generate dynamic suggestions: {str(e)}")
            return [
                "Berapa total sisa stok barang di toko saat ini?",
                "Barang apa saja yang stoknya hampir habis?",
                "Berapa banyak nota tagihan yang belum dibayar lunas?",
                "Siapa pelanggan dengan nilai transaksi nota terbesar?",
                "Tampilkan rangkuman stok barang dagangan",
            ]

    async def _resolve_tenant_groq_client(self, tenant_id: str) -> Optional[GroqLLMClient]:
        """Resolve a custom GroqLLMClient for the given tenant using tenant_ai_settings (BYOK)."""
        try:
            db = get_supabase_admin_client()
            response = db.table("tenant_ai_settings").select("*").eq("tenant_id", tenant_id).execute()
            if response.data:
                settings_data = response.data[0]
                api_key = settings_data.get("api_key")
                base_url = settings_data.get("base_url")
                model_name = settings_data.get("model_name")
                temperature = settings_data.get("temperature")
                
                # Check if custom settings are provided
                if api_key:
                    temp_val = float(temperature) if temperature is not None else 0.2
                    return GroqLLMClient(
                        api_key=api_key,
                        base_url=base_url,
                        model=model_name,
                        temperature=temp_val
                    )
            return None
        except Exception as e:
            logger.warning(f"Failed to resolve tenant specific Groq client for {tenant_id}: {str(e)}")
            return None
