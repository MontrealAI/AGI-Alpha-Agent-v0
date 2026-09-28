# SPDX-License-Identifier: Apache-2.0
# ===================================================================
# archive.py – Meta-Agentic α-AGI lineage store
# ===================================================================
#
# Production-grade helper for reading/writing/searching the lineage DB
# produced by meta-agentic search loops.
#
# Key capabilities
# ----------------
# • Zero-dependency core (uses only Python ≥3.9 std-lib; pandas optional)
# • Insert / update / merge and real-time streaming of candidate rows
# • Fast Pareto-front & crowding-distance selection for N ≤ 1e5
# • Shannon-entropy & Jaccard-distance novelty metrics
# • Round-trip converters: SQLite ⇆ JSONL ⇆ CSV ⇆ Parquet
# • CLI helpers: info · export · tail · vacuum
#
# Copyright © 2025 MONTREAL.AI – Apache-2.0
# ===================================================================

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Iterable, List, Sequence

# -------------------------------------------------------------------
# 1 · DATA MODEL
# -------------------------------------------------------------------


@dataclass(slots=True)
class Fitness:
    """
    Multi-objective fitness container.

    *All* numeric fields follow the convention **lower = better**
    for Pareto dominance, so we store accuracy/novelty as their
    negative values when comparing.
    Extend or shrink the schema freely – every attr that is a float
    will automatically participate in Pareto ranking & crowding.
    """

    accuracy: float
    latency: float
    cost: float
    carbon: float
    novelty: float
    # runtime-assigned (None → not yet computed)
    rank: int | None = field(default=None, compare=False)
    crowd: float | None = field(default=None, compare=False)

    # -- dominance ---------------------------------------------------
    def _vec(self) -> list[float]:
        """Vector with ‘minimise-everything’ ordering."""
        return [
            -self.accuracy,  # we maximise accuracy
            self.latency,
            self.cost,
            self.carbon,
            -self.novelty,  # we maximise novelty
        ]

    def dominated_by(self, other: "Fitness") -> bool:
        """Return True if *other* Pareto-dominates *self*."""
        s, o = self._vec(), other._vec()
        return all(ov <= sv for ov, sv in zip(o, s)) and any(ov < sv for ov, sv in zip(o, s))


@dataclass(slots=True)
class Candidate:
    """Single lineage entry."""

    id: int
    gen: int
    ts: str  # ISO 8601 timestamp (UTC)
    code: str  # single-file agent implementation
    fitness: Fitness


# -------------------------------------------------------------------
# 2 · SQLITE BACKEND
# -------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lineage(
    id      INTEGER PRIMARY KEY,
    gen     INTEGER,
    ts      TEXT,
    code    TEXT,
    fitness TEXT
);
"""


@contextmanager
def _cx(path: Path | str, readonly: bool = False):
    """
    Context-managed SQLite connection (WAL-mode, thread-safe).

    Parameters
    ----------
    path      : DB file path
    readonly  : open in read-only mode (sets PRAGMA accordingly)
    """
    uri = Path(path).absolute().as_uri() + f"?mode={'ro' if readonly else 'rwc'}"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    if not readonly:
        conn.execute(_SCHEMA)
        conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        if not readonly:
            conn.commit()
        conn.close()


# -------------------------------------------------------------------
# 3 · CRUD HELPERS  &  CONVERTERS
# -------------------------------------------------------------------


# -- helpers ---------------------------------------------------------
def _row_to_cand(r: sqlite3.Row | tuple) -> Candidate:
    """SQLite row → `Candidate`."""
    return Candidate(
        id=r[0],
        gen=r[1],
        ts=r[2],
        code=r[3],
        fitness=Fitness(**json.loads(r[4])),
    )


# -- single & bulk insert -------------------------------------------
def insert(c: Candidate, db: Path | str) -> None:
    """Insert or replace one candidate."""
    with _cx(db) as cx:
        cx.execute(
            "REPLACE INTO lineage VALUES (?,?,?,?,?)",
            (c.id, c.gen, c.ts, c.code, json.dumps(asdict(c.fitness))),
        )


def bulk_insert(cands: Iterable[Candidate], db: Path | str) -> None:
    """High-throughput bulk writer (uses executemany)."""
    rows = [(c.id, c.gen, c.ts, c.code, json.dumps(asdict(c.fitness))) for c in cands]
    with _cx(db) as cx:
        cx.executemany("REPLACE INTO lineage VALUES (?,?,?,?,?)", rows)


# -- load / stream ---------------------------------------------------
def load(
    db: Path | str,
    *,
    start_gen: int | None = None,
    end_gen: int | None = None,
) -> list[Candidate]:
    """Return all candidates, optionally sliced by generation range."""
    q = "SELECT * FROM lineage"
    filters, params = [], []
    if start_gen is not None:
        filters.append("gen >= ?")
        params.append(start_gen)
    if end_gen is not None:
        filters.append("gen <= ?")
        params.append(end_gen)
    if filters:
        q += " WHERE " + " AND ".join(filters)
    q += " ORDER BY gen, id"
    with _cx(db, readonly=True) as cx:
        rows = list(cx.execute(q, params))
    return [_row_to_cand(r) for r in rows]


def stream(db: Path | str, poll: float = 2.0) -> Iterable[Candidate]:
    """
    Infinite generator that yields **new** rows as they appear
    (tail-f behaviour). Suitable for live dashboards.
    """
    seen: set[int] = set()
    while True:
        for c in load(db):
            if c.id not in seen:
                seen.add(c.id)
                yield c
        time.sleep(poll)


# -- dataframe & file formats ---------------------------------------
def to_dataframe(cands: Sequence[Candidate]):
    """Convert to pandas DataFrame (raises if pandas missing)."""
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("`pip install pandas` required for DataFrame export") from exc
    recs = []
    for c in cands:
        row = {"id": c.id, "gen": c.gen, "ts": c.ts, "code": c.code}
        row.update(asdict(c.fitness))
        recs.append(row)
    return pd.DataFrame.from_records(recs)


def save_jsonl(cands: Sequence[Candidate], path: Path | str) -> None:
    """Write archive to newline-delimited JSON (*jsonl*)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for c in cands:
            fh.write(json.dumps(asdict(c)) + "\n")


