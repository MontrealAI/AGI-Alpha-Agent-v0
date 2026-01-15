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
_MODEL: "SentenceTransformer" | None = None
_DIM = 384
_USING_HASH = False


def _hash_embed(text: str) -> np.ndarray:
    """Return a deterministic hash-based embedding."""
    digest = np.frombuffer(hashlib.sha256(text.encode("utf-8")).digest(), dtype=np.uint8)
    reps = int(np.ceil(_DIM / digest.size))
    vec = np.tile(digest, reps)[:_DIM].astype("float32")
    vec = (vec / 255.0) * 2 - 1
    norm = np.linalg.norm(vec) or 1.0
    return (vec / norm).reshape(1, -1)


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
        raise ImportError("sentence-transformers missing") from exc
    global _MODEL
    global _USING_HASH
    if _MODEL is None:
        try:
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2", device="cpu", local_files_only=True)
        except Exception as exc:  # pragma: no cover - offline or missing cache
            _LOG.warning("MiniLM model unavailable (%s); using hash embeddings.", exc)
            _USING_HASH = True
            return None
    _USING_HASH = False
    return _MODEL


def embed(text: str) -> np.ndarray:
    """Return the MiniLM embedding for ``text``."""
    model = _get_model()
    if model is None:
        return _hash_embed(text)
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
        if _USING_HASH:
            denom = float(np.linalg.norm(vec) * np.linalg.norm(self.mean)) or 1.0
            cos_sim = float(np.dot(vec[0], self.mean) / denom)
            return max(0.0, 1.0 - cos_sim)
        p = _softmax(vec[0])
        q = _softmax(self.mean)
        kl = float(np.sum(p * np.log((p + 1e-12) / (q + 1e-12))))
        return kl
