from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import uuid
from .chromadb_client import get_log_collection

print("⏳ Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded!")


def embed_logs(logs: List[Dict[str, Any]], chunk_size: int = 10):
    collection = get_log_collection()  # ← lazy connection
    if not logs:
        return 0

    chunks = []
    chunk_texts = []
    chunk_ids = []
    chunk_metadatas = []

    for i in range(0, len(logs), chunk_size):
        chunk = logs[i:i + chunk_size]
        chunk_text = "\n".join([log.get("raw", str(log)) for log in chunk])
        first_log = chunk[0]
        metadata = {
            "severity": first_log.get("severity", "INFO"),
            "component": first_log.get("component", "Unknown"),
            "region": first_log.get("region", "Unknown"),
            "source": first_log.get("source", "live"),
            "chunk_size": len(chunk)
        }
        chunks.append(chunk)
        chunk_texts.append(chunk_text)
        chunk_ids.append(str(uuid.uuid4()))
        chunk_metadatas.append(metadata)

    embeddings = embedding_model.encode(
        chunk_texts,
        show_progress_bar=False,
        convert_to_numpy=True
    ).tolist()

    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=chunk_texts,
        metadatas=chunk_metadatas
    )
    print(f"✅ Stored {len(chunks)} chunks in ChromaDB")
    return len(chunks)


def embed_single_log(log: Dict[str, Any]):
    collection = get_log_collection()  # ← lazy connection
    log_text = log.get("raw", str(log))
    embedding = embedding_model.encode(
        log_text,
        convert_to_numpy=True
    ).tolist()
    collection.add(
        ids=[str(uuid.uuid4())],
        embeddings=[embedding],
        documents=[log_text],
        metadatas=[{
            "severity": log.get("severity", "INFO"),
            "component": log.get("component", "Unknown"),
            "region": log.get("region", "Unknown"),
            "source": "live"
        }]
    )


def search_logs(query: str, n_results: int = 5, filter_severity: str = None):
    collection = get_log_collection()  # ← lazy connection
    query_embedding = embedding_model.encode(
        query,
        convert_to_numpy=True
    ).tolist()

    where_filter = None
    if filter_severity:
        where_filter = {"severity": filter_severity}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        retrieved.append({
            "text": doc,
            "metadata": meta,
            "relevance_score": round(1 - dist, 3)
        })
    return retrieved


def get_collection_stats():
    collection = get_log_collection()  # ← lazy connection
    count = collection.count()
    return {"total_chunks": count}