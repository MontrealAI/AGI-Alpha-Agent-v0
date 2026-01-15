#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype and does not implement real AGI.
"""OpenAI Agents SDK bridge for the Meta-Agentic Tree Search demo.

This utility registers a small agent that exposes the tree-search loop via the
OpenAI Agents runtime.  It gracefully degrades to offline mode when the
``openai-agents`` package is unavailable or no API key is configured.
"""
from __future__ import annotations

import os
import argparse
import importlib.util
import logging
import sys
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")


def verify_env() -> None:
    """Best-effort runtime dependency check."""
    try:
        import check_env

        check_env.main([])
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Environment verification failed: %s", exc)


if __package__ is None:  # pragma: no cover - allow direct execution
    # Ensure imports resolve when running the script directly
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.meta_agentic_tree_search_v0"

try:
    _spec = importlib.util.find_spec("openai_agents")
except ValueError:
    _spec = None
has_oai = _spec is not None
runtime_supported = False
if has_oai:
    import openai_agents
    from openai_agents import Agent, function_tool

    runtime_supported = hasattr(openai_agents, "AgentRuntime") and hasattr(openai_agents.AgentRuntime, "run")

if has_oai and runtime_supported:
    from openai_agents import AgentRuntime
    if hasattr(openai_agents, "AgentRuntime"):
        from openai_agents import AgentRuntime as _AgentRuntime
    else:
        _AgentRuntime = None

    from agents.run import Runner

    class _FallbackAgentRuntime:
        def __init__(self, *_: object, **__: object) -> None:
            self._runner = Runner()
            self._agent: Agent | None = None

        def register(self, agent: Agent) -> None:
            self._agent = agent

        def run(self) -> None:
            import asyncio

            if self._agent is None:
                raise RuntimeError("No agent registered")
            asyncio.run(self._runner.run(self._agent, ""))

    if _AgentRuntime is None or not hasattr(_AgentRuntime, "run"):
        AgentRuntime = _FallbackAgentRuntime
    else:
        AgentRuntime = _AgentRuntime

    try:
        from .run_demo import run
    except ImportError:  # pragma: no cover - direct script execution
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo import run

    @function_tool(
        name_override="run_search",
        description_override="Run the MATS demo for a few episodes",
    )  # type: ignore[misc]
    async def run_search(
        episodes: int = 10,
        target: int = 5,
        model: str | None = None,
        rewriter: str | None = None,
        market_data: list[int] | None = None,
    ) -> str:
        """Execute the search loop and return a summary string."""
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        if rewriter:
            os.environ.setdefault("MATS_REWRITER", rewriter)
        run(
            episodes=episodes,
            target=target,
            model=model,
            rewriter=rewriter,
            market_data=market_data,
        )
        return f"completed {episodes} episodes toward target {target}"

    class MATSAgent(Agent):  # type: ignore[misc]
        """Tiny helper agent wrapping :func:`run_search`."""

        name = "mats_helper"
        tools = [run_search]

        def __init__(self, market_data: list[int] | None = None) -> None:
            super().__init__()
            self.market_data = market_data

        async def policy(self, obs: object, _ctx: object) -> str:
            episodes = int(obs.get("episodes", 10)) if isinstance(obs, dict) else 10
            target = int(obs.get("target", 5)) if isinstance(obs, dict) else 5
            model = obs.get("model") if isinstance(obs, dict) else None
            rewriter = obs.get("rewriter") if isinstance(obs, dict) else None
            market_data = (
                [int(x) for x in obs.get("market_data", [])] if isinstance(obs, dict) and "market_data" in obs else None
            )
            if market_data is None:
                market_data = self.market_data
            result = await run_search(
                episodes=episodes,
                target=target,
                model=model,
                rewriter=rewriter,
                market_data=market_data,
            )
            return cast(str, result)

    def _run_runtime(
        episodes: int,
        target: int,
        model: str | None = None,
        rewriter: str | None = None,
        market_data: list[int] | None = None,
    ) -> None:
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        if rewriter:
            os.environ.setdefault("MATS_REWRITER", rewriter)
        runtime = AgentRuntime(api_key=os.getenv("OPENAI_API_KEY"))
        agent = MATSAgent(market_data=market_data)
        runtime.register(agent)
        try:
            from alpha_factory_v1.backend import adk_bridge

            if adk_bridge.adk_enabled():
                adk_bridge.auto_register([agent])
                adk_bridge.maybe_launch()
            else:
                logger.info("ADK gateway disabled.")
        except Exception as exc:  # pragma: no cover - ADK optional
            logger.warning("ADK bridge unavailable: %s", exc)

        logger.info("Registered MATSAgent with runtime")
        runtime.run()

else:
    try:
        from .run_demo import run
    except ImportError:  # pragma: no cover - direct script execution
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo import run

    def _run_search_helper(
        episodes: int,
        target: int,
        model: str | None = None,
        rewriter: str | None = None,
        market_data: list[int] | None = None,
    ) -> str:
        """Execute the search loop and return a summary string."""
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        run(
            episodes=episodes,
            target=target,
            model=model,
            rewriter=rewriter,
            market_data=market_data,
        )
        return f"completed {episodes} episodes toward target {target}"

    async def run_search(
        episodes: int = 10,
        target: int = 5,
        model: str | None = None,
        rewriter: str | None = None,
        market_data: list[int] | None = None,
    ) -> str:
        return _run_search_helper(episodes, target, model, rewriter, market_data)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="OpenAI Agents bridge for MATS")
    parser.add_argument("--episodes", type=int, default=10, help="Search episodes when offline")
    parser.add_argument("--target", type=int, default=5, help="Target integer when offline")
    parser.add_argument("--model", type=str, help="Optional model override")
    parser.add_argument(
        "--rewriter",
        choices=["random", "openai", "anthropic"],
        help="Rewrite strategy to use",
    )
    parser.add_argument(
        "--market-data",
        type=Path,
        help="CSV file with comma-separated integers for LiveBrokerEnv",
    )
    parser.add_argument(
        "--enable-adk",
        action="store_true",
        help="Enable the Google ADK gateway for remote control",
    )
    parser.add_argument(
        "--verify-env",
        action="store_true",
        help="Check runtime dependencies before launching",
    )
    args = parser.parse_args(argv)

    market_data: list[int] | None = None
    if args.market_data:
        text = args.market_data.read_text(encoding="utf-8")
        market_data = [int(x) for x in text.split(",") if x.strip()]

    if args.verify_env:
        verify_env()

    if not has_oai or not runtime_supported:
        if not has_oai:
            logger.info("openai-agents package is missing. Running offline demo...")
        else:
            logger.info("openai-agents runtime unavailable. Running offline demo...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not has_oai or not api_key:
        logger.info("openai-agents unavailable or OPENAI_API_KEY unset. Running offline demo...")
        run(
            episodes=args.episodes,
            target=args.target,
            model=args.model,
            rewriter=args.rewriter,
            market_data=market_data,
        )
        return

    if args.enable_adk:
        os.environ.setdefault("ALPHA_FACTORY_ENABLE_ADK", "true")

    try:
        _run_runtime(
            args.episodes,
            args.target,
            args.model,
            args.rewriter,
            market_data,
        )
    except Exception as exc:  # pragma: no cover - offline fallback
        logger.warning("Runtime failed (%s). Falling back to offline demo.", exc)
        run(
            episodes=args.episodes,
            target=args.target,
            model=args.model,
            rewriter=args.rewriter,
            market_data=market_data,
        )


__all__ = [
    "DEFAULT_MODEL_NAME",
    "has_oai",
    "run_search",
    "verify_env",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    main()
