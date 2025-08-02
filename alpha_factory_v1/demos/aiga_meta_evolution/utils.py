# SPDX-License-Identifier: Apache-2.0
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

Shared helpers for the AI-GA Meta-Evolution demo. Compatible with either the
``openai_agents`` package or the ``agents`` backport.
"""
from __future__ import annotations

import importlib
import os
from types import SimpleNamespace


def _resolve_openai_agent() -> type:
    """Return the ``OpenAIAgent`` class from the available package."""
    try:  # prefer the official ``openai_agents`` package
        return importlib.import_module("openai_agents").OpenAIAgent
    except Exception:
        try:  # pragma: no cover - fallback for legacy package
            return importlib.import_module("agents").OpenAIAgent
        except Exception:  # pragma: no cover - optional dependency

            class _FallbackAgent:  # type: ignore[misc]
                def __init__(self, *a, **kw) -> None:
                    pass

                async def __call__(self, text: str) -> str:
                    return "ok"

            return _FallbackAgent


def build_llm() -> object:
    """Create the default ``OpenAIAgent`` instance."""
    OpenAIAgent = _resolve_openai_agent()
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAIAgent(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=api_key,
        base_url=None if api_key else os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
    )
