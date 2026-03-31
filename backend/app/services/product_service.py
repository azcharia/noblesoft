"""
Product Service Layer
Encapsulates business logic and database operations for products
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import logging

from supabase import Client
from app.core.dependencies import CurrentUser
from app.core.database import get_supabase_admin_client
from app.ai.embeddings import EmbeddingService
from app.models.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    StockAdjustment
)

logger = logging.getLogger(__name__)


class ProductService:
    """Service class for product operations"""
    
    def __init__(self, db: Client = None):
        """Initialize service with database client"""
        # Backend services run server-side and enforce tenant scoping in query filters.
        # Use admin client to avoid RLS failures when writing through API endpoints.
        self.db = db or get_supabase_admin_client()

        # Lazy initialize because model loading is expensive and not needed for read-only paths.
        self._embedding_service: Optional[EmbeddingService] = None

    def _get_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    async def _sync_product_embedding(self, product: Dict[str, Any], tenant_id: str) -> None:
        """Best-effort embedding sync so CRUD does not fail when embeddings fail."""
        try:
            await self._get_embedding_service().upsert_product_embedding(product, tenant_id)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "Failed to sync product embedding for %s (tenant=%s): %s",
                product.get("id"),
                tenant_id,
                exc,
                exc_info=True,
            )

    async def _remove_product_embedding(self, product_id: str, tenant_id: str) -> None:
        """Best-effort embedding cleanup on delete/deactivate."""
        try:
            await self._get_embedding_service().delete_embeddings_for_document(product_id, tenant_id)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "Failed to remove product embedding for %s (tenant=%s): %s",
                product_id,
                tenant_id,
                exc,
                exc_info=True,
            )
    
    def _enrich_product_response(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich product data with computed fields
        
        Args:
            product: Raw product data from database
        
        Returns:
            Enriched product data
        """
        # Check if stock is low
        product['is_low_stock'] = (
            product.get('stock_quantity', 0) <= product.get('low_stock_threshold', 0)
        )
        return product

    def _to_json_compatible(self, value: Any) -> Any:
        """Convert Decimal values recursively for Supabase JSON serialization."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, dict):
            return {k: self._to_json_compatible(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._to_json_compatible(item) for item in value]
        return value
    
    async def create_product(
        self,
        product_data: ProductCreate,
        current_user: CurrentUser
    ) -> ProductResponse:
        """
        Create a new product
        
        Args:
            product_data: Product creation data
            current_user: Current authenticated user
        
        Returns:
            Created product
        
        Raises:
            Exception: If creation fails or SKU already exists
        """
        try:
            # Check if SKU already exists for this tenant
            existing = self.db.table("products").select("id").eq(
                "tenant_id", current_user.tenant_id
            ).eq("sku", product_data.sku).execute()
            
            if existing.data:
                raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
            
            # Prepare product data
            product_dict = self._to_json_compatible(product_data.model_dump())
            product_dict['tenant_id'] = current_user.tenant_id
            product_dict['created_by'] = current_user.id
            
            # Insert product
            response = self.db.table("products").insert(product_dict).execute()
            
            if not response.data:
                raise Exception("Failed to create product")
            
            product = response.data[0]
            enriched = self._enrich_product_response(product)
            await self._sync_product_embedding(enriched, current_user.tenant_id)
            
            logger.info(
                f"Product created: {product['id']} by user {current_user.id} "
                f"in tenant {current_user.tenant_id}"
            )
            
            return ProductResponse(**enriched)
        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            raise Exception(f"Failed to create product: {str(e)}")
    
    async def get_product(
        self,
        product_id: str,
        current_user: CurrentUser
    ) -> Optional[ProductResponse]:
        """
        Get a single product by ID
        
        Args:
            product_id: Product UUID
            current_user: Current authenticated user
        
        Returns:
            Product if found, None otherwise
        """
        try:
            response = self.db.table("products").select("*").eq(
                "id", product_id
            ).eq(
                "tenant_id", current_user.tenant_id  # Extra tenant check
            ).single().execute()
            
            if not response.data:
                return None
            
            enriched = self._enrich_product_response(response.data)
            return ProductResponse(**enriched)
        
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None
    
    async def list_products(
        self,
        current_user: CurrentUser,
        page: int = 1,
        page_size: int = 50,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        low_stock_only: bool = False
    ) -> Dict[str, Any]:
        """
        List products with pagination and filters
        
        Args:
            current_user: Current authenticated user
            page: Page number (1-indexed)
            page_size: Items per page
            category: Filter by category
            is_active: Filter by active status
            search: Search in name, SKU, or description
            low_stock_only: Show only low stock items
        
        Returns:
            Dictionary with products list and pagination info
        """
        try:
            # Build query
            query = self.db.table("products").select(
                "*", count="exact"
            ).eq("tenant_id", current_user.tenant_id)
            
            # Apply filters
            if category:
                query = query.eq("category", category)
            
            if is_active is not None:
                query = query.eq("is_active", is_active)
            
            if search:
                # Search in name, SKU, or description
                query = query.or_(
                    f"name.ilike.%{search}%,"
                    f"sku.ilike.%{search}%,"
                    f"description.ilike.%{search}%"
                )
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Execute query with pagination
            response = query.order(
                "created_at", desc=True
            ).range(offset, offset + page_size - 1).execute()
            
            products = response.data or []
            total = response.count or 0
            
            # Enrich products and filter low stock if needed
            enriched_products = [
                self._enrich_product_response(p) for p in products
            ]
            
            if low_stock_only:
                enriched_products = [
                    p for p in enriched_products if p['is_low_stock']
                ]
                total = len(enriched_products)
            
            return {
                "products": [ProductResponse(**p) for p in enriched_products],
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": (offset + page_size) < total
            }
        
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            raise Exception(f"Failed to list products: {str(e)}")
    
    async def update_product(
        self,
        product_id: str,
        product_data: ProductUpdate,
        current_user: CurrentUser
    ) -> Optional[ProductResponse]:
        """
        Update an existing product
        
        Args:
            product_id: Product UUID
            product_data: Product update data
            current_user: Current authenticated user
        
        Returns:
            Updated product if found, None otherwise
        """
        try:
            # Check if product exists and belongs to tenant
            existing = await self.get_product(product_id, current_user)
            if not existing:
                return None
            
            # Prepare update data (exclude None values)
            update_dict = self._to_json_compatible(product_data.model_dump(exclude_none=True))
            
            if not update_dict:
                return existing  # No changes
            
            # Check SKU uniqueness if SKU is being updated
            if 'sku' in update_dict and update_dict['sku'] != existing.sku:
                sku_check = self.db.table("products").select("id").eq(
                    "tenant_id", current_user.tenant_id
                ).eq("sku", update_dict['sku']).execute()
                
                if sku_check.data:
                    raise ValueError(f"Product with SKU '{update_dict['sku']}' already exists")
            
            # Update product
            response = self.db.table("products").update(update_dict).eq(
                "id", product_id
            ).eq(
                "tenant_id", current_user.tenant_id  # Extra tenant check
            ).execute()
            
            if not response.data:
                return None
            
            enriched = self._enrich_product_response(response.data[0])
            await self._sync_product_embedding(enriched, current_user.tenant_id)
            
            logger.info(
                f"Product updated: {product_id} by user {current_user.id}"
            )
            
            return ProductResponse(**enriched)
        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise Exception(f"Failed to update product: {str(e)}")
    
    async def delete_product(
        self,
        product_id: str,
        current_user: CurrentUser
    ) -> bool:
        """
        Delete a product (soft delete by setting is_active=False)
        
        Args:
            product_id: Product UUID
            current_user: Current authenticated user
        
        Returns:
            True if deleted, False if not found
        """
        try:
            # Soft delete: set is_active to False
            response = self.db.table("products").update({
                "is_active": False
            }).eq("id", product_id).eq(
                "tenant_id", current_user.tenant_id  # Extra tenant check
            ).execute()
            
            if not response.data:
                return False

            await self._remove_product_embedding(product_id, current_user.tenant_id)
            
            logger.info(
                f"Product soft-deleted: {product_id} by user {current_user.id}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            raise Exception(f"Failed to delete product: {str(e)}")
    
    async def adjust_stock(
        self,
        product_id: str,
        adjustment: StockAdjustment,
        current_user: CurrentUser
    ) -> Optional[ProductResponse]:
        """
        Adjust product stock quantity
        
        Args:
            product_id: Product UUID
            adjustment: Stock adjustment data
            current_user: Current authenticated user
        
        Returns:
            Updated product if found, None otherwise
        """
        try:
            # Get current product
            product = await self.get_product(product_id, current_user)
            if not product:
                return None
            
            # Calculate new stock
            new_stock = product.stock_quantity + adjustment.adjustment
            
            if new_stock < 0:
                raise ValueError(
                    f"Insufficient stock. Current: {product.stock_quantity}, "
                    f"Adjustment: {adjustment.adjustment}"
                )
            
            # Update stock
            response = self.db.table("products").update({
                "stock_quantity": new_stock
            }).eq("id", product_id).eq(
                "tenant_id", current_user.tenant_id
            ).execute()
            
            if not response.data:
                return None
            
            enriched = self._enrich_product_response(response.data[0])
            await self._sync_product_embedding(enriched, current_user.tenant_id)
            
            logger.info(
                f"Stock adjusted for product {product_id}: {adjustment.adjustment} "
                f"(reason: {adjustment.reason or 'N/A'})"
            )
            
            return ProductResponse(**enriched)
        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error adjusting stock for product {product_id}: {str(e)}")
            raise Exception(f"Failed to adjust stock: {str(e)}")
