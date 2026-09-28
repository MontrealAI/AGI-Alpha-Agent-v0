# SPDX-License-Identifier: Apache-2.0
"""Legacy provider-backed agent primitives and append-only local lineage.

Provider calls use a token-rate limiter and finite retry count. Metrics and risk
are illustrative heuristics. Generated Python always uses the repository Docker
boundary; this module does not promise automatic provider failover or perfect isolation.
"""

from __future__ import annotations

import os, sys, time, json, uuid, math, json, pathlib, logging, importlib, hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Iterable, Callable

try:
    # resource & signal are POSIX only – guard for Windows
    import resource, signal  # type: ignore
except ImportError:
    resource = None  # type: ignore
    signal = None  # type: ignore

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("ALPHA_FACTORY_LOGLEVEL", os.getenv("LOGLEVEL", "INFO")))

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:10]


def _utcnow_ms() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int((time.time()%1)*1000):03d}Z"


def _str_tkn(text: str) -> int:
    # naïve token estimate ≈‑ 1 token / 4 chars in English
    return max(1, math.ceil(len(text) / 4))


# ---------------------------------------------------------------------------
# Rate limiter (token bucket, per‑second)
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, tps: float = 3.0):
        if not math.isfinite(tps) or tps <= 0:
            raise ValueError("Token rate must be positive and finite")
        self._tps = float(tps)
        self._allow = self._tps
        self._last = time.perf_counter()

    def acquire(self, cost: float = 1.0):
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("Token cost must be positive and finite")
        # A request may exceed one second of capacity; debit chunks, not an impossible bucket.
        if cost > self._tps:
            remaining = cost
            while remaining > 0:
                chunk = min(remaining, self._tps)
                self.acquire(chunk)
                remaining -= chunk
            return
        while True:
            now = time.perf_counter()
            elapsed = now - self._last
            self._last = now
            self._allow = min(self._tps, self._allow + elapsed * self._tps)
            if self._allow >= cost:
                self._allow -= cost
                return
            sleep = (cost - self._allow) / self._tps + 1e-3
            time.sleep(sleep)


GLOBAL_LIMITER = RateLimiter(float(os.getenv("ALPHA_TPS", 3)))


# ---------------------------------------------------------------------------
# LM Provider adapter
# ---------------------------------------------------------------------------
class LMClient:
    """Provider‑agnostic chat/completions wrapper."""

    _ENV_MAP = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "llama": None,  # local
    }

    def __init__(
        self,
        endpoint: str = "openai:gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        context_len: int = 8192,
        stream: bool = False,
        timeout: int = 120,
        **extra,
    ):
        self.endpoint = endpoint
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.context_len = context_len
        self.stream = stream
        self.timeout = timeout
        self.extra = extra
        self._backend, self._model = self._parse(endpoint)
        self._client = self._init_backend()

    # .................................
    def _parse(self, ep: str):
        if ":" not in ep:
            raise ValueError("Endpoint must be <backend>:<model>")
        return ep.split(":", 1)

    def _init_backend(self):
        back = self._backend
        if back == "openai":
            mod = importlib.import_module("openai")
            return mod.OpenAI()
        if back == "anthropic":
            mod = importlib.import_module("anthropic")
            return mod.Anthropic()
        if back == "gemini":
            mod = importlib.import_module("google.generativeai")
            return mod.GenerativeModel(self._model)
        if back in ("mistral", "llama"):
            mod = importlib.import_module("llama_cpp")
            return mod.Llama(model_path=self._model, n_ctx=self.context_len)
        raise NotImplementedError(back)

    # .................................
    def chat(self, msgs: List[Dict[str, str]], **kw) -> str:
        merged = {"temperature": self.temperature, "max_tokens": self.max_tokens, **kw}
        attempts = 0
        while True:
            GLOBAL_LIMITER.acquire(_str_tkn(json.dumps(msgs)))
            try:
                if self._backend == "openai":
                    rsp = self._client.chat.completions.create(model=self._model, messages=msgs, stream=False, **merged)
                    return rsp.choices[0].message.content
                if self._backend == "anthropic":
                    rsp = self._client.messages.create(model=self._model, messages=msgs, **merged)
                    return rsp.content[0].text
                if self._backend == "gemini":
                    return self._client.generate_content(msgs[-1]["content"], **merged).text
                if self._backend in ("mistral", "llama"):
                    prompt = "".join(f"<{m['role']}> {m['content']}" for m in msgs) + "\n<assistant> "
                    out = self._client(
                        prompt, max_tokens=self.max_tokens, temperature=self.temperature, stop=["</assistant>"]
                    )
                    return out["choices"][0]["text"].strip()
            except Exception as e:
                attempts += 1
                if attempts >= 3:
                    raise RuntimeError("Provider failed after three attempts") from e
                wait = min(60, 2**attempts)
                LOGGER.warning("LM error %s; retry in %.1fs", e, wait)
                time.sleep(wait)


# ---------------------------------------------------------------------------
# Lineage tracer & UI stub
# ---------------------------------------------------------------------------
class LineageTracer:
    def __init__(self, ledger_path: str | pathlib.Path):
        self.path = pathlib.Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **payload):
        with self.path.open("a", encoding="utf-8") as fp:
            json.dump({"ts": _utcnow_ms(), "event": event, **payload}, fp, ensure_ascii=False)
            fp.write("\n")


