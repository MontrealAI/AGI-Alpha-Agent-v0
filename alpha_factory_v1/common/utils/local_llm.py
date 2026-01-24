# SPDX-License-Identifier: Apache-2.0
"""Very small wrapper around optional local language models.

The :func:`chat` helper loads a model on demand using either ``llama-cpp`` or
``ctransformers``. If neither is present an echo implementation is used.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, cast

from . import config
from .config import Settings
from alpha_factory_v1.core.utils.tracing import span

try:  # pragma: no cover - optional dependency
    from llama_cpp import Llama
except Exception:  # pragma: no cover - llama-cpp optional
    Llama = None

try:  # pragma: no cover - optional dependency
    from ctransformers import AutoModelForCausalLM
except Exception:  # pragma: no cover - ctransformers optional
    AutoModelForCausalLM = None

_log = logging.getLogger(__name__)

_MODEL: Any | None = None
_CALL: Callable[[str, Settings], str] | None = None


def _load_model(cfg: Settings | None = None) -> None:
    """Load a local model if available, otherwise use an echo stub."""
    global _MODEL, _CALL
    cfg = cfg or config.CFG
    model_path = os.getenv("LLAMA_MODEL_PATH", cfg.model_name)
    n_ctx = int(os.getenv("LLAMA_N_CTX", str(cfg.context_window)))

    def _wrap(fn: Callable[[str, Settings], str]) -> Callable[[str, Settings], str]:
        return fn

    if os.getenv("NO_LLM") == "1" or os.getenv("PYTEST_NET_OFF") == "1":
        def call_stub(prompt: str, s: Settings) -> str:
            return f"[offline] {prompt}"

        _CALL = _wrap(call_stub)
        return

    if Llama is not None:
        try:
            _MODEL = Llama(model_path=model_path, n_ctx=n_ctx)

            def call_llama(prompt: str, s: Settings) -> str:
                out = cast(Any, _MODEL)(prompt, temperature=s.temperature)
                return cast(str, out["choices"][0]["text"]).strip()

            _CALL = _wrap(call_llama)
            return
        except Exception as exc:  # pragma: no cover - model load failure
            _log.warning("Failed to load Llama model: %s", exc)
            _MODEL = None
    if AutoModelForCausalLM is not None:
        try:
            _MODEL = AutoModelForCausalLM.from_pretrained(model_path, model_type="llama")

            def call_ctrans(prompt: str, s: Settings) -> str:
                return cast(str, cast(Any, _MODEL)(prompt, temperature=s.temperature))

            _CALL = _wrap(call_ctrans)
            return
        except Exception as exc:  # pragma: no cover - model load failure
            _log.warning("Failed to load ctransformers model: %s", exc)
            _MODEL = None

    def call_stub(prompt: str, s: Settings) -> str:
        return f"[offline] {prompt}"

    _CALL = _wrap(call_stub)


def chat(prompt: str, cfg: Settings | None = None) -> str:
    """Return a completion using the local model or a simple echo."""
    cfg = cfg or config.CFG
    if _CALL is None:
        _load_model(cfg)
    assert _CALL is not None
    try:
        with span("local_llm.chat"):
            return _CALL(prompt, cfg)
    except Exception as exc:  # pragma: no cover - runtime error
        _log.exception("Local chat failed: %s", exc)
        return f"[offline] {prompt}"