def load_jsonl(path: Path | str) -> list[Candidate]:
    """Read archive from JSONL file."""
    out: list[Candidate] = []
    for line in Path(path).open():
        d = json.loads(line)
        out.append(
            Candidate(
                id=d["id"],
                gen=d["gen"],
                ts=d["ts"],
                code=d["code"],
                fitness=Fitness(**d["fitness"]),
            )
        )
    return out


# -------------------------------------------------------------------
# 4 · PARETO FRONT  &  DIVERSITY
# -------------------------------------------------------------------


def pareto_front(cands: Sequence[Candidate]) -> list[Candidate]:
    """
    Compute Pareto ranks *in-place* and return the non-dominated set.

    Notes
    -----
    • `candidate.fitness.rank` is set to an integer ≥ 1
    • A simple O(N²) sweep is sufficient for N ≲ 1e5 – high-dim
      dominance checks are the real bottleneck. Optimise later if
      required (e.g. NSGA-II fast-non-dominated sort).
    """
    if not cands:
        return []

    for c in cands:
        c.fitness.rank = 1

    for i, c in enumerate(cands):
        for o in cands[i + 1 :]:
            if c.fitness.dominated_by(o.fitness):
                c.fitness.rank += 1
            elif o.fitness.dominated_by(c.fitness):
                o.fitness.rank += 1

    return [c for c in cands if c.fitness.rank == 1]


# -- crowding distance ----------------------------------------------
def crowding_distance(front: Sequence[Candidate]) -> None:
    """
    Assign `fitness.crowd` for NSGA-II style diversity preservation.

    Larger crowding distance  →  more isolated in objective space.
    """
    if not front:
        return

    # keys participating in diversity (exclude rank / crowd fields)
    mkeys = [k for k in vars(front[0].fitness) if k not in {"rank", "crowd"}]

    # initialise
    for f in front:
        f.fitness.crowd = 0.0

    for k in mkeys:
        sorted_front = sorted(front, key=lambda c: getattr(c.fitness, k))
        k_min = getattr(sorted_front[0].fitness, k)
        k_max = getattr(sorted_front[-1].fitness, k)

        # boundary points → ∞ crowd (always selected)
        sorted_front[0].fitness.crowd = sorted_front[-1].fitness.crowd = math.inf

        if k_max == k_min:  # degenerate dimension
            continue

        # internal points
        for i in range(1, len(sorted_front) - 1):
            prev_k = getattr(sorted_front[i - 1].fitness, k)
            next_k = getattr(sorted_front[i + 1].fitness, k)
            sorted_front[i].fitness.crowd += (next_k - prev_k) / (k_max - k_min)


# -------------------------------------------------------------------
# 5 · NOVELTY & SIMILARITY METRICS
# -------------------------------------------------------------------
#
# These lightweight heuristics are *language-agnostic* and work on
# the literal source-code string.  For richer semantics plug-in
# AST-aware or embedding-based measures later on.

from collections import Counter
from functools import lru_cache
from hashlib import blake2b


