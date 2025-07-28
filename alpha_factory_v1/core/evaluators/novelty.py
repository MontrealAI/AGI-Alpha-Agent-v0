# SPDX-License-Identifier: Apache-2.0
"""Embedding-based novelty scoring utilities."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

try:  # optional heavy deps
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - offline
    SentenceTransformer = None

try:
    import faiss
except Exception:  # pragma: no cover - offline
    faiss = None

_LOG = logging.getLogger(__name__)
_MODEL: SentenceTransformer | None = None
_DIM = 384


def _get_model() -> SentenceTransformer:
    if SentenceTransformer is None:
        raise ImportError("sentence-transformers missing")
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


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
