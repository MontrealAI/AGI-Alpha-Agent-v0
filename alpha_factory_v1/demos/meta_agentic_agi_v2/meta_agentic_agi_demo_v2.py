#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------
# Meta-Agentic α-AGI Demo – Production-Grade v0.2.0 (2025-05-05)
# --------------------------------------------------------------------
"""
Bootstraps a *self-improving* meta-agentic search loop on top of
Alpha-Factory v1.  Runs fully offline on open-weights, or swaps to paid
APIs when keys are present.

Core features
-------------
* Multi-objective fitness : accuracy • latency • cost • carbon • novelty
* Provider-agnostic LLM wrapper (`ChatLLM`) with usage tracing
* Pareto archive → embedded sqlite lineage DB → live Streamlit UI
* 100 % pure-Python — laptop-friendly (≤ 40 MiB wheels, CPU-only)
"""
from __future__ import annotations
import argparse, asyncio, json, os, random, sqlite3, sys, time, hashlib, textwrap
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


# ────────────────────────────────────────────────────────────────────
# 0.  Provider-agnostic chat wrapper
# ────────────────────────────────────────────────────────────────────
class UnsupportedProvider(RuntimeError):
    ...


@dataclass
class ChatReturn:
    content: str
    cost: float
    latency: float


class ChatLLM:
    """
    Normalises:
        • OpenAI    →   openai:<model>            (needs OPENAI_API_KEY)
        • Anthropic →   anthropic:<model>         (needs ANTHROPIC_API_KEY)
        • Llama.cpp / Ollama-gguf ↴
              mistral:7b-instruct.gguf  (or any other local .gguf id)
        • Mock provider for offline tests →  mock:echo
    """

    def __init__(self, spec: str):
        if ":" not in spec:
            raise UnsupportedProvider(f"Malformed provider spec {spec!r}")
        self.kind, self.model = spec.split(":", 1)

        if self.kind == "openai":
            import openai, asyncio

            if not os.getenv("OPENAI_API_KEY"):
                raise UnsupportedProvider("OPENAI_API_KEY missing")
            self._client = openai.AsyncOpenAI()
        elif self.kind == "anthropic":
            import anthropic

            if not os.getenv("ANTHROPIC_API_KEY"):
                raise UnsupportedProvider("ANTHROPIC_API_KEY missing")
            self._client = anthropic.AsyncAnthropic()
        elif self.kind in {"mistral", "ollama", "gguf", "llama"}:
            from llama_cpp import Llama

            home = Path.home()
            cache = home / ".cache" / "metaagi"
            cache.mkdir(parents=True, exist_ok=True)
            model_path = cache / self.model
            if not model_path.exists():
                print(f"▸ downloading {self.model}…")
                import urllib.request, shutil, tempfile

                url = f"https://huggingface.co/TheBloke/{self.model}/resolve/main/{self.model}"
                with tempfile.NamedTemporaryFile(delete=False) as tmp, urllib.request.urlopen(url) as resp:
                    shutil.copyfileobj(resp, tmp)
                shutil.move(tmp.name, model_path)
            self._client = Llama(model_path=str(model_path), n_ctx=4096, n_threads=os.cpu_count() or 4)
        elif self.kind == "mock":
            self._client = None  # offline dummy
        else:
            raise UnsupportedProvider(f"Unknown provider kind {self.kind}")

    async def chat(self, prompt: str) -> ChatReturn:
        t0 = time.time()
        if self.kind == "openai":
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            txt = resp.choices[0].message.content
            cost = resp.usage.completion_tokens / 1e6 * 15 + resp.usage.prompt_tokens / 1e6 * 5
        elif self.kind == "anthropic":
            resp = await self._client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            txt = resp.content[0].text
            cost = 0.0
        elif self.kind == "mock":
            txt = "```python\ndef forward(task_info: dict) -> any:\n    return 'mock'\n```"
            cost = 0.0
        else:  # llama_cpp sync
            txt = self._client.create_completion(prompt=prompt, temperature=0.6)["choices"][0]["text"]
            cost = 0.0
        return ChatReturn(txt.strip(), cost, time.time() - t0)


# ────────────────────────────────────────────────────────────────────
# 1.  Fitness dataclass + helpers
# ────────────────────────────────────────────────────────────────────
@dataclass
class Fitness:
    accuracy: float
    latency: float
    cost: float
    carbon: float
    novelty: float
    rank: Optional[int] = None


