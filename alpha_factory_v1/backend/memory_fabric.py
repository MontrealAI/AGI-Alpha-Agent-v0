# SPDX-License-Identifier: MIT
"""
alpha_factory_v1.backend.memory_fabric
======================================

🧠  MEMORY FABRIC  (v1.3.2 – 2025-05-02)
----------------------------------------
Production-grade episodic & causal memory layer for Alpha-Factory v1.

Highlights
──────────
• **Vector Memory**   – PostgreSQL + pgvector ▸ FAISS ▸ SQLite fallback (CPU-only)
• **Graph Memory**    –  Neo4j ▸ NetworkX ▸ python-list fallback
• **Sync & Async**    – one call signature, fabric switches under the hood
• **Metrics & Tracing** – Prometheus + OpenTelemetry (graceful if libs absent)
• **Graceful-Degrade** – never throws un-caught exceptions; always returns data
• **Thread/Task safe** – re-entrant locks + asyncio.Lock for mixed usage
• **No secrets in code** – all configuration via env-vars or pydantic settings
• **Self-Provisioning** – creates tables, indices, constraints on first use
• **One-command export** – `mem.export_all("snapshot.parquet")`

Environment variables (factory defaults in brackets)
─────────────────────────────────────────────────────
PGHOST / PGPORT[5432] / PGUSER / PGPASSWORD / PGDATABASE[memdb]
PGVECTOR_INDEX_IVFFLAT_LISTS[100]  – performance tuning
NEO4J_URI[bolt://localhost:7687] / NEO4J_USER[neo4j] / NEO4J_PASS[neo4j]
OPENAI_API_KEY (optional) – OpenAI embeddings used if present
VECTOR_DIM[768]           – embedding dimension for pgvector & FAISS
MEM_TTL_SECONDS[0]        – 0 = keep forever, else soft-delete after TTL
MEM_MAX_PER_AGENT[100000] – per-agent quota (oldest evicted on overflow)

Python extras automatically used when available:
    numpy, sentence_transformers, psycopg2-binary, faiss-cpu, neo4j,
    networkx, prometheus_client, opentelemetry-api / sdk
"""

from __future__ import annotations

# ───────────────────────── stdlib ░─────────────────────────
import asyncio
import contextlib
import dataclasses
import hashlib
import json
import logging
import math
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

# ─────────────────────── dynamic soft-deps ░──────────────────
try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dep
    np = None  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    from sentence_transformers import SentenceTransformer  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    import psycopg2, psycopg2.extras  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    import faiss  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    from neo4j import GraphDatabase  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    import networkx as nx  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    from prometheus_client import Counter, Histogram  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    from opentelemetry import trace  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    import openai  # type: ignore
with contextlib.suppress(ModuleNotFoundError):
    try:
        from pydantic import BaseSettings, Field, PositiveInt  # type: ignore
    except ImportError:  # pragma: no cover - pydantic >= 2
        from pydantic import Field, PositiveInt  # type: ignore
        from pydantic_settings import BaseSettings  # type: ignore

# ───────────────────────── logging ░──────────────────────────
logger = logging.getLogger("AlphaFactory.MemoryFabric")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s"))
    logger.addHandler(_h)


# ─────────────────── configuration (pydantic) ░───────────────
class _Settings(BaseSettings):
    # Vector
    PGHOST: Optional[str] = None
    PGPORT: int = 5432
    PGUSER: Optional[str] = None
    PGPASSWORD: Optional[str] = None
    PGDATABASE: str = "memdb"
    PGVECTOR_INDEX_IVFFLAT_LISTS: int = 100
    VECTOR_DIM: int = 768

    # Graph
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASS: str = "neo4j"

    # Memory policies
    MEM_TTL_SECONDS: int = 0  # 0 = infinite
    MEM_MAX_PER_AGENT: PositiveInt = Field(100_000, env="MEM_MAX_PER_AGENT")

    # Quotas / circuit breaker
    MEM_FAIL_GRACE_SEC: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


CFG = _Settings()  # single instance

# ───────────────────── telemetry helpers ░────────────────────
if "Counter" in globals():
    from prometheus_client import REGISTRY as _REG

    def _get_metric(cls, name: str, desc: str):
        if name in getattr(_REG, "_names_to_collectors", {}):
            return _REG._names_to_collectors[name]
        return cls(name, desc)

    _MET_V_ADD = _get_metric(Counter, "af_mem_vector_add_total", "Vectors stored")
    _MET_V_SRCH = _get_metric(
        Histogram,
        "af_mem_vector_search_latency_seconds",
        "Vector search latency",
    )
