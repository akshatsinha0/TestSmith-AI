from __future__ import annotations
import os
from typing import List, Dict, Any

from backend.vector_store import add_documents, query as vs_query

DATA_DIR = os.path.join("data")
RUNTIME_HTML_PATH = os.path.join(DATA_DIR, "runtime_checkout.html")

os.makedirs(DATA_DIR, exist_ok=True)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def build_kb(texts_with_meta: List[Dict[str, Any]]) -> int:
    to_add = []
    for item in texts_with_meta:
        text = (item.get("text") or "").strip()
        meta = item.get("metadata") or {}
        if not text:
            continue
        for ch in chunk_text(text):
            to_add.append({"text": ch, "metadata": meta})
    if not to_add:
        return 0
    return add_documents(to_add)


def retrieve_context(query: str, k: int = 6) -> List[Dict[str, Any]]:
    return vs_query(query=query, k=k)


def persist_runtime_html(html: str) -> None:
    with open(RUNTIME_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def load_runtime_html() -> str:
    if os.path.exists(RUNTIME_HTML_PATH):
        with open(RUNTIME_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""
