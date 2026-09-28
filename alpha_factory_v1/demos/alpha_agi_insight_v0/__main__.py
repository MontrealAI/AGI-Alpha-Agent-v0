#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Launch discovery by default; retain all explicit legacy search options."""
from __future__ import annotations
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    legacy = {
        "--version",
        "--legacy",
        "--episodes",
        "--target",
        "--exploration",
        "--seed",
        "--rewriter",
        "--model",
        "--sectors",
        "--list-sectors",
        "--log-dir",
        "--config",
        "--offline",
        "--skip-verify",
        "--verify-env",
        "--no-banner",
        "--dashboard",
        "--runtime",
        "--enable-adk",
        "--adk-host",
        "--adk-port",
    }
    if any(arg.split("=", 1)[0] in legacy for arg in args):
        from .official_demo_final import main as launch

        launch([arg for arg in args if arg != "--legacy"])
        return 0
    from .discovery_cli import main as discovery

    return discovery(args)


if __name__ == "__main__":
    raise SystemExit(main())
