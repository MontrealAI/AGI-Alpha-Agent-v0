# SPDX-License-Identifier: Apache-2.0
"""Rebuild all frozen arms in isolated copies and replay the published confirmation bank."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

ARMS = ("ordinary", "expert", "conventional")
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    """Hash exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_files() -> dict[str, Any]:
    """Refuse modified experiment evidence or upstream module closure."""
    experiment = ROOT / "experiment"
    manifest = json.loads((experiment / "source_freeze.json").read_text())
    for name, expected in manifest["files"].items():
        if sha256(experiment / name) != expected:
            raise ValueError(f"Frozen artifact mismatch: {name}")
    native = json.loads((ROOT / "delivery/native_reuse_manifest.json").read_text())
    for row in native["files"]:
        path = ROOT / "delivery/native_reuse" / row["path"]
        if sha256(path) != row["sha256"]:
            raise ValueError(f"Native closure mismatch: {row['path']}")
    provenance = json.loads((ROOT / "delivery/provenance.json").read_text())
    for name, expected in provenance["frozen_confirmation_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Confirmation evidence mismatch: {name}")
    return {"frozen_arm_files": len(manifest["files"]), "native_source_files": len(native["files"])}


def run(command: list[str], cwd: Path, environment: dict[str, str], name: str, output: Path) -> dict[str, Any]:
    """Execute one bounded reproduction step and retain its complete stdout/stderr."""
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=300)
    record = {
        "command": command,
        "returncode": completed.returncode,
        "wall_seconds": time.perf_counter() - started,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    (output / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
    if completed.returncode:
        raise RuntimeError(f"{name} failed; see {output / (name + '.json')}")
    return record


def main() -> None:
    """Create an isolated replay directory without changing the original study files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory; existing paths are refused.")
    parser.add_argument("--skip-reference", action="store_true", help="Use verified stored references for fast replay.")
    parser.add_argument("--native", action="store_true", help="Also exercise existing journal/accounting/evaluation.")
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise SystemExit("Output already exists; choose a new path to preserve all previous evidence.")
    if output == ROOT or ROOT / "experiment" in output.parents or ROOT / "vendor" in output.parents:
        raise SystemExit("Output cannot replace frozen inputs or vendor files.")
    checks = verify_frozen_files()
    output.mkdir(parents=True)
    work = output / "work"
    experiment = work / "experiment"
    experiment.mkdir(parents=True)
    # Link only immutable pinned dependencies. Arm sources and all compiler outputs are independent copies.
    (work / "vendor").symlink_to(ROOT / "vendor", target_is_directory=True)
    names = ["worker.py", "score.py", "reference.py", "fresh_cases.json", "fresh_case_metadata.json"]
    for name in names:
        shutil.copyfile(ROOT / "experiment" / name, experiment / name)
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "TMPDIR": str(output),
        }
    )
    steps = {}
    for arm in ARMS:
        target = experiment / "arms" / arm
        target.mkdir(parents=True)
        for name in ("solution.py", "run.py", "kernel.cpp", "build.py"):
            shutil.copyfile(ROOT / "experiment/arms" / arm / name, target / name)
        steps[f"build_{arm}"] = run(
            [sys.executable, "-B", str(target / "build.py")], work, environment, f"build_{arm}", output
        )
        steps[f"worker_{arm}"] = run(
            [
                sys.executable,
                "-B",
                str(experiment / "worker.py"),
                str(target),
                str(experiment / "fresh_cases.json"),
                str(experiment / f"{arm}_raw.json"),
            ],
            work,
            environment,
            f"worker_{arm}",
            output,
        )
    if arguments.skip_reference:
        shutil.copyfile(ROOT / "experiment/fresh_references.json", experiment / "fresh_references.json")
    else:
        steps["reference"] = run(
            [
                sys.executable,
                "-B",
                str(experiment / "reference.py"),
                str(experiment / "fresh_cases.json"),
                str(experiment / "fresh_references.json"),
            ],
            work,
            environment,
            "reference",
            output,
        )
    steps["score"] = run([sys.executable, "-B", str(experiment / "score.py")], work, environment, "score", output)
    original = json.loads((ROOT / "experiment/comparison_results.json").read_text())
    replay = json.loads((experiment / "comparison_results.json").read_text())
    fields = (
        "arm",
        "cases",
        "accepted",
        "numeric_and_endpoint_cases",
        "numeric_and_endpoint_accepted",
        "correct_refusals",
    )
    for previous, current in zip(original["primary_results"], replay["primary_results"], strict=True):
        if any(previous[field] != current[field] for field in fields):
            raise ValueError(f"Acceptance decisions differ in arm {current['arm']}; retained as failed reproduction.")
    if replay["reference_cases_verified"] != 64:
        raise ValueError("Reference verification incomplete")
    if arguments.native:
        steps["native"] = run(
            [
                sys.executable,
                "-B",
                str(ROOT / "delivery/native_bridge.py"),
                "--experiment",
                str(experiment),
                "--output",
                str(output / "native_capture.json"),
            ],
            work,
            environment,
            "native",
            output,
        )
    final_checks = verify_frozen_files()
    report = {
        "edition": "DIGITAL-20261027-R1",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_hashes_verified_before_and_after": checks == final_checks,
        "checks": checks,
        "reference_recomputed": not arguments.skip_reference,
        "native_components_replayed": arguments.native,
        "accepted_counts_reproduced": [row["accepted"] for row in replay["primary_results"]],
        "meaning": "Replay of the same 64 recorded cases, not another fresh confirmation or customer mission.",
        "resource_warning": "Timing and RSS depend on host accounting; no speedup or model-billing claim.",
        "steps": {
            name: {k: v for k, v in step.items() if k not in ("stdout", "stderr")} for name, step in steps.items()
        },
    }
    (output / "reproduction_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
