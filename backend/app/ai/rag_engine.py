"""
RAG Engine using Supabase pgvector + FREE local embeddings
Retrieval-Augmented Generation for tenant-scoped queries
100% FREE: Groq for LLM + sentence-transformers for embeddings
"""
from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.ai.groq_client import GroqLLMClient
from app.ai.prompts import SYSTEM_PROMPT, get_context_prompt

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine
    Uses Supabase pgvector for tenant-scoped document retrieval
    100% FREE with local embeddings and Groq LLM
    """
    
    _embedding_model: Optional[SentenceTransformer] = None

    def __init__(self):
        """Initialize RAG engine with FREE local embeddings and Groq"""
        self.groq_client = GroqLLMClient()
        
        # Load FREE local embedding model
        if settings.USE_LOCAL_EMBEDDINGS:
            if RAGEngine._embedding_model is None:
                logger.info(f"Loading local embedding model: {settings.EMBEDDING_MODEL}")
                RAGEngine._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
                logger.info("Local embedding model loaded (100% FREE)")
            self.embedding_model = RAGEngine._embedding_model
        else:
            raise ValueError("Local embeddings must be enabled for free operation")
    
    async def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for query using FREE local model asynchronously
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector
        """
        try:
            import asyncio
            embedding = await asyncio.to_thread(
                self.embedding_model.encode, query, convert_to_numpy=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise
    
    async def query_with_rag(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Query using RAG pipeline with tenant-scoped retrieval
        
        Args:
            query: User query
            tenant_id: Tenant UUID for filtering
            top_k: Number of documents to retrieve
        
        Returns:
            Dictionary with response and retrieved documents
        """
        try:
            # Step 1: Generate query embedding using FREE local model asynchronously
            query_embedding = await self._generate_query_embedding(query)
            
            # Step 2: Retrieve relevant documents from pgvector (tenant-scoped)
            retrieved_docs = await self._retrieve_documents(
                query_embedding,
                tenant_id,
                top_k,
                query_text=query,
            )
            
            if not retrieved_docs:
                return {
                    "response": (
                        "Maaf, saya tidak menemukan data yang relevan untuk menjawab "
                        "pertanyaan Anda. Pastikan data sudah diinput ke sistem."
                    ),
                    "sources": [],
                    "retrieved_count": 0
                }
            
            # Step 3: Build context from retrieved documents
            context = self._build_context(retrieved_docs)
            
            # Step 4: Generate response using Groq with context
            response = await self._generate_response(
                query,
                context,
                conversation_history=conversation_history,
            )
            
            return {
                "response": response,
                "sources": [
                    {
                        "type": doc.get("document_type", "unknown"),
                        "content": doc.get("content", ""),
                        "metadata": doc.get("metadata") or {}
                    }
                    for doc in retrieved_docs
                ],
                "retrieved_count": len(retrieved_docs)
            }
        
        except Exception as e:
            logger.error(f"RAG query error: {str(e)}")
            raise Exception(f"Failed to process query: {str(e)}")
    
    async def _retrieve_documents(
        self,
        query_embedding: List[float],
        tenant_id: str,
        top_k: int,
        query_text: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using vector similarity (tenant-scoped)
        
        Args:
            query_embedding: Query vector
            tenant_id: Tenant UUID
            top_k: Number of results
        
        Returns:
            List of retrieved documents
        """
        try:
            from app.core.database import get_supabase_admin_client
            db = get_supabase_admin_client()
            
            # Use Supabase RPC for vector similarity search
            # This requires creating a custom function in Supabase
            # For now, we'll use a direct query approach
            
            # Query: Find similar documents filtered by tenant_id
            response = db.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': 0.7,
                    'match_count': top_k,
                    'filter_tenant_id': tenant_id
                }
            ).execute()

            docs = [doc for doc in (response.data or []) if isinstance(doc, dict)]

            # Measure coverage using unique docs, not raw row count.
            deduped_docs: List[Dict[str, Any]] = []
            seen_markers = set()
            for doc in docs:
                self._append_unique_doc(doc, deduped_docs, seen_markers)

            if len(deduped_docs) >= top_k:
                return deduped_docs[:top_k]

            # If vector search is sparse, enrich with embeddings/live-table fallbacks.
            return await self._fallback_retrieve(
                tenant_id=tenant_id,
                limit=top_k,
                query_text=query_text,
                existing_docs=deduped_docs,
            )
        
        except Exception as e:
            logger.warning(f"Vector search failed, using fallback: {str(e)}")
            return await self._fallback_retrieve(
                tenant_id=tenant_id,
                limit=top_k,
                query_text=query_text,
                existing_docs=[],
            )
    
    async def _fallback_retrieve(
        self,
        tenant_id: str,
        limit: int,
        query_text: str = "",
        existing_docs: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fallback retrieval without vector search
        Returns recent documents for tenant
        """
        try:
            from app.core.database import get_supabase_admin_client
            db = get_supabase_admin_client()

            effective_limit = max(1, int(limit or 1))
            merged_docs: List[Dict[str, Any]] = []
            seen_markers = set()

            for doc in existing_docs or []:
                self._append_unique_doc(doc, merged_docs, seen_markers)

            # Pull more from embedding store if vector result is sparse.
            embedding_limit = max(effective_limit * 4, 20)
            embeddings_response = db.table("document_embeddings").select(
                "document_type, content, metadata"
            ).eq("tenant_id", tenant_id).order(
                "created_at", desc=True
            ).limit(embedding_limit).execute()

            for doc in (embeddings_response.data or []):
                self._append_unique_doc(doc, merged_docs, seen_markers)
                if len(merged_docs) >= effective_limit:
                    return merged_docs[:effective_limit]

            normalized_query = (query_text or "").strip().lower()
            product_keywords = ("stok", "stock", "inventory", "produk", "product", "sku", "restock", "laptop")
            invoice_keywords = ("invoice", "faktur", "tagihan", "payment", "pembayaran", "piutang", "customer")
            unpaid_keywords = ("unpaid", "belum bayar", "belum dibayar", "overdue", "jatuh tempo")

            has_product_intent = any(keyword in normalized_query for keyword in product_keywords)
            has_invoice_intent = any(keyword in normalized_query for keyword in invoice_keywords)
            prioritize_unpaid = any(keyword in normalized_query for keyword in unpaid_keywords)

            # Secondary fallback: build context from live business tables so chat still works.
            live_limit = max(effective_limit * 3, 12)
            products_response = db.table("products").select(
                "id, sku, name, category, unit_price, stock_quantity, low_stock_threshold"
            ).eq("tenant_id", tenant_id).eq("is_active", True).order(
                "created_at", desc=True
            ).limit(live_limit).execute()

            invoice_query = db.table("invoices").select(
                "id, invoice_number, customer_name, total_amount, payment_status, issue_date, due_date"
            ).eq("tenant_id", tenant_id)

            if prioritize_unpaid:
                invoice_query = invoice_query.in_("payment_status", ["unpaid", "partial", "overdue"])

            invoices_response = invoice_query.order(
                "created_at", desc=True
            ).limit(live_limit).execute()

            live_product_docs = [
                self._build_live_product_doc(product) for product in (products_response.data or [])
            ]
            live_invoice_docs = [
                self._build_live_invoice_doc(invoice) for invoice in (invoices_response.data or [])
            ]
            product_summary_doc = self._build_live_product_summary_doc(products_response.data or [])
            invoice_summary_doc = self._build_live_invoice_summary_doc(invoices_response.data or [])

            candidate_docs: List[Dict[str, Any]] = []
            if prioritize_unpaid or (has_invoice_intent and not has_product_intent):
                if invoice_summary_doc:
                    candidate_docs.append(invoice_summary_doc)
                candidate_docs.extend(live_invoice_docs)
                if product_summary_doc:
                    candidate_docs.append(product_summary_doc)
                candidate_docs.extend(live_product_docs)
            elif has_product_intent and not has_invoice_intent:
                if product_summary_doc:
                    candidate_docs.append(product_summary_doc)
                candidate_docs.extend(live_product_docs)
                if invoice_summary_doc:
                    candidate_docs.append(invoice_summary_doc)
                candidate_docs.extend(live_invoice_docs)
            else:
                if product_summary_doc:
                    candidate_docs.append(product_summary_doc)
                if invoice_summary_doc:
                    candidate_docs.append(invoice_summary_doc)
                max_length = max(len(live_product_docs), len(live_invoice_docs))
                for index in range(max_length):
                    if index < len(live_product_docs):
                        candidate_docs.append(live_product_docs[index])
                    if index < len(live_invoice_docs):
                        candidate_docs.append(live_invoice_docs[index])

            for doc in candidate_docs:
                self._append_unique_doc(doc, merged_docs, seen_markers)
                if len(merged_docs) >= effective_limit:
                    break

            return merged_docs[:effective_limit]
        
        except Exception as e:
            logger.error(f"Fallback retrieve error: {str(e)}")
            return (existing_docs or [])[: max(1, int(limit or 1))]

    def _build_live_product_summary_doc(self, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build aggregate summary doc from live product rows."""
        if not products:
            return None

        total_products = len(products)
        total_stock_units = 0
        in_stock_count = 0
        low_stock_count = 0

        for product in products:
            stock = int(product.get("stock_quantity") or 0)
            threshold = int(product.get("low_stock_threshold") or 0)

            total_stock_units += stock
            if stock > 0:
                in_stock_count += 1
            if stock <= threshold:
                low_stock_count += 1

        out_of_stock_count = total_products - in_stock_count
        content = (
            "Product Summary: "
            f"total_active_products={total_products}; "
            f"in_stock_products={in_stock_count}; "
            f"out_of_stock_products={out_of_stock_count}; "
            f"low_stock_products={low_stock_count}; "
            f"total_stock_units={total_stock_units}"
        )

        return {
            "document_type": "product_summary",
            "content": content,
            "metadata": {
                "source": "live_products_summary",
                "total_active_products": total_products,
                "in_stock_products": in_stock_count,
                "out_of_stock_products": out_of_stock_count,
                "low_stock_products": low_stock_count,
                "total_stock_units": total_stock_units,
            },
        }

    def _build_live_invoice_summary_doc(self, invoices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build aggregate summary doc from live invoice rows."""
        if not invoices:
            return None

        total_invoices = len(invoices)
        unpaid_statuses = {"unpaid", "partial", "overdue"}
        paid_count = 0
        unpaid_count = 0
        total_amount = 0.0

        for invoice in invoices:
            status = str(invoice.get("payment_status") or "").lower()
            amount = invoice.get("total_amount")

            if status in unpaid_statuses:
                unpaid_count += 1
            elif status == "paid":
                paid_count += 1

            try:
                total_amount += float(amount or 0)
            except (TypeError, ValueError):
                continue

        content = (
            "Invoice Summary: "
            f"total_invoices={total_invoices}; "
            f"unpaid_or_overdue_invoices={unpaid_count}; "
            f"paid_invoices={paid_count}; "
            f"total_invoice_amount={total_amount:.2f}"
        )

        return {
            "document_type": "invoice_summary",
            "content": content,
            "metadata": {
                "source": "live_invoices_summary",
                "total_invoices": total_invoices,
                "unpaid_or_overdue_invoices": unpaid_count,
                "paid_invoices": paid_count,
                "total_invoice_amount": round(total_amount, 2),
            },
        }

    def _build_live_product_doc(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Build normalized fallback document from product row."""
        stock = int(product.get("stock_quantity") or 0)
        threshold = int(product.get("low_stock_threshold") or 0)
        status = "LOW STOCK" if stock <= threshold else "IN STOCK"
        content = (
            f"Product: {product.get('name', 'N/A')} | "
            f"SKU: {product.get('sku', 'N/A')} | "
            f"Category: {product.get('category', 'Uncategorized')} | "
            f"Price: {product.get('unit_price', 0)} | "
            f"Stock: {stock} | "
            f"Status: {status}"
        )

        return {
            "document_type": "product",
            "content": content,
            "metadata": {
                "product_id": product.get("id"),
                "sku": product.get("sku"),
                "stock_quantity": stock,
                "low_stock_threshold": threshold,
                "source": "live_products",
            },
        }

    def _build_live_invoice_doc(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Build normalized fallback document from invoice row."""
        payment_status = str(invoice.get("payment_status") or "unknown")
        content = (
            f"Invoice: {invoice.get('invoice_number', 'N/A')} | "
            f"Customer: {invoice.get('customer_name', 'N/A')} | "
            f"Total: {invoice.get('total_amount', 0)} | "
            f"Status: {payment_status.upper()} | "
            f"Issue Date: {invoice.get('issue_date', 'N/A')} | "
            f"Due Date: {invoice.get('due_date', 'N/A')}"
        )

        return {
            "document_type": "invoice",
            "content": content,
            "metadata": {
                "invoice_id": invoice.get("id"),
                "invoice_number": invoice.get("invoice_number"),
                "customer_name": invoice.get("customer_name"),
                "payment_status": payment_status,
                "source": "live_invoices",
            },
        }

    def _extract_doc_marker(self, doc: Dict[str, Any]) -> Any:
        """Generate stable marker used for deduplicating retrieval documents."""
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        document_type = str(doc.get("document_type") or doc.get("type") or metadata.get("document_type") or "unknown")
        document_id = (
            metadata.get("product_id")
            or metadata.get("invoice_id")
            or metadata.get("document_id")
            or metadata.get("id")
            or ""
        )
        content_marker = str(doc.get("content") or "")[:200]
        return (document_type, str(document_id), content_marker)

    def _append_unique_doc(
        self,
        doc: Dict[str, Any],
        merged_docs: List[Dict[str, Any]],
        seen_markers: set,
    ) -> bool:
        """Append a document if not seen yet; return True when appended."""
        if not isinstance(doc, dict):
            return False

        normalized_doc = dict(doc)
        normalized_doc["document_type"] = str(
            normalized_doc.get("document_type")
            or normalized_doc.get("type")
            or "unknown"
        )

        metadata = normalized_doc.get("metadata")
        if not isinstance(metadata, dict):
            normalized_doc["metadata"] = {}

        marker = self._extract_doc_marker(normalized_doc)
        if marker in seen_markers:
            return False

        seen_markers.add(marker)
        merged_docs.append(normalized_doc)
        return True
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved documents
        
        Args:
            documents: Retrieved documents
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            doc_type = doc.get('document_type', 'unknown')
            content = doc.get('content', '')
            context_parts.append(f"[Document {i} - {doc_type.upper()}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate response using Groq with retrieved context
        
        Args:
            query: User query
            context: Retrieved context
        
        Returns:
            Generated response
        """
        try:
            # Build prompt with context
            user_prompt = get_context_prompt(query, context)
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]

            messages.extend(self._prepare_history_messages(conversation_history))
            messages.append({"role": "user", "content": user_prompt})
            
            response = await self.groq_client.chat_completion_async(messages)
            return response
        
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            raise

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
