# SPDX-License-Identifier: Apache-2.0
"""Reproduce frozen core/economic outputs in a new, isolated package directory.

Usage: python study/reproduce.py --out /tmp/archive-claim-reproduction

Only JSON whitespace/object-key order and CSV column order are normalized.
CSV row order and every value remain exact. Core timings.json is excluded
because it records machine-dependent elapsed times and platform metadata.
The deterministic capability ZIP and the regenerated economic policy must
match as well. A failure preserves the staging directory, logs, and receipt.
This uses the existing Python standard library; it does not install anything.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE = Path(__file__).resolve().parent
INPUTS = (
    "run_study.py",
    "src/claim_engine.py",
    "src/exhaustive_reference.py",
    "config/construction_protocol.json",
    "provenance/constructor_freeze.json",
    "provenance/model_manifest.json",
    "economics/runner.py",
    "economics/config.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def normalized(path: Path) -> bytes:
    if path.suffix == ".json":
        return canonical_json(json.loads(path.read_text(encoding="utf-8")))
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            if not fields or len(fields) != len(set(fields)):
                raise ValueError(f"Absent or duplicate CSV columns: {path}")
            rows = list(reader)
            if any(None in row or None in row.values() for row in rows):
                raise ValueError(f"Malformed CSV row: {path}")
        return canonical_json({"columns": sorted(fields), "rows": rows})
    return path.read_bytes()


def compare_tree(expected: Path, actual: Path, ignored: set[str]) -> dict[str, Any]:
    def inventory(root: Path) -> dict[str, Path]:
        return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}

    left, right = inventory(expected), inventory(actual)
    if set(left) != set(right):
        raise AssertionError(
            f"Output inventory differs: missing={sorted(set(left) - set(right))}, "
            f"extra={sorted(set(right) - set(left))}"
        )
    entries = []
    raw_matches = 0
    mismatches = []
    for name in sorted(set(left) - ignored):
        original, reproduced = normalized(left[name]), normalized(right[name])
        if original != reproduced:
            mismatches.append(name)
        entries.append([name, hashlib.sha256(reproduced).hexdigest()])
        raw_matches += left[name].read_bytes() == right[name].read_bytes()
    if mismatches:
        raise AssertionError(f"Deterministic outputs differ: {mismatches}")
    return {
        "compared_files": len(entries),
        "byte_identical_files": raw_matches,
        "normalized_only_files": len(entries) - raw_matches,
        "ignored_files": sorted(ignored),
        "canonical_manifest_sha256": hashlib.sha256(canonical_json(entries)).hexdigest(),
    }


def verify_source_freezes() -> None:
    freeze = json.loads((SOURCE / "provenance/constructor_freeze.json").read_text())
    for path_key, hash_key in (
        ("path", "sha256"),
        ("oracle_path", "oracle_sha256"),
        ("harness_path", "harness_sha256"),
    ):
        if sha(SOURCE / freeze[path_key]) != freeze[hash_key]:
            raise AssertionError(f"Core source differs from freeze: {path_key}")
    if sha(SOURCE / "config/construction_protocol.json") != freeze["protocol_sha256"]:
        raise AssertionError("Core protocol differs from freeze")
    policy = json.loads((SOURCE / "economics/policy_frozen.json").read_text())
    for name, key in (
        ("economics/runner.py", "runner_sha256"),
        ("economics/config.json", "config_sha256"),
        ("config/construction_protocol.json", "construction_protocol_sha256"),
        ("provenance/model_manifest.json", "model_manifest_sha256"),
        ("economics/results/exploratory.json", "exploration_file_sha256"),
    ):
        if sha(SOURCE / name) != policy[key]:
            raise AssertionError(f"Economic input differs from freeze: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.absolute()
    if out.exists() or out.is_symlink():
        parser.error("--out must not exist; evidence is never overwritten")
    out.mkdir(parents=True)
    logs, work, temp = (out / name for name in ("logs", "work", "tmp"))
    for directory in (logs, work, temp):
        directory.mkdir()
    stage = out / "study"
    receipt: dict[str, Any] = {
        "schema": "agialpha.archive-claim.reproduction.v1",
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "source_study": str(SOURCE),
        "staging_root": str(out),
        "working_directory": str(work),
        "wrapper_sha256": sha(Path(__file__)),
        "native_integration_rerun": False,
        "normalization": [
            "JSON object-key order and whitespace only; numeric values are not rounded",
            "CSV column order only; all cell strings and row order are preserved",
            "Core timings.json is present but excluded from equality checks",
            "Capability ZIP is compared byte-for-byte; economic policy is compared as JSON",
        ],
        "commands": [],
    }
    receipt_path = out / "reproduction_receipt.json"

    def checkpoint() -> None:
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    try:
        verify_source_freezes()
        receipt["input_sha256"] = {name: sha(SOURCE / name) for name in INPUTS}
        for name in INPUTS:
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, destination)
        commands = [
            ("core", [str(stage / "run_study.py"), "--out", str(stage / "results/primary")]),
            *[(f"economics_{name}", [str(stage / "economics/runner.py"), name])
              for name in ("check", "explore", "confirm", "robustness", "supplementary")],
        ]
        env = {**os.environ, "TMPDIR": str(temp)}
        for name, arguments in commands:
            print(f"Running {name}", flush=True)
            started = time.monotonic()
            result = subprocess.run(
                [sys.executable, "-I", "-B", *arguments], cwd=work,
                env=env, capture_output=True, text=True, check=False,
            )
            (logs / f"{name}.stdout.txt").write_text(result.stdout)
            (logs / f"{name}.stderr.txt").write_text(result.stderr)
            receipt["commands"].append({
                "name": name, "arguments": arguments, "returncode": result.returncode,
                "elapsed_seconds": time.monotonic() - started,
                "stdout": result.stdout, "stderr": result.stderr,
                "isolated_python": True,
            })
            checkpoint()
            if result.returncode != 0:
                raise RuntimeError(f"{name} failed; logs preserved in {logs}")
        receipt["comparisons"] = {
            "core": compare_tree(SOURCE / "results/primary", stage / "results/primary", {"timings.json"}),
            "economics": compare_tree(SOURCE / "economics/results", stage / "economics/results", set()),
        }
        if normalized(SOURCE / "economics/policy_frozen.json") != normalized(stage / "economics/policy_frozen.json"):
            raise AssertionError("Regenerated economic policy differs from the included policy")
        receipt["economic_policy_sha256"] = sha(stage / "economics/policy_frozen.json")
        if receipt["input_sha256"] != {name: sha(SOURCE / name) for name in INPUTS}:
            raise AssertionError("Original input changed during reproduction")
        if any(sha(stage / name) != receipt["input_sha256"][name] for name in INPUTS):
            raise AssertionError("Staged input changed during reproduction")
        receipt["status"] = "passed"
        receipt["staged_bytes_before_receipt"] = sum(p.stat().st_size for p in out.rglob("*") if p.is_file() and p != receipt_path)
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        checkpoint()
    print(json.dumps({"status": receipt["status"], "comparisons": receipt["comparisons"], "receipt": str(receipt_path)}, indent=2))


if __name__ == "__main__":
    main()
