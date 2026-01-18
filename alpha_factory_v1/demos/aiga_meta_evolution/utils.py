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
import sys


class _FallbackAgent:  # pragma: no cover - used in tests and offline paths
    def __init__(self, *a, **kw) -> None:
        pass

    async def __call__(self, text: str) -> str:
        return "ok"


def _resolve_openai_agent() -> type:
    """Return the ``OpenAIAgent`` class from the available package."""
    if "openai_agents" not in sys.modules and "agents" in sys.modules:
        return sys.modules["agents"].OpenAIAgent  # type: ignore[no-any-return]
    try:  # prefer the official ``openai_agents`` package
        oa = importlib.import_module("openai_agents")
        if getattr(oa, "__alpha_factory_stub__", False):
            raise ModuleNotFoundError("OpenAI Agents SDK stub detected")
        return oa.OpenAIAgent
    except Exception:
        try:  # pragma: no cover - fallback for legacy package
            return importlib.import_module("agents").OpenAIAgent
        except Exception:  # pragma: no cover - optional dependency
            return _FallbackAgent


OpenAIAgent = _resolve_openai_agent()


def build_llm() -> object:
    """Create the default ``OpenAIAgent`` instance."""
    global OpenAIAgent
    OpenAIAgent = _resolve_openai_agent()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = None if api_key else os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
    try:
        llm = OpenAIAgent(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            api_key=api_key,
            base_url=base_url,
        )
        if base_url:
            print(f"Using ollama backend via {base_url}", flush=True)
        return llm
    except TypeError:  # pragma: no cover - allow dummy classes in tests
        return _FallbackAgent()
