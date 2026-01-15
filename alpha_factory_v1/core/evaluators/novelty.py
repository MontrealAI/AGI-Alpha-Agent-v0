# SPDX-License-Identifier: Apache-2.0
"""Embedding-based novelty scoring utilities."""
from __future__ import annotations

import hashlib
import logging
import hashlib
from typing import Any, TYPE_CHECKING

import numpy as np

try:  # optional heavy deps
    import faiss
except Exception:  # pragma: no cover - offline
    faiss = None

if TYPE_CHECKING:  # pragma: no cover
    from sentence_transformers import SentenceTransformer

_LOG = logging.getLogger(__name__)
_MODEL: "SentenceTransformer" | None = None
_DIM = 384


def _hash_embed(text: str, dim: int = _DIM) -> np.ndarray:
    """Return a deterministic hashing-based embedding."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big", signed=False)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype("float32")
    vec /= np.linalg.norm(vec) or 1.0
    return vec.reshape(1, -1)


def _get_model() -> "SentenceTransformer | None":
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
        _LOG.warning("SentenceTransformer unavailable (%s) → hashing fallback.", exc)
        return None
    global _MODEL
    if _MODEL is None:
        try:
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:  # pragma: no cover - offline
            _LOG.warning("SentenceTransformer load failed (%s) → hashing fallback.", exc)
            return None
    return _MODEL


def embed(text: str) -> np.ndarray:
    """Return the MiniLM embedding for ``text``."""
    model = _get_model()
    if model is None:
        return _hash_embed(text)
    vec = model.encode([text], normalize_embeddings=True)
    return np.asarray(vec, dtype="float32")  # type: ignore[no-any-return]
    try:
        model = _get_model()
        vec = model.encode([text], normalize_embeddings=True)
        return np.asarray(vec, dtype="float32")  # type: ignore[no-any-return]
    except Exception as exc:  # pragma: no cover - offline fallback
        _LOG.warning("SentenceTransformer unavailable (%s) → hashing fallback.", exc)
        return _hash_embedding(text)


def _hash_embedding(text: str) -> np.ndarray:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big", signed=False) % _DIM
    vec = np.zeros(_DIM, dtype="float32")
    vec[idx] = 20.0
    return vec.reshape(1, -1)


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
        if _MODEL is None:
            v = vec[0]
            denom = float(np.linalg.norm(v) * np.linalg.norm(self.mean)) or 1.0
            cosine = float(np.dot(v, self.mean) / denom)
            return 1.0 - cosine
        p = _softmax(vec[0])
        q = _softmax(self.mean)
        kl = float(np.sum(p * np.log((p + 1e-12) / (q + 1e-12))))
        return kl
