# SPDX-License-Identifier: Apache-2.0
"""Run or replay a finite governance review without providers or credentials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from alpha_factory_v1.utils.disclaimer import print_disclaimer
from .workbench import brief, evaluate, read_json, verify, write_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Governance workbench: review proposal gates and export verification jobs"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--case", help="Built-in scenario (default: accountable-upgrade)")
    group.add_argument("--input", type=Path, help="Local scenario JSON")
    group.add_argument("--verify", type=Path, help="Recompute an exported dossier; no output is written")
    group.add_argument("--list", action="store_true", help="List the constructed cases")
    parser.add_argument(
        "--output", type=Path, default=Path("governance-runs"), help="Retain content-addressed evidence here"
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")
    args = parser.parse_args(argv)
    try:
        cases = read_json(Path(__file__).with_name("scenarios.json"))
        if args.list:
            for case in cases:
                print(f"{case['id']:<24} {case['title']}")
            return 0
        if args.verify:
            report = verify(read_json(args.verify))
            print(json.dumps(report) if args.json else f"Recomputed every gate and job: {report['sha256']}")
            return 0
        scenario = (
            read_json(args.input)
            if args.input
            else next((case for case in cases if case["id"] == (args.case or "accountable-upgrade")), None)
        )
        if scenario is None:
            raise ValueError("Unknown case. Use --list to see the available scenarios.")
        report = evaluate(scenario)
        folder = write_bundle(report, args.output)
        if args.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print_disclaimer()
            print(brief(report))
            print(f"Saved 5 evidence files: {folder.resolve()}")
            print(f'Verify: governance-workbench --verify "{folder / "dossier.json"}"')
            print(f'Prepare jobs: alpha-agent ascension-compile "{folder / "jobs.json"}" --output fusion-plan.json')
            print("A valid BLOCKED result is a successful calculation, not a process error.")
        return 0
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        print(f"Governance: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Stopped. Prior output is retained; use a new directory if a run is partial.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
