# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
# NOTE: This demo is a research prototype and does not implement real AGI.
"""OpenAI Agents SDK bridge for the α‑AGI Insight demo.

This utility exposes the Meta‑Agentic Tree Search loop used by
:mod:`alpha_agi_insight_v0` through the OpenAI Agents runtime.
It gracefully degrades to offline mode when the optional
``openai-agents`` package is missing or the environment lacks API keys.
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o")

# Prefix used when running without the optional ``openai-agents`` package.
# Makes it easy for unit tests and calling code to detect the offline path.
FALLBACK_MODE_PREFIX = "fallback_mode_active: "


def _truthy(val: bool | str | None) -> bool:
    """Return ``True`` when *val* represents an affirmative value."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "y"}
    return False


def banner() -> str:
    """Return the standard startup banner."""
    return (
        "\N{MILITARY MEDAL} \N{GREEK SMALL LETTER ALPHA}\N{HYPHEN-MINUS}AGI"
        " Insight \N{EYE}\N{SPARKLES} — Beyond Human Foresight"
        " (Zero‑Data Official Demo)"
    )


def print_banner() -> None:
    """Display the default banner."""
    print(banner())


if __package__ is None:  # pragma: no cover - allow direct execution
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from .insight_demo import parse_sectors, run, verify_environment
from ... import get_version

try:
    _spec = importlib.util.find_spec("openai_agents")
except ValueError:  # loaded stub with missing spec
    _spec = None

_has_key = bool(os.getenv("OPENAI_API_KEY"))
_has_runtime = False
if _spec is not None:
    try:
        import openai_agents as _oa

        _has_runtime = hasattr(getattr(_oa, "AgentRuntime", None), "run")
    except Exception:  # pragma: no cover - optional dependency
        _has_runtime = False

has_oai = bool(_spec is not None and _has_key and _has_runtime)


def refresh_runtime_availability() -> bool:
    """Recompute :data:`has_oai` after environment changes."""
    global has_oai, _spec, _has_key, _has_runtime
    try:
        _spec = importlib.util.find_spec("openai_agents")
    except ValueError:  # pragma: no cover - loaded stub without spec
        _spec = None
    _has_key = bool(os.getenv("OPENAI_API_KEY"))
    _has_runtime = False
    if _spec is not None:
        try:
            import openai_agents as _oa

            _has_runtime = hasattr(getattr(_oa, "AgentRuntime", None), "run")
        except Exception:  # pragma: no cover - optional dependency
            _has_runtime = False

    has_oai = bool(_spec is not None and _has_key and _has_runtime)
    return has_oai


