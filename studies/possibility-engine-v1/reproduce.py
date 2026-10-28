# SPDX-License-Identifier: Apache-2.0
"""Verify or stage replays outside the original study without changing frozen evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FREEZE_HASH = "e1ccee55bf1269fd3fc0932538782a2eaaa1eeda31cf06880435708fd74e33d7"
SEEDS_HASH = "e721d18d75f2c6f95bd3d25668d4799a4d7d54e85db24cd8ff414e801ec0fea1"


def digest(path: Path) -> str:
    """Return a local byte identity."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_freeze(root: Path) -> dict[str, str]:
    """Check the published freeze, every bound source and the original seed bank."""
    freeze_path, seeds_path = root / "FREEZE.json", root / "evidence/confirmation/seeds.json"
    if digest(freeze_path) != FREEZE_HASH or digest(seeds_path) != SEEDS_HASH:
        raise ValueError("This wrapper requires the exact original study freeze and seed bank")
    freeze = json.loads(freeze_path.read_text())
    if freeze.get("status") != "frozen":
        raise ValueError("Study is not frozen")
    for name, expected in freeze["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path) != expected:
            raise ValueError(f"Frozen source mismatch: {name}")
    if json.loads(seeds_path.read_text())["freeze_sha256"] != FREEZE_HASH:
        raise ValueError("Seed bank is bound to another freeze")
    return freeze["files"]


def new_output(path: Path) -> Path:
    """Require a new output outside this study; never reuse or delete an existing path."""
    output = path.resolve()
    if output == ROOT or output.is_relative_to(ROOT) or output.exists():
        raise ValueError("Output must be a nonexistent directory outside the study")
    output.mkdir(parents=True, exist_ok=False)
    return output


def copy_file(source: Path, target: Path) -> None:
    """Copy bytes into an isolated workspace and validate the transfer."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if digest(source) != digest(target):
        raise RuntimeError("Copy validation failed")


def run(command: list[str], cwd: Path, logs: Path, label: str) -> dict[str, Any]:
    """Execute a local command only in the copy and retain its complete output."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True,
                            timeout=180, check=False)
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{label}.stdout.txt").write_text(result.stdout)
    (logs / f"{label}.stderr.txt").write_text(result.stderr)
    receipt = {"command": command, "cwd": str(cwd), "returncode": result.returncode,
               "seconds": time.perf_counter() - started}
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}; retained logs: {logs}")
    return receipt


def quick(output: Path, frozen: dict[str, str]) -> dict[str, Any]:
    """Replay two development deliveries and all existing scoped unit controls."""
    workspace = output / "workspace"
    selected = set(frozen) | {"FREEZE.json", "evidence/confirmation/seeds.json"}
    for arm in ("joint", "successor"):
        selected.update(f"evidence/development/{arm}/{name}" for name in ("input.json", "result.json"))
    original_hashes = {name: digest(ROOT / name) for name in selected}
    for name in sorted(selected):
        copy_file(ROOT / name, workspace / name)
    commands = []
    comparisons = []
    for arm in ("joint", "successor"):
        source = workspace / "evidence/development" / arm
        delivery = workspace / "replayed" / arm
        commands.append(run([sys.executable, "-B", "src/engine.py", str(source / "input.json"),
                             "--output", str(delivery)], workspace, output / "logs", f"{arm}_delivery"))
        commands.append(run([sys.executable, "-B", "verification/check_protocol.py", str(delivery),
                             "--output", str(delivery / "independent_check.json")], workspace,
                            output / "logs", f"{arm}_independent"))
        expected, actual = [json.loads(path.read_text()) for path in (source / "result.json", delivery / "result.json")]
        semantic_keys = ("status", "input_sha256", "time", "robust_margin", "cost_units", "failure_mode",
                         "nominal_parameters", "model_pairs", "requirements", "noise_inclusive_intervals")
        if any(expected[key] != actual[key] for key in semantic_keys):
            raise AssertionError(f"{arm} semantic result changed")
        comparisons.append({"arm": arm, "semantic_equivalence": True, "complete_json_equality": expected == actual,
                            "status": actual["status"], "cost_units": actual["cost_units"],
                            "independent_optimality_and_predictions": "pass"})
    commands.append(run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "verification",
                         "-p", "test_*.py", "-v"], workspace, output / "logs", "unit_controls"))
    check_freeze(workspace)
    for name, expected in original_hashes.items():
        if digest(ROOT / name) != expected:
            raise RuntimeError(f"Original source or used evidence changed during replay: {name}")
    return {"mode": "quick", "status": "pass", "frozen_files_verified": len(frozen),
            "original_used_files_unchanged": len(original_hashes), "comparisons": comparisons, "commands": commands,
            "scope": "Local study replay and scoped controls; not repository release qualification"}


