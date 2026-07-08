# chat.py — RAG chatbot API endpoint

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models.database import get_db
from rag.rag_chain import ask_rag
from rag.embeddings import get_collection_stats

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Request schema
class ChatRequest(BaseModel):
    question: str
    filter_severity: Optional[str] = None  # optional: CRITICAL/WARNING/INFO

# Response schema
class ChatResponse(BaseModel):
    answer: str
    context_used: int
    sources: list

@router.post("", response_model=ChatResponse)
async def chat_with_logs(request: ChatRequest):
    """
    RAG-powered chat endpoint
    
    User sends question → 
    ChromaDB retrieves relevant logs →
    Groq answers based on actual data →
    Returns answer + sources used
    
    Example request:
    {
        "question": "Which tower had most failures today?",
        "filter_severity": "CRITICAL"
    }
    """
    print(f"💬 Chat question: {request.question}")

    result = ask_rag(
        question=request.question,
        filter_severity=request.filter_severity
    )

    print(f"🤖 Answer generated: {result['answer'][:100]}...")

    return ChatResponse(
        answer=result["answer"],
        context_used=result["context_used"],
        sources=result["sources"]
    )

@router.get("/stats")
async def get_rag_stats():
    """
    Returns how many log chunks are in ChromaDB
    Useful for debugging and dashboard display
    """
    stats = get_collection_stats()
    return {
        "chromadb_chunks": stats["total_chunks"],
        "status": "ready" if stats["total_chunks"] > 0 else "empty"
    }