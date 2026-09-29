# SPDX-License-Identifier: Apache-2.0
"""Dependency-free dashboard, finite experiment, and exact report verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import print_disclaimer
from .delivery import export, strict_json, verify
from .paper import CASES, Config, MAX_BYTES, STRATEGIES, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finance Alpha — inspect costs, risk and paper P&L; no live orders")
    parser.add_argument("--headless", action="store_true", help="Run once and write a new evidence directory")
    parser.add_argument("--case", choices=CASES, default="trend")
    parser.add_argument("--input", type=Path, help="Aligned date,symbol,open,close CSV; requires --headless")
    parser.add_argument("--strategy", choices=STRATEGIES, default="momentum")
    parser.add_argument("--cash", type=float, default=10000)
    parser.add_argument("--fee-bps", type=float, default=10)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--rebalance-every", type=int, default=5)
    parser.add_argument("--max-exposure", type=float, default=0.9)
    parser.add_argument("--max-position", type=float, default=0.6)
    parser.add_argument("--max-drawdown", type=float, default=0.15)
    parser.add_argument("--max-cvar", type=float, default=0.04)
    parser.add_argument("--output", type=Path, help="New directory; required with --headless")
    parser.add_argument("--verify", type=Path, help="Replay an exported report.json and exit")
    parser.add_argument("--port", type=int, default=7864)
    args = parser.parse_args(argv)
    try:
        if args.verify:
            if args.headless or args.input or args.output:
                raise ValueError("--verify cannot be combined with --headless, --input or --output")
            with args.verify.open("rb") as source:
                raw = source.read(32_000_001)
            if len(raw) > 32_000_000:
                raise ValueError("Report exceeds 32 MB")
            print(json.dumps(verify(strict_json(raw.decode("utf-8"))), indent=2))
            return 0
        config = Config(
            args.strategy,
            args.cash,
            args.lookback,
            args.rebalance_every,
            args.fee_bps,
            args.slippage_bps,
            args.max_exposure,
            args.max_position,
            args.max_drawdown,
            args.max_cvar,
        )
        if not 1 <= args.port <= 65535:
            raise ValueError("Port must be in 1–65535")
        if args.headless:
            if not args.output or args.output.exists():
                raise ValueError("--headless requires --output pointing to a new directory")
            text = None
            if args.input:
                with args.input.open("rb") as source:
                    raw = source.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError("CSV exceeds 2 MB")
                text = raw.decode("utf-8")
            report = run(text, config, case=args.case)
            export(report, args.output)
            print(json.dumps(report["result"]["summary"], indent=2))
            print(
                f"Open {(args.output / 'report.html').resolve()}\nVerify: python -m alpha_factory_v1.demos.finance_alpha --verify {args.output / 'report.json'}"
            )
        else:
            if args.output or args.input:
                raise ValueError("--input and --output require --headless")
            # Prevent a dashboard quietly ignoring requested experiment settings.
            if config != Config() or args.case != "trend":
                raise ValueError("Use --headless for CLI experiment settings, or set them in the dashboard")
            from .server import serve

            print_disclaimer()
            serve(args.port)
    except (ValueError, OSError, TypeError, RecursionError, OverflowError) as exc:
        parser.exit(2, f"Finance Alpha: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