def stage_circuits(technical: Path, output: Path) -> dict[str, Any]:
    """Stage only fresh case netlists, excluding copied ordinary-library duplicates."""
    records = []
    for case in sorted(technical.resolve().iterdir()):
        if not case.is_dir() or not case.name.startswith(("binary_", "successor_")):
            continue
        netlists = sorted(case.glob("*.cir"))
        if not netlists:
            continue
        for path in [case / "result.json", *netlists]:
            target = output / case.name / path.name
            copy_file(path, target)
            records.append({"source": str(path), "copy": str(target.relative_to(output)), "sha256": digest(target)})
    count = sum(record["copy"].endswith(".cir") for record in records)
    if not count:
        raise ValueError("No constructed-case netlists found")
    return {"mode": "stage-circuits", "status": "staged", "netlists": count, "files": records,
            "scope": "Byte-identical staging only; no simulator was run"}


def stage_full(output: Path, ngspice: Path | None, library_dir: Path | None) -> dict[str, Any]:
    """Copy the full study and write explicit commands; retain copied original results."""
    workspace = output / "workspace"
    shutil.copytree(ROOT, workspace, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    for relative in ("evidence/confirmation/technical", "economics/confirmation"):
        source = workspace / relative
        preserved = workspace / "original_results" / relative
        if source.exists():
            preserved.parent.mkdir(parents=True, exist_ok=True)
            source.rename(preserved)
    check_freeze(workspace)
    python = [sys.executable, "-B"]
    circuit_inputs, circuit_results = output / "circuit-inputs", output / "circuit-results"
    commands = [
        python + ["verification/run_confirmation.py", "FREEZE.json", "evidence/confirmation/seeds.json",
                  "--output", "evidence/confirmation/technical"],
        python + ["economics/model.py", "confirm", "--seed-file", "evidence/confirmation/seeds.json",
                  "--output", "economics/confirmation"],
        python + ["economics/persist_confirmation_references.py"],
        python + ["verification/check_accounts.py", "economics/confirmation", "--config", "economics/assumptions.json",
                  "--output", "verification/replayed_accounting.json"],
        python + ["verification/check_summaries.py", "."],
        python + ["verification/check_reference_accounts.py", "."],
        python + ["reproduce.py", "--mode", "stage-circuits", "--technical", "evidence/confirmation/technical",
                  "--output", str(circuit_inputs)],
        python + ["verification/circuit_runner.py", str(circuit_inputs), str(circuit_results)],
    ]
    if ngspice:
        commands[-1] += ["--ngspice", str(ngspice.resolve())]
    if library_dir:
        commands[-1] += ["--library-dir", str(library_dir.resolve())]
    script = "#!/bin/sh\nset -eu\nexport PYTHONDONTWRITEBYTECODE=1\nunset PYTHONPATH\n"
    script += f"cd {shlex.quote(str(workspace))}\n" + "\n".join(shlex.join(command) for command in commands) + "\n"
    (output / "REPLAY_COMMANDS.sh").write_text(script)
    return {"mode": "stage-full", "status": "staged", "workspace": str(workspace), "commands": commands,
            "command_file": str(output / "REPLAY_COMMANDS.sh"), "ngspice_requested": ngspice is not None,
            "scope": ("No replay executed by staging; same issued seeds reproduce original confirmation, "
                      "not fresh evidence")}


def main() -> None:
    """Provide safe quick verification and explicit full-replay staging."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quick", "stage-full", "stage-circuits"), default="quick")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--technical", type=Path)
    parser.add_argument("--ngspice", type=Path)
    parser.add_argument("--library-dir", type=Path)
    args = parser.parse_args()
    frozen = check_freeze(ROOT)
    if args.mode == "stage-circuits" and args.technical is None:
        parser.error("stage-circuits requires --technical")
    if args.ngspice and not args.ngspice.is_file():
        parser.error("--ngspice must identify an existing executable file")
    if args.library_dir and not args.library_dir.is_dir():
        parser.error("--library-dir must identify an existing directory")
    output = new_output(args.output)
    if args.mode == "quick":
        receipt = quick(output, frozen)
    elif args.mode == "stage-full":
        receipt = stage_full(output, args.ngspice, args.library_dir)
    else:
        receipt = stage_circuits(args.technical, output)
    check_freeze(ROOT)
    receipt.update({"freeze_sha256": FREEZE_HASH, "seed_bank_sha256": SEEDS_HASH,
                    "wrapper_sha256": digest(Path(__file__)), "python": platform.python_version(),
                    "original_frozen_sources_and_seed_bank_unchanged": True})
    (output / "reproduction_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key not in ("commands", "files")}, indent=2))


if __name__ == "__main__":
    main()
