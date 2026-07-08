# chromadb_client.py
import chromadb
from chromadb.config import Settings
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Global variables — not connected at import time
_chroma_client = None
_log_collection = None


def get_chroma_client():
    """
    Lazy connection to ChromaDB
    Only connects when first called
    Retries if ChromaDB not ready yet
    """
    global _chroma_client

    if _chroma_client is not None:
        return _chroma_client

    # Retry logic — ChromaDB might need time to start
    max_retries = 5
    for attempt in range(max_retries):
        try:
            _chroma_client = chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST", "chromadb"),
                port=8000,  # internal Docker network port
                settings=Settings(anonymized_telemetry=False)
            )
            # Test connection
            _chroma_client.heartbeat()
            print("✅ Connected to ChromaDB successfully!")
            return _chroma_client

        except Exception as e:
            print(f"⚠️ ChromaDB not ready (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)  # wait 3 seconds before retry

    raise Exception("❌ Could not connect to ChromaDB after multiple attempts")


def get_log_collection():
    """
    Gets or creates the logs collection
    Lazy — only runs when first called
    """
    global _log_collection

    if _log_collection is not None:
        return _log_collection

    client = get_chroma_client()
    _log_collection = client.get_or_create_collection(
        name="teleguard_logs",
        metadata={"hnsw:space": "cosine"}
    )
    print("✅ ChromaDB collection 'teleguard_logs' ready")
    return _log_collection