# rag_chain.py
# The complete RAG pipeline
# Connects ChromaDB retrieval with Groq LLM

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
from .embeddings import search_logs

load_dotenv()

# Initialize Groq LLM
# temperature=0 means deterministic answers (no creativity)
# Perfect for factual log analysis
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=1000
)

print("✅ Groq LLM initialized for RAG")

# System prompt — tells LLM how to behave
SYSTEM_PROMPT = """You are Teleguard, an expert network analyst 
for BSNL (Bharat Sanchar Nigam Limited) telecom network.

You analyze network logs and answer questions about:
- Network anomalies and failures
- Tower performance (BTS stations)
- Router issues
- Signal quality (RSSI values)
- Network regions and coverage

RULES:
1. Only answer based on the provided log context
2. If information isn't in the logs, say so clearly
3. Be specific — mention tower names, values, timestamps
4. Give actionable insights when possible
5. Keep answers concise but complete

You are analyzing REAL BSNL network data. Be professional."""


def ask_rag(question: str, filter_severity: str = None) -> dict:
    """
    Main RAG function — answers questions about logs
    
    Flow:
    1. Search ChromaDB for relevant logs
    2. Format as context
    3. Send to Groq with system prompt
    4. Return answer + sources
    
    Args:
        question: User's question in plain English
        filter_severity: Optional — only search CRITICAL logs etc
    
    Returns:
        dict with answer and source logs used
    """

    # Step 1: Retrieve relevant logs from ChromaDB
    retrieved = search_logs(
        query=question,
        n_results=5,
        filter_severity=filter_severity
    )

    if not retrieved:
        return {
            "answer": "No log data found in the database yet. "
                     "Please wait for logs to be collected or upload a log file.",
            "sources": [],
            "context_used": 0
        }

    # Step 2: Format retrieved logs as context string
    context = "\n\n".join([
        f"[Relevance: {r['relevance_score']}] "
        f"[Severity: {r['metadata'].get('severity', 'Unknown')}] "
        f"[Tower: {r['metadata'].get('component', 'Unknown')}]\n"
        f"{r['text']}"
        for r in retrieved
    ])

    # Step 3: Build the prompt
    prompt = f"""Based on these BSNL network logs:

═══════════════════════════════════
NETWORK LOG CONTEXT:
═══════════════════════════════════
{context}
═══════════════════════════════════

QUESTION: {question}

Please analyze the logs above and answer the question.
Be specific with tower names, values, and timestamps from the logs."""

    # Step 4: Send to Groq LLM
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    answer = response.content

    # Step 5: Return answer with metadata
    return {
        "answer": answer,
        "sources": retrieved,
        "context_used": len(retrieved)
    }


def analyze_anomalies_with_rag(logs: list) -> dict:
    """
    Uses RAG to analyze a batch of logs for anomalies
    Called after file upload
    
    Different from ask_rag — this proactively analyzes
    instead of answering a specific question
    """

    # Format logs as text
    log_text = "\n".join([
        log.get("raw", str(log)) for log in logs[:50]  # first 50 logs
    ])

    prompt = f"""Analyze these BSNL network logs and provide:

1. ANOMALIES DETECTED: List each anomaly with severity
2. MOST AFFECTED TOWERS: Which towers have most issues
3. ROOT CAUSES: What's likely causing the problems
4. RECOMMENDATIONS: What actions should engineers take

LOGS TO ANALYZE:
{log_text}

Provide a structured analysis."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)

    return {
        "analysis": response.content,
        "logs_analyzed": len(logs)
    }