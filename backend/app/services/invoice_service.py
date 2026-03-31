"""
Invoice Service Layer
Encapsulates business logic and database operations for invoices
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import logging

from supabase import Client
from app.core.dependencies import CurrentUser
from app.core.database import get_supabase_admin_client
from app.ai.embeddings import EmbeddingService
from app.models.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceItemResponse,
    PaymentStatus,
    PaymentStatusUpdate
)

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service class for invoice operations"""
    
    def __init__(self, db: Client = None):
        """Initialize service with database client"""
        # Backend services run server-side and enforce tenant scoping in query filters.
        # Use admin client to avoid RLS failures when writing through API endpoints.
        self.db = db or get_supabase_admin_client()
        self._embedding_service: Optional[EmbeddingService] = None

    def _get_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    async def _remove_invoice_embedding(self, invoice_id: str, tenant_id: str) -> None:
        """Best-effort embedding cleanup for deleted invoices."""
        try:
            await self._get_embedding_service().delete_embeddings_for_document(invoice_id, tenant_id)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "Failed to remove invoice embedding for %s (tenant=%s): %s",
                invoice_id,
                tenant_id,
                exc,
                exc_info=True,
            )

    async def _sync_invoice_embedding(
        self,
        invoice: Dict[str, Any],
        tenant_id: str,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Best-effort embedding sync for invoice changes."""
        try:
            invoice_items = items
            if invoice_items is None:
                invoice_id = invoice.get("id")
                if invoice_id:
                    items_response = self.db.table("invoice_items").select("*").eq(
                        "invoice_id", invoice_id
                    ).execute()
                    invoice_items = items_response.data or []
                else:
                    invoice_items = []

            await self._get_embedding_service().upsert_invoice_embedding(
                invoice,
                invoice_items,
                tenant_id,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "Failed to sync invoice embedding for %s (tenant=%s): %s",
                invoice.get("id"),
                tenant_id,
                exc,
                exc_info=True,
            )
    
    def _calculate_totals(self, items: List[Dict[str, Any]], tax_amount: Decimal = Decimal("0.00")) -> Dict[str, Decimal]:
        """
        Calculate invoice totals from items
        
        Args:
            items: List of invoice items
            tax_amount: Tax amount
        
        Returns:
            Dictionary with subtotal, tax_amount, and total_amount
        """
        subtotal = sum(
            Decimal(str(item.get('quantity', 0))) * Decimal(str(item.get('unit_price', 0)))
            for item in items
        )
        total = subtotal + Decimal(str(tax_amount))
        
        return {
            "subtotal": round(subtotal, 2),
            "tax_amount": round(Decimal(str(tax_amount)), 2),
            "total_amount": round(total, 2)
        }

    def _to_json_compatible(self, value: Any) -> Any:
        """Convert Decimal values recursively for Supabase JSON serialization."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, dict):
            return {k: self._to_json_compatible(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._to_json_compatible(item) for item in value]
        return value
    
    def _enrich_invoice_response(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich invoice data with computed fields
        
        Args:
            invoice: Raw invoice data from database
        
        Returns:
            Enriched invoice data
        """
        # Check if overdue
        due_date = invoice.get('due_date')
        if due_date:
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date()
            
            today = date.today()
            invoice['is_overdue'] = (
                due_date < today and 
                invoice.get('payment_status') not in ['paid']
            )
            invoice['days_until_due'] = (due_date - today).days
        else:
            invoice['is_overdue'] = False
            invoice['days_until_due'] = None
        
        return invoice
    
    async def create_invoice(
        self,
        invoice_data: InvoiceCreate,
        current_user: CurrentUser
    ) -> InvoiceResponse:
        """
        Create a new invoice with items
        
        Args:
            invoice_data: Invoice creation data
            current_user: Current authenticated user
        
        Returns:
            Created invoice with items
        
        Raises:
            Exception: If creation fails or invoice number already exists
        """
        try:
            # Check if invoice number already exists for this tenant
            existing = self.db.table("invoices").select("id").eq(
                "tenant_id", current_user.tenant_id
            ).eq("invoice_number", invoice_data.invoice_number).execute()
            
            if existing.data:
                raise ValueError(
                    f"Invoice with number '{invoice_data.invoice_number}' already exists"
                )
            
            # Calculate totals
            items_data = self._to_json_compatible([item.model_dump() for item in invoice_data.items])
            totals = self._calculate_totals(items_data, invoice_data.tax_amount)
            
            # Prepare invoice data
            invoice_dict = self._to_json_compatible(invoice_data.model_dump(exclude={'items'}))
            invoice_dict.update(self._to_json_compatible(totals))
            invoice_dict['tenant_id'] = current_user.tenant_id
            invoice_dict['created_by'] = current_user.id
            invoice_dict['payment_status'] = PaymentStatus.UNPAID.value
            
            # Convert dates to strings
            if isinstance(invoice_dict.get('issue_date'), date):
                invoice_dict['issue_date'] = invoice_dict['issue_date'].isoformat()
            if isinstance(invoice_dict.get('due_date'), date):
                invoice_dict['due_date'] = invoice_dict['due_date'].isoformat()
            
            # Insert invoice
            invoice_response = self.db.table("invoices").insert(invoice_dict).execute()
            
            if not invoice_response.data:
                raise Exception("Failed to create invoice")
            
            invoice = invoice_response.data[0]
            invoice_id = invoice['id']
            
            # Insert invoice items
            invoice_items = []
            for item_data in items_data:
                # Calculate line total
                line_total = Decimal(str(item_data['quantity'])) * Decimal(str(item_data['unit_price']))
                item_data['line_total'] = float(round(line_total, 2))
                item_data['invoice_id'] = invoice_id
                invoice_items.append(item_data)
            
            items_response = self.db.table("invoice_items").insert(invoice_items).execute()
            
            if not items_response.data:
                # Rollback: delete invoice if items fail
                self.db.table("invoices").delete().eq("id", invoice_id).execute()
                raise Exception("Failed to create invoice items")
            
            # Fetch complete invoice with items
            invoice['items'] = items_response.data
            enriched = self._enrich_invoice_response(invoice)
            await self._sync_invoice_embedding(invoice, current_user.tenant_id, items_response.data)
            
            logger.info(
                f"Invoice created: {invoice_id} by user {current_user.id} "
                f"in tenant {current_user.tenant_id}"
            )
            
            return InvoiceResponse(**enriched)
        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            raise Exception(f"Failed to create invoice: {str(e)}")
    
    async def get_invoice(
        self,
        invoice_id: str,
        current_user: CurrentUser
    ) -> Optional[InvoiceResponse]:
        """
        Get a single invoice by ID with items
        
        Args:
            invoice_id: Invoice UUID
            current_user: Current authenticated user
        
        Returns:
            Invoice if found, None otherwise
        """
        try:
            # Fetch invoice
            invoice_response = self.db.table("invoices").select("*").eq(
                "id", invoice_id
            ).eq(
                "tenant_id", current_user.tenant_id  # Extra tenant check
            ).single().execute()
            
            if not invoice_response.data:
                return None
            
            invoice = invoice_response.data
            
            # Fetch invoice items
            items_response = self.db.table("invoice_items").select("*").eq(
                "invoice_id", invoice_id
            ).execute()
            
            invoice['items'] = items_response.data or []
            enriched = self._enrich_invoice_response(invoice)
            
            return InvoiceResponse(**enriched)
        
        except Exception as e:
            logger.error(f"Error fetching invoice {invoice_id}: {str(e)}")
            return None
    
    async def list_invoices(
        self,
        current_user: CurrentUser,
        page: int = 1,
        page_size: int = 50,
        payment_status: Optional[PaymentStatus] = None,
        customer_name: Optional[str] = None,
        overdue_only: bool = False
    ) -> Dict[str, Any]:
        """
        List invoices with pagination and filters
        
        Args:
            current_user: Current authenticated user
            page: Page number (1-indexed)
            page_size: Items per page
            payment_status: Filter by payment status
            customer_name: Filter by customer name (partial match)
            overdue_only: Show only overdue invoices
        
        Returns:
            Dictionary with invoices list and pagination info
        """
        try:
            # Build query
            query = self.db.table("invoices").select(
                "*", count="exact"
            ).eq("tenant_id", current_user.tenant_id)
            
            # Apply filters
            if payment_status:
                query = query.eq("payment_status", payment_status.value)
            
            if customer_name:
                query = query.ilike("customer_name", f"%{customer_name}%")
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Execute query with pagination
            response = query.order(
                "created_at", desc=True
            ).range(offset, offset + page_size - 1).execute()
            
            invoices = response.data or []
            total = response.count or 0
            
            # Fetch items for each invoice
            invoice_ids = [inv['id'] for inv in invoices]
            if invoice_ids:
                items_response = self.db.table("invoice_items").select("*").in_(
                    "invoice_id", invoice_ids
                ).execute()
                
                items_by_invoice = {}
                for item in items_response.data or []:
                    invoice_id = item['invoice_id']
                    if invoice_id not in items_by_invoice:
                        items_by_invoice[invoice_id] = []
                    items_by_invoice[invoice_id].append(item)
                
                # Attach items to invoices
                for invoice in invoices:
                    invoice['items'] = items_by_invoice.get(invoice['id'], [])
            
            # Enrich invoices
            enriched_invoices = [
                self._enrich_invoice_response(inv) for inv in invoices
            ]
            
            # Filter overdue if needed
            if overdue_only:
                enriched_invoices = [
                    inv for inv in enriched_invoices if inv.get('is_overdue', False)
                ]
                total = len(enriched_invoices)
            
            return {
                "invoices": [InvoiceResponse(**inv) for inv in enriched_invoices],
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": (offset + page_size) < total
            }
        
        except Exception as e:
            logger.error(f"Error listing invoices: {str(e)}")
            raise Exception(f"Failed to list invoices: {str(e)}")
    
    async def update_invoice(
        self,
        invoice_id: str,
        invoice_data: InvoiceUpdate,
        current_user: CurrentUser
    ) -> Optional[InvoiceResponse]:
        """
        Update an existing invoice
        
        Args:
            invoice_id: Invoice UUID
            invoice_data: Invoice update data
            current_user: Current authenticated user
        
        Returns:
            Updated invoice if found, None otherwise
        """
        try:
            # Check if invoice exists and belongs to tenant
            existing = await self.get_invoice(invoice_id, current_user)
            if not existing:
                return None
            
            # Prepare update data (exclude None values)
            update_dict = self._to_json_compatible(invoice_data.model_dump(exclude_none=True))
            
            if not update_dict:
                return existing  # No changes
            
            # Convert dates to strings
            if 'issue_date' in update_dict and isinstance(update_dict['issue_date'], date):
                update_dict['issue_date'] = update_dict['issue_date'].isoformat()
            if 'due_date' in update_dict and isinstance(update_dict['due_date'], date):
                update_dict['due_date'] = update_dict['due_date'].isoformat()
            
            # Convert enum to value
            if 'payment_status' in update_dict:
                update_dict['payment_status'] = update_dict['payment_status'].value
            
            # Check invoice number uniqueness if being updated
            if 'invoice_number' in update_dict and update_dict['invoice_number'] != existing.invoice_number:
                num_check = self.db.table("invoices").select("id").eq(
                    "tenant_id", current_user.tenant_id
                ).eq("invoice_number", update_dict['invoice_number']).execute()
                
                if num_check.data:
                    raise ValueError(
                        f"Invoice with number '{update_dict['invoice_number']}' already exists"
                    )
            
            # Update invoice
            response = self.db.table("invoices").update(update_dict).eq(
                "id", invoice_id
            ).eq(
                "tenant_id", current_user.tenant_id  # Extra tenant check
            ).execute()
            
            if not response.data:
                return None
            
            logger.info(
                f"Invoice updated: {invoice_id} by user {current_user.id}"
            )
            
            # Return updated invoice with items
            updated_invoice = await self.get_invoice(invoice_id, current_user)
            if updated_invoice:
                await self._sync_invoice_embedding(
                    updated_invoice.model_dump(),
                    current_user.tenant_id,
                    [item.model_dump() for item in updated_invoice.items],
                )
            return updated_invoice
        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating invoice {invoice_id}: {str(e)}")
            raise Exception(f"Failed to update invoice: {str(e)}")
    
    async def update_payment_status(
        self,
        invoice_id: str,
        status_update: PaymentStatusUpdate,
        current_user: CurrentUser
    ) -> Optional[InvoiceResponse]:
        """
        Update invoice payment status
        
        Args:
            invoice_id: Invoice UUID
            status_update: Payment status update data
            current_user: Current authenticated user
        
        Returns:
            Updated invoice if found, None otherwise
        """
        try:
            update_dict = {
                "payment_status": status_update.payment_status.value
            }
            
            if status_update.notes:
                update_dict["notes"] = status_update.notes
            
            response = self.db.table("invoices").update(update_dict).eq(
                "id", invoice_id
            ).eq(
                "tenant_id", current_user.tenant_id
            ).execute()
            
            if not response.data:
                return None
            
            logger.info(
                f"Invoice payment status updated: {invoice_id} -> {status_update.payment_status.value}"
            )
            
            updated_invoice = await self.get_invoice(invoice_id, current_user)
            if updated_invoice:
                await self._sync_invoice_embedding(
                    updated_invoice.model_dump(),
                    current_user.tenant_id,
                    [item.model_dump() for item in updated_invoice.items],
                )
            return updated_invoice
        
        except Exception as e:
            logger.error(f"Error updating payment status for invoice {invoice_id}: {str(e)}")
            raise Exception(f"Failed to update payment status: {str(e)}")
    
    async def delete_invoice(
        self,
        invoice_id: str,
        current_user: CurrentUser
    ) -> bool:
        """
        Delete an invoice and its items
        
        Args:
            invoice_id: Invoice UUID
            current_user: Current authenticated user
        
        Returns:
            True if deleted, False if not found
        """
        try:
            # Check if invoice exists
            existing = await self.get_invoice(invoice_id, current_user)
            if not existing:
                return False
            
            # Delete invoice items first (cascade should handle this, but explicit is better)
            self.db.table("invoice_items").delete().eq("invoice_id", invoice_id).execute()
            
            # Delete invoice
            response = self.db.table("invoices").delete().eq(
                "id", invoice_id
            ).eq(
                "tenant_id", current_user.tenant_id  # Extra tenant check
            ).execute()
            
            if not response.data:
                return False

            await self._remove_invoice_embedding(invoice_id, current_user.tenant_id)
            
            logger.info(
                f"Invoice deleted: {invoice_id} by user {current_user.id}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting invoice {invoice_id}: {str(e)}")
            raise Exception(f"Failed to delete invoice: {str(e)}")
