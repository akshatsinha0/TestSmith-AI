from __future__ import annotations
from typing import List

# Lightweight, dependency-free stand-ins for embeddings to keep the interface
# intact without requiring heavy ML frameworks on Python 3.13.

def embed_texts(texts: List[str]) -> List[List[float]]:  # pragma: no cover
    """Return trivial length-based embeddings.

    These are not used by the current vector store implementation, which relies
    on lexical matching, but are kept for compatibility if imported elsewhere.
    """
    return [[float(len(t))] for t in texts]


def embed_text(text: str) -> List[float]:  # pragma: no cover
    return embed_texts([text])[0]
