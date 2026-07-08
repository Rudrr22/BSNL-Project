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

    try:
        # Use PersistentClient to run ChromaDB inside the same Python process!
        # This completely removes the need for a separate Docker container.
        _chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        print("✅ Connected to ChromaDB successfully!")
        return _chroma_client

    except Exception as e:
        print(f"⚠️ ChromaDB initialization failed: {e}")
        raise Exception("❌ Could not initialize local ChromaDB")


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