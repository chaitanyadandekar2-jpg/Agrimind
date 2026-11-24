"""Wraps the embedding model with automatic lightweight memory-safe fallback.

On memory-constrained hosting environments (e.g. Render free tier 512MB RAM),
this avoids PyTorch/SentenceTransformer out-of-memory crashes by falling back
to deterministic 384-dimensional feature embeddings.
"""
from __future__ import annotations

import os
import math
import hashlib
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Automatically detect memory-constrained cloud environments (e.g. Render free tier with 512MB limit).
# When running locally on your PC / laptop (8GB-16GB RAM), PyTorch & SentenceTransformer run automatically.
# On Render (where RENDER environment variable is set), it defaults to lightweight mode to prevent OOM restarts.
IS_CLOUD_CONSTRAINED = bool(os.getenv("RENDER"))
LOW_MEMORY_MODE = os.getenv("LOW_MEMORY_MODE", "true" if IS_CLOUD_CONSTRAINED else "false").lower() in ("true", "1", "yes")


@lru_cache(maxsize=1)
def _get_model():
    if LOW_MEMORY_MODE:
        logger.info("Operating in low-memory cloud mode: using lightweight feature ranker")
        return None
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"High-memory environment detected: loading {_MODEL_NAME} via PyTorch")
        return SentenceTransformer(_MODEL_NAME)
    except Exception as exc:
        logger.warning(f"SentenceTransformer unavailable or memory constrained ({exc}); falling back to lightweight embeddings")
        return None


def _lightweight_embed(text: str, dim: int = 384) -> list[float]:
    """Zero-memory deterministic 384-dimensional feature vector."""
    vec = [0.0] * dim
    words = text.lower().split()
    if not words:
        return vec
    for w in words:
        idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 5) for x in vec]


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    if model is not None:
        try:
            embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception as exc:
            logger.warning(f"Model encode failed ({exc}); falling back to lightweight")

    return [_lightweight_embed(t) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
