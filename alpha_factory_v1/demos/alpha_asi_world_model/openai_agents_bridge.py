# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype and does not implement real AGI.
"""Minimal OpenAI Agents & Google ADK bridge for the α‑ASI demo.

This utility registers a tiny inspector agent with the local orchestrator
and prints the list of active agents. When the optional Google ADK
dependency is installed and ``ALPHA_FACTORY_ENABLE_ADK=true`` is set,
the agent is also exposed via an ADK gateway. It works offline when no API
key is provided. Set ``OPENAI_API_KEY`` to connect to the OpenAI Agents
platform. Run after the demo server is up:

    python openai_agents_bridge.py
"""
from __future__ import annotations

import os

import af_requests as requests

try:
    from openai_agents import Agent, AgentRuntime, Tool
except Exception:  # pragma: no cover - fallback for older SDKs
    from openai_agents import Agent, Tool

    class AgentRuntime:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            pass

        def register(self, *args, **kwargs) -> None:
            pass


def _tool_fallback(*_args, **_kwargs):
    def _decorator(func):
        return func

    return _decorator


try:
    Tool(name="__probe__", description="__probe__")
except Exception:  # pragma: no cover - handle non-callable Tool
    Tool = _tool_fallback  # type: ignore[assignment]

from alpha_factory_v1.backend.logger import get_logger

_LOG = get_logger("alpha_factory.asi_inspector")

try:
    # Optional ADK integration
    from alpha_factory_v1.backend.adk_bridge import auto_register, maybe_launch

    ADK_AVAILABLE = True
except Exception:  # pragma: no cover - adk not installed
    ADK_AVAILABLE = False


@Tool(name="list_agents", description="List active orchestrator agents")
async def list_agents() -> list[str]:
    try:
        resp = requests.get("http://localhost:7860/agents", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        _LOG.warning("Demo server not running")
        return []


@Tool(name="new_env", description="Spawn a new demo environment")
async def new_env() -> dict:
    try:
        resp = requests.post("http://localhost:7860/command", json={"cmd": "new_env"}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        _LOG.warning("Demo server not running")
        return {}


POLICY_MAP = {
    "list_agents": lambda _o: list_agents(),
    "new_env": lambda _o: new_env(),
}


class InspectorAgent(Agent):
    name = "inspector"
    tools = [list_agents, new_env]

    def __init__(self) -> None:
        try:
            super().__init__(name=self.name, tools=self.tools)
        except TypeError:
            super().__init__()

    async def policy(self, obs, ctx):  # type: ignore[override]
        if isinstance(obs, dict):
            action = obs.get("action")
            handler = POLICY_MAP.get(action)
            if handler:
                return await handler(obs)
        return await list_agents()


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    rt = AgentRuntime(api_key=api_key)
    agent = InspectorAgent()
    rt.register(agent)
    _LOG.info("Registered InspectorAgent with runtime")

    if ADK_AVAILABLE:
        auto_register([agent])
        maybe_launch()
        _LOG.info("InspectorAgent exposed via ADK gateway")

    rt.run()


if __name__ == "__main__":
    main()
