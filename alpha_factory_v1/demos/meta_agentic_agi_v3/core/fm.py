# SPDX-License-Identifier: Apache-2.0
"""Legacy provider-qualified synchronous completion adapter.

Optional SDKs initialize only on explicit construction. Responses include estimated
token, cost and carbon metadata; these are not measured billing or emissions.
Streaming, MCP and context-window management are not implemented by this adapter.
"""

from __future__ import annotations

import os
import json
import time
import logging
import importlib
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger("alpha_factory.fm")
_LOGGER.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Helper utilities                                                            #
# --------------------------------------------------------------------------- #
def _lazy_import(pkg: str, attr: str | None = None):
    """Import a package only when first used."""
    module = importlib.import_module(pkg)
    return getattr(module, attr) if attr else module


def _env(name: str, default: str | None = None) -> Optional[str]:
    return os.getenv(name, default)


def _now_ms() -> int:
    return int(time.time() * 1e3)


def _usd_cost(tokens: int, ppm_usd: float) -> float:
    """Approximate USD cost given token count and price per million tokens."""
    return tokens / 1_000_000 * ppm_usd


def _gco2e(usd: float, kg_per_dollar: float = 0.0006) -> float:
    """Crude carbon footprint (gCO₂e) estimate based on spend."""
    return usd * kg_per_dollar * 1_000  # gCO₂e


# --------------------------------------------------------------------------- #
# Exceptions                                                                  #
# --------------------------------------------------------------------------- #
class ProviderNotAvailable(RuntimeError):
    """Raised when the requested provider SDK cannot be initialised."""

    ...


class ModelNotFound(RuntimeError):
    """Raised when the requested model id cannot be located."""

    ...


