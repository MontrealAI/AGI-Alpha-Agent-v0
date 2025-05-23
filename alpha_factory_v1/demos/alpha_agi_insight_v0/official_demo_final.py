#!/usr/bin/env python3
"""Entry point for the *Beyond Human Foresight* α‑AGI Insight demo.

This wrapper automatically chooses the most capable runtime for the
Meta‑Agentic Tree Search. When the optional OpenAI Agents SDK is
installed and an API key is configured the demo registers an agent with
the hosted runtime.  In environments without these credentials it
transparently falls back to the lightweight offline CLI so the search can
run anywhere.  Runtime dependencies are verified when ``--verify-env`` is
supplied and the optional Google ADK gateway is enabled when available.
The behaviour mirrors ``alpha-agi-insight-final`` and provides the
official, production‑ready experience for the demo regardless of network
access.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

if __package__ is None:  # pragma: no cover - allow `python official_demo_final.py`
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from . import insight_demo
from . import openai_agents_bridge
from . import insight_dashboard
from ... import get_version


def _agents_available() -> bool:
    """Return ``True`` when the OpenAI Agents runtime is usable.

    An explicit ``ALPHA_AGI_OFFLINE`` environment variable forces offline mode
    even when the package and API key are present.  This mirrors the
    ``--offline`` command line option and offers parity with other demos.
    """

    if os.getenv("ALPHA_AGI_OFFLINE"):
        return False
    return openai_agents_bridge.refresh_runtime_availability()


def _run_offline(args: argparse.Namespace) -> None:
    """Execute the search loop using local defaults and environment overrides."""

    print("Running offline demo…")

    sectors = insight_demo.parse_sectors(None, args.sectors)

    episodes = int(args.episodes or os.getenv("ALPHA_AGI_EPISODES", 0) or 5)
    exploration = float(
        args.exploration
        if args.exploration is not None
        else os.getenv("ALPHA_AGI_EXPLORATION", 1.4)
    )
    rewriter = args.rewriter or os.getenv("MATS_REWRITER")
    target = int(
        args.target if args.target is not None else os.getenv("ALPHA_AGI_TARGET", 3)
    )
    seed_val = args.seed if args.seed is not None else os.getenv("ALPHA_AGI_SEED")
    seed = int(seed_val) if seed_val is not None else None
    model = args.model or os.getenv("OPENAI_MODEL")

    result = insight_demo.run(
        episodes=episodes,
        exploration=exploration,
        rewriter=rewriter,
        log_dir=Path(args.log_dir) if args.log_dir else None,
        target=target,
        seed=seed,
        model=model,
        sectors=sectors,
        json_output=args.json,
    )
    if args.json:
        print(result)


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch the α‑AGI Insight demo")
    parser.add_argument("--episodes", type=int, help="Search iterations")
    parser.add_argument("--target", type=int, help="Target sector index")
    parser.add_argument("--exploration", type=float, help="Exploration constant")
    parser.add_argument("--seed", type=int, help="Optional RNG seed")
    parser.add_argument("--model", type=str, help="Model override")
    parser.add_argument(
        "--rewriter", choices=["random", "openai", "anthropic"], help="Rewrite strategy"
    )
    parser.add_argument(
        "--sectors", type=str, help="Comma-separated sectors or path to file"
    )
    parser.add_argument("--log-dir", type=str, help="Directory for episode metrics")
    parser.add_argument("--offline", action="store_true", help="Force offline mode")
    parser.add_argument(
        "--skip-verify", action="store_true", help="Skip environment check"
    )
    parser.add_argument(
        "--enable-adk",
        action="store_true",
        help="Expose agent via the optional ADK gateway",
    )
    parser.add_argument("--adk-host", type=str, help="ADK bind host")
    parser.add_argument("--adk-port", type=int, help="ADK bind port")
    parser.add_argument(
        "--list-sectors",
        action="store_true",
        help="Display the resolved sector list and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Return JSON summary instead of text",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the Streamlit dashboard and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show package version and exit",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the startup banner",
    )
    args = parser.parse_args(argv)

    skip_verify_env = os.getenv("ALPHA_AGI_SKIP_VERIFY")
    if skip_verify_env and not args.skip_verify:
        args.skip_verify = skip_verify_env.lower() == "true"

    no_banner_env = os.getenv("ALPHA_AGI_NO_BANNER")
    if no_banner_env and not args.no_banner:
        args.no_banner = no_banner_env.lower() == "true"

    enable_adk = args.enable_adk or os.getenv("ALPHA_AGI_ENABLE_ADK") == "true"
    if args.adk_host is None:
        args.adk_host = os.getenv("ALPHA_AGI_ADK_HOST")
    if args.adk_port is None and os.getenv("ALPHA_AGI_ADK_PORT"):
        try:
            args.adk_port = int(os.getenv("ALPHA_AGI_ADK_PORT"))
        except ValueError:
            args.adk_port = None

    if not args.no_banner:
        openai_agents_bridge.print_banner()

    if not args.skip_verify:
        insight_demo.verify_environment()

    if args.list_sectors:
        sector_list = insight_demo.parse_sectors(None, args.sectors)
        print("Sectors:")
        for name in sector_list:
            print(f"- {name}")
        return

    if args.dashboard:
        insight_dashboard.main()
        return

    if args.offline or not _agents_available():
        _run_offline(args)
    else:
        if enable_adk:
            os.environ.setdefault("ALPHA_FACTORY_ENABLE_ADK", "true")
        openai_agents_bridge._run_runtime(
            args.episodes or 5,
            args.target or 3,
            args.model,
            args.rewriter,
            args.log_dir,
            args.sectors,
            exploration=args.exploration,
            seed=args.seed,
            json_output=args.json,
            adk_host=args.adk_host,
            adk_port=args.adk_port,
        )


if __name__ == "__main__":  # pragma: no cover
    main()
