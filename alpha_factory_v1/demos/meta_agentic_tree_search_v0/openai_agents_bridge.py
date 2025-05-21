#!/usr/bin/env python3
"""OpenAI Agents SDK bridge for the Meta-Agentic Tree Search demo.

This utility registers a small agent that exposes the tree-search loop via the
OpenAI Agents runtime.  It gracefully degrades to offline mode when the
``openai-agents`` package is unavailable or no API key is configured.
"""
from __future__ import annotations

import os
import argparse
import importlib.util
import sys
import pathlib

DEFAULT_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")

if __package__ is None:  # pragma: no cover - allow direct execution
    sys.path.append(str(pathlib.Path(__file__).resolve().parents[3]))

has_oai = importlib.util.find_spec("openai_agents") is not None
if has_oai:
    from openai_agents import Agent, AgentRuntime, Tool  # type: ignore

    try:
        from .run_demo import run
    except ImportError:  # pragma: no cover - direct script execution
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo import run

    @Tool(name="run_search", description="Run the MATS demo for a few episodes")
    async def run_search(episodes: int = 10, target: int = 5, model: str | None = None) -> str:
        """Execute the search loop and return a summary string."""
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        agents, score = run(episodes=episodes, target=target, model=model)
        return (
            f"completed {episodes} episodes toward target {target} | "
            f"best {agents} score {score:.3f}"
        )

    class MATSAgent(Agent):
        """Tiny helper agent wrapping :func:`run_search`."""

        name = "mats_helper"
        tools = [run_search]

        async def policy(self, obs, _ctx):  # type: ignore[override]
            episodes = int(obs.get("episodes", 10)) if isinstance(obs, dict) else 10
            target = int(obs.get("target", 5)) if isinstance(obs, dict) else 5
            model = obs.get("model") if isinstance(obs, dict) else None
            return await run_search(episodes=episodes, target=target, model=model)

    def _run_runtime(episodes: int, target: int, model: str | None = None) -> None:
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        runtime = AgentRuntime(api_key=os.getenv("OPENAI_API_KEY"))
        agent = MATSAgent()
        runtime.register(agent)
        try:
            from alpha_factory_v1.backend import adk_bridge

            if adk_bridge.adk_enabled():
                adk_bridge.auto_register([agent])
                adk_bridge.maybe_launch()
            else:
                print("ADK gateway disabled.")
        except Exception as exc:  # pragma: no cover - ADK optional
            print(f"ADK bridge unavailable: {exc}")

        print("Registered MATSAgent with runtime")
        runtime.run()
else:
    try:
        from .run_demo import run
    except ImportError:  # pragma: no cover - direct script execution
        from alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo import run

    def _run_search_helper(episodes: int, target: int, model: str | None = None) -> str:
        """Execute the search loop and return a summary string."""
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        agents, score = run(episodes=episodes, target=target, model=model)
        return (
            f"completed {episodes} episodes toward target {target} | "
            f"best {agents} score {score:.3f}"
        )
    async def run_search(episodes: int = 10, target: int = 5, model: str | None = None) -> str:
        return _run_search_helper(episodes, target, model)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="OpenAI Agents bridge for MATS")
    parser.add_argument("--episodes", type=int, default=10, help="Search episodes when offline")
    parser.add_argument("--target", type=int, default=5, help="Target integer when offline")
    parser.add_argument("--model", type=str, help="Optional OpenAI model override")
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

    if args.verify_env:
        try:
            import check_env  # type: ignore

            check_env.main([])
        except Exception as exc:  # pragma: no cover - best effort
            print(f"Environment verification failed: {exc}")

    if not has_oai:
        print("openai-agents package is missing. Running offline demo...")
        agents, score = run(episodes=args.episodes, target=args.target, model=args.model)
        print(f"best {agents} score {score:.3f}")
        return

    if args.enable_adk:
        os.environ.setdefault("ALPHA_FACTORY_ENABLE_ADK", "true")

    _run_runtime(args.episodes, args.target, args.model)


__all__ = [
    "DEFAULT_MODEL_NAME",
    "has_oai",
    "run_search",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    main()