# --------------------------------------------------------------------------- #
# Core foundation‑model abstraction                                           #
# --------------------------------------------------------------------------- #
class FoundationModel:
    """
    Unified chat‑completion interface across providers (+ offline fallback).

    Parameters
    ----------
    model : str
        Provider-qualified model id, e.g. ``"openai:gpt-4o"`` or
        ``"mistral:models/llama-3-8b-gguf"``.
    temperature : float, default 0.2
        Sampling temperature.
    max_tokens : int, default 2048
        Maximum tokens to generate.
    stream : bool, default False
        Whether to stream responses (if provider supports).
    context_window : int, default 8192
        Prompt context window for local models.
    retries : int, default 3
        Maximum retry attempts before raising.
    """

    REGISTRY: Dict[str, Dict[str, Any]] = {
        "openai": {
            "pkg": "openai",
            "chat_func": lambda cli, **kw: cli.chat.completions.create(**kw),
            "price": 0.01,
        },
        "anthropic": {
            "pkg": "anthropic",
            "chat_func": lambda cli, **kw: cli.messages.create(**kw),
            "price": 0.012,
        },
        "google": {
            "pkg": "google.generativeai",
            "chat_func": lambda cli, **kw: cli.generate_content(**kw),
            "price": 0.013,
        },
        "mistral": {  # local gguf via llama‑cpp
            "pkg": "llama_cpp",
            "chat_func": None,  # handled specially
            "price": 0.0,
        },
    }

    def __init__(
        self,
        model: str = "openai:gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        stream: bool = False,
        context_window: int = 8192,
        retries: int = 3,
    ) -> None:
        if ":" not in model:
            raise ValueError("Model string must be <provider>:<model_id>")
        self.provider, self.model_id = model.split(":", 1)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.stream = bool(stream)
        self.context_window = int(context_window)
        self.retries = max(1, int(retries))
        if self.stream:
            raise ValueError("Streaming is not supported by this text-returning compatibility adapter")
        self._init_client()

    # ------------------------------------------------------------------ #
    def _init_client(self) -> None:
        """Initialise provider SDK or local model runtime."""
        if self.provider not in self.REGISTRY:
            raise ProviderNotAvailable(self.provider)

        meta = self.REGISTRY[self.provider]
        try:
            if self.provider == "mistral":
                Llama = _lazy_import(meta["pkg"], "Llama")
                self.client = Llama(model_path=self.model_id, n_ctx=self.context_window)
            else:
                sdk = _lazy_import(meta["pkg"])
                if self.provider == "openai":
                    self.client = sdk.OpenAI()
                elif self.provider == "anthropic":
                    self.client = sdk.Client()
                elif self.provider == "google":
                    self.client = sdk.GenerativeModel(self.model_id)
        except ModuleNotFoundError as e:
            raise ProviderNotAvailable(f"{self.provider} SDK missing: pip install {meta['pkg']}") from e

    # ------------------------------------------------------------------ #
    def completion(self, messages: List[Dict[str, str]], **overrides) -> Dict[str, Any]:
        """
        Execute a chat completion and return the text plus usage metadata.

        Returns
        -------
        dict with keys ``text`` (str) and ``usage`` (dict).
        """
        meta = self.REGISTRY[self.provider]
        params = dict(
            model=self.model_id,
            temperature=overrides.get("temperature", self.temperature),
            max_tokens=overrides.get("max_tokens", self.max_tokens),
            stream=overrides.get("stream", self.stream),
        )

        if params["stream"]:
            raise ValueError("Streaming requires a separate streaming adapter")
        attempt = 0
        start_ms = _now_ms()
        while attempt < self.retries:
            try:
                # provider‑specific invocation
                if self.provider == "mistral":
                    prompt = "".join(f"<{m['role']}>{m['content']}" for m in messages)
                    res = self.client(
                        prompt,
                        temperature=params["temperature"],
                        max_tokens=params["max_tokens"],
                        stop=["</s>"],
                    )
                    text = res["choices"][0]["text"]
                elif self.provider == "anthropic":
                    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
                    res = self.client.messages.create(
                        system=system, messages=[m for m in messages if m["role"] != "system"], **params
                    )
                    text = "".join(block.text for block in res.content if hasattr(block, "text"))
                elif self.provider == "google":
                    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                    res = self.client.generate_content(
                        prompt,
                        generation_config={
                            "temperature": params["temperature"],
                            "max_output_tokens": params["max_tokens"],
                        },
                    )
                    text = res.text
                else:
                    chat_fn = meta["chat_func"]
                    res = chat_fn(self.client, messages=messages, **params)
                    if self.provider == "openai":
                        text = res.choices[0].message.content
                    elif self.provider == "anthropic":
                        text = res.content[0].text
                    elif self.provider == "google":
                        text = res.text

                # basic usage accounting
                tokens_in = sum(len(m["content"].split()) for m in messages)
                tokens_out = len(text.split())
                usd = _usd_cost(tokens_in + tokens_out, meta["price"])
                usage = {
                    "input_tokens": tokens_in,
                    "output_tokens": tokens_out,
                    "cost_usd": usd,
                    "gco2e": _gco2e(usd),
                    "latency_ms": _now_ms() - start_ms,
                    "accounting": "heuristic estimate, not measured billing or emissions",
                }
                return {"text": text, "usage": usage}

            except Exception as exc:
                attempt += 1
                if attempt >= self.retries:
                    raise RuntimeError(f"Completion failed after {self.retries} attempts: {exc}") from exc
                backoff = 2**attempt
                _LOGGER.warning(
                    "FM error (%s/%s): %s – retrying in %ss",
                    attempt,
                    self.retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

    # ------------------------------------------------------------------ #
    def __call__(self, messages: List[Dict[str, str]], **kw) -> str:
        """Alias for chat invocation returning only the text."""
        return self.completion(messages, **kw)["text"]


# --------------------------------------------------------------------------- #
# Convenience wrapper                                                         #
# --------------------------------------------------------------------------- #
def chat(
    model: str,
    messages: List[Dict[str, str]],
    **kw,
) -> str:
    """
    Lightweight one‑shot helper returning only the generated text.

    Examples
    --------
    >>> chat("openai:gpt-4o", [{"role": "user", "content": "Hello"}])
    'Hi there!'
    """
    fm = FoundationModel(model, **kw)
    return fm.completion(messages)["text"]
