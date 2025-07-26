"""Integration tests for the AI-GA OpenAI Agents bridge."""

from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0

import asyncio
import importlib
import importlib.util
import subprocess
import sys
import time
from typing import Any

import pytest

_SKIP: Any = pytest.mark.skipif(
    importlib.util.find_spec("openai_agents") is None or importlib.util.find_spec("gymnasium") is None,
    reason="openai_agents or gymnasium not installed",
)


@_SKIP  # type: ignore[misc]
def test_bridge_launch() -> None:
    """Start ``openai_agents_bridge.main`` and confirm registration."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(2)
        proc.terminate()
        out, _ = proc.communicate(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    assert "EvolverAgent" in out


@_SKIP  # type: ignore[misc]
def test_evolve_tool() -> None:
    """Invoke ``evolve`` once and verify ``best_alpha`` output."""
    mod = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge")
    runtime = mod.AgentRuntime(api_key=None)
    agent = mod.EvolverAgent()
    runtime.register(agent)

    asyncio.run(mod.evolve(1))
    result = asyncio.run(mod.best_alpha())
    assert "architecture" in result
