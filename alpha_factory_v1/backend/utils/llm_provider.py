# SPDX-License-Identifier: Apache-2.0
"""
alpha_factory_v1.backend.utils.llm_provider
===========================================

Battle-hardened one-liner interface to any large-language-model back-end
(OpenAI, Anthropic, Google Gemini, Mistral, Together AI, HF-TGI, Ollama,
llama-cpp …) with graceful, zero-downtime degradation all the way down to an
offline quantised GGUF model.

Public API
----------
>>> from alpha_factory_v1.backend.utils.llm_provider import LLMProvider
>>> llm = LLMProvider()
>>> print(llm.chat("Explain risk-parity like I'm five."))

Extras
~~~~~~
* ``LLMProvider.achat`` – `async` variant (awaitable).
* CLI smoke-test: ``python -m alpha_factory_v1.backend.utils.llm_provider
  --prompt "quick demo"``

Design pillars
--------------
1. Single **call-site** for every agent → ``llm.chat(...)``.
2. **Provider-cascade** → automatic fail-over & rate-limit budgeting.
3. **Disk cache** (SQLite) + in-mem LRU to slash cost/latency.
4. Full **observability** – Prometheus counters + latency histograms.
5. **Extensible** – drop a new provider in `_providers/` and it registers
   automatically (≤10 LOC).
6. Runs **with or without** any cloud API key; offline path via llama-cpp.

"""
from __future__ import annotations

# ───────────────────────── stdlib ──────────────────────────
import asyncio
import dataclasses
import functools
import hashlib
import json
import logging
import os
import pathlib
import sqlite3
import time
from collections import OrderedDict
from types import GeneratorType
from typing import Any, Dict, Generator, List, Optional, Sequence

from alpha_factory_v1.core.monitoring import metrics
from alpha_factory_v1.backend import metrics_registry

# ──────────────────── optional dependencies ────────────────
_HAS_PROM = _HAS_TOK = False
try:
    from prometheus_client import Counter, Histogram  # type: ignore

    _HAS_PROM = True
except Exception:
    pass
try:
    import tiktoken  # type: ignore

    _HAS_TOK = True
except Exception:
    pass

# will lazily import heavy provider libs later

# ───────────────────────── logging ─────────────────────────
_log = logging.getLogger("alpha_factory.llm_provider")
if not _log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", "%H:%M:%S"))
    _log.addHandler(h)
_log.setLevel(logging.INFO)

# ───────────────────── Prometheus metrics ──────────────────
if _HAS_PROM:
    _CNT_REQ = metrics_registry.get_metric(
        Counter,
        "af_llm_requests_total",
        "LLM requests",
        ["provider", "status"],
    )
    _CNT_TOK = metrics_registry.get_metric(
        Counter,
        "af_llm_tokens_total",
        "Tokens used",
        ["provider"],
    )
    _HIST_LAT = metrics_registry.get_metric(
        Histogram,
        "af_llm_latency_seconds",
        "Latency",
        ["provider"],
    )
else:  # no-op stubs

    class _N:
        def labels(self, *_, **__):
            return self

        def inc(self, *_, **__):
            ...

        def observe(self, *_, **__):
            ...

    _CNT_REQ = _CNT_TOK = _HIST_LAT = _N()  # type: ignore


# ─────────────────── token estimation util ─────────────────
@functools.lru_cache(maxsize=8)
def _enc(model: str = "cl100k_base"):  # OpenAI default vocab
    return tiktoken.get_encoding(model) if _HAS_TOK else None


