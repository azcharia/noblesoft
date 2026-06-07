"""
AI Chat API Endpoints
Conversational AI interface (Pro/Enterprise only)
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import io

from app.core.dependencies import require_add_on, require_tier, CurrentUser, get_current_user
from app.core.database import get_supabase_admin_client
from app.ai.embeddings import EmbeddingService
from app.services.ai_agent_service import AIAgentService
from app.ai.groq_client import GroqLLMClient

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


class TranscriptionResponse(BaseModel):
    """Voice transcription response schema"""
    text: str = Field(..., description="Transcribed text from audio")
    language: str = Field(default="id", description="Detected or requested language")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")


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


@router.post(
    "/transcribe/",
    response_model=TranscriptionResponse,
    summary="Transcribe voice to text",
    description="Convert Indonesian voice notes to text using Groq Whisper"
)
async def transcribe_voice(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Convert recorded audio (.webm, .wav, .mp3, etc.) into text.
    Optimized for Indonesian language and business context.
    
    **Requires Pro or Enterprise subscription.**
    """
    # Validate file type (basic)
    allowed_types = ["audio/webm", "audio/wav", "audio/mpeg", "audio/ogg", "audio/mp4", "application/octet-stream"]
    if file.content_type not in allowed_types:
        # We also check application/octet-stream because some browsers send webm as blob
        pass

    try:
        # Read file into memory
        audio_data = await file.read()
        audio_file = io.BytesIO(audio_data)
        audio_file.name = file.filename or "recording.webm" # Groq needs a filename extension

        service = AIAgentService()
        tenant_groq = await service._resolve_tenant_groq_client(current_user.tenant_id)
        groq_client = tenant_groq or GroqLLMClient()
        
        # Add context prompt for better UMKM Indonesian transcription
        prompt = (
            "Ini adalah percakapan kasir UMKM di Indonesia. "
            "Konteks: penjualan barang, stok inventory, harga, invoice, dan nama pelanggan. "
            "Contoh istilah: lusin, kodi, pcs, bks, karton, eceran."
        )

        transcribed_text = await groq_client.transcribe_audio_async(
            audio_file=audio_file,
            language="id",
            prompt=prompt
        )

        return TranscriptionResponse(
            text=transcribed_text,
            language="id"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal melakukan transkripsi suara: {str(e)}"
        )


@router.get(
    "/suggestions/",
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


class ConfirmActionRequest(BaseModel):
    function: str
    parameters: Dict[str, Any]


@router.post(
    "/confirm",
    response_model=ChatResponse,
    summary="Confirm and execute AI action",
    description="Execute a pending transaction that has been confirmed by the user"
)
async def confirm_action(
    request: ConfirmActionRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Execute an AI-generated action that requires human confirmation.
    """
    service = AIAgentService()
    try:
        function_call = {
            "function": request.function,
            "parameters": request.parameters
        }
        
        execution_result = await service._execute_function(
            function_call,
            current_user
        )
        
        user_context = {
            "tenant_id": current_user.tenant_id,
            "company_name": current_user.company_name,
            "subscription_tier": current_user.subscription_tier
        }
        
        return ChatResponse(
            response=execution_result["message"],
            sources=[],
            retrieved_count=0,
            user_context=user_context,
            assistant_mode="function_calling",
            orchestration_mode="single",
            execution_result=execution_result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menjalankan aksi yang dikonfirmasi: {str(e)}"
        )
