"""
alpha_factory_v1.backend.memory_vector
======================================

🚀  *Vector Memory Fabric* – production-grade, fault-tolerant, self-contained
----------------------------------------------------------------------------

Primary store   : **PostgreSQL + pgvector**        (durable, horizontally-scalable)  
Secondary store : **FAISS in RAM**                 (ultra-fast, ephemeral)  
Tertiary store  : **Pure-NumPy cosine search**     (zero-dependency fallback)  

Embedding back-ends
-------------------
1. **OpenAI** `text-embedding-3-small` (1536 d) – if ``OPENAI_API_KEY`` is set.  
2. **Sentence-Transformers** `all-MiniLM-L6-v2` (384 d) – local CPU model.  

Design goals
------------
* **Graceful degradation** – *never* crash at import-time; run anywhere.  
* **Observability first** – Prometheus counters/gauges baked-in.  
* **Thread/Fork safety** – one DB connection per PID via lazy pool.  
* **CLI self-test** – ``python -m alpha_factory_v1.backend.memory_vector --demo``  
* **Zero intra-project deps** – drop-in usable in any repo / unit tests.  

MIT License © 2025 Montreal AI
"""

from __future__ import annotations

# ────────────────────────── stdlib ────────────────────────────
import logging
import os
import queue
import random
import sqlite3
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as _np

_LOG = logging.getLogger("alpha_factory.memory_vector")
if not _LOG.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _LOG.addHandler(_h)
_LOG.setLevel(os.getenv("LOGLEVEL", "INFO").upper())

# ─────────────────── optional third-party deps ──────────────────
try:                            # Embeddings – OpenAI first
    import openai  # type: ignore

    _HAS_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
except Exception:               # noqa: BLE001 pragma: no cover
    _HAS_OPENAI = False

try:                            # Local SBERT
    from sentence_transformers import SentenceTransformer  # type: ignore
except ModuleNotFoundError:      # pragma: no cover
    SentenceTransformer = None  # type: ignore

try:                            # Postgres + pgvector
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
    _HAS_PG = True
except ModuleNotFoundError:      # pragma: no cover
    _HAS_PG = False

try:                            # FAISS
    import faiss  # type: ignore
    _HAS_FAISS = True
except ModuleNotFoundError:      # pragma: no cover
    _HAS_FAISS = False

try:                            # Prometheus metrics
    from prometheus_client import Counter, Gauge  # type: ignore

    _MET_ADD = Counter("af_mem_add_total", "Memories added", ["backend"])
    _MET_QRY = Counter("af_mem_query_total", "Vector queries", ["backend"])
    _MET_SZ = Gauge("af_mem_size", "Total memories stored", ["backend"])
except ModuleNotFoundError:      # pragma: no cover

    class _Noop:  # pylint: disable=too-few-public-methods
        def labels(self, *_a):  # noqa: D401
            return self

        def inc(self, *_a): ...
        def set(self, *_a): ...

    _MET_ADD = _MET_QRY = _MET_SZ = _Noop()


# ─────────────────────── embedding layer ───────────────────────
_DIM_OPENAI, _DIM_SBERT = 1536, 384
_SBERT: SentenceTransformer | None = None


def _l2(mat: _np.ndarray) -> _np.ndarray:
    """L2-normalise each row of *mat* (0-safe)."""
    norm = _np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return mat / norm


def _embed(texts: Sequence[str]) -> _np.ndarray:
    """Return L2-normalised embeddings for *texts*."""
    if _HAS_OPENAI:
        try:  # OpenAI – multilingual & SOTA
            resp = openai.embeddings.create(  # type: ignore[attr-defined]
                model="text-embedding-3-small",
                input=list(texts),
            )
            vectors = _np.asarray([d.embedding for d in resp.data], "float32")
            return _l2(vectors)
        except Exception:  # pragma: no cover
            _LOG.exception("OpenAI embed failed – falling back to SBERT")

    if SentenceTransformer is None:
        raise RuntimeError(
            "No embedding backend available. Install "
            "`sentence-transformers` or set OPENAI_API_KEY."
        )

    global _SBERT  # pylint: disable=global-statement
    if _SBERT is None:
        _SBERT = SentenceTransformer(
            os.getenv("AF_SBER_MODEL", "all-MiniLM-L6-v2")
        )
    vectors = _SBERT.encode(list(texts), normalize_embeddings=True)
    return _np.asarray(vectors, "float32")


