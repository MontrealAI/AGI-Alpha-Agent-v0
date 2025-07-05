# SPDX-License-Identifier: Apache-2.0
"""Unified diff generator for repository mutations."""

from __future__ import annotations

import asyncio
import os
import threading
from typing import cast
from pathlib import Path

from alpha_factory_v1.core.tools.diff_mutation import propose_diff as _fallback_diff

__all__ = ["propose_diff"]


def _offline() -> bool:
    return not os.getenv("OPENAI_API_KEY") or os.getenv("AGI_INSIGHT_OFFLINE") == "1"


def _parse_spec(spec: str) -> tuple[str, str]:
    if ":" in spec:
        path, goal = spec.split(":", 1)
    else:
        parts = spec.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError("spec must contain 'path goal'")
        path, goal = parts
    return path.strip(), goal.strip()


def _sync_chat(prompt: str) -> str:
    """Synchronously invoke the async chat helper."""
    from alpha_factory_v1.backend.llm_provider import chat

    async def _call() -> str:
        return cast(str, await chat(prompt, max_tokens=512))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call())

    result: list[str] = []

    def _worker() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(_call())
        try:
            result.append(loop.run_until_complete(task))
        finally:
            loop.close()

    t = threading.Thread(target=_worker)
    t.start()
    t.join()
    return result[0]


def propose_diff(repo_path: str, spec: str) -> str:
    """Return a git diff implementing ``spec`` inside ``repo_path``."""
    rel, goal = _parse_spec(spec)
    file_path = str(Path(repo_path) / rel)
    if _offline():
        return cast(str, _fallback_diff(file_path, goal))
    prompt = "Generate a unified git diff for the repository at '{repo}'.\nApply the following change: {spec}".format(
        repo=repo_path, spec=spec
    )
    try:
        diff = _sync_chat(prompt)
        if not diff.endswith("\n"):
            diff += "\n"
        return diff
    except Exception:
        return cast(str, _fallback_diff(file_path, goal))
