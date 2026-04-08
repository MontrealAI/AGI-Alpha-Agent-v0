# SPDX-License-Identifier: Apache-2.0

"""
novel_solution_reward.py – Alpha‑Factory v1 👁️✨
-------------------------------------------------------------------------
Reward backend that incentivises *novel problem‑solving strategies*.

Motivation
==========
In the **Era of Experience** agents should *out‑imagine* human priors.  We
approximate "novelty" by comparing the current *result* (any textual or
structured solution object) with a memory of past solutions:

    • If the cosine similarity < τ_low  → **1.0**   (brand‑new idea)
    • If  τ_low ≤ sim < τ_high         → value in (0, 1) by interpolation
    • Else (sim ≥ τ_high)              → **0.0**   (redundant)

Implementation details
----------------------
• Memory stores the *64‑bit SimHash* of each solution for O(1) lookup.
• Optionally, if **sentence_transformers** is importable *and* an embedding
  model path is set via the env‑var ``EMBED_MODEL`` (defaults to
  ``all-MiniLM-L6-v2``) we compute embeddings for higher‑fidelity cosine
  similarity.  Otherwise we fall back to the SimHash Hamming distance.
• Pure‑Python, thread‑safe, zero hard dependencies.

Public API (required by reward_backends framework)
--------------------------------------------------
    reward(state, action, result) -> float

Parameters
----------
state   : ignored
action  : ignored
result  : Any   – current solution object (string / dict / list / …)

Returns
-------
float ∈ [0.0, 1.0]

© 2025 Montreal.AI   – Apache-2.0 License
"""

from __future__ import annotations

import os as _os
import threading as _th
import hashlib as _hl
import math as _math
from typing import Any, List, Dict

_lock = _th.Lock()

# ── hyper‑parameters (env‑tunable) ────────────────────────────────────
_TAU_LOW = float(_os.getenv("NOVEL_TAU_LOW", 0.25))  # novelty threshold
_TAU_HIGH = float(_os.getenv("NOVEL_TAU_HIGH", 0.75))  # redundancy threshold
_MAX_MEM = int(_os.getenv("NOVEL_MEM_LIMIT", 2048))  # ring‑buffer length

# ── in‑memory ring buffers ───────────────────────────────────────────
_sig_mem: List[int] = []
_emb_mem: List[List[float]] | None = None
_idx = 0  # ring pointer

# ── optional sentence‑transformers backend ───────────────────────────
_have_embed = False
try:
    import importlib as _imp

    _st = _imp.import_module("sentence_transformers")
    _model_name = _os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
    _model = _st.SentenceTransformer(_model_name)
    _have_embed = True
except Exception:
    _have_embed = False


# ── helpers ──────────────────────────────────────────────────────────
def _simhash(text: str) -> int:
    """Return 64‑bit SimHash of *text*."""
    hv = [0] * 64
    for token in text.split():
        h = int.from_bytes(_hl.sha1(token.encode()).digest()[:8], "big")
        for i in range(64):
            hv[i] += -1 if (h >> i) & 1 else 1
    bits = 0
    for i, v in enumerate(hv):
        if v < 0:
            bits |= 1 << i
    return bits


def _sim_sig(a: int, b: int) -> float:
    dist = bin(a ^ b).count("1")
    return 1.0 - dist / 64.0


def _cos(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = _math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = _math.sqrt(sum(x * x for x in b)) or 1e-9
    return max(0.0, min(1.0, dot / (na * nb)))


def _normalize_embedding(raw: Any) -> List[float]:
    """Return a flat float vector from encoder output shapes."""
    if isinstance(raw, list):
        if raw and isinstance(raw[0], list):
            return [float(x) for x in raw[0]]
        return [float(x) for x in raw]
    return [float(x) for x in raw.tolist()]


def _to_text(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    try:
        import json as _json

        return _json.dumps(obj, sort_keys=True, ensure_ascii=False)
    except Exception:
        return repr(obj)


# ── core API ─────────────────────────────────────────────────────────
def reward(state: Any, action: Any, result: Any) -> float:  # noqa: D401
    """Compute and return novelty reward."""
    global _idx, _emb_mem

    txt = _to_text(result)
    sig = _simhash(txt)

    if _have_embed:
        emb = _normalize_embedding(_model.encode(txt, normalize_embeddings=True))

    with _lock:
        sims: List[float] = []
        for j, old_sig in enumerate(_sig_mem):
            s = _sim_sig(sig, old_sig)
            if _have_embed and _emb_mem is not None:
                s = 0.75 * s + 0.25 * _cos(emb, _emb_mem[j])
            sims.append(s)

        sim = max(sims) if sims else 0.0

        # update ring buffer
        if len(_sig_mem) < _MAX_MEM:
            _sig_mem.append(sig)
            if _have_embed:
                if _emb_mem is None:
                    _emb_mem = []
                _emb_mem.append(emb if _have_embed else [])
        else:
            _sig_mem[_idx] = sig
            if _have_embed and _emb_mem is not None:
                _emb_mem[_idx] = emb
            _idx = (_idx + 1) % _MAX_MEM

    # similarity → reward mapping
    if sim <= _TAU_LOW:
        return 1.0
    if sim >= _TAU_HIGH:
        return 0.0
    return 1.0 - (sim - _TAU_LOW) / (_TAU_HIGH - _TAU_LOW)
