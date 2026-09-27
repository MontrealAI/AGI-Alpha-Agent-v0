# SPDX-License-Identifier: Apache-2.0
"""Offline enterprise decisions and an explicit opt-in to the preserved research loop."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from alpha_factory_v1.utils.disclaimer import print_disclaimer
from .enterprise import MAX_REPORT_BYTES, brief, read_json, solve, verify, write_bundle


def main(argv: list[str] | None = None) -> int:
    """Produce or verify a useful dossier without providers, services or downloads."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--legacy-loop" in argv:
        argv.remove("--legacy-loop")
        from .alpha_agi_business_3_v1 import main as legacy_main

        print_disclaimer()
        try:
            asyncio.run(legacy_main(argv))
            return 0
        except KeyboardInterrupt:
            return 130
        except (ValueError, OSError, RuntimeError, ImportError) as exc:
            print(f"Business 3 research integration: {exc}", file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(
        description="Business 3: allocate enterprise resources and export reviewable Ascension jobs.",
        epilog="Default operation is offline. Use --legacy-loop --help for the preserved optional research integrations.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--case", help="Built-in constructed scenario (default: industrial)")
    source.add_argument("--input", type=Path, help="Your scenario JSON; no URL is fetched")
    source.add_argument("--verify", type=Path, help="Recompute and verify an exported dossier without writing files")
    source.add_argument("--list", action="store_true", help="List included cases")
    parser.add_argument(
        "--output", type=Path, default=Path("business3-runs"), help="Directory retaining content-addressed runs"
    )
    parser.add_argument("--json", action="store_true", help="Print the complete dossier as JSON")
    args = parser.parse_args(argv)
    try:
        cases = read_json(Path(__file__).with_name("scenarios.json"))
        if args.list:
            for case in cases:
                print(f"{case['id']:<18} {case['title']}")
            return 0
        if args.verify:
            report = verify(read_json(args.verify, MAX_REPORT_BYTES))
            print(
                json.dumps(report)
                if args.json
                else f"Verified all decisions and job specifications: {report['sha256']}"
            )
            return 0
        if args.input:
            scenario = read_json(args.input)
        else:
            scenario = next((case for case in cases if case["id"] == (args.case or "industrial")), None)
            if scenario is None:
                raise ValueError("Unknown case. Run --list to see available scenarios.")
        report = solve(scenario)
        folder = write_bundle(report, args.output)
        if args.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print_disclaimer()
            print(brief(report))
            print(f"Saved 7 evidence files: {folder.resolve()}")
            print(
                f'Verify: python -m alpha_factory_v1.demos.alpha_agi_business_3_v1 --verify "{folder / "dossier.json"}"'
            )
            if report["result"]["jobs"]:
                print(f'Next: alpha-agent ascension-compile "{folder / "jobs.json"}" --output fusion-plan.json')
                print("The plan still needs independent review. No job, seed or payment has been submitted.")
        return 0
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        print(f"Business 3: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Stopped. Existing outputs are retained; use a new directory if a run is incomplete.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