def _count_tokens(text: str) -> int:
    e = _enc()
    if e:
        return len(e.encode(text))
    # 1 token ≈ 4 chars heuristic
    return max(1, len(text) // 4)


# ───────────────────────── cache ───────────────────────────
_TTL = int(os.getenv("AF_LLM_CACHE_TTL", "86400"))  # 1 day default
_CACHE_SIZE = int(os.getenv("AF_LLM_CACHE_SIZE", "1024"))  # in-memory entries
_cache_mem: OrderedDict[str, tuple[float, str]] = OrderedDict()

_db_path = pathlib.Path(os.getenv("AF_LLM_CACHE_PATH", pathlib.Path.home() / ".cache" / "alpha_factory_llm.sqlite"))


def _db_init() -> sqlite3.Connection | None:
    try:
        _db_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(_db_path)
        db.execute("PRAGMA journal_mode=WAL;")
        db.execute(
            """CREATE TABLE IF NOT EXISTS cache
                   (h TEXT PRIMARY KEY, ts REAL, out TEXT, provider TEXT)"""
        )
        os.chmod(_db_path, 0o600)
        return db
    except Exception as exc:
        _log.warning("Disk-cache disabled: %s", exc)
        return None


_DB = _db_init()


def _cache_get(h: str) -> str | None:
    # in-memory first
    v = _cache_mem.get(h)
    if v:
        if time.time() - v[0] < _TTL:
            _cache_mem.move_to_end(h)
            return v[1]
        _cache_mem.pop(h, None)
    if _DB:
        row = _DB.execute(
            "SELECT out, ts FROM cache WHERE h=? AND ?-ts<?",
            (h, time.time(), _TTL),
        ).fetchone()
        if row:
            return row[0]
    return None


def _cache_put(h: str, out: str, prov: str) -> None:
    _cache_mem[h] = (time.time(), out)
    _cache_mem.move_to_end(h)
    if len(_cache_mem) > _CACHE_SIZE:
        _cache_mem.popitem(last=False)
    if _DB:
        with _DB:
            _DB.execute(
                "INSERT OR REPLACE INTO cache VALUES (?,?,?,?)",
                (h, time.time(), out, prov),
            )


# ───────────────── rate-limit budgeting ────────────────────
@dataclasses.dataclass
class _Budget:
    rpm: int = int(os.getenv("AF_RPM_LIMIT", "900"))  # requests / min
    tpm: int = int(os.getenv("AF_TPM_LIMIT", "60000"))  # tokens / min
    # sliding window
    _req_ts: List[float] = dataclasses.field(default_factory=list)
    _tok_ts: List[tuple[float, int]] = dataclasses.field(default_factory=list)

    def allow(self, tokens: int) -> bool:
        now = time.time()
        # purge old
        self._req_ts = [t for t in self._req_ts if now - t < 60]
        self._tok_ts = [p for p in self._tok_ts if now - p[0] < 60]
        if len(self._req_ts) >= self.rpm:
            return False
        if sum(t for _, t in self._tok_ts) + tokens > self.tpm:
            return False
        # record
        self._req_ts.append(now)
        self._tok_ts.append((now, tokens))
        return True


# ───────────────── provider base class ─────────────────────
class _Provider:
    name: str = "base"
    _budget = _Budget()

    # ----- helpers ---------------------------------------------------------
    def _record(self, ok: bool, tokens: int | None, lat: float) -> None:
        _CNT_REQ.labels(self.name, "ok" if ok else "fail").inc()
        if tokens:
            _CNT_TOK.labels(self.name).inc(tokens)
            metrics.dgm_tokens_total.labels(self.name).inc(tokens)
            metrics.dgm_cost_usd_total.labels(self.name).inc(tokens * metrics.COST_PER_TOKEN)
        _HIST_LAT.labels(self.name).observe(lat)

    # ----- public sync interface ------------------------------------------
    def chat(  # noqa: D401
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool,
        stop: Optional[Sequence[str]],
    ) -> str | Generator[str, None, None]:
        t0 = time.perf_counter()
        # estimated tokens (cheap; provider may return more/less)
        est_toks = sum(_count_tokens(m["content"]) for m in messages) + max_tokens
        if not self._budget.allow(est_toks):
            raise RuntimeError(f"{self.name} rate-limit budget exhausted")
        try:
            out = self._invoke(messages, temperature, max_tokens, stream, stop)
            if not isinstance(out, GeneratorType):
                self._record(True, est_toks, time.perf_counter() - t0)
            return out
        except Exception:
            self._record(False, None, time.perf_counter() - t0)
            raise

    # ----- async wrapper ---------------------------------------------------
    async def achat(self, *a: Any, **k: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.chat(*a, **k))

    # ----- to be implemented by concrete providers ------------------------
    def _invoke(self, *a: Any, **k: Any):  # noqa: D401
        raise NotImplementedError


# ───────────────────── dynamic provider import ─────────────
_PROVIDERS: Dict[str, "_Provider"] = {}


def _install(name: str, prov_cls: type[_Provider]) -> None:
    try:
        inst = prov_cls()
        _PROVIDERS[name] = inst
        _log.info("LLMProvider: registered backend '%s'", name)
    except Exception as exc:
        _log.warning("Skipping provider %s – init failed: %s", name, exc)


# -------- built-ins -------------------------------------------------------


def _maybe(env: str):
    return bool(os.getenv(env))


# OpenAI
try:
    if _maybe("OPENAI_API_KEY"):
        import openai  # type: ignore

        class _OpenAI(_Provider):
            name = "openai"
            _cli = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                kw = dict(
                    model=model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop or None,
                    stream=stream,
                )
                if stream:
                    for chunk in self._cli.chat.completions.create(**kw):
                        yield chunk.choices[0].delta.content or ""
                else:
                    r = self._cli.chat.completions.create(**kw)
                    return r.choices[0].message.content.strip()

        _install("openai", _OpenAI)
except ImportError:
    pass

# Anthropic
try:
    if _maybe("ANTHROPIC_API_KEY"):
        import anthropic  # type: ignore

        class _Anthropic(_Provider):
            name = "anthropic"
            _cli = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
                amsg = [{"role": m["role"], "content": m["content"]} for m in msgs]
                if stream:
                    for ch in self._cli.messages.create(
                        model=model,
                        messages=amsg,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stop_sequences=stop or None,
                        stream=True,
                    ):
                        yield ch.delta.text or ""
                else:
                    r = self._cli.messages.create(
                        model=model,
                        messages=amsg,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stop_sequences=stop or None,
                    )
                    return r.content[0].text.strip()

        _install("anthropic", _Anthropic)
except ImportError:
    pass

# Google Gemini
try:
    if _maybe("GOOGLE_API_KEY"):
        import google.generativeai as genai  # type: ignore

        class _Gemini(_Provider):
            name = "gemini"
            _model = genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) or genai.GenerativeModel(
                os.getenv("GOOGLE_MODEL", "gemini-pro")
            )

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                text = "\n".join(m["content"] for m in msgs)
                res = self._model.generate_content(
                    text,
                    generation_config=dict(temperature=temperature, max_output_tokens=max_tokens, stop_sequences=stop),
                )
                return res.text

        _install("gemini", _Gemini)