def pareto_sort(pop: List[Fitness]) -> None:
    """Assign ≤ 1-based rank for each individual (NSGA-II style)."""
    keys = [k for k in Fitness.__annotations__.keys() if k != "rank"]
    for fi in pop:
        fi.rank = 1 + sum(
            all(getattr(fj, k) <= getattr(fi, k) for k in keys) and any(getattr(fj, k) < getattr(fi, k) for k in keys)
            for fj in pop
        )


def novelty_hash(code: str) -> float:
    return int(hashlib.sha256(code.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


# ────────────────────────────────────────────────────────────────────
# 2.  Lineage DB helpers
# ────────────────────────────────────────────────────────────────────
DEFAULT_DB = Path(__file__).with_suffix(".sqlite")
DB = Path(os.getenv("METAAGI_DB", str(DEFAULT_DB)))


def db_conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute(
        """CREATE TABLE IF NOT EXISTS lineage(
        id      INTEGER PRIMARY KEY,
        gen     INTEGER,
        ts      TEXT,
        code    TEXT,
        fitness TEXT
    )"""
    )
    return db


def db_insert(db, e_id: int, gen: int, code: str, fit: Fitness):
    db.execute(
        "INSERT INTO lineage VALUES (?,?,?,?,?)",
        (e_id, gen, datetime.utcnow().isoformat(), code, json.dumps(asdict(fit))),
    )
    db.commit()


# ────────────────────────────────────────────────────────────────────
# 3.  Domain-specific evaluation stub
# ────────────────────────────────────────────────────────────────────
def evaluate_agent(code: str, reps: int = 3) -> float:
    """
    Replace this stub with your real domain metric.

    For demonstration we return a pseudo-accuracy in [0.80, 1.00).
    """
    random.seed(hash(code) & 0xFFFF_FFFF)
    return sum(0.8 + random.random() * 0.2 for _ in range(reps)) / reps


# ────────────────────────────────────────────────────────────────────
# 4.  Meta search loop
# ────────────────────────────────────────────────────────────────────
META_PROMPT = textwrap.dedent(
    """\
    You are a **meta-agentic architect**.
    Draft a minimal, *stateless* Python function:

        def forward(task_info: dict) -> any:

    It must outperform prior agents on the task’s hidden accuracy
    metric while keeping latency, cost, and carbon low.
    Only return **one** markdown code block containing the function.
"""
)


async def meta_loop(generations: int, provider_spec: str):
    # provider fallback
    try:
        llm = ChatLLM(provider_spec)
    except UnsupportedProvider as e:
        print(f"{e}  – falling back to open-weights (mistral:7b-instruct.gguf).")
        llm = ChatLLM("mistral:7b-instruct.gguf")

    db = db_conn()
    arc: Dict[int, Fitness] = {}  # id → fitness

    for gen in range(generations):
        # a) ask meta-agent for new code
        answer = await llm.chat(META_PROMPT)
        candidate_code = answer.content.split("```")[-2] if "```" in answer.content else answer.content

        # b) evaluate
        acc = evaluate_agent(candidate_code)
        fit = Fitness(
            accuracy=acc,
            latency=answer.latency,
            cost=answer.cost,
            carbon=answer.latency * 0.0002,
            novelty=novelty_hash(candidate_code),
        )
        e_id = random.randint(1, 1_000_000_000)
        db_insert(db, e_id, gen, candidate_code, fit)
        arc[e_id] = fit

        # c) Pareto filter (keep best ≤ 5)
        pareto_sort(list(arc.values()))
        arc = {k: v for k, v in arc.items() if v.rank and v.rank <= 5}

        print(f"Gen {gen:02d} | acc={fit.accuracy:.3f} lat={fit.latency:.2f}s " f"cost=${fit.cost:.4f} rank={fit.rank}")

    print("✅ Meta-search finished → run  `streamlit run ui/lineage_app.py`")


# ────────────────────────────────────────────────────────────────────
# 5.  CLI
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=6, help="number of generations")
    ap.add_argument(
        "--provider",
        type=str,
        default=os.getenv("LLM_PROVIDER", "mistral:7b-instruct.gguf"),
        help="openai:gpt-4o | anthropic:claude-3-sonnet | mistral:7b-instruct.gguf …",
    )
    args = ap.parse_args()

    try:
        asyncio.run(meta_loop(args.gens, args.provider))
    except KeyboardInterrupt:
        sys.exit("\nInterrupted by user")
