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
import stat
import subprocess
import sys
import time
from typing import Any

ARMS = ("ordinary", "expert", "conventional")
ROOT = Path(__file__).resolve().parents[1]
VENDOR_MANIFEST_SHA256 = "a4cd4c283e6f1f860487b50195ec4c71bf5fd4b8c1e1c36ecf2b96e473092709"
VENDOR_MANIFEST_BYTES = 127993
NATIVE_MANIFEST_SHA256 = "1df647a26674c8bff52dd14b7869b9d9c619ca376973033b2f91d9b8949dfc13"
NATIVE_MANIFEST_BYTES = 5596
SOURCE_FREEZE_SHA256 = "d167d2c13e8fbf303fe7872711dca0c924b218b169bcd5681cedbe876dc97e40"
SOURCE_FREEZE_BYTES = 11830
PROVENANCE_SHA256 = "b970c2444b45050c7f8194c9ea4ed75276860f9b45f5d9fe3f08645f460b69ef"
PROVENANCE_BYTES = 5969


def sha256(path: Path) -> str:
    """Hash exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular_bytes(path: Path, expected_size: int, label: str = "Vendor") -> bytes:
    """Read a bounded regular file without following a symlink or blocking on a special file."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
            raise ValueError(f"{label} file type or size mismatch: {path}")
        data = stream.read(expected_size + 1)
        after = os.fstat(stream.fileno())
        if len(data) != expected_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"{label} file changed while reading: {path}")
        return data


def verify_vendor_closure(vendor_root: Path | None = None) -> dict[str, int]:
    """Verify the complete pinned vendor inventory before any dependency is executed."""
    vendor = vendor_root if vendor_root is not None else ROOT / "vendor"
    manifest_bytes = regular_bytes(ROOT / "delivery/vendor_manifest.json", VENDOR_MANIFEST_BYTES)
    if hashlib.sha256(manifest_bytes).hexdigest() != VENDOR_MANIFEST_SHA256:
        raise ValueError("Vendor manifest identity mismatch")
    manifest = json.loads(manifest_bytes)
    required = manifest["required_files"]
    optional = manifest["optional_historical_bytecode"]
    expected = {**required, **optional}
    for relative in expected:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise ValueError("Unsafe vendor manifest path")
    if not stat.S_ISDIR(vendor.lstat().st_mode):
        raise ValueError("Vendor root must be an actual directory, not a symlink")
    found: set[str] = set()
    pending = [vendor]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(vendor).as_posix()
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    pending.append(path)
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise ValueError(f"Vendor symlink or special file refused: {relative}")
                if relative not in expected:
                    raise ValueError(f"Unexpected vendor file: {relative}")
                record = expected[relative]
                data = regular_bytes(path, record["bytes"])
                if hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise ValueError(f"Vendor content mismatch: {relative}")
                found.add(relative)
    missing = set(required) - found
    if missing:
        raise ValueError(f"Missing required vendor files: {sorted(missing)}")
    return {"required_vendor_files": len(required), "verified_optional_cache_files": len(found & set(optional))}


def verify_native_closure(native_root: Path | None = None) -> dict[str, int]:
    """Reject extra importable code as well as altered or missing pinned native files."""
    native = native_root if native_root is not None else ROOT / "delivery/native_reuse"
    data = regular_bytes(ROOT / "delivery/native_reuse_manifest.json", NATIVE_MANIFEST_BYTES, "Native")
    if hashlib.sha256(data).hexdigest() != NATIVE_MANIFEST_SHA256:
        raise ValueError("Native manifest identity mismatch")
    manifest = json.loads(data)
    expected = {row["path"]: row["sha256"] for row in manifest["files"]}
    if len(expected) != len(manifest["files"]):
        raise ValueError("Duplicate native manifest paths")
    for relative in expected:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise ValueError("Unsafe native manifest path")
    if not stat.S_ISDIR(native.lstat().st_mode):
        raise ValueError("Native root must be an actual directory, not a symlink")
    found: set[str] = set()
    pending = [native]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(native).as_posix()
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    pending.append(path)
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise ValueError(f"Native symlink or special file refused: {relative}")
                if relative not in expected:
                    raise ValueError(f"Unexpected native file: {relative}")
                if metadata.st_size > 2 * 1024 * 1024:
                    raise ValueError(f"Native file exceeds bounded size: {relative}")
                content = regular_bytes(path, metadata.st_size, "Native")
                if hashlib.sha256(content).hexdigest() != expected[relative]:
                    raise ValueError(f"Native content mismatch: {relative}")
                found.add(relative)
    missing = set(expected) - found
    if missing:
        raise ValueError(f"Missing required native files: {sorted(missing)}")
    return {"native_source_files": len(expected)}


def verify_frozen_files() -> dict[str, Any]:
    """Check pinned manifests and closed dependencies under the trusted reviewed-verifier boundary.

    This script and the reviewed native_bridge.py wrapper are trusted entrypoints; the operating
    system, interpreter and compiler remain outside this artifact-integrity check.
    """
    vendor_checks = verify_vendor_closure()
    native_checks = verify_native_closure()
    experiment = ROOT / "experiment"
    source_bytes = regular_bytes(experiment / "source_freeze.json", SOURCE_FREEZE_BYTES, "Source freeze")
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_FREEZE_SHA256:
        raise ValueError("Source freeze manifest identity mismatch")
    manifest = json.loads(source_bytes)
    for name, expected in manifest["files"].items():
        if sha256(experiment / name) != expected:
            raise ValueError(f"Frozen artifact mismatch: {name}")
    provenance_bytes = regular_bytes(ROOT / "delivery/provenance.json", PROVENANCE_BYTES, "Provenance")
    if hashlib.sha256(provenance_bytes).hexdigest() != PROVENANCE_SHA256:
        raise ValueError("Provenance manifest identity mismatch")
    provenance = json.loads(provenance_bytes)
    for name, expected in provenance["frozen_confirmation_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Confirmation evidence mismatch: {name}")
    return {"frozen_arm_files": len(manifest["files"]), **native_checks, **vendor_checks}


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
    # The closed vendor inventory is verified before any imports or compilation and again after replay.
    # Concurrent privileged filesystem attacks are outside this reproducibility check's threat model.
    (work / "vendor").symlink_to(ROOT / "vendor", target_is_directory=True)
    names = ["worker.py", "score.py", "reference.py", "fresh_cases.json", "fresh_case_metadata.json"]
    for name in names:
        shutil.copyfile(ROOT / "experiment" / name, experiment / name)
    cache_root = output / "empty-bytecode-cache"
    cache_root.mkdir(mode=0o700)
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(cache_root),
            "BETA_VENDOR_ROOT": str(work / "vendor"),
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
