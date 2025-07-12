#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Meta-Agentic α-AGI Demo v3 — Production Grade
============================================

A *single* entry-point that can launch as:

 • **CLI** evolutionary demo:     `python meta_agentic_agi_demo_v3.py`
 • **Streamlit** lineage UI:      `python meta_agentic_agi_demo_v3.py -m streamlit`
 • **FastAPI** micro-service:     `python meta_agentic_agi_demo_v3.py -m api`

(Model provider & curriculum engine are runtime-selectable).

Dependencies (auto-install via `pip install -r requirements.txt`):

    openai>=1.0.0
    anthropic>=0.25
    llama-cpp-python>=0.2.73
    streamlit>=1.30
    fastapi>=0.111  uvicorn>=0.29
    rich>=13.7

All secondary imports are *lazy* — if a package is missing, the
feature quietly degrades instead of crashing.

© 2025 Montreal.AI  ·  Apache-2.0
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import json
import logging
import os
import pathlib
import random
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# --------------------------------------------------------------------------- #
#                               Logging set-up                                #
# --------------------------------------------------------------------------- #
LOG_LVL = os.getenv("METAAGI_LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LVL,
    format="%(asctime)s | %(name)-15s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
LOG = logging.getLogger("metaagi")


# --------------------------------------------------------------------------- #
#                 Foundation-Model Provider Abstractions                      #
# --------------------------------------------------------------------------- #
class BaseProvider:
    """Minimal synchronous chat interface shared by all providers."""

    name: str = "base"

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.4,
        max_tokens: int = 1024,
    ) -> str:  # noqa: D401
        """Return LLM completion for *(system,user)* messages."""
        raise NotImplementedError


class _Lazy:
    """Helper for optional imports (avoids try/except clutter)."""

    @staticmethod
    def require(pkg: str, err: str) -> Any:
        with contextlib.suppress(ModuleNotFoundError):
            return importlib.import_module(pkg)
        raise RuntimeError(err)


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini"):
        openai = _Lazy.require(
            "openai",
            "Package `openai` missing - `pip install openai` or choose another provider.",
        )
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set.")
        self._client = openai.OpenAI()
        self._model = model

    def chat(self, system: str, user: str, **kw) -> str:  # type: ignore[override]
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **kw,
        )
        return resp.choices[0].message.content.strip()


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-3-sonnet-20240229"):
        anthropic = _Lazy.require(
            "anthropic",
            "Package `anthropic` missing - `pip install anthropic` or pick another provider.",
        )
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set.")
        self._client = anthropic.Anthropic()
        self._model = model

    def chat(self, system: str, user: str, **kw) -> str:  # type: ignore[override]
        resp = self._client.messages.create(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": user}],
            **kw,
        )
        # anthropic splits content into blocks:
        return "".join(block.text for block in resp.content).strip()


class LocalLlamaProvider(BaseProvider):
    name = "local"

    def __init__(self, path: str, n_ctx: int = 8192):
        llama_cpp = _Lazy.require(
            "llama_cpp",
            "Package `llama-cpp-python` missing - `pip install llama-cpp-python`.",
        )
        if not pathlib.Path(path).exists():
            raise FileNotFoundError(f"Local model not found: {path}")
        self._llm = llama_cpp.Llama(model_path=path, n_ctx=n_ctx, logits_all=False)

    def chat(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 1024, **_) -> str:
        prompt = f"<|system|>{system}\n<|user|>{user}\n<|assistant|>"
        out = self._llm(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=["</s>"],
        )
        return out["choices"][0]["text"].strip()


class StubProvider(BaseProvider):
    name = "stub"

    def chat(self, system: str, user: str, **kw) -> str:  # type: ignore[override]
        LOG.debug("StubProvider called - offline mode.")
        return "⚠️ Offline stub: no provider available.\n" f"(Echo of last 120 chars of user prompt)\n\n{user[-120:]}"


