from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import time
import uvicorn

from models.database import Base, engine
from models.models import LogEntry, Analysis, Anomaly
from routes.logs import router as logs_router
from routes.analyses import router as analyses_router
from routes.kpis import router as kpis_router

from rag.embeddings import embed_single_log
from routes.chat import router as chat_router


# Create all database tables on startup
# This creates the tables if they don't exist yet
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully")

# Track when the server started (for uptime calculation)
_start_time = time.time()

app = FastAPI(
    title="Teleguard",
    description="Intelligent Telecom Network Monitor",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # MUST be False if origins is "*" to satisfy browser CORS rules
    allow_methods=["*"],
    allow_headers=["*"],
    # Expose these headers so the browser can read them for file downloads
    expose_headers=["Content-Disposition", "Content-Length", "X-Total-Count"],
)

# ─── WebSocket Manager ─────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        # Clean up dead connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

# ─── Include Routers ───────────────────────────────────────
# This registers all routes from routes/ folder
app.include_router(logs_router)
app.include_router(analyses_router)
app.include_router(chat_router)
app.include_router(kpis_router)

# ─── Override ingest to also broadcast ────────────────────
@app.post("/api/logs/ingest")
async def ingest_log_and_broadcast(log: dict):
    from models.database import SessionLocal
    from models.models import LogEntry

    # Save to PostgreSQL
    db = SessionLocal()
    try:
        db_log = LogEntry(
            timestamp=log.get("timestamp", ""),
            severity=log.get("severity", "INFO"),
            component=log.get("component", "Unknown"),
            region=log.get("region"),
            event_type=log.get("event_type"),
            metric=log.get("metric"),
            value=float(log.get("value", 0)) if log.get("value") is not None else None,
            raw=log.get("raw", ""),
            source="live"
        )
        db.add(db_log)
        db.commit()
        print(f"📡 Received log: {log.get('raw', '')}")
    finally:
        db.close()

    # Save to ChromaDB for RAG
    try:
        embed_single_log(log)
    except Exception as e:
        print(f"⚠️ ChromaDB embed failed: {e}")

    # Broadcast to frontend via WebSocket
    await manager.broadcast(log)
    return {"status": "received"}

# ─── WebSocket ─────────────────────────────────────────────
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ─── Health Check (basic) ──────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Teleguard",
        "version": "2.0.0"
    }

# ─── Detailed Health Check ─────────────────────────────────
@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed system status — checks every subsystem.
    Used by the Status page and monitoring tools.
    """
    import os
    from models.database import SessionLocal

    uptime_seconds = int(time.time() - _start_time)
    results = {
        "service": "Teleguard",
        "version": "2.0.0",
        "uptime_seconds": uptime_seconds,
        "websocket_connections": len(manager.active_connections),
        "components": {}
    }

    # Check PostgreSQL
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        log_count = db.query(LogEntry).count()
        db.close()
        results["components"]["postgresql"] = {"status": "healthy", "log_count": log_count}
    except Exception as e:
        results["components"]["postgresql"] = {"status": "error", "error": str(e)}

    # Check ChromaDB
    try:
        from rag.chromadb_client import get_chroma_client
        client = get_chroma_client()
        collections = client.list_collections()
        chunk_count = 0
        for col in collections:
            chunk_count += col.count()
        results["components"]["chromadb"] = {"status": "healthy", "chunks_indexed": chunk_count}
    except Exception as e:
        results["components"]["chromadb"] = {"status": "error", "error": str(e)}

    # Check Groq API key
    groq_key = os.getenv("GROQ_API_KEY", "")
    results["components"]["groq_api"] = {
        "status": "configured" if groq_key and len(groq_key) > 10 else "missing",
        "key_hint": f"{groq_key[:8]}..." if groq_key else "NOT SET"
    }

    # Overall status
    component_statuses = [v.get("status") for v in results["components"].values()]
    results["overall"] = "healthy" if all(s == "healthy" or s == "configured" for s in component_statuses) else "degraded"

    return results

@app.get("/")
async def root():
    return {"message": "Welcome to Teleguard 🛡️", "version": "2.0.0", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)