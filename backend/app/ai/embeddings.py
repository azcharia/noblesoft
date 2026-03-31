"""
Embedding Generation and Storage
Converts business data (products, invoices) into vector embeddings for RAG
100% FREE using local sentence-transformers model
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and storing document embeddings using FREE local model"""

    _model: Optional[SentenceTransformer] = None
    
    def __init__(self):
        """Initialize local sentence-transformers model (FREE)"""
        self.use_local = settings.USE_LOCAL_EMBEDDINGS
        
        if self.use_local:
            # Load FREE local model once and reuse it across requests
            if EmbeddingService._model is None:
                logger.info(f"Loading local embedding model: {settings.EMBEDDING_MODEL}")
                EmbeddingService._model = SentenceTransformer(settings.EMBEDDING_MODEL)
                logger.info("Local embedding model loaded successfully (100% FREE)")
            self.model = EmbeddingService._model
        
        self.db = get_supabase_admin_client()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using FREE local model
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (list of floats)
        """
        try:
            if self.use_local:
                # Use FREE local model
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding.tolist()
            else:
                raise ValueError("Local embeddings not enabled")
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def _product_to_text(self, product: Dict[str, Any]) -> str:
        """
        Convert product data to searchable text
        
        Args:
            product: Product dictionary
        
        Returns:
            Formatted text representation
        """
        text_parts = [
            f"Product: {product.get('name', 'Unknown')}",
            f"SKU: {product.get('sku', 'N/A')}",
            f"Category: {product.get('category', 'Uncategorized')}",
            f"Price: Rp {product.get('unit_price', 0):,.2f}",
            f"Stock: {product.get('stock_quantity', 0)} units",
        ]
        
        if product.get('description'):
            text_parts.append(f"Description: {product['description']}")
        
        # Add stock status
        if product.get('stock_quantity', 0) <= product.get('low_stock_threshold', 0):
            text_parts.append("Status: LOW STOCK - needs restocking")
        else:
            text_parts.append("Status: In stock")
        
        return " | ".join(text_parts)
    
    def _invoice_to_text(self, invoice: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
        """
        Convert invoice data to searchable text
        
        Args:
            invoice: Invoice dictionary
            items: List of invoice items
        
        Returns:
            Formatted text representation
        """
        text_parts = [
            f"Invoice: {invoice.get('invoice_number', 'Unknown')}",
            f"Customer: {invoice.get('customer_name', 'Unknown')}",
            f"Date: {invoice.get('issue_date', 'N/A')}",
            f"Total: Rp {invoice.get('total_amount', 0):,.2f}",
            f"Status: {invoice.get('payment_status', 'unknown').upper()}",
        ]
        
        # Add items summary
        if items:
            items_text = "Items: " + ", ".join([
                f"{item.get('description', 'Unknown')} (qty: {item.get('quantity', 0)})"
                for item in items
            ])
            text_parts.append(items_text)
        
        # Add due date if exists
        if invoice.get('due_date'):
            text_parts.append(f"Due: {invoice['due_date']}")
        
        # Add customer contact if exists
        if invoice.get('customer_email'):
            text_parts.append(f"Email: {invoice['customer_email']}")
        
        return " | ".join(text_parts)
    
    async def embed_product(
        self,
        product: Dict[str, Any],
        tenant_id: str
    ) -> Optional[str]:
        """
        Generate and store embedding for a product
        
        Args:
            product: Product data
            tenant_id: Tenant UUID
        
        Returns:
            Embedding ID if successful, None otherwise
        """
        try:
            # Convert product to text
            text = self._product_to_text(product)
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                "product_id": product.get('id'),
                "sku": product.get('sku'),
                "name": product.get('name'),
                "category": product.get('category'),
                "price": float(product.get('unit_price', 0)),
                "stock": product.get('stock_quantity', 0)
            }
            
            # Store in database
            response = self.db.table("document_embeddings").insert({
                "tenant_id": tenant_id,
                "document_type": "product",
                "document_id": product.get('id'),
                "content": text,
                "embedding": embedding,
                "metadata": metadata
            }).execute()
            
            if response.data:
                logger.info(f"Product embedded: {product.get('id')} for tenant {tenant_id}")
                return response.data[0]['id']
            
            return None
        
        except Exception as e:
            logger.error(f"Error embedding product: {str(e)}")
            return None
    
    async def embed_invoice(
        self,
        invoice: Dict[str, Any],
        items: List[Dict[str, Any]],
        tenant_id: str
    ) -> Optional[str]:
        """
        Generate and store embedding for an invoice
        
        Args:
            invoice: Invoice data
            items: Invoice items
            tenant_id: Tenant UUID
        
        Returns:
            Embedding ID if successful, None otherwise
        """
        try:
            # Convert invoice to text
            text = self._invoice_to_text(invoice, items)
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                "invoice_id": invoice.get('id'),
                "invoice_number": invoice.get('invoice_number'),
                "customer_name": invoice.get('customer_name'),
                "total_amount": float(invoice.get('total_amount', 0)),
                "payment_status": invoice.get('payment_status'),
                "issue_date": invoice.get('issue_date'),
                "due_date": invoice.get('due_date')
            }
            
            # Store in database
            response = self.db.table("document_embeddings").insert({
                "tenant_id": tenant_id,
                "document_type": "invoice",
                "document_id": invoice.get('id'),
                "content": text,
                "embedding": embedding,
                "metadata": metadata
            }).execute()
            
            if response.data:
                logger.info(f"Invoice embedded: {invoice.get('id')} for tenant {tenant_id}")
                return response.data[0]['id']
            
            return None
        
        except Exception as e:
            logger.error(f"Error embedding invoice: {str(e)}")
            return None
    
    async def embed_all_products(self, current_user: CurrentUser) -> int:
        """
        Embed all products for a tenant
        
        Args:
            current_user: Current user context
        
        Returns:
            Number of products embedded
        """
        try:
            # Fetch all products for tenant
            response = self.db.table("products").select("*").eq(
                "tenant_id", current_user.tenant_id
            ).eq("is_active", True).execute()
            
            products = response.data or []
            count = 0
            
            for product in products:
                result = await self.upsert_product_embedding(product, current_user.tenant_id)
                if result:
                    count += 1
            
            logger.info(f"Embedded {count} products for tenant {current_user.tenant_id}")
            return count
        
        except Exception as e:
            logger.error(f"Error embedding all products: {str(e)}")
            return 0
    
    async def embed_all_invoices(self, current_user: CurrentUser) -> int:
        """
        Embed all invoices for a tenant
        
        Args:
            current_user: Current user context
        
        Returns:
            Number of invoices embedded
        """
        try:
            # Fetch all invoices for tenant
            invoices_response = self.db.table("invoices").select("*").eq(
                "tenant_id", current_user.tenant_id
            ).execute()
            
            invoices = invoices_response.data or []
            count = 0
            
            for invoice in invoices:
                # Fetch items for this invoice
                items_response = self.db.table("invoice_items").select("*").eq(
                    "invoice_id", invoice['id']
                ).execute()
                
                items = items_response.data or []
                result = await self.upsert_invoice_embedding(invoice, items, current_user.tenant_id)
                if result:
                    count += 1
            
            logger.info(f"Embedded {count} invoices for tenant {current_user.tenant_id}")
            return count
        
        except Exception as e:
            logger.error(f"Error embedding all invoices: {str(e)}")
            return 0
    
    async def delete_embeddings_for_document(
        self,
        document_id: str,
        tenant_id: str
    ) -> bool:
        """
        Delete embeddings for a specific document
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
        
        Returns:
            True if successful
        """
        try:
            self.db.table("document_embeddings").delete().eq(
                "document_id", document_id
            ).eq("tenant_id", tenant_id).execute()
            
            logger.info(f"Deleted embeddings for document {document_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting embeddings: {str(e)}")
            return False

    async def upsert_product_embedding(
        self,
        product: Dict[str, Any],
        tenant_id: str,
    ) -> Optional[str]:
        """Replace existing product embedding with a fresh one."""
        product_id = product.get("id")
        if product_id:
            await self.delete_embeddings_for_document(str(product_id), tenant_id)
        return await self.embed_product(product, tenant_id)

    async def upsert_invoice_embedding(
        self,
        invoice: Dict[str, Any],
        items: List[Dict[str, Any]],
        tenant_id: str,
    ) -> Optional[str]:
        """Replace existing invoice embedding with a fresh one."""
        invoice_id = invoice.get("id")
        if invoice_id:
            await self.delete_embeddings_for_document(str(invoice_id), tenant_id)
        return await self.embed_invoice(invoice, items, tenant_id)

    async def rebuild_tenant_embeddings(self, current_user: CurrentUser) -> Dict[str, int]:
        """Rebuild all embeddings for one tenant by clearing stale vectors first."""
        tenant_id = current_user.tenant_id

        try:
            self.db.table("document_embeddings").delete().eq("tenant_id", tenant_id).execute()
        except Exception as e:
            logger.warning(f"Failed to clear embeddings for tenant {tenant_id}: {str(e)}")

        products_embedded = await self.embed_all_products(current_user)
        invoices_embedded = await self.embed_all_invoices(current_user)

        return {
            "products_embedded": products_embedded,
            "invoices_embedded": invoices_embedded,
            "total_embedded": products_embedded + invoices_embedded,
        }
