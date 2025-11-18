from __future__ import annotations
import os
import uuid
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions

from backend.embeddings import embed_texts, embed_text

CHROMA_DIR = os.path.join("data", "chroma")
COLLECTION_NAME = "kb"

os.makedirs(CHROMA_DIR, exist_ok=True)

_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    if _collection is None:
        # Use "None" embedding func; we supply embeddings manually
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def add_documents(docs: List[Dict[str, Any]]) -> int:
    """
    docs: list of {text: str, metadata: dict}
    Returns number of chunks added
    """
    col = get_collection()
    texts = [d["text"] for d in docs]
    metas = [d.get("metadata", {}) for d in docs]
    ids = [str(uuid.uuid4()) for _ in docs]
    embeddings = embed_texts(texts)
    col.add(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings)
    return len(docs)


def query(query: str, k: int = 6) -> List[Dict[str, Any]]:
    col = get_collection()
    q_emb = embed_text(query)
    res = col.query(query_embeddings=[q_emb], n_results=k)
    items = []
    if res and res.get("documents"):
        for i in range(len(res["documents"][0])):
            items.append(
                {
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "id": res["ids"][0][i],
                    "distance": res.get("distances", [[None]])[0][i],
                }
            )
    return items