# -- Shannon entropy -------------------------------------------------
def shannon_novelty(code: str, k: int = 32) -> float:
    """
    Estimate behavioural novelty as the Shannon entropy of `k`-gram
    frequencies in the candidate's source code.

    Parameters
    ----------
    code : str
        Full source code (arbitrary language).
    k : int, default=32
        Token-granularity (split by whitespace).

    Returns
    -------
    float
        Entropy in nats (larger  →  more diverse w.r.t. itself).
    """
    toks = code.split()
    if len(toks) < k:
        return 0.0

    grams = (" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1))
    freq = Counter(grams)
    total = sum(freq.values())

    return -sum((n / total) * math.log(n / total + 1e-12) for n in freq.values())


# -- Jaccard distance ------------------------------------------------
def jaccard_novelty(a: str, b: str, k: int = 6) -> float:
    """
    Fast Jaccard distance between two code snippets using `k`-shingles.

    0.0 → identical, 1.0 → completely disjoint.

    Tip
    ---
    Works well for pruning obvious clones before expensive evaluation.
    """
    if a == b:
        return 0.0

    grams = lambda s: {s[i : i + k] for i in range(len(s) - k + 1)}
    A, B = grams(a), grams(b)
    return 1 - len(A & B) / (len(A | B) or 1)


# -- Simhash (binary fingerprint) ------------------------------------
def _simhash(code: str, bits: int = 128) -> int:
    """
    Minimal, deterministic SimHash implementation for rapid *Hamming*
    similarity checks (useful in large archives).

    Returns an integer fingerprint with `bits` significant bits.
    """
    vec = [0] * bits
    for token in code.split():
        h = int.from_bytes(blake2b(token.encode(), digest_size=bits // 8).digest(), "big")
        for i in range(bits):
            vec[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i, v in enumerate(vec):
        if v > 0:
            out |= 1 << i
    return out


@lru_cache(maxsize=4096)
def simhash_distance(a: str, b: str, bits: int = 128) -> int:
    """
    Hamming distance between SimHash fingerprints (≤ `bits`).

    Lower  →  more similar (0 == identical fingerprints).
    """
    ha, hb = _simhash(a, bits), _simhash(b, bits)
    return (ha ^ hb).bit_count()


# -------------------------------------------------------------------
# 6 · ARCHIVE I/O, EXPORT & CLI
# -------------------------------------------------------------------
#
# *Round-trip* converters ↔  SQLite / JSONL / CSV / Parquet
# plus a tiny command-line interface for quick ops.  All file paths
# are resolved relative to *cwd*; non-existent parent dirs are created.

import csv
import argparse
from datetime import datetime


# -- helpers ---------------------------------------------------------
def _ensure_dir(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ----------------- JSONL --------------------------------------------
def save_jsonl(cands: Sequence[Candidate], dst: Path | str) -> None:
    dst = _ensure_dir(Path(dst))
    with dst.open("w", encoding="utf-8") as fh:
        for c in cands:
            fh.write(json.dumps(asdict(c)) + "\n")


def load_jsonl(src: Path | str) -> List[Candidate]:
    with Path(src).open(encoding="utf-8") as fh:
        return [
            Candidate(
                id=d["id"],
                gen=d["gen"],
                ts=d["ts"],
                code=d["code"],
                fitness=Fitness(**d["fitness"]),
            )
            for d in map(json.loads, fh)
        ]


# ----------------- CSV  ---------------------------------------------
def save_csv(cands: Sequence[Candidate], dst: Path | str) -> None:
    dst = _ensure_dir(Path(dst))
    fieldnames = ["id", "gen", "ts", "code"] + [k for k in vars(cands[0].fitness) if k not in {"rank", "crowd"}]
    with dst.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for c in cands:
            row = {"id": c.id, "gen": c.gen, "ts": c.ts, "code": c.code}
            row.update(asdict(c.fitness))
            writer.writerow(row)


# ----------------- Parquet (optional) -------------------------------
def save_parquet(cands: Sequence[Candidate], dst: Path | str) -> None:
    try:
        import pandas as pd  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pandas is required for Parquet export") from e
    df = pd.DataFrame([asdict(c) | asdict(c.fitness) for c in cands])
    df.to_parquet(_ensure_dir(Path(dst)), index=False)


# ----------------- CLI ----------------------------------------------
def _cli_info(db: Path) -> None:
    rows = load(db)
    gens = {c.gen for c in rows}
    print(
        f"📦  {len(rows)} rows, {len(gens)} generations "
        f"(min={min(gens) if gens else '-'} · max={max(gens) if gens else '-'})"
    )
    print(f"Pareto-front size: {len(pareto_front(rows))}")


def _cli_export(db: Path, dst: Path) -> None:
    rows = load(db)
    ext = dst.suffix.lower()
    if ext == ".jsonl":
        save_jsonl(rows, dst)
    elif ext == ".csv":
        save_csv(rows, dst)
    elif ext in {".parquet", ".pq"}:
        save_parquet(rows, dst)
    else:
        raise ValueError("Unsupported export format: " + dst.suffix)
    print("✅  exported →", dst)


def _cli_import(src: Path, db: Path) -> None:
    rows = load_jsonl(src) if src.suffix.lower() == ".jsonl" else None
    if rows is None:
        raise ValueError("Only JSONL import is supported right now.")
    for c in rows:
        insert(c, db)
    print(f"✅  imported {len(rows)} rows into {db}")


def _cli_tail(db: Path) -> None:
    for c in stream(db):
        print(json.dumps(asdict(c), ensure_ascii=False))


def _cli_vacuum(db: Path) -> None:
    with _cx(db) as cx:
        cx.execute("VACUUM")
    print("🧹  VACUUM complete")


def _parse_cli():
    ap = argparse.ArgumentParser(prog="archive.py", description="Meta-Agentic α-AGI lineage toolbox")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # info
    p = sub.add_parser("info", help="quick stats")
    p.add_argument("db", type=Path)

    # export
    p = sub.add_parser("export", help="dump archive to file")
    p.add_argument("db", type=Path)
    p.add_argument("dst", type=Path)

    # import
    p = sub.add_parser("import", help="merge JSONL into DB")
    p.add_argument("src", type=Path)
    p.add_argument("db", type=Path)

    # tail
    p = sub.add_parser("tail", help="follow DB changes (like tail -f)")
    p.add_argument("db", type=Path)

    # vacuum
    p = sub.add_parser("vacuum", help="VACUUM optimise DB")
    p.add_argument("db", type=Path)

    return ap.parse_args()


def _main_cli() -> None:  # pragma: no cover
    args = _parse_cli()
    if args.cmd == "info":
        _cli_info(args.db)
    elif args.cmd == "export":
        _cli_export(args.db, args.dst)
    elif args.cmd == "import":
        _cli_import(args.src, args.db)
    elif args.cmd == "tail":
        _cli_tail(args.db)
    elif args.cmd == "vacuum":
        _cli_vacuum(args.db)


if __name__ == "__main__":  # pragma: no cover
    _main_cli()

# -------------------------------------------------------------------
# 7 · SELF-TESTS  (pytest / doctest friendly)
# -------------------------------------------------------------------
#
# Run “pytest -q archive.py”  or  “python -m doctest -v archive.py”
# to verify core invariants.  Tests never touch the user’s filesystem;
# everything is executed in a *temp* dir.

from tempfile import TemporaryDirectory

try:
    import pytest  # type: ignore
except ImportError:  # Embedded self-tests are optional; archive users need only stdlib.
    pytest = None


# ---------- doctest examples ---------------------------------------
def _example_candidate() -> Candidate:  # pragma: no cover
    """
    Quick interaction demo.

    >>> from datetime import datetime
    >>> c = _example_candidate()
    >>> with TemporaryDirectory() as directory:
    ...     db = Path(directory) / 'example.sqlite'
    ...     insert(c, db)
    ...     load(db)[0].id == c.id
    True
    """
    return Candidate(
        id=1,
        gen=0,
        ts=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        code="def foo(): pass",
        fitness=Fitness(accuracy=0.9, latency=1.0, cost=0.01, carbon=0.0, novelty=0.1),
    )


# ---------- pytest --------------------------------------------------
def tmpdb():
    with TemporaryDirectory() as td:
        yield Path(td) / "lineage.sqlite"


if pytest is not None:
    tmpdb = pytest.fixture()(tmpdb)


def test_roundtrip(tmpdb):
    cand = _example_candidate()
    insert(cand, tmpdb)
    rows = load(tmpdb)
    assert len(rows) == 1
    assert rows[0].fitness.accuracy == cand.fitness.accuracy


def test_pareto_front(tmpdb):
    # two identical fitness → both are on front
    f = Fitness(0.8, 1, 1, 0, 0.1)
    insert(Candidate(1, 0, "t", "c", f), tmpdb)
    insert(Candidate(2, 0, "t", "c", replace(f, accuracy=0.9)), tmpdb)
    cand = load(tmpdb)
    front = pareto_front(cand)
    assert all(c.fitness.rank == 1 for c in front)
    assert len(front) == 1  # second dominates first


def test_novelty():
    a = "print('hello world')"
    b = "print('goodbye world')"
    assert shannon_novelty(a) == 0.0
    assert 0 <= jaccard_novelty(a, b) <= 1
