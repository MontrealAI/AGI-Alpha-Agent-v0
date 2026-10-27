#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replay unchanged supporting studies plus the opportunity-first 2.1.0 extension."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parent
SUPPORTING_SHA256 = "598fe56134ed1f745568a9b31bdd513bfc8cab94ccf01add5cfcdaf585490010"
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def sha(path: Path) -> str:
    """Compute the source binding."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(full_economics: bool = False, native_enabled: bool = True) -> dict[str, Any]:
    """Call both additive replayers, preserve evidence and expose each result."""
    started = time.perf_counter()
    result: dict[str, Any] = {
        "schema": "agi-alpha-complete-edition-replay/1",
        "edition": "2.1.0",
        "reproducer_sha256": sha(Path(__file__)),
        "supporting_source_sha256": sha(ROOT / "reproduce.py"),
        "opportunity_reproducer_sha256": sha(ROOT / "opportunity/reproduce.py"),
        "scope": "Executable research evidence only; no new hosted calls, external scientific replication, full repository CI, publication or deployment.",
    }
    try:
        if sys.flags.optimize:
            raise ValueError("Run without -O or PYTHONOPTIMIZE; frozen evaluator assertions must remain enabled")
        if result["supporting_source_sha256"] != SUPPORTING_SHA256:
            raise ValueError("The completed supporting reproducer was changed")
        with tempfile.TemporaryDirectory(prefix="alpha-complete-replay-") as directory:
            temporary = Path(directory)
            for label, script in (
                ("supporting", ROOT / "reproduce.py"),
                ("opportunity", ROOT / "opportunity/reproduce.py"),
            ):
                output = temporary / (label + ".json")
                command = [sys.executable, str(script), "--report", str(output)]
                if full_economics and label == "supporting":
                    command.append("--full-economics")
                if not native_enabled:
                    command.append("--skip-native")
                process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=600)
                if output.is_file():
                    result[label] = json.loads(output.read_text())
                else:
                    raise RuntimeError(f"{label} did not emit a report: {process.stdout}\n{process.stderr}")
                if process.returncode or not result[label]["passed"]:
                    raise RuntimeError(label + " replay failed; inspect its nested report")
        result["passed"] = True
    except Exception as exc:
        result.update(passed=False, failure_type=type(exc).__name__, failure=str(exc))
    result["elapsed_seconds"] = time.perf_counter() - started
    return result


def main() -> None:
    """Parse options and write only a requested new report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-economics", action="store_true", help="Also re-execute all 13,824 frozen selected economic histories."
    )
    parser.add_argument(
        "--skip-native",
        action="store_true",
        help="Skip fresh native controls in both replayers; retain all byte/pin checks.",
    )
    parser.add_argument(
        "--report", type=Path, help="Write a new report; refuse overwrites and frozen evidence destinations."
    )
    args = parser.parse_args()
    if args.report is not None:
        path = args.report.resolve()
        if path.exists() or (path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / "validation")):
            parser.error("report must be a new file outside frozen evidence directories; validation is allowed")
    result = run(args.full_economics, not args.skip_native)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