def auto_provider(spec: Optional[str] = None) -> BaseProvider:
    """Instantiate the best available provider, respecting an optional spec."""
    if spec:
        pid, *rest = spec.split(":", 1)
        if pid in {"openai", "oai"}:
            return OpenAIProvider(rest[0] if rest else "gpt-4o-mini")
        if pid in {"anthropic", "claude"}:
            return AnthropicProvider(rest[0] if rest else "claude-3-sonnet-20240229")
        if pid in {"local", "gguf"}:
            mpath = rest[0] if rest else os.getenv("LOCAL_MODEL_PATH", "mistral-7b-instruct.gguf")
            return LocalLlamaProvider(mpath)

    # Auto-detect precedence
    with contextlib.suppress(Exception):
        return OpenAIProvider()
    with contextlib.suppress(Exception):
        return AnthropicProvider()
    mpath = os.getenv("LOCAL_MODEL_PATH", "mistral-7b-instruct.gguf")
    if pathlib.Path(mpath).exists():
        return LocalLlamaProvider(mpath)
    LOG.warning("No FM provider available – falling back to stub.")
    return StubProvider()


# --------------------------------------------------------------------------- #
#                         Lineage Storage & Audit Log                         #
# --------------------------------------------------------------------------- #
class LineageDB:
    """Tiny SQLite helper – stores agent lineage & event audit stream."""

    def __init__(self, path: str = "meta_agentic_agi.sqlite"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS agent_lineage (
                   id          INTEGER PRIMARY KEY AUTOINCREMENT,
                   generation  INTEGER,
                   agent_code  TEXT,
                   metrics     TEXT,
                   ts          REAL
               );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS events (
                   id      INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts      REAL,
                   kind    TEXT,
                   payload TEXT
               );"""
        )
        self._conn.commit()

    # ----- persisters ----------------------------------------------------- #
    def agent(self, gen: int, code: str, metrics: Dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO agent_lineage(generation,agent_code,metrics,ts) VALUES(?,?,?,?)",
            (gen, code, json.dumps(metrics, separators=(",", ":")), time.time()),
        )
        self._conn.commit()

    def event(self, kind: str, payload: Dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO events(ts,kind,payload) VALUES(?,?,?)",
            (time.time(), kind, json.dumps(payload, separators=(",", ":"))),
        )
        self._conn.commit()

    # ----- convenience getters for UI / API ------------------------------ #
    def fetch_agents(self) -> List[Dict[str, Any]]:
        cur = self._conn.execute("SELECT generation,agent_code,metrics,ts FROM agent_lineage ORDER BY id")
        return [
            {
                "generation": g,
                "code": code,
                "metrics": json.loads(mets),
                "ts": ts,
            }
            for g, code, mets, ts in cur.fetchall()
        ]

    def fetch_events(self, since_id: int = 0) -> List[Dict[str, Any]]:
        cur = self._conn.execute("SELECT id,ts,kind,payload FROM events WHERE id>?", (since_id,))
        return [{"id": i, "ts": ts, "kind": k, "payload": json.loads(p)} for i, ts, k, p in cur.fetchall()]


# --------------------------------------------------------------------------- #
#               Candidate Agent & Evolutionary Search Utilities              #
# --------------------------------------------------------------------------- #
@dataclass
class Candidate:
    """Simple container representing a generated agent solution."""

    code: str
    metrics: Dict[str, Any] = field(default_factory=dict)


# ---------------------------- secure execution ----------------------------- #
_FORBIDDEN = (
    "os.",
    "sys.",
    "subprocess",
    "socket",
    "threading",
    "multiprocessing",
    "asyncio",
    "signal",
)


def _safe_exec(agent_code: str, x: Any, timeout: int = 3) -> Optional[str]:
    """
    Run candidate code in a *very* restrictive subprocess.

    Returns `str(output)` or `None` on error / policy violation.
    """
    if any(tok in agent_code for tok in _FORBIDDEN):
        return None

    # Wrap candidate into isolated script
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as tmp:
        tmp.write(
            agent_code
            + "\n\n"
            + textwrap.dedent(
                f"""
                if __name__ == '__main__':
                    import json, sys
                    try:
                        _res = agent({json.dumps(x)})
                        print(json.dumps(_res, separators=(',', ':')))
                    except Exception as e:
                        print(repr(e), file=sys.stderr)
                """
            )
        )
        tmp.flush()
        script = tmp.name

    # Launch in capped resource subprocess
    cmd = [sys.executable, script]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return None
    finally:
        with contextlib.suppress(OSError):
            os.remove(script)
    if err.strip():
        return None
    return out.strip()


# --------------------------------------------------------------------------- #
#                        Evolutionary Search (NSGA-Lite)                      #
# --------------------------------------------------------------------------- #
async def evolutionary_search(
    fm: BaseProvider,
    db: LineageDB,
    *,
    generations: int = 8,
    pop_size: int = 6,
) -> Candidate:
    """
    Minimal multi-objective evolutionary loop
    (accuracy only by default for brevity & speed).
    """
    # Run-time import of AZR curriculum (ensures we don’t require it if absent).
    try:
        from curriculum.azr_engine import curriculum_factory  # type: ignore
    except ImportError as exc:  # pragma: no cover
        LOG.error("AZR engine missing - did you pull sub-module? %s", exc)
        raise

    azr = curriculum_factory(fm)
    rng = random.Random(2025)

    # Seed population with identity agent
    population: List[Candidate] = [
        Candidate(
            code=textwrap.dedent(
                """
                def agent(x):
                    \"\"\"Identity baseline.\"\"\"
                    return x
                """
            ).strip()
        )
    ]
    db.agent(0, population[0].code, {"seed": True})
    LOG.info("🚀 Evolutionary run begins | generations=%d | pop=%d", generations, pop_size)

    for gen in range(1, generations + 1):
        # --- AZR self-curriculum ------------------------------------------------ #
        tasks = azr.propose(k=max(4, pop_size))  # new challenges
        solve_res = azr.solve(tasks)
        azr.learn(solve_res)
        db.event(
            "AZR",
            {
                "gen": gen,
                "tasks": len(tasks),
                "solved": sum(r.solved for r in solve_res),
                "temperature": getattr(azr, "temperature", None),
            },
        )

        # --- Generate new offspring via FM builder ----------------------------- #
        offspring: List[Candidate] = []
        for _ in range(pop_size):
            # Small in-context prompt (2 AZR tasks) → new agent code
            ctx = "\n\n".join(f"# Task:\n{t.program[:120]} …" for t in rng.sample(tasks, k=min(2, len(tasks))))
            prompt = (
                "Write a *deterministic* Python function `agent(x)` that can solve tasks like:\n"
                f"{ctx}\n\n"
                "Return *only* the code block."
            )
            code = fm.chat("You are Builder-Agent.", prompt, temperature=0.7, max_tokens=400)
            # ensure we only keep the code part
            if "def agent" not in code:
                code = "def agent(x):\n    return x"
            offspring.append(Candidate(code.strip()))

        # --- Evaluate on AZR tasks --------------------------------------------- #
        for cand in offspring:
            correct = 0
            for t in tasks:
                inp = json.loads(t.inp)  # type: ignore[arg-type]
                expected = t.out.strip()
                out = _safe_exec(cand.code.replace("def agent", "def main"), inp)
                if out == expected:
                    correct += 1
            cand.metrics = {"correct": correct, "total": len(tasks)}

        # --- Selection (keep best by accuracy, break ties by shorter code) ------ #
        population.extend(offspring)
        population.sort(
            key=lambda c: (-c.metrics.get("correct", 0), len(c.code)),
        )
        population = population[:pop_size]
        best = population[0]
        db.agent(gen, best.code, best.metrics)
        LOG.info(
            "Gen %02d | best %d/%d | code_len=%d",
            gen,
            best.metrics["correct"],
            len(tasks),
            len(best.code.splitlines()),
        )

    LOG.info("✅ Evolution finished. Best metrics: %s", best.metrics)
    return best


# --------------------------------------------------------------------------- #
#                           Deployment mode wrappers                          #
# --------------------------------------------------------------------------- #
def _print_banner() -> None:
    banner = r"""
     __  __      _            _           _   _____ ____  _   _
    |  \/  | ___| |_ ___  ___| |__   __ _| |_|___ /|  _ \| | | |
    | |\/| |/ _ \ __/ _ \/ __| '_ \ / _` | __| |_ \| |_) | |_| |
    | |  | |  __/ ||  __/ (__| | | | (_| | |____) |  __/|  _  |
    |_|  |_|\___|\__\___|\___|_| |_|\__,_|\__|____/|_|   |_| |_|

    """
    print(banner)


# ---------- CLI ------------------------------------------------------------ #
def run_cli(args, fm: BaseProvider, db: LineageDB) -> None:
    _print_banner()
    best = asyncio.run(
        evolutionary_search(
            fm,
            db,
            generations=args.gens,
            pop_size=args.pop_size,
        )
    )
    print("\n✔  Run complete.\n")
    print(best.code)
    print(
        f"\n🔍  Open the lineage dashboard:\n"
        f"    streamlit run {pathlib.Path(__file__).with_name('ui_lineage_app.py')} "
        f"-- --db {args.db}\n"
    )


# ---------- Streamlit UI --------------------------------------------------- #
def run_streamlit(args) -> None:
    try:
        import pandas as pd
        import streamlit as st
    except ImportError:
        print("⚠  Install UI deps:  pip install streamlit pandas", file=sys.stderr)
        sys.exit(1)

    db_path = args.db
    conn = sqlite3.connect(db_path)

    st.set_page_config(page_title="Meta-Agentic AGI Lineage", layout="wide", page_icon="🧬")
    st.title("📈 Meta-Agentic α-AGI Lineage")

    # Auto-refresh every few seconds
    poll = st.sidebar.slider("Refresh interval (s)", 2, 30, 5)

    def load_agents():
        return pd.read_sql("SELECT * FROM agent_lineage ORDER BY id", conn)

    placeholder = st.empty()
    last = 0
    while True:
        with placeholder.container():
            df = load_agents()
            st.write(f"Loaded {len(df)} agents")
            st.dataframe(df, height=600, use_container_width=True)
        time.sleep(poll)


# ---------- FastAPI service ------------------------------------------------ #
def run_api(args, fm: BaseProvider, db: LineageDB) -> None:
    try:
        from fastapi import FastAPI
        from contextlib import asynccontextmanager
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError:
        print("⚠  Install API deps:  pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)

    app = FastAPI(title="Meta-Agentic α-AGI API")
    state: Dict[str, Any] = {"best": None}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        state["best"] = await evolutionary_search(
            fm,
            db,
            generations=args.gens,
            pop_size=args.pop_size,
        )
        yield

    app.router.lifespan_context = lifespan

    @app.get("/status")
    def status() -> Dict[str, Any]:
        best = state["best"]
        return {"ready": best is not None}

    @app.get("/best")
    def best() -> JSONResponse:
        if state["best"] is None:  # type: ignore[comparison-overlap]
            return JSONResponse({"status": "running"}, status_code=202)
        return JSONResponse({"code": state["best"].code})  # type: ignore[index]

    uvicorn.run(app, host="0.0.0.0", port=args.port)


# --------------------------------------------------------------------------- #
#                                    CLI                                      #
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Meta-Agentic α-AGI Demo v3")
    p.add_argument(
        "-p",
        "--provider",
        help="provider spec " "(openai[:model] | anthropic[:model] | local[:/path/model.gguf] | stub)",
    )
    p.add_argument("-g", "--gens", type=int, default=int(os.getenv("ALPHA_N_GEN", 8)))
    p.add_argument("-n", "--pop_size", type=int, default=int(os.getenv("ALPHA_POP_SIZE", 6)))
    p.add_argument("-m", "--mode", choices=["cli", "streamlit", "api"], default="cli", help="deployment mode")
    p.add_argument(
        "--db",
        default=os.getenv("METAAGI_DB", "meta_agentic_agi.sqlite"),
        help="SQLite DB for lineage",
    )
    p.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("METAAGI_API_PORT", 8000)),
        help="Port for FastAPI mode",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    fm = auto_provider(args.provider)
    LOG.info("Using provider: %s", fm.name)
    db = LineageDB(args.db)

    if args.mode == "cli":
        run_cli(args, fm, db)
    elif args.mode == "streamlit":
        run_streamlit(args)
    elif args.mode == "api":
        run_api(args, fm, db)
    else:  # pragma: no cover
        raise ValueError(f"Unknown mode {args.mode}")


if __name__ == "__main__":
    main()
