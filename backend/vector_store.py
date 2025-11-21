from __future__ import annotations
import os
import uuid
import json
import re
from typing import List, Dict, Any

DATA_DIR = os.path.join("data")
STORE_PATH = os.path.join(DATA_DIR, "kb_store.json")

os.makedirs(DATA_DIR, exist_ok=True)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _load_store() -> Dict[str, Any]:
    if os.path.exists(STORE_PATH):
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"docs": []}


def _save_store(store: Dict[str, Any]) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False)


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def add_documents(docs: List[Dict[str, Any]]) -> int:
    """Persist documents on disk and index them for simple lexical retrieval.

    Each doc is stored as {id, text, metadata}. Retrieval uses token overlap scoring.
    """
    store = _load_store()
    existing = store.get("docs", [])
    for d in docs:
        existing.append(
            {
                "id": str(uuid.uuid4()),
                "text": d.get("text", ""),
                "metadata": d.get("metadata", {}),
            }
        )
    store["docs"] = existing
    _save_store(store)
    return len(docs)


def query(query: str, k: int = 6) -> List[Dict[str, Any]]:
    """Return top-k docs ranked by simple token-overlap similarity.

    This is gonna avoid "what I don't like" dependencies (numpy, chromadb) while still providing
    deterministic, document-grounded retrieval suitable for small corpora as per the assignment.
    """
    store = _load_store()
    docs = store.get("docs", [])
    if not docs:
        return []

    q_tokens = set(_tokenize(query))
    scored = []
    for d in docs:
        text = d.get("text", "")
        t_tokens = set(_tokenize(text))
        if not t_tokens:
            continue
        overlap = len(q_tokens & t_tokens)
        if overlap == 0:
            continue
        score = overlap / max(1, len(q_tokens))
        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:k]
    results: List[Dict[str, Any]] = []
    for score, d in top:
        results.append(
            {
                "text": d.get("text", ""),
                "metadata": d.get("metadata", {}),
                "id": d.get("id"),
                # distance is 1 - similarity to keep shape compatible
                "distance": 1.0 - float(score),
            }
        )
    return results