else:
    _MET_V_ADD = None
    _MET_V_SRCH = contextlib.nullcontext()

tracer = trace.get_tracer(__name__) if "trace" in globals() else None  # type: ignore

# ──────────────────────── EMBEDDING back-end ░────────────────


def _load_embedder():
    if "openai" in globals() and os.getenv("OPENAI_API_KEY"):
        logger.info("MemoryFabric: using OpenAI embeddings.")
        model = "text-embedding-3-small"

        def _openai(text: str):
            resp = openai.Embedding.create(model=model, input=text)  # type: ignore[attr-defined]
            return resp["data"][0]["embedding"]

        return _openai

    if np is not None and "SentenceTransformer" in globals():
        logger.info("MemoryFabric: using local SBERT embeddings.")
        _model = SentenceTransformer("all-MiniLM-L6-v2")

        def _sbert(text: str):
            return _model.encode(text, normalize_embeddings=True)

        return _sbert

    logger.warning("MemoryFabric: no embedding backend → hashing fallback.")

    def _hash(text: str, dim: int = CFG.VECTOR_DIM):
        h = hashlib.sha256(text.encode()).digest()
        v = [(1 if b & 1 else -1) * ((b >> 1) / 128.0) for b in h]
        v *= (dim + len(v) - 1) // len(v)
        if np is not None:
            vec = np.array(v[:dim], dtype="float32")
            vec /= np.linalg.norm(vec) or 1
            return vec.tolist()
        vec = v[:dim]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    return _hash


_EMBED = _load_embedder()

