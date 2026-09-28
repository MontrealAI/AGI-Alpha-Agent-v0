# SPDX-License-Identifier: Apache-2.0
"""Run, export, verify or locally serve the dependency-free Experience Lab."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lab import brief, evaluate, read_json, verify, write_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Experience Lab: learn from synthetic outcomes, then test a frozen policy"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--case", help="Starter case (default: build-routing)")
    group.add_argument("--input", type=Path, help="Local scenario JSON, up to 1 MB")
    group.add_argument("--verify", type=Path, help="Recompute a complete exported run")
    group.add_argument("--list", action="store_true", help="List synthetic cases")
    group.add_argument("--serve", action="store_true", help="Serve the local browser lab on loopback only")
    parser.add_argument("--port", type=int, default=7860, help="Local browser port (default 7860)")
    parser.add_argument("--output", type=Path, default=Path("experience-runs"), help="Write six evidence files per run")
    parser.add_argument("--json", action="store_true", help="Print the complete run as JSON")
    args = parser.parse_args(argv)
    try:
        if args.serve:
            from .lab_server import serve

            serve(args.port)
            return 0
        cases = read_json(Path(__file__).with_name("scenarios.json"))
        if args.list:
            for case in cases:
                print(f"{case['id']:<24} {case['title']}")
            return 0
        if args.verify:
            report = verify(read_json(args.verify))
            print(
                json.dumps(report, ensure_ascii=False)
                if args.json
                else f"Recomputed every episode, policy and gate: {report['sha256']}"
            )
            return 0
        scenario = (
            read_json(args.input)
            if args.input
            else next((c for c in cases if c["id"] == (args.case or "build-routing")), None)
        )
        if scenario is None:
            raise ValueError("Unknown case. Use --list to see available cases.")
        report = evaluate(scenario)
        target = write_bundle(report, args.output)
        if args.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print(brief(report))
            print(f"Saved six evidence files: {target.resolve()}")
            print(f'Verify: python -m alpha_factory_v1.demos.era_of_experience --verify "{target / "run.json"}"')
        return 0
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        print(f"Experience Lab: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Experience Lab stopped. Existing exports remain intact.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
