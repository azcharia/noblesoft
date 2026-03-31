"""
Pydantic Models for AI Chat Module
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ChatMessageRequest(BaseModel):
    """Request schema for chat message"""
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_history: Optional[List[Dict[str, str]]] = None


class SourceDocument(BaseModel):
    """Retrieved source document"""
    type: str = Field(..., description="Document type (product, invoice, etc.)")
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    """Response schema for chat message"""
    response: str = Field(..., description="AI's response")
    sources: List[SourceDocument] = Field(default_factory=list)
    retrieved_count: int = Field(default=0)
    user_context: Optional[Dict[str, Any]] = None
    assistant_mode: str = Field(default="rag")
    orchestration_mode: str = Field(default="single")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    manager_result_summary: Optional[Dict[str, Any]] = None
    auditor_result_summary: Optional[Dict[str, Any]] = None
    reconciliation_notes: Optional[str] = None
    error: Optional[str] = None


class ConversationHistory(BaseModel):
    """Conversation history entry"""
    role: str = Field(..., description="Role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
