# SPDX-License-Identifier: Apache-2.0
"""Embedding-based novelty scoring utilities."""
from __future__ import annotations

import hashlib
import logging
from typing import Any, TYPE_CHECKING

import numpy as np

try:  # optional heavy deps
    import faiss
except Exception:  # pragma: no cover - offline
    faiss = None

if TYPE_CHECKING:  # pragma: no cover
    from sentence_transformers import SentenceTransformer

_LOG = logging.getLogger(__name__)
_MODEL: Any | None = None
_DIM = 384
_HASH_SCALE = 10.0


class _HashEmbeddingModel:
    """Deterministic fallback embedder for offline environments."""

    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> np.ndarray:
        vectors = [_hash_vector(text) for text in texts]
        arr = np.vstack(vectors)
        return arr * _HASH_SCALE


def _hash_vector(text: str) -> np.ndarray:
    digest = hashlib.sha256(text.encode()).digest()
    idx = int.from_bytes(digest[:2], "big", signed=False) % _DIM
    vec = np.full(_DIM, -1.0, dtype="float32")
    vec[idx] = 1.0
    return vec


def _get_model() -> "SentenceTransformer":
    """Lazily import and initialize the MiniLM encoder.

    Importing ``sentence-transformers`` pulls in PyTorch, which can take several
    seconds and may attempt to initialize hardware backends. Performing the
    import only when embeddings are requested keeps lightweight test suites
    (including CI smoke runs) fast and avoids unnecessary startup cost when the
    novelty index is unused.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - offline
        raise ImportError("sentence-transformers missing") from exc
    global _MODEL
    if _MODEL is None:
        try:
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:  # pragma: no cover - network/model issues
            _LOG.warning("MiniLM unavailable (%s); using hash embeddings.", exc)
            _MODEL = _HashEmbeddingModel()
    return _MODEL  # type: ignore[return-value]


def embed(text: str) -> np.ndarray:
    """Return the MiniLM embedding for ``text``."""
    model = _get_model()
    vec = model.encode([text], normalize_embeddings=True)
    return np.asarray(vec, dtype="float32")  # type: ignore[no-any-return]


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - float(np.max(x)))
    return e / (e.sum() + 1e-12)  # type: ignore[no-any-return]


class NoveltyIndex:
    """In-memory FAISS index tracking the embedding mean."""

    def __init__(self) -> None:
        self.dim: int = _DIM
        self.index: faiss.IndexFlatIP | None = faiss.IndexFlatIP(self.dim) if faiss else None
        self.mean: np.ndarray = np.zeros(self.dim, dtype="float32")
        self.count: int = 0

    def add(self, text: str) -> None:
        """Index the embedding of ``text`` and update the mean vector."""
        vec = embed(text)
        if self.index is not None:
            self.index.add(vec)
        self.mean = (self.mean * self.count + vec[0]) / (self.count + 1)
        self.count += 1

    def divergence(self, text: str) -> float:
        """Return the KL divergence between ``text`` and the index mean."""
        vec = embed(text)
        if self.count == 0:
            return 1.0
        p = _softmax(vec[0])
        q = _softmax(self.mean)
        kl = float(np.sum(p * np.log((p + 1e-12) / (q + 1e-12))))
        return kl
