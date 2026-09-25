# SPDX-License-Identifier: Apache-2.0
"""Command line launcher for Alpha‑Factory v1."""

import os
import argparse
import sys
from pathlib import Path

from .utils.disclaimer import print_disclaimer

from .utils.env import _load_env_file

from .scripts.preflight import main as preflight_main
from . import __version__


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Return command line arguments for the launcher."""
    ap = argparse.ArgumentParser(description="Alpha-Factory launcher")
    ap.add_argument("--dev", action="store_true", help="Enable dev mode")
    ap.add_argument("--env-file", help="Load environment variables from file")
    ap.add_argument("--preflight", action="store_true", help="Run environment checks and exit")
    ap.add_argument("--port", type=int, help="REST API port")
    ap.add_argument("--metrics-port", type=int, help="Prometheus metrics port")
    ap.add_argument("--a2a-port", type=int, help="A2A gRPC port")
    ap.add_argument("--enabled", help="Comma separated list of enabled agents")
    ap.add_argument(
        "--loglevel",
        default=None,
        help="Log level (defaults to $LOGLEVEL or INFO)",
    )
    ap.add_argument("--version", action="store_true", help="Print version and exit")
    ap.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agents and exit",
    )
    return ap.parse_args(argv)


def apply_env(args: argparse.Namespace) -> None:
    """Apply command line options to ``os.environ``.

    Args:
        args: Parsed command line arguments.

    Returns:
        None
    """
    env_file = args.env_file
    if env_file is None and Path(".env").is_file():
        env_file = ".env"
    if env_file:
        for k, v in _load_env_file(env_file).items():
            os.environ.setdefault(k, v)
    if args.dev:
        os.environ["DEV_MODE"] = "true"
    if args.port is not None:
        os.environ["PORT"] = str(args.port)
    if args.metrics_port is not None:
        os.environ["METRICS_PORT"] = str(args.metrics_port)
    if args.a2a_port is not None:
        os.environ["A2A_PORT"] = str(args.a2a_port)
    if args.enabled is not None:
        os.environ["ALPHA_ENABLED_AGENTS"] = args.enabled
    if args.loglevel:
        os.environ["LOGLEVEL"] = args.loglevel.upper()


def run(show_disclaimer: bool = True) -> None:
    """Entry point used by the ``alpha-factory`` console script."""
    if len(sys.argv) > 1 and sys.argv[1] == "mission":
        from .core.runtime.cli import main

        raise SystemExit(main(sys.argv[2:]))
    args = parse_args()
    if show_disclaimer:
        print_disclaimer()
    if args.version:
        print(__version__)
        return
    if args.list_agents:
        from .backend.agents import list_agents

        for name in list_agents():
            print(name)
        return
    if args.preflight:
        preflight_main()
        return
    apply_env(args)
    from .backend.orchestrator import Orchestrator

    Orchestrator().run_forever()


if __name__ == "__main__":
    run()
