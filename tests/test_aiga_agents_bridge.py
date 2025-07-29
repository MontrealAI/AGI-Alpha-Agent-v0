"""Integration tests for the AI-GA OpenAI Agents bridge."""

from __future__ import annotations

# SPDX-License-Identifier: Apache-2.0

import asyncio
import importlib
import subprocess
import sys
import time
from typing import Any

import pytest

openai_agents = pytest.importorskip("openai_agents", minversion="0.0.17")
import inspect

if "Minimal stub" in inspect.getsource(openai_agents):
    pytest.skip("openai_agents stub present", allow_module_level=True)
pytest.importorskip("gymnasium", minversion="0.29")
pytest.importorskip("google_adk")


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
    assert "Registered EvolverAgent with runtime" in out
    assert "EvolverAgent exposed via ADK gateway" in out


def test_evolve_tool() -> None:
    """Invoke ``evolve`` once and verify ``best_alpha`` output."""
    mod = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge")
    runtime = mod.AgentRuntime(api_key=None)
    agent = mod.EvolverAgent()
    runtime.register(agent)

    asyncio.run(mod.evolve(1))
    result = asyncio.run(mod.best_alpha())
    assert "architecture" in result