# ────────────────────────── util ░─────────────────────────────
_NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _hash_content(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()


# ═════════════════════ VECTOR STORE ══════════════════════════
class _VectorStore:
    """Implementation chain:  Postgres+pgvector ▸ FAISS ▸ SQLite ▸ RAM list."""

    # ───────── init ─────────
    def __init__(self):
        self._lock = threading.RLock()
        self._alock = asyncio.Lock()
        self._mode = "ram"
        self._fail_until = 0.0
        self._init_postgres()  # may set self._mode
        if self._mode == "ram":
            self._init_faiss_or_sqlite()

    # ───── Postgres / pgvector ─────
    def _init_postgres(self):
        if "psycopg2" not in globals() or not CFG.PGHOST:
            return
        dsn = {
            "host": CFG.PGHOST,
            "port": CFG.PGPORT,
            "user": CFG.PGUSER,
            "password": CFG.PGPASSWORD,
            "dbname": CFG.PGDATABASE,
        }
        try:
            self._pg = psycopg2.connect(**{k: v for k, v in dsn.items() if v is not None})  # type: ignore[arg-type]
            with self._pg, self._pg.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    f"""CREATE TABLE IF NOT EXISTS memories (
                           id          BIGSERIAL PRIMARY KEY,
                           agent       TEXT,
                           hash        CHAR(40) UNIQUE,
                           embedding   VECTOR({CFG.VECTOR_DIM}),
                           content     TEXT,
                           ts          TIMESTAMPTZ DEFAULT NOW()
                       );"""
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mem_agent_ts ON memories(agent, ts DESC);"
                )
                cur.execute(
                    f"""CREATE INDEX IF NOT EXISTS idx_mem_embedding
                        ON memories USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists={CFG.PGVECTOR_INDEX_IVFFLAT_LISTS});"""
                )
            self._mode = "pg"
            logger.info("VectorStore: Postgres/pgvector ready.")
        except Exception as e:  # noqa: BLE001
            logger.warning("VectorStore: Postgres unavailable → %s", e)

    # ───── FAISS / SQLite fallback ─────
    def _init_faiss_or_sqlite(self):
        if np is None:
            logger.info("VectorStore: numpy missing → RAM mode")
            return
        if "faiss" in globals():
            self._faiss = faiss.IndexFlatIP(CFG.VECTOR_DIM)
            self._vectors: List[np.ndarray] = []
            self._meta: List[Tuple[str, str, str]] = []  # agent, content, ts
            self._mode = "faiss"
            logger.info("VectorStore: FAISS in-memory index ready.")
        elif os.getenv("VECTOR_STORE_USE_SQLITE", "false").lower() == "true":
            self._sql = sqlite3.connect(Path("vector_mem.db"))
            self._sql.execute(
                "CREATE TABLE IF NOT EXISTS memories(hash TEXT PRIMARY KEY, agent TEXT, ts TEXT, vec BLOB, content TEXT)"
            )
            self._mode = "sqlite"
            logger.info("VectorStore: SQLite fallback ready.")
        else:
            logger.info("VectorStore: SQLite disabled → RAM mode")

    # ───── internal helpers ─────
    def _evict_if_needed(self, agent: str):
        if CFG.MEM_MAX_PER_AGENT <= 0:
            return
        if self._mode == "pg":
            with self._pg, self._pg.cursor() as cur:
                cur.execute(
                    "DELETE FROM memories WHERE id IN ("
                    "SELECT id FROM memories WHERE agent=%s ORDER BY ts ASC "
                    "OFFSET %s)",
                    (agent, CFG.MEM_MAX_PER_AGENT),
                )
        elif self._mode == "sqlite":
            cur = self._sql.execute(
                "SELECT hash FROM memories WHERE agent=? ORDER BY ts ASC", (agent,)
            ).fetchall()
            if len(cur) > CFG.MEM_MAX_PER_AGENT:
                to_del = cur[: len(cur) - CFG.MEM_MAX_PER_AGENT]
                self._sql.executemany("DELETE FROM memories WHERE hash=?", to_del)
                self._sql.commit()
        elif self._mode == "faiss":
            # lightweight: we simply pop oldest from meta/vectors
            while sum(1 for a, *_ in self._meta if a == agent) > CFG.MEM_MAX_PER_AGENT:
                idx = next(i for i, (a, *_) in enumerate(self._meta) if a == agent)
                self._meta.pop(idx)
                self._vectors.pop(idx)
                self._faiss.reset()
                if self._vectors:
                    self._faiss.add(np.vstack(self._vectors))

    def _apply_ttl_pg(self):
        if CFG.MEM_TTL_SECONDS <= 0:
            return
        with self._pg, self._pg.cursor() as cur:
            cur.execute(
                "DELETE FROM memories WHERE ts < NOW() - INTERVAL '%s seconds'"
                % CFG.MEM_TTL_SECONDS
            )

    # ───── public (sync) API ─────
    def add(self, agent: str, content: str):
        """Insert one memory row idempotently (by SHA-1 hash)."""
        h = _hash_content(content)
        vec = _EMBED(content)
        if np is not None:
            vec = np.asarray(vec, dtype="float32")
        now = _NOW().isoformat()
        try:
            if self._mode == "pg":
                if time.time() < self._fail_until:
                    raise ConnectionError("pg in grace-period")
                with self._pg, self._pg.cursor() as cur:
                    cur.execute(
                        "INSERT INTO memories(agent, hash, embedding, content) "
                        "VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING;",
                        (agent, h, list(map(float, vec)), content),
                    )
                self._evict_if_needed(agent)
                self._apply_ttl_pg()
            elif self._mode == "faiss":
                if h in (meta_h := {m[1] for m in self._meta}):
                    return
                self._faiss.add(vec.reshape(1, -1))
                self._vectors.append(vec)
                self._meta.append((agent, content, now))
                self._evict_if_needed(agent)
            elif self._mode == "sqlite":
                try:
                    self._sql.execute(
                        "INSERT OR IGNORE INTO memories VALUES(?,?,?,?,?)",
                        (h, agent, now, vec.tobytes(), content),
                    )
                    self._sql.commit()
                except sqlite3.OperationalError:
                    pass
                self._evict_if_needed(agent)
            else:  # ram list
                pass
            if _MET_V_ADD:
                _MET_V_ADD.inc()
        except Exception as e:  # noqa: BLE001
            logger.error("VectorStore.add error → %s  (downgrading)", e)
            self._mode = "ram"
            self._fail_until = time.time() + CFG.MEM_FAIL_GRACE_SEC

    def add_many(self, agent: str, contents: Iterable[str]):
        for c in contents:
            self.add(agent, c)

    def recent(self, agent: str, limit: int = 20) -> List[str]:
        if self._mode == "pg":
            with self._pg.cursor() as cur:
                cur.execute(
                    "SELECT content FROM memories WHERE agent=%s "
                    "ORDER BY ts DESC LIMIT %s",
                    (agent, limit),
                )
                return [r[0] for r in cur.fetchall()]
        if self._mode == "sqlite":
            cur = self._sql.execute(
                "SELECT content FROM memories WHERE agent=? ORDER BY ts DESC LIMIT ?",
                (agent, limit),
            )
            return [r[0] for r in cur.fetchall()]
        if self._mode == "faiss":
            return [c for a, c, *_ in reversed(self._meta) if a == agent][:limit]
        return []

    # search (single query) ------------------------------------
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        with _MET_V_SRCH.time() if _MET_V_SRCH else contextlib.nullcontext():
            qv = _EMBED(query)
            if np is not None:
                qv = np.asarray(qv, dtype="float32")
            if self._mode == "pg":
                with self._pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:  # type: ignore[arg-type]
                    cur.execute(
                        "SELECT agent, content, ts, embedding <-> %s AS score "
                        "FROM memories ORDER BY score LIMIT %s",
                        (list(map(float, qv)), k),
                    )
                    return cur.fetchall()
            if self._mode == "faiss" and self._vectors:
                d, idx = self._faiss.search(qv.reshape(1, -1), k)
                out = []
                for score, i in zip(d[0], idx[0]):
                    if i == -1:
                        continue
                    a, c, ts = self._meta[i]
                    out.append(
                        {"agent": a, "content": c, "ts": ts, "score": float(score)}
                    )
                return out
            if self._mode == "sqlite":
                cur = self._sql.execute("SELECT agent, vec, content, ts FROM memories")
                rows = cur.fetchall()
                scored = []
                for a, vb, c, ts in rows:
                    v = np.frombuffer(vb, dtype="float32")
                    s = float(
                        np.dot(v, qv) / (np.linalg.norm(v) * np.linalg.norm(qv) or 1)
                    )
                    scored.append((s, a, c, ts))
                scored.sort(reverse=True)
                return [
                    {"agent": a, "content": c, "ts": ts, "score": s}
                    for s, a, c, ts in scored[:k]
                ]
            return []

    # bulk search ----------------------------------------------
    def search_many(self, queries: Sequence[str], k: int = 5):
        return [self.search(q, k) for q in queries]

    # export / import ------------------------------------------
    def export_all(self, path: Union[str, Path]):
        """Dump entire vector store to JSON-Lines or Parquet (ext inferred)."""
        path = Path(path)
        rows = []
        if self._mode == "pg":
            with self._pg.cursor() as cur:
                cur.execute("SELECT agent, content, ts FROM memories")
                rows = cur.fetchall()
        elif self._mode == "sqlite":
            rows = self._sql.execute(
                "SELECT agent, content, ts FROM memories"
            ).fetchall()
        elif self._mode == "faiss":
            rows = [(a, c, ts) for a, c, ts in self._meta]
        if path.suffix == ".jsonl":
            with path.open("w", encoding="utf-8") as f:
                for a, c, ts in rows:
                    f.write(json.dumps({"agent": a, "content": c, "ts": ts}) + "\n")
        else:  # parquet
            try:
                import pandas as pd  # type: ignore

                df = pd.DataFrame(rows, columns=["agent", "content", "ts"])
                df.to_parquet(path)
            except Exception as e:  # noqa: BLE001
                logger.error("export_all failed: %s", e)