def _emb_dim() -> int:
    """Return active embedding dimensionality."""
    return _DIM_OPENAI if _HAS_OPENAI else _DIM_SBERT


# ─────────────────── persistent Postgres store ───────────────────
class _PgPool:
    """*Lazy, fork-safe* Postgres connection pool (very light)."""

    def __init__(self, dsn: str):
        self._dsn, self._pid = dsn, os.getpid()
        self._pool: queue.SimpleQueue[psycopg2.extensions.connection] = (
            queue.SimpleQueue()
        )

    def _new_conn(self):
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = True
        return conn

    def get(self):  # noqa: D401
        if os.getpid() != self._pid:  # Fork? Reset pool.
            self._pool = queue.SimpleQueue()
            self._pid = os.getpid()
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            return self._new_conn()

    def put(self, conn):
        if os.getpid() == self._pid:
            self._pool.put(conn)
        else:  # pragma: no cover
            conn.close()


class _PostgresStore:
    """Persistent pgvector-backed store."""

    def __init__(self, dsn: str):
        self._pool = _PgPool(dsn)
        self._ensure_schema()
        _MET_SZ.labels("postgres").set(len(self))

    # ---------- schema ---------- #
    def _ensure_schema(self):
        conn = self._pool.get()
        with conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            dim = _emb_dim()
            cur.execute(
                f"""CREATE TABLE IF NOT EXISTS memories(
                        id        BIGSERIAL PRIMARY KEY,
                        agent     TEXT NOT NULL,
                        embedding VECTOR({dim}),
                        content   TEXT,
                        ts        TIMESTAMPTZ DEFAULT NOW()
                )"""
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS mem_vec_idx "
                "ON memories USING ivfflat(embedding vector_cosine_ops)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS mem_agent_ts_idx "
                "ON memories (agent, ts DESC)"
            )
        self._pool.put(conn)

    # ---------- CRUD ---------- #
    def add(self, agent: str, vecs: _np.ndarray, texts: List[str]):
        rows = [(agent, v.tolist(), t) for v, t in zip(vecs, texts)]
        conn = self._pool.get()
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                "INSERT INTO memories(agent, embedding, content) "
                "VALUES (%s, %s, %s)",
                rows,
                page_size=256,
            )
        self._pool.put(conn)
        _MET_ADD.labels("postgres").inc(len(rows))
        _MET_SZ.labels("postgres").set(len(self))

    def query(self, vec: _np.ndarray, k: int):
        conn = self._pool.get()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT agent,
                          content,
                          1 - (embedding <=> %s::vector) AS score
                     FROM memories
                 ORDER BY embedding <=> %s::vector
                    LIMIT %s""",
                (vec.tolist(), vec.tolist(), k),
            )
            rows = cur.fetchall()
        self._pool.put(conn)
        return rows

    def __len__(self):
        conn = self._pool.get()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM memories")
            n = cur.fetchone()[0]
        self._pool.put(conn)
        return int(n)


# ────────────────────── in-RAM FAISS / NumPy store ──────────────────────
class _FaissStore:
    """Ultra-fast in-memory store. Falls back to pure NumPy if FAISS missing."""

    def __init__(self):
        self._dim = _emb_dim()
        self._faiss_idx = faiss.IndexFlatIP(self._dim) if _HAS_FAISS else None
        self._meta: list[tuple[str, str]] = []  # (agent, text)
        self._vecs: list[_np.ndarray] = []      # only used when FAISS absent

    # ---------- CRUD ---------- #
    def add(self, agent: str, vecs: _np.ndarray, texts: List[str]):
        self._meta.extend((agent, t) for t in texts)
        if self._faiss_idx is not None:
            self._faiss_idx.add(vecs)
        else:  # NumPy fallback
            self._vecs.append(vecs.astype("float32", copy=False))
        backend = "faiss" if self._faiss_idx is not None else "numpy"
        _MET_ADD.labels(backend).inc(len(texts))
        _MET_SZ.labels(backend).set(len(self))

    def query(self, vec: _np.ndarray, k: int):
        if not len(self):
            return []
        if self._faiss_idx is not None:
            k = min(k, self._faiss_idx.ntotal)  # type: ignore[attr-defined]
            D, I = self._faiss_idx.search(vec, k)  # type: ignore[attr-defined]
            return [
                (*self._meta[idx], float(sim)) for idx, sim in zip(I[0], D[0])
            ]

        # ---- NumPy brute-force cosine ----
        mat = _np.vstack(self._vecs)  # type: ignore[arg-type]
        sims = mat @ vec.T
        order = sims[:, 0].argsort()[::-1][:k]
        return [
            (*self._meta[i], float(sims[i, 0])) for i in order
        ]

    def __len__(self):
        if self._faiss_idx is not None:
            return self._faiss_idx.ntotal  # type: ignore[attr-defined]
        return sum(v.shape[0] for v in self._vecs)


# ─────────────────────── public façade ───────────────────────
class VectorMemory:
    """Unified API wrapping *whichever* back-end is available."""

    def __init__(self, dsn: str | None = None):
        dsn = dsn or os.getenv("PG_DSN") or os.getenv("DATABASE_URL")

        if dsn and _HAS_PG:
            try:
                self._store: _PostgresStore | _FaissStore = _PostgresStore(dsn)
                self.backend = "postgres"
            except Exception as exc:  # pragma: no cover
                _LOG.warning(
                    "Postgres unavailable (%s) – falling back to RAM store", exc
                )
                self._store = _FaissStore()
                self.backend = "faiss" if _HAS_FAISS else "numpy"
        else:
            self._store = _FaissStore()
            self.backend = "faiss" if _HAS_FAISS else "numpy"
            _LOG.warning(
                "VectorMemory running in *%s* mode (non-persistent)",
                self.backend,
            )

        _MET_SZ.labels(self.backend).set(len(self))

    # ---------- public ops ---------- #
    def add(self, agent: str, content: str | Iterable[str]):
        """Embed *content* and store under *agent* namespace."""
        texts = [content] if isinstance(content, str) else list(content)
        vecs = _embed(texts)
        self._store.add(agent, vecs, texts)

    def search(
        self, query: str, k: int = 5
    ) -> List[Tuple[str, str, float]]:
        """Return *k* (agent, text, similarity) tuples."""
        _MET_QRY.labels(self.backend).inc()
        vec = _embed([query])
        return self._store.query(vec, k)

    # ---------- helpers ---------- #
    def __len__(self):
        return len(self._store)

    # noinspection PyProtectedMember
    def flush(self):
        """**Dangerous** – wipe all memories (only if persistent)."""
        if isinstance(self._store, _PostgresStore):
            conn = self._store._pool.get()  # type: ignore[attr-defined]
            with conn, conn.cursor() as c:
                c.execute("TRUNCATE TABLE memories")
            self._store._pool.put(conn)  # type: ignore[attr-defined]
            _MET_SZ.labels("postgres").set(0)
        else:
            raise RuntimeError("Flush only supported on PostgreSQL backend")


# ────────────────────────── CLI demo ──────────────────────────
def _demo():
    _LOG.info("💾  VectorMemory demo starting …")
    mem = VectorMemory()
    _LOG.info("Using backend → %s", mem.backend.upper())

    samples = [
        "the quick brown fox",
        "jumps over",
        "the lazy dog",
        "crypto markets rally on ETF approval",
        "factory schedule shifted to off-peak hours",
    ]
    random.shuffle(samples)
    mem.add("demo_agent", samples)
    time.sleep(0.3)  # simulate latency

    for q in ("quick fox", "crypto rally", "factory schedule"):
        hits = mem.search(q, k=3)
        print(f"\n🔎 Query: {q!r}")
        for agent, text, score in hits:
            print(f"   {score:5.3f}  {agent:<12s} | {text}")
    print("\n✅ Demo complete – VectorMemory operational.")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("Vector Memory Fabric CLI")
    ap.add_argument("--dsn", help="PostgreSQL DSN (e.g. postgres://user:pwd@host/db)")
    ap.add_argument(
        "--demo", action="store_true", help="run offline self-test (no DSN needed)"
    )
    args = ap.parse_args()

    if args.demo:
        _demo()
    else:
        print(
            "Tip: run with --demo to execute a self-contained smoke-test "
            "even when Postgres/FAISS/OpenAI are unavailable."
        )
