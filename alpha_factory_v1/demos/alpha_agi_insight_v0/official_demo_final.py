#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# References to "AGI" and "superintelligence" describe aspirational goals
# and do not indicate the presence of a real general intelligence.
# Use at your own risk. Nothing herein constitutes financial advice.
# MontrealAI and the maintainers accept no liability for losses incurred.
"""Preserved search launcher with explicit offline/provider/runtime boundaries."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import sys
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
from .insight_dashboard import main as launch_dashboard
from ... import get_version


def _agents_available() -> bool:
    """Return ``True`` when the OpenAI Agents runtime is usable.

    An explicit ``ALPHA_AGI_OFFLINE`` environment variable forces offline mode
    even when the package and API key are present.  This mirrors the
    ``--offline`` command line option and offers parity with other demos.
    """

    if insight_demo.offline_requested():
        return False
    return openai_agents_bridge.refresh_runtime_availability()


def _run_offline(args: argparse.Namespace) -> None:
    """Execute the search loop using local defaults and environment overrides."""

    if not args.json:
        print("Running local search demo…")

    sectors = insight_demo.parse_sectors(None, args.sectors)

    episodes = int(args.episodes if args.episodes is not None else os.getenv("ALPHA_AGI_EPISODES", 5))
    exploration = float(args.exploration if args.exploration is not None else os.getenv("ALPHA_AGI_EXPLORATION", 1.4))
    rewriter = args.rewriter or os.getenv("MATS_REWRITER")
    target = int(args.target if args.target is not None else os.getenv("ALPHA_AGI_TARGET", 3))
    seed_val = args.seed if args.seed is not None else os.getenv("ALPHA_AGI_SEED")
    seed = int(seed_val) if seed_val is not None else None
    model = args.model

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
        offline=args.offline,
    )
    if args.json:
        print(result)


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch the α‑AGI Insight demo")
    parser.add_argument("--episodes", type=int, help="Search iterations")
    parser.add_argument("--target", type=int, help="Toy numeric target; not a sector forecast")
    parser.add_argument("--exploration", type=float, help="Exploration constant")
    parser.add_argument("--seed", type=int, help="Optional RNG seed")
    parser.add_argument("--model", type=str, help="Model override")
    parser.add_argument("--rewriter", choices=["random", "openai", "anthropic"], help="Rewrite strategy")
    parser.add_argument("--sectors", type=str, help="Comma-separated sectors or path to file")
    parser.add_argument("--log-dir", type=str, help="Directory for episode metrics")
    parser.add_argument("--offline", action="store_true", help="Forbid provider calls")
    parser.add_argument(
        "--runtime", action="store_true", help="Explicitly start an installed legacy compatibility runtime"
    )
    parser.add_argument("--verify-env", action="store_true", help="Check optional runtime dependencies")
    parser.add_argument("--config", type=Path, help="YAML search configuration")
    parser.add_argument("--skip-verify", action="store_true", help="Skip environment check")
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

    if not args.no_banner and not args.json:
        openai_agents_bridge.print_banner()

    if args.verify_env and not args.skip_verify:
        with redirect_stdout(sys.stderr):
            insight_demo.verify_environment()

    try:
        if args.config:
            cfg = insight_demo.load_config(args.config)
            for key, value in cfg.items():
                if getattr(args, key, None) is None:
                    setattr(args, key, value)
        if args.list_sectors:
            sector_list = insight_demo.parse_sectors(None, args.sectors)
            print("Sectors:")
            for name in sector_list:
                print(f"- {name}")
            return
        if args.dashboard:
            previous = os.environ.get("ALPHA_AGI_OFFLINE")
            try:
                if args.offline:
                    os.environ["ALPHA_AGI_OFFLINE"] = "true"
                launch_dashboard()
            finally:
                if args.offline:
                    if previous is None:
                        os.environ.pop("ALPHA_AGI_OFFLINE", None)
                    else:
                        os.environ["ALPHA_AGI_OFFLINE"] = previous
            return
        if args.offline and args.runtime:
            raise ValueError("--offline cannot be combined with --runtime")
        if args.runtime:
            if not _agents_available():
                raise ValueError("The legacy runtime interface is unavailable. Omit --runtime for a local run.")
            if enable_adk:
                os.environ.setdefault("ALPHA_FACTORY_ENABLE_ADK", "true")
            openai_agents_bridge._run_runtime(
                args.episodes if args.episodes is not None else 5,
                args.target if args.target is not None else 3,
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
        else:
            if enable_adk:
                raise ValueError("ADK exposure requires an explicit --runtime")
            _run_offline(args)
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":  # pragma: no cover
    main()