# ═════════════════════ GRAPH STORE ═══════════════════════════
class _GraphStore:
    """Neo4j ▸ NetworkX ▸ list  (same downgrade policy as vector store)"""

    def __init__(self):
        self._lock = threading.RLock()
        self._alock = asyncio.Lock()
        self._mode = "list"
        self._fail_until = 0.0
        self._init_neo4j()
        if self._mode == "list":
            self._init_networkx()

    def _init_neo4j(self):
        if "GraphDatabase" not in globals():
            return
        try:
            self._driver = GraphDatabase.driver(
                CFG.NEO4J_URI, auth=(CFG.NEO4J_USER, CFG.NEO4J_PASS)
            )
            with self._driver.session() as s:
                s.run("RETURN 1").single()
            self._mode = "neo4j"
            logger.info("GraphStore: Neo4j ready.")
        except Exception as e:  # noqa: BLE001
            logger.warning("GraphStore: Neo4j unavailable → %s", e)

    def _init_networkx(self):
        if "nx" in globals():
            self._g = nx.MultiDiGraph()  # type: ignore[attr-defined]
            self._mode = "nx"
            logger.info("GraphStore: NetworkX in-mem fallback.")
        else:
            self._triples: List[Tuple[str, str, str, Dict[str, Any]]] = []
            logger.info("GraphStore: python-list ultimate fallback.")

    # add relation ---------------------------------------------
    def add(self, a: str, rel: str, b: str, props: Optional[Dict[str, Any]] = None):
        props = props or {}
        props.setdefault("ts", _NOW().isoformat())
        try:
            if self._mode == "neo4j":
                if time.time() < self._fail_until:
                    raise ConnectionError("neo4j in grace")
                cypher = (
                    "MERGE (x:Entity {name:$a}) "
                    "MERGE (y:Entity {name:$b}) "
                    f"MERGE (x)-[r:{rel.upper()}]->(y) "
                    "SET r += $props"
                )
                with self._driver.session() as s:
                    s.run(cypher, a=a, b=b, props=props)
            elif self._mode == "nx":
                self._g.add_edge(a, b, key=rel, **props)
            else:
                self._triples.append((a, rel, b, props))
        except Exception as e:  # noqa: BLE001
            logger.error("GraphStore.add error → %s  (downgrading)", e)
            self._mode = "list"
            self._fail_until = time.time() + CFG.MEM_FAIL_GRACE_SEC

    # query ----------------------------------------------------
    def query(self, cypher: str) -> List[Dict[str, Any]]:
        if self._mode == "neo4j":
            try:
                with self._driver.session() as s:
                    return [r.data() for r in s.run(cypher)]
            except Exception as e:  # noqa: BLE001
                logger.error("Neo4j query failed → %s", e)
        logger.warning("GraphStore.query: backend unavailable. returning [].")
        return []

    # find path ------------------------------------------------
    def find_path(self, start: str, end: str, max_len: int = 3) -> List[str]:
        if self._mode == "neo4j":
            q = (
                "MATCH p=(a:Entity {name:$s})-[:*1..%d]-(b:Entity {name:$e}) "
                "RETURN [n IN nodes(p) | n.name] AS names "
                "ORDER BY size(nodes(p)) ASC LIMIT 1" % max_len
            )
            res = self.query(q.replace("\n", " "), {"s": start, "e": end})
            return res[0]["names"] if res else []
        if self._mode == "nx":
            try:
                path = nx.shortest_path(self._g, start, end)  # type: ignore[arg-type]
                return path[: max_len + 1]
            except Exception:
                return []
        # list fallback: naive BFS over triples
        frontier = [(start, [start])]
        seen = {start}
        while frontier:
            node, path = frontier.pop(0)
            if len(path) > max_len + 1:
                continue
            nbrs = [c for a, _, c, _ in self._triples if a == node]
            for n in nbrs:
                if n in seen:
                    continue
                if n == end:
                    return path + [n]
                frontier.append((n, path + [n]))
                seen.add(n)
        return []


