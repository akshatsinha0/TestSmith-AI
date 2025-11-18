from __future__ import annotations
import os
from typing import List
import numpy as np

from sentence_transformers import SentenceTransformer

_model = None

def get_embedder():
    global _model
    if _model is None:
        model_name = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _model = SentenceTransformer(model_name)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedder()
    vecs = model.encode(texts, normalize_embeddings=True).tolist()
    return vecs


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]