# ---------------------------------------------------------------------------
# Multi‑objective scorer
# ---------------------------------------------------------------------------
@dataclass
class ObjectiveWeights:
    latency: float = 0.2
    cost: float = 0.3
    carbon: float = 0.2
    risk: float = 0.3

    def score(self, metrics: Dict[str, float]) -> float:
        return (
            self.latency * (1 / (1 + metrics.get("latency", 0)))
            + self.cost * (1 / (1 + metrics.get("cost", 0)))
            + self.carbon * (1 / (1 + metrics.get("carbon", 0)))
            + self.risk * (1 - metrics.get("risk", 0))
        )


# ---------------------------------------------------------------------------
# Agent base‑class
# ---------------------------------------------------------------------------
class Agent:
    def __init__(
        self,
        name: str,
        role: str = "autonomous‑agent",
        provider: str | None = None,
        objectives: Optional[ObjectiveWeights] = None,
        lineage_dir: str | pathlib.Path = "./lineage",
        rate_limit_tps: float = 3.0,
    ):
        self.name = name
        self.role = role
        self.id = f"{name}-{_sha(uuid.uuid4().hex)}"
        self.objectives = objectives or ObjectiveWeights()
        self.lm = LMClient(provider or os.getenv("ALPHA_PROVIDER", "openai:gpt-4o"))
        self.tracer = LineageTracer(pathlib.Path(lineage_dir) / f"{self.id}.jsonl")
        self.tracer.log("init", role=role, provider=self.lm.endpoint)
        GLOBAL_LIMITER._tps = rate_limit_tps

    # .................................................................
    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        price = float(os.getenv("ALPHA_USD_PER_M", 0.01))  # user override
        return ((prompt_tokens + completion_tokens) / 1_000_000) * price

    def run(self, prompt: str, context: Optional[Iterable[Dict[str, str]]] = None, **kw) -> Dict[str, Any]:
        ctx: List[Dict[str, str]] = list(context or [])
        ctx.append({"role": "user", "content": prompt})
        t0 = time.perf_counter()
        output = self.lm.chat(ctx, **kw)
        latency = time.perf_counter() - t0
        tokens_in = _str_tkn(prompt)
        tokens_out = _str_tkn(output)
        cost = self._estimate_cost(tokens_in, tokens_out)
        carbon = cost * 0.00015  # placeholder multiplier (avg kgCO2 per $ cloud)
        risk = self._risk_assess(prompt, output)
        metrics = dict(latency=latency, cost=cost, carbon=carbon, risk=risk)
        score = self.objectives.score(metrics)
        self.tracer.log("run", prompt=prompt[:120], response=output[:120], metrics=metrics, score=score)
        return {"response": output, "metrics": metrics, "score": score}

    # .................................................................
    def _risk_assess(self, prompt: str, response: str) -> float:
        # toy heuristic: long responses & code carry more risk
        return min(1.0, 0.1 + 0.9 * (len(response) / 4000))

    # .................................................................
    def __call__(self, prompt: str, **kw):
        return self.run(prompt, **kw)


# ---------------------------------------------------------------------------
# Sandbox utilities for dynamic code exec (optional)
# ---------------------------------------------------------------------------
class SafeExec:
    """Compatibility adapter for the shared Docker isolation boundary.

    The legacy cpu_sec/mem_mb arguments are retained. Effective limits are the
    repository sandbox's 120 seconds, 2 GiB, no network and read-only filesystem.
    Host resource limits are never modified.
    """

    def __init__(self, cpu_sec: int = 2, mem_mb: int = 128):
        self.cpu_sec = cpu_sec
        self.mem_mb = mem_mb

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, code: str, func_name: str, *args, **kw):
        from ..isolation import run_python

        return json.loads(run_python(code, func_name, args, kw))


# ---------------------------------------------------------------------------
# Simple lineage viewer (optional)
# ---------------------------------------------------------------------------
VIEW_HTML = """<!doctype html>
<title>Agent Lineage</title>
<script src=\"https://unpkg.com/htmx.org@1.9.10\"></script>
<style>body{font-family:sans-serif;background:#f7f9fb}pre{white-space:pre-wrap}</style>
<h2>Lineage log</h2>
<pre hx-get="/log" hx-trigger="load, every 2s"></pre>"""


def serve_lineage(path: pathlib.Path, port: int = 8000):
    import flask, threading

    app = flask.Flask("lineage-viewer")

    @app.route("/")
    def idx():
        return VIEW_HTML

    @app.route("/log")
    def log():
        if not path.exists():
            return "(no events yet)"
        from markupsafe import escape

        return escape(path.read_text("utf-8"))

    th = threading.Thread(target=app.run, kwargs=dict(port=port, host="127.0.0.1", debug=False))
    th.daemon = True
    th.start()
    LOGGER.info("Lineage viewer at http://localhost:%d", port)
    return th


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = Agent("demo", role="example")
    rsp = agent("Hello! Summarise ADAS in one sentence.")
    print(rsp["response"])
