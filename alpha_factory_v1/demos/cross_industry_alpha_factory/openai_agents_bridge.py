#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
# [See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
# NOTE: This demo is a research prototype and does not implement real AGI.
"""OpenAI Agents SDK bridge for the cross-industry Alpha-Factory demo.

Warning: The agent outputs are illustrative only and do not constitute
financial advice. Tool registration is skipped when the Agents SDK is
missing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict

import os

from .cross_alpha_discovery_stub import SAMPLE_ALPHA, discover_alpha, _ledger_path

logger = logging.getLogger(__name__)


def _load_agents():
    """Return OpenAI Agents classes when available, otherwise stubs."""
    try:
        from openai_agents import Agent, AgentRuntime, Tool  # type: ignore

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set")
        logger.debug("Using real OpenAI Agents runtime")
        return Agent, AgentRuntime, Tool, True
    except Exception as exc:  # pragma: no cover - optional dep
        logger.warning("OpenAI Agents SDK unavailable: %s", exc)

        class AgentRuntime:  # type: ignore
            def __init__(self, *a, **kw) -> None:  # noqa: D401 - simple stub
                pass

            def register(self, *_a, **_k) -> None:
                pass

            def run(self) -> None:
                logger.info("OpenAI Agents bridge disabled.")

        def Tool(*_args, **_kw):  # type: ignore
            def _decorator(func):
                return func

            return _decorator

        return object, AgentRuntime, Tool, False


Agent, AgentRuntime, Tool, _OPENAI_AGENTS_AVAILABLE = _load_agents()


def _read_log(limit: int) -> List[Dict[str, str]]:
    path = _ledger_path(None)
    try:
        data = json.loads(Path(path).read_text())
        if isinstance(data, dict):
            data = [data]
        return data[-limit:]
    except (
        FileNotFoundError,
        PermissionError,
        json.JSONDecodeError,
    ):  # pragma: no cover - missing or invalid log
        return []


@Tool(name="list_samples", description="List bundled sample opportunities")
async def list_samples() -> List[Dict[str, str]]:
    return SAMPLE_ALPHA


@Tool(name="discover_alpha", description="Generate new opportunities")
async def discover(num: int = 1) -> List[Dict[str, str]]:
    return discover_alpha(num=num)


@Tool(name="recent_log", description="Return recently logged opportunities")
async def recent_log(limit: int = 5) -> List[Dict[str, str]]:
    return _read_log(limit)


class CrossIndustryAgent(Agent):
    """Agent exposing cross-industry discovery tools."""

    name = "cross_industry_helper"
    tools = [list_samples, discover, recent_log]

    async def policy(self, obs, ctx):  # type: ignore[override]
        if isinstance(obs, dict):
            action = obs.get("action")
            if action == "discover":
                return await discover(obs.get("num", 1))
            if action == "recent":
                return await recent_log(obs.get("limit", 5))
        return await list_samples()


def main() -> None:
    runtime = AgentRuntime(api_key=os.getenv("OPENAI_API_KEY"))
    agent = CrossIndustryAgent()
    runtime.register(agent)
    try:
        from alpha_factory_v1.backend.adk_bridge import auto_register, maybe_launch

        auto_register([agent])
        maybe_launch()
    except Exception as exc:  # pragma: no cover - ADK optional
        logger.warning(f"ADK bridge unavailable: {exc}")

    logger.info("Registered CrossIndustryAgent with runtime")
    runtime.run()


if __name__ == "__main__":  # pragma: no cover
    main()