except ImportError:
    pass

# Mistral
try:
    if _maybe("MISTRAL_API_KEY"):
        import mistralai  # type: ignore

        class _Mistral(_Provider):
            name = "mistral"
            _cli = mistralai.MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
                res = self._cli.chat(
                    model=model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop or None,
                    stream=stream,
                )
                if stream:
                    for ch in res:
                        yield ch.choices[0].delta.content or ""
                else:
                    return res.choices[0].message.content.strip()

        _install("mistral", _Mistral)
except ImportError:
    pass

# Together AI
try:
    if _maybe("TOGETHER_API_KEY"):
        import together  # type: ignore

        class _Together(_Provider):
            name = "together"
            _cli = together.Together(api_key=os.getenv("TOGETHER_API_KEY"))

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                model = os.getenv("TOGETHER_MODEL", "mistralai/Mixtral-8x22B-Instruct-v0.1")
                res = self._cli.chat.completions.create(
                    model=model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop or None,
                    stream=stream,
                )
                if stream:
                    for ch in res:
                        yield ch.choices[0].delta.content or ""
                else:
                    return res.choices[0].message.content.strip()

        _install("together", _Together)
except ImportError:
    pass

# HF text-generation-inference
try:
    if os.getenv("TGI_ENDPOINT"):
        from text_generation import Client as _TGIC  # type: ignore

        class _TGI(_Provider):
            name = "tgi"
            _cli = _TGIC(os.getenv("TGI_ENDPOINT"))

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                prompt = "\n".join(m["content"] for m in msgs)
                res = self._cli.generate_stream(
                    prompt, temperature=temperature, max_new_tokens=max_tokens, stop_sequences=stop or []
                )
                if stream:
                    for tok in res:
                        yield tok.token.text
                else:
                    return "".join(tok.token.text for tok in res).strip()

        _install("tgi", _TGI)
except ImportError:
    pass

# Ollama (local server)
try:
    import ollama  # type: ignore

    class _Ollama(_Provider):
        name = "ollama"

        def _invoke(self, msgs, temperature, max_tokens, stream, stop):
            prompt = "\n".join(m["content"] for m in msgs)
            r = ollama.chat(
                model=os.getenv("OLLAMA_MODEL", "llama3"),
                stream=stream,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": max_tokens, "stop": stop},
            )
            if stream:
                for ch in r:
                    yield ch["message"]["content"]
            else:
                return r["message"]["content"].strip()

    _install("ollama", _Ollama)
except ImportError:
    pass