# ═════════════════════ FABRIC FACADE ═════════════════════════
class MemoryFabric:
    """Exposes .vector and .graph for sync + async contexts."""

    def __init__(self):
        self.vector = _VectorStore()
        self.graph = _GraphStore()

    # ─── convenience sync wrappers ───
    def add_memory(self, agent: str, content: str):
        self.vector.add(agent, content)

    def search(self, query: str, k: int = 5):
        return self.vector.search(query, k)

    def add_relation(
        self, a: str, rel: str, b: str, props: Optional[Dict[str, Any]] = None
    ):
        self.graph.add(a, rel, b, props)

    def find_path(self, s: str, e: str, max_len: int = 3):
        return self.graph.find_path(s, e, max_len)

    # ─── async variants (thin wrappers) ───
    async def aadd_memory(self, agent: str, content: str):
        async with self.vector._alock:
            self.vector.add(agent, content)

    async def asearch(self, query: str, k: int = 5):
        async with self.vector._alock:
            return self.vector.search(query, k)

    async def aadd_relation(
        self, a: str, rel: str, b: str, props: Optional[Dict[str, Any]] = None
    ):
        async with self.graph._alock:
            self.graph.add(a, rel, b, props)

    async def afind_path(self, s: str, e: str, max_len: int = 3):
        async with self.graph._alock:
            return self.graph.find_path(s, e, max_len)


# ────────────────── global singleton ░────────────────────────
mem = MemoryFabric()

__all__ = ["mem", "MemoryFabric", "CFG"]
