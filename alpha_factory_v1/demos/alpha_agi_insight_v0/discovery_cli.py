# SPDX-License-Identifier: Apache-2.0
"""Run or replay an Insight discovery portfolio without providers or credentials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .discovery import brief, evaluate, read_json, verify, write_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Insight discovery: source-linked opportunities and a bounded review portfolio"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--case", help="Constructed scenario (default: public-software)")
    group.add_argument("--input", type=Path, help="Local scenario JSON")
    group.add_argument("--verify", type=Path, help="Recompute an exported dossier without writing output")
    group.add_argument("--list", action="store_true", help="List the available cases")
    parser.add_argument("--output", type=Path, default=Path("insight-runs"), help="Retain six evidence files here")
    parser.add_argument("--json", action="store_true", help="Print only the complete JSON dossier")
    args = parser.parse_args(argv)
    try:
        cases = read_json(Path(__file__).with_name("scenarios.json"))
        if args.list:
            for case in cases:
                print(f"{case['id']:<24} {case['title']}")
            return 0
        if args.verify:
            report = verify(read_json(args.verify))
            print(
                json.dumps(report)
                if args.json
                else f"Recomputed scores, portfolio, jobs and drafts: {report['sha256']}"
            )
            return 0
        scenario = (
            read_json(args.input)
            if args.input
            else next((c for c in cases if c["id"] == (args.case or "public-software")), None)
        )
        if scenario is None:
            raise ValueError("Unknown case. Use --list to see available cases.")
        report = evaluate(scenario)
        folder = write_bundle(report, args.output)
        if args.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print(brief(report))
            print(f"Saved 6 evidence files: {folder.resolve()}")
            print(f'Verify: insight-workbench --verify "{folder / "dossier.json"}"')
            print(f'Prepare jobs: alpha-agent ascension-compile "{folder / "jobs.json"}" --output fusion-plan.json')
        return 0
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        print(f"Insight: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Stopped. Prior output remains intact; use a new directory if a run is partial.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