# llama-cpp (offline fallback)
try:
    from llama_cpp import Llama  # type: ignore

    class _LlamaCPP(_Provider):
        name = "llama"

        def __init__(self) -> None:
            default = pathlib.Path.home() / ".cache" / "llama" / "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"
            mpath = pathlib.Path(os.getenv("LLAMA_MODEL_PATH", default))
            mpath.parent.mkdir(parents=True, exist_ok=True)
            if not mpath.exists():
                _log.info("Downloading TinyLlama weight (~380 MB) …")
                import huggingface_hub as hf  # type: ignore

                tmp = hf.hf_hub_download(repo_id="TheBloke/TinyLlama-1.1B-Chat-GGUF", filename=mpath.name)
                pathlib.Path(tmp).rename(mpath)
            self._llm = Llama(
                model_path=str(mpath),
                n_ctx=int(os.getenv("LLAMA_N_CTX", "2048")),
                n_threads=max(1, os.cpu_count() // 2),
            )

        def _invoke(self, msgs, temperature, max_tokens, stream, stop):
            prompt = "\n".join(m["content"] for m in msgs)
            out = self._llm(prompt, temperature=temperature, max_tokens=max_tokens, stop=stop or [])
            return out["choices"][0]["text"].strip()

    _install("llama", _LlamaCPP)
except ImportError:
    pass

_ORDER_ENV = os.getenv("AF_LLM_PROVIDERS")
if _ORDER_ENV:
    requested = [n.strip() for n in _ORDER_ENV.split(",") if n.strip()]
    ordered: OrderedDict[str, _Provider] = OrderedDict()
    for name in requested:
        if name in _PROVIDERS:
            ordered[name] = _PROVIDERS[name]
    for name, prov in _PROVIDERS.items():
        if name not in ordered:
            ordered[name] = prov
    _PROVIDERS = ordered
    _log.info("Provider order via AF_LLM_PROVIDERS: %s", ", ".join(_PROVIDERS))

if not _PROVIDERS:
    if os.getenv("AGI_INSIGHT_OFFLINE") == "1":
        _log.warning("No LLM back-end available in offline mode – using stub provider")

        class _Stub(_Provider):
            name = "offline"

            def _invoke(self, msgs, temperature, max_tokens, stream, stop):
                answer = "[offline] " + msgs[-1]["content"][:400]
                if stream:
                    for tok in answer.split():
                        yield tok + " "
                else:
                    return answer

        _PROVIDERS["offline"] = _Stub()
    else:
        _log.critical("‼️  No LLM back-end available – set OPENAI_API_KEY or install llama-cpp")
        raise RuntimeError("No LLM provider available")


# ──────────────────────── facade class ─────────────────────
class LLMProvider:
    """
    Unified chat-completion interface for all Alpha-Factory agents.

    Parameters
    ----------
    temperature : float
        Default sampling temperature.
    max_tokens : int
        Default maximum tokens for completions.

    Environment knobs
    -----------------
    * ``AF_LLM_CACHE_TTL`` (secs) – disk-cache expiry (default 86400).
    * ``AF_LLM_CACHE_SIZE`` – max in-memory cache entries (default 1024).
    * ``AF_RPM_LIMIT`` / ``AF_TPM_LIMIT`` – per-provider budgets.
    * ``AF_LOG_PROMPTS`` – if *truthy*, user prompts are logged verbatim.
    * ``AF_LLM_PROVIDERS`` – comma-separated provider order override.
    """

    def __init__(self, *, temperature: float = 0.7, max_tokens: int = 512) -> None:
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ----------------------------- helpers ------------------------------
    @staticmethod
    def _hash(messages: List[Dict[str, str]]) -> str:
        blob = json.dumps(messages, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    @staticmethod
    def _log_prompt(msgs: Sequence[Dict[str, str]]) -> None:
        if os.getenv("AF_LOG_PROMPTS"):
            _log.debug("Prompt: %s", msgs)

    # ----------------------------- public API ---------------------------
    def chat(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system_prompt: str | None = None,
        stream: bool = False,
        stop: Optional[Sequence[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        cache: bool = True,
    ) -> str | Generator[str, None, None]:
        """
        Synchronous call – returns answer *or* generator when ``stream=True``.
        """
        msgs = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + (
            [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt
        )
        self._log_prompt(msgs)

        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        # trim history if needed
        while sum(_count_tokens(m["content"]) for m in msgs) > 12000 and len(msgs) > 2:
            msgs.pop(1)

        hsh = self._hash(msgs)
        if cache and not stream:
            if hit := _cache_get(hsh):
                _CNT_REQ.labels("cache", "hit").inc()
                return hit

        last_exc: Optional[Exception] = None
        for name, prov in _PROVIDERS.items():
            try:
                out = prov.chat(msgs, temperature, max_tokens, stream, stop)
                if not stream and cache:
                    _cache_put(hsh, out, name)  # type: ignore[arg-type]
                return out
            except Exception as e:
                last_exc = e
                _log.warning("Provider '%s' failed: %s", name, e)

        raise RuntimeError("All providers failed") from last_exc

    # --------------------------- async wrapper --------------------------
    async def achat(self, *a: Any, **k: Any):
        """
        Asynchronous counterpart of :meth:`chat`.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.chat(*a, **k))


# --------------------------- CLI smoke test -----------------------------
if __name__ == "__main__":
    import argparse
    import textwrap

    ap = argparse.ArgumentParser(description="LLMProvider smoke-test")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--system")
    ap.add_argument("--stream", action="store_true")
    args = ap.parse_args()

    llm = LLMProvider()
    if args.stream:
        print("⇢ streaming reply:")
        for tok in llm.chat(args.prompt, system_prompt=args.system, stream=True):
            print(tok, end="", flush=True)
        print()
    else:
        resp = llm.chat(args.prompt, system_prompt=args.system)
        print(textwrap.fill(resp, 100))
