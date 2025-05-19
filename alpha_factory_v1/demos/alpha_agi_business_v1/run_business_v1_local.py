#!/usr/bin/env python3
"""Local launcher for the Alpha‑AGI Business v1 demo.

Runs the orchestrator directly without Docker and optionally starts the
OpenAI Agents bridge when available. This script is intended for quick
experimentation on a developer workstation or inside a Colab runtime.
"""
from __future__ import annotations

import argparse
import threading

import check_env
from alpha_factory_v1.demos.alpha_agi_business_v1 import alpha_agi_business_v1


def _start_bridge() -> None:
    """Start the OpenAI Agents bridge in a background thread."""
    try:
        from alpha_factory_v1.demos.alpha_agi_business_v1 import openai_agents_bridge
    except Exception as exc:  # pragma: no cover - optional dep
        print(f"⚠️  OpenAI bridge not available: {exc}")
        return
    thread = threading.Thread(target=openai_agents_bridge.main, daemon=True)
    thread.start()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run alpha_agi_business_v1 locally")
    parser.add_argument(
        "--bridge",
        action="store_true",
        help="Launch OpenAI Agents bridge if available",
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Attempt automatic installation of missing packages",
    )
    parser.add_argument(
        "--wheelhouse",
        help="Optional local wheelhouse path for offline installs",
    )
    args = parser.parse_args(argv)

    check_opts: list[str] = []
    if args.auto_install:
        check_opts.append("--auto-install")
    if args.wheelhouse:
        check_opts += ["--wheelhouse", args.wheelhouse]

    check_env.main(check_opts)

    if args.bridge:
        _start_bridge()

    alpha_agi_business_v1.main()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
