#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce frozen finite technical results without overwriting original evidence.

This script replays the original public synthetic seeds. It is reproducibility,
not another prospective confirmation or an independent recipient experiment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COHORTS = ("origin_confirmation", "successor_confirmation")


def load(path: Path) -> Any:
    """Read a research JSON record."""
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    """Bind exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze() -> dict[str, str]:
    """Require all frozen sources, configuration and vendored dependencies."""
    expected: dict[str, str] = load(ROOT / "evidence/technical_freeze.json")["files"]
    for name, value in expected.items():
        if sha(ROOT / name) != value:
            raise ValueError(f"Frozen source differs: {name}")
    return expected


def reproduce(destination: Path, port: int) -> dict[str, Any]:
    """Regenerate both cohorts and replay the identical ordinary library."""
    if destination.exists():
        raise ValueError("Choose a destination that does not exist; preserved runs are never overwritten")
    before = verify_freeze()
    destination.mkdir(parents=True)
    started = time.perf_counter()
    result: dict[str, Any] = {
        "schema": "agialpha.reserve.technical-reproduction.v1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(ROOT),
        "output_root": str(destination),
        "python": sys.version,
        "reproduction_source_sha256": sha(Path(__file__)),
        "freeze_sha256": sha(ROOT / "evidence/technical_freeze.json"),
        "frozen_bindings_verified_before": len(before),
        "commands": [],
        "comparisons": [],
        "scope": "Same public seeds and frozen source; reproducibility only, not additional fresh confirmation.",
        "ignored_execution_fields": {
            "actual_process_ids": "New processes necessarily have new identifiers.",
            "wall_seconds": "Execution timing depends on the host and concurrent work.",
            "total_stream_bytes_sent": "Recorded descriptively; randomized MPC execution is not identified by traffic counts.",
            "total_stream_bytes_received": "Recorded descriptively; randomized MPC execution is not identified by traffic counts.",
        },
    }
    try:
        for offset, command in enumerate(("confirm", "library-replay")):
            arguments = [
                sys.executable,
                "-B",
                str(ROOT / "src/study.py"),
                command,
                "--authority",
                "--port",
                str(port + 40 * offset),
                "--output-root",
                str(destination),
            ]
            executed = subprocess.run(arguments, capture_output=True, text=True, check=False, timeout=1200)
            result["commands"].append(
                {
                    "argv": arguments,
                    "exit_code": executed.returncode,
                    "stdout": executed.stdout,
                    "stderr": executed.stderr,
                }
            )
            if executed.returncode:
                raise RuntimeError(f"Reproduction command failed: {command}")
        for cohort in COHORTS:
            for original in sorted((ROOT / "data" / cohort).rglob("*.json")):
                relative = original.relative_to(ROOT)
                reproduced = destination / relative
                equal = sha(original) == sha(reproduced)
                result["comparisons"].append(
                    {"kind": "exact_input_bytes", "path": str(relative), "sha256": sha(original), "passed": equal}
                )
                if not equal:
                    raise AssertionError(f"Regenerated input differs: {relative}")
            for suffix in ("", "_ordinary_library"):
                relative = Path("results") / f"{cohort}{suffix}.json"
                original_result = load(ROOT / relative)
                repeated_result = load(destination / relative)
                original_execution = original_result.pop("execution")
                repeated_execution = repeated_result.pop("execution")
                unknown_fields = set(repeated_execution) - {"answer", *result["ignored_execution_fields"]}
                if unknown_fields:
                    raise AssertionError(f"Unclassified execution fields: {unknown_fields}")
                equal = (
                    original_result == repeated_result and original_execution["answer"] == repeated_execution["answer"]
                )
                result["comparisons"].append(
                    {
                        "kind": "all_scientific_fields_and_answer",
                        "path": str(relative),
                        "worlds": repeated_result["n"],
                        "passed": equal,
                        "original_execution": original_execution,
                        "reproduced_execution": repeated_execution,
                    }
                )
                if not equal:
                    raise AssertionError(f"Scientific result differs: {relative}")
        after = verify_freeze()
        result["frozen_bindings_verified_after"] = len(after)
        result["frozen_bindings_unchanged"] = before == after
        result["passed"] = before == after and all(row["passed"] for row in result["comparisons"])
    except Exception as error:
        result["passed"] = False
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    result["wall_seconds"] = time.perf_counter() - started
    result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    (destination / "reproduction.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    """Run the exact preserved protocol into a fresh directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--port", type=int, default=19100)
    args = parser.parse_args()
    result = reproduce(args.destination.resolve(), args.port)
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "comparisons": len(result["comparisons"]),
                "wall_seconds": result["wall_seconds"],
                "receipt": str(args.destination / "reproduction.json"),
            },
            indent=2,
        )
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
