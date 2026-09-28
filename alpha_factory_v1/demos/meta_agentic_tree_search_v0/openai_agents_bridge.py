#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Optional Agents SDK adapter; importing it never initializes clients or tracing."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import logging
import os
from pathlib import Path
import sys

if __package__ is None:  # pragma: no cover - direct script entry
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.meta_agentic_tree_search_v0"

from .run_demo import run  # noqa: E402

logger = logging.getLogger(__name__)
DEFAULT_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")
try:
    has_oai = importlib.util.find_spec("agents") is not None
except (ImportError, ValueError):
    has_oai = False


def verify_env() -> None:
    """Run the optional repository environment checker when explicitly requested."""
    try:
        import check_env

        check_env.main([])
    except Exception as exc:  # pragma: no cover - optional diagnostic
        logger.warning("Environment verification failed: %s", type(exc).__name__)


async def run_search(
    episodes: int = 10,
    target: int = 5,
    model: str | None = None,
    rewriter: str | None = None,
    market_data: list[int] | None = None,
) -> str:
    """Run exactly the supplied bounded search without changing environment variables."""
    await asyncio.to_thread(
        run,
        episodes=episodes,
        target=target,
        model=model,
        rewriter=rewriter or "random",
        market_data=market_data,
    )
    return f"completed {episodes} episodes toward target {target}"


def _run_runtime(
    episodes: int,
    target: int,
    model: str | None = None,
    rewriter: str | None = None,
    market_data: list[int] | None = None,
    enable_adk: bool = False,
) -> None:
    from agents import Agent, Runner, RunConfig, function_tool, set_tracing_disabled
    from agents.models.openai_provider import OpenAIProvider
    from openai import AsyncOpenAI

    # Import and initialize optional provider components only on this explicit CLI path.
    set_tracing_disabled(True)
    completed: str | None = None

    @function_tool(name_override="run_search", description_override="Execute the configured bounded integer search")
    async def execute_search() -> str:
        nonlocal completed
        if completed is None:
            completed = await run_search(episodes, target, model, rewriter, market_data)
        return completed

    agent = Agent(
        name="mats_helper",
        model=model or DEFAULT_MODEL_NAME,
        instructions="Call run_search once, then return its summary. Its configured parameters must not be changed.",
        tools=[execute_search],
    )
    if enable_adk:
        try:
            from alpha_factory_v1.backend import adk_bridge

            if adk_bridge.adk_enabled():
                adk_bridge.auto_register([agent])
                adk_bridge.maybe_launch()
            else:
                logger.warning("ADK gateway is not enabled in this environment")
        except Exception as exc:  # pragma: no cover - optional adapter
            logger.warning("ADK gateway unavailable: %s", type(exc).__name__)

    async def coordinate() -> None:
        async with AsyncOpenAI(timeout=15.0, max_retries=0) as client:
            await Runner.run(
                agent,
                "Execute the configured search and return its result.",
                max_turns=3,
                run_config=RunConfig(model_provider=OpenAIProvider(openai_client=client), tracing_disabled=True),
            )

    try:
        asyncio.run(coordinate())
    except Exception:
        if completed is None:
            raise
        logger.warning("Coordinator response unavailable; keeping the completed search without repeating it")
    if completed is None:
        raise RuntimeError("The SDK coordinator did not execute the configured search")
    logger.info("%s", completed)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Optional OpenAI Agents bridge for the preserved integer MATS demo")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--target", type=int, default=5)
    parser.add_argument("--model", type=str)
    parser.add_argument("--rewriter", choices=["random", "openai", "anthropic"])
    parser.add_argument("--market-data", type=Path, help="Local comma-separated integer target replay")
    parser.add_argument("--enable-adk", action="store_true", help="Enable the optional configured ADK adapter")
    parser.add_argument("--verify-env", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.episodes <= 10000 or not -10000 <= args.target <= 10000:
        parser.error("Use 1–10000 episodes and a target between -10000 and 10000")
    market_data = None
    if args.market_data:
        with args.market_data.open(encoding="utf-8") as stream:
            data = stream.read(1_000_001)
        if len(data) > 1_000_000:
            parser.error("Market replay exceeds 1 MB")
        try:
            market_data = [int(value) for value in data.split(",") if value.strip()]
        except ValueError:
            parser.error("Market replay must contain comma-separated integers")
    if args.verify_env:
        verify_env()
    if args.enable_adk:
        os.environ.setdefault("ALPHA_FACTORY_ENABLE_ADK", "true")
    if has_oai and os.getenv("OPENAI_API_KEY") and os.getenv("NO_LLM") != "1":
        try:
            _run_runtime(args.episodes, args.target, args.model, args.rewriter, market_data, args.enable_adk)
            return
        except Exception as exc:  # pragma: no cover - optional online runtime
            logger.warning("SDK coordinator unavailable (%s); running the configured offline demo", type(exc).__name__)
    else:
        logger.info("SDK coordinator unavailable or disabled. Running offline demo...")
    run(
        episodes=args.episodes,
        target=args.target,
        model=args.model,
        rewriter=args.rewriter or "random",
        market_data=market_data,
    )


__all__ = ["DEFAULT_MODEL_NAME", "has_oai", "run_search", "verify_env", "main"]

if __name__ == "__main__":
    main()