if has_oai:
    from openai_agents import Agent, AgentRuntime, Tool  # type: ignore

    @Tool(name="run_insight_search", description="Run the α‑AGI Insight demo")
    async def run_insight_search(
        episodes: int = 5,
        target: int = 3,
        model: str | None = None,
        rewriter: str | None = None,
        sectors: str | None = None,
        log_dir: str | None = None,
        exploration: float | None = None,
        seed: int | None = None,
        json_output: bool | None = None,
    ) -> str:
        """Execute the search loop and return the textual summary."""
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        if rewriter:
            os.environ.setdefault("MATS_REWRITER", rewriter)
        sector_list = parse_sectors(None, sectors)
        result = run(
            episodes=episodes,
            target=target,
            model=model,
            rewriter=rewriter,
            log_dir=Path(log_dir) if log_dir else None,
            exploration=exploration or 1.4,
            seed=seed,
            sectors=sector_list,
            json_output=_truthy(json_output),
        )
        return result

    class InsightAgent(Agent):
        name = "agi_insight_helper"
        tools = [run_insight_search]

        async def policy(self, obs, _ctx):  # type: ignore[override]
            params = obs if isinstance(obs, dict) else {}
            return await run_insight_search(
                episodes=int(params.get("episodes", 5)),
                target=int(params.get("target", 3)),
                model=params.get("model"),
                rewriter=params.get("rewriter"),
                sectors=params.get("sectors"),
                log_dir=params.get("log_dir"),
                exploration=float(params.get("exploration", 1.4)),
                seed=params.get("seed"),
                json_output=params.get("json", False),
            )

    def _run_runtime(
        episodes: int,
        target: int,
        model: str | None = None,
        rewriter: str | None = None,
        log_dir: str | None = None,
        sectors: str | None = None,
        exploration: float | None = None,
        seed: int | None = None,
        json_output: bool | None = None,
        *,
        adk_host: str | None = None,
        adk_port: int | None = None,
    ) -> None:
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        if rewriter:
            os.environ.setdefault("MATS_REWRITER", rewriter)
        if sectors:
            os.environ.setdefault("ALPHA_AGI_SECTORS", sectors)
        if exploration is not None:
            os.environ.setdefault("ALPHA_AGI_EXPLORATION", str(exploration))
        if seed is not None:
            os.environ.setdefault("ALPHA_AGI_SEED", str(seed))
        runtime = AgentRuntime(api_key=os.getenv("OPENAI_API_KEY"))
        agent = InsightAgent()
        runtime.register(agent)
        try:
            from alpha_factory_v1.backend import adk_bridge

            if adk_bridge.adk_enabled():
                adk_bridge.auto_register([agent])
                adk_bridge.maybe_launch(host=adk_host, port=adk_port)
            else:
                logger.info("ADK gateway disabled.")
        except ImportError as exc:  # pragma: no cover - optional ADK
            logger.warning(f"ADK bridge import failed: {exc}")
        except AttributeError as exc:  # pragma: no cover - optional ADK
            logger.error(f"ADK bridge attribute error: {exc}")

        logger.info("Registered InsightAgent with runtime")
        runtime.run()

