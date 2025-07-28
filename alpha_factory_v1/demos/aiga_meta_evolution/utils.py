# SPDX-License-Identifier: Apache-2.0
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

Shared helpers for the AI-GA Meta-Evolution demo. Compatible with either the
``openai_agents`` package or the ``agents`` backport.
"""
from __future__ import annotations

import os

try:
    from openai_agents import OpenAIAgent
except ImportError:
    try:  # pragma: no cover - fallback for legacy package
        from agents import OpenAIAgent
    except Exception as exc:  # pragma: no cover - optional dependency

        class OpenAIAgent:  # type: ignore[misc]
            def __init__(self, *a, **kw):
                pass

            async def __call__(self, text: str) -> str:
                return "ok"


def build_llm() -> OpenAIAgent:
    """Create the default ``OpenAIAgent`` instance."""
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAIAgent(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=api_key,
        base_url=None if api_key else os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
    )
