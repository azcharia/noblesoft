"""
AI Chat API Endpoints
Conversational AI interface (Pro/Enterprise only)
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.core.dependencies import require_add_on, require_tier, CurrentUser, get_current_user
from app.core.database import get_supabase_admin_client
from app.ai.embeddings import EmbeddingService
from app.services.ai_agent_service import AIAgentService

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message request schema"""
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Optional conversation history for context"
    )


class ChatResponse(BaseModel):
    """Chat response schema"""
    response: str = Field(..., description="AI's response")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved source documents"
    )
    retrieved_count: int = Field(default=0, description="Number of documents retrieved")
    user_context: Optional[Dict[str, Any]] = Field(
        None,
        description="User context information"
    )
    assistant_mode: str = Field(
        default="rag",
        description="Assistant mode used (rag, tavily, rag_fallback, etc.)",
    )
    orchestration_mode: str = Field(
        default="single",
        description="Execution strategy used (single, hybrid_parallel, etc.)",
    )
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tool usage metadata for web retrieval mode",
    )
    manager_result_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional manager worker execution summary",
    )
    auditor_result_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional auditor worker execution summary",
    )
    reconciliation_notes: Optional[str] = Field(
        None,
        description="Optional notes about hybrid reconciliation or fallback",
    )
    error: Optional[str] = Field(None, description="Error message if any")
    function_executed: Optional[str] = Field(None, description="Function name executed")
    execution_result: Optional[Dict[str, Any]] = Field(None, description="Execution result")


class SuggestedQuestionsResponse(BaseModel):
    """Suggested questions response"""
    suggestions: List[str] = Field(..., description="List of suggested questions")


def _build_coverage_response(tenant_id: str) -> Dict[str, Any]:
    """Compute indexing coverage for chat retrieval data."""
    db = get_supabase_admin_client()

    total_products = (
        db.table("products").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute().count
        or 0
    )
    total_invoices = (
        db.table("invoices").select("id", count="exact").eq("tenant_id", tenant_id).execute().count
        or 0
    )

    indexed_products = (
        db.table("document_embeddings").select("id", count="exact").eq("tenant_id", tenant_id).eq("document_type", "product").execute().count
        or 0
    )
    indexed_invoices = (
        db.table("document_embeddings").select("id", count="exact").eq("tenant_id", tenant_id).eq("document_type", "invoice").execute().count
        or 0
    )

    def to_percent(indexed: int, total: int) -> float:
        if total <= 0:
            return 100.0
        return round((indexed / total) * 100, 2)

    return {
        "tenant_id": tenant_id,
        "products": {
            "total": total_products,
            "indexed": indexed_products,
            "coverage_percent": to_percent(indexed_products, total_products),
        },
        "invoices": {
            "total": total_invoices,
            "indexed": indexed_invoices,
            "coverage_percent": to_percent(indexed_invoices, total_invoices),
        },
        "recommendation": (
            "Run POST /api/v1/chat/reindex when coverage is below 100% "
            "or when seeded SQL data was inserted outside API flows."
        ),
    }


@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send a message to AI assistant",
    description="Chat with NobleSoft AI Assistant (Pro/Enterprise only)"
)
async def chat(
    chat_message: ChatMessage,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Send a message to the AI assistant and get a response.
    
    The AI will:
    - Retrieve relevant data from your company's inventory and invoices
    - Generate accurate, data-driven responses
    - Never hallucinate or make up information
    
    **Requires Pro or Enterprise subscription.**
    
    Example questions:
    - "Berapa stok laptop yang tersedia?"
    - "Tampilkan invoice yang belum dibayar"
    - "Produk apa saja yang stoknya rendah?"
    - "Siapa customer dengan invoice terbesar?"
    """
    service = AIAgentService()
    
    try:
        result = await service.process_chat_message(
            query=chat_message.message,
            current_user=current_user,
            conversation_history=chat_message.conversation_history
        )
        
        return ChatResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.get(
    "/suggestions",
    response_model=SuggestedQuestionsResponse,
    summary="Get suggested questions",
    description="Get AI-generated suggested questions based on your data"
)
async def get_suggestions(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get suggested questions you can ask the AI assistant.
    
    Suggestions are tailored to your company's data and common use cases.
    
    **Requires Pro or Enterprise subscription.**
    """
    service = AIAgentService()
    
    try:
        suggestions = await service.get_suggested_questions(current_user)
        return SuggestedQuestionsResponse(suggestions=suggestions)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get(
    "/index-coverage",
    summary="Get chat index coverage",
    description="Check product/invoice embedding coverage used by chat retrieval"
)
async def get_index_coverage(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get embedding coverage diagnostics for current tenant."""
    try:
        return _build_coverage_response(current_user.tenant_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute index coverage: {str(e)}"
        )


@router.post(
    "/reindex",
    summary="Rebuild chat embeddings",
    description="Rebuild all product/invoice embeddings for current tenant"
)
async def reindex_chat_documents(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Rebuild tenant embeddings to recover from stale or partial index state."""
    try:
        embedding_service = EmbeddingService()
        rebuild_result = await embedding_service.rebuild_tenant_embeddings(current_user)
        coverage = _build_coverage_response(current_user.tenant_id)

        return {
            "status": "ok",
            "reindexed_at": datetime.utcnow().isoformat() + "Z",
            **rebuild_result,
            "coverage": coverage,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild chat embeddings: {str(e)}"
        )


@router.post(
    "/function-call",
    response_model=ChatResponse,
    summary="Chat with function calling (EXPERIMENTAL)",
    description="Advanced chat that can execute actions",
)
async def chat_with_function_calling(
    chat_message: ChatMessage,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **EXPERIMENTAL FEATURE - Enterprise Only**
    
    Advanced chat interface that allows the AI to execute actions:
    - Create products
    - Update stock
    - Create invoices
    - And more...
    
    Example requests:
    - "Buatkan produk baru: Laptop HP, harga 12 juta, stok 10"
    - "Kurangi stok laptop Dell sebanyak 5 unit"
    - "Buatkan invoice untuk PT Maju Jaya"
    
    The AI will:
    1. Understand your intent
    2. Extract required parameters
    3. Execute the appropriate function
    4. Confirm the action
    
    **Requires Enterprise subscription and AI Agent Pack add-on.**
    """
    service = AIAgentService()
    
    try:
        result = await service.process_with_function_calling(
            query=chat_message.message,
            current_user=current_user,
            conversation_history=chat_message.conversation_history,
        )
        
        return ChatResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process function call: {str(e)}"
        )