else:

    async def run_insight_search(
        episodes: int = 5,
        target: int = 3,
        model: str | None = None,
        rewriter: str | None = None,
        sectors: str | None = None,
        log_dir: str | None = None,
        exploration: float | None = None,
        seed: int | None = None,
        json_output: bool | None = None,
    ) -> str:
        sector_list = parse_sectors(None, sectors)
        summary = run(
            episodes=episodes,
            target=target,
            model=model,
            rewriter=rewriter,
            log_dir=Path(log_dir) if log_dir else None,
            exploration=exploration or 1.4,
            seed=seed,
            sectors=sector_list,
            json_output=_truthy(json_output),
        )
        return f"{FALLBACK_MODE_PREFIX}{summary}"

    def _run_runtime(
        episodes: int,
        target: int,
        model: str | None = None,
        rewriter: str | None = None,
        log_dir: str | None = None,
        sectors: str | None = None,
        exploration: float | None = None,
        seed: int | None = None,
        json_output: bool | None = None,
        *,
        adk_host: str | None = None,
        adk_port: int | None = None,
    ) -> None:
        """Execute the demo directly when the Agents runtime is unavailable."""
        if model:
            os.environ.setdefault("OPENAI_MODEL", model)
        if rewriter:
            os.environ.setdefault("MATS_REWRITER", rewriter)
        if sectors:
            os.environ.setdefault("ALPHA_AGI_SECTORS", sectors)
        if exploration is not None:
            os.environ.setdefault("ALPHA_AGI_EXPLORATION", str(exploration))
        if seed is not None:
            os.environ.setdefault("ALPHA_AGI_SEED", str(seed))

        import asyncio

        summary = asyncio.run(
            run_insight_search(
                episodes=episodes,
                target=target,
                model=model,
                rewriter=rewriter,
                sectors=sectors,
                log_dir=log_dir,
                exploration=exploration,
                seed=seed,
                json_output=json_output,
            )
        )
        print(summary)

    def _run_runtime(
        episodes: int,
        target: int,
        model: str | None = None,
        rewriter: str | None = None,
        log_dir: str | None = None,
        sectors: str | None = None,
        exploration: float | None = None,
        seed: int | None = None,
        json_output: bool | None = None,
        *,
        adk_host: str | None = None,
        adk_port: int | None = None,
    ) -> None:
        reasons = []
        if _spec is None:
            reasons.append("OpenAI Agents package missing")
        if not _has_key:
            reasons.append("OPENAI_API_KEY not set")
        msg = " and ".join(reasons) or "offline mode"
        print(f"Running offline demo in {msg}…")
        # Ensure submodules detect the offline environment
        os.environ.setdefault("ALPHA_AGI_OFFLINE", "true")
        sector_list = parse_sectors(None, sectors)
        episodes = int(episodes or os.getenv("ALPHA_AGI_EPISODES", 0) or 5)
        exploration = float(exploration or os.getenv("ALPHA_AGI_EXPLORATION", 1.4))
        rewriter = rewriter or os.getenv("MATS_REWRITER")
        target = int(target or os.getenv("ALPHA_AGI_TARGET", 3))
        if seed is None:
            seed_env = os.getenv("ALPHA_AGI_SEED")
            seed = int(seed_env) if seed_env else None
        model = model or os.getenv("OPENAI_MODEL")
        summary = run(
            episodes=episodes,
            exploration=exploration,
            rewriter=rewriter,
            log_dir=Path(log_dir) if log_dir else None,
            target=target,
            seed=seed,
            model=model,
            sectors=sector_list,
            json_output=_truthy(json_output),
        )
        print(summary)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="OpenAI Agents bridge for the α‑AGI Insight demo")
    parser.add_argument("--episodes", type=int, help="Search episodes when offline")
    parser.add_argument("--target", type=int, help="Target sector index when offline")
    parser.add_argument("--model", type=str, help="Model name override")
    parser.add_argument(
        "--rewriter",
        choices=["random", "openai", "anthropic"],
        help="Rewrite strategy",
    )
    parser.add_argument(
        "--exploration",
        type=float,
        help="Exploration constant when offline",
    )
    parser.add_argument("--seed", type=int, help="Optional RNG seed")
    parser.add_argument("--sectors", type=str, help="Comma-separated sector names")
    parser.add_argument(
        "--log-dir",
        type=str,
        help="Directory to store episode logs",
    )
    parser.add_argument(
        "--list-sectors",
        action="store_true",
        help="Print the resolved sector list and exit",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the startup banner",
    )
    parser.add_argument(
        "--enable-adk",
        action="store_true",
        help="Enable the Google ADK gateway",
    )
    parser.add_argument("--adk-host", type=str, help="ADK bind host")
    parser.add_argument("--adk-port", type=int, help="ADK bind port")
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip runtime dependency checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Return JSON summary when offline or via tool",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show package version and exit",
    )
    args = parser.parse_args(argv)

    if not args.no_banner and os.getenv("ALPHA_AGI_NO_BANNER", "false").lower() not in {"1", "true", "yes"}:
        print_banner()

    enable_adk = args.enable_adk or os.getenv("ALPHA_AGI_ENABLE_ADK") == "true"
    if args.adk_host is None:
        args.adk_host = os.getenv("ALPHA_AGI_ADK_HOST")
    if args.adk_port is None and os.getenv("ALPHA_AGI_ADK_PORT"):
        try:
            args.adk_port = int(os.getenv("ALPHA_AGI_ADK_PORT"))
        except ValueError:
            args.adk_port = None

    if not args.skip_verify:
        verify_environment()

    sector_list = parse_sectors(None, args.sectors)
    if args.list_sectors:
        print("Sectors:")
        for name in sector_list:
            print(f"- {name}")
        return

    if enable_adk:
        os.environ.setdefault("ALPHA_FACTORY_ENABLE_ADK", "true")

    _run_runtime(
        args.episodes,
        args.target,
        args.model,
        args.rewriter,
        args.log_dir,
        args.sectors,
        args.exploration,
        args.seed,
        json_output=_truthy(args.json),
        adk_host=args.adk_host,
        adk_port=args.adk_port,
    )


__all__ = [
    "DEFAULT_MODEL_NAME",
    "has_oai",
    "refresh_runtime_availability",
    "run_insight_search",
    "banner",
    "print_banner",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    main()
