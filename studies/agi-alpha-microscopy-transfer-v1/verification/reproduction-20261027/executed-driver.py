# SPDX-License-Identifier: Apache-2.0
"""Replay the study offline in a fresh copy, preserving all original evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
EXPECTED_INSTRUMENT = "a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db"
EXPECTED_POLICY = "2639f04946d2921b686ab460992893197e5a111fc9483d5f01881bbae1568f12"
EXPECTED_ECONOMICS = "5d967ccd2dfd2d587b7e82d3bb61013d91e3f3c917aac381ffff08b2197c59e0"
EXPECTED_CONFIG = "339c11248ce11bbb63168ee793e8484d513457cf551ce4073c8788d7c5598077"


def digest(path: Path) -> str:
    """Return the identity of an ordinary file."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected an ordinary file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    """Read a trusted study JSON document."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    """Create a new receipt without overwriting an earlier one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def verify_originals() -> dict[str, str]:
    """Check the declared source, data, evaluation and economic commitments."""
    checked: dict[str, str] = {}

    def check(relative: str, expected: str) -> None:
        actual = digest(ROOT / relative)
        if actual != expected:
            raise ValueError(f"Frozen identity differs: {relative}")
        checked[relative] = actual

    freeze = read_json(ROOT / "protocols/source-freeze.json")
    for path, expected in freeze["files"].items():
        check(path, expected)
    check("src/microscopy_transfer.py", EXPECTED_INSTRUMENT)
    check("integration/results/frozen-v1/received-artifact.py", EXPECTED_INSTRUMENT)
    check("protocols/held_tasks.json", freeze["confirmation_task_commitment"])
    for row in read_json(ROOT / "integration/source_manifest.json")["files"]:
        check("integration/" + row["local_path"], row["sha256"])
    for path, expected in read_json(ROOT / "integration/VALIDATION.json")["maintained_callers"].items():
        check("integration/" + path, expected)
    for selection in ["development/idr0062", "confirmation/idr0052"]:
        prefix = "data/" + selection + "/"
        manifest = read_json(ROOT / prefix / "manifest.json")
        for row in manifest["records"]:
            check(prefix + row["relative_path"], row["sha256"])
        for row in manifest["arrays"]:
            check(prefix + row["file"], row["sha256"])
    for row in read_json(ROOT / "confirmation/provenance.json")["files"]:
        check(row["path"], row["sha256"])
    archived = "confirmation/results/frozen-v1/"
    for row in read_json(ROOT / archived / "SHA256SUMS.json")["files"]:
        check(archived + row["path"], row["sha256"])
    commitment = read_json(ROOT / "hosted_trials/pretrial_commitment.json")
    for path, expected in commitment["inputs"].items():
        check("hosted_trials/" + path, expected)
    for arm, row in read_json(ROOT / "hosted_trials/scoring.json")["arms"].items():
        check("hosted_trials/" + arm + "/answers.json", row["answer_sha256"])
    check("economics/simulate.py", EXPECTED_ECONOMICS)
    check("economics/config.json", EXPECTED_CONFIG)
    check("economics/results/policy_freeze.json", EXPECTED_POLICY)
    return checked


def copy_inputs(work: Path) -> dict[str, str]:
    """Copy the small executable closure without original result directories."""
    paths = [
        "src",
        "protocols",
        "data",
        "integration/vendor",
        "hosted_trials",
        "run_confirmation.py",
        "confirmation_reference.py",
        "score_hosted_trials.py",
    ]
    paths.extend(
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "integration").iterdir())
        if path.is_file() and path.suffix in (".py", ".mjs", ".json")
    )
    paths.extend(["economics/simulate.py", "economics/config.json", "economics/test_accounting.py"])
    copied: dict[str, str] = {}
    for relative in paths:
        source = ROOT / relative
        files = sorted(source.rglob("*")) if source.is_dir() else [source]
        for path in files:
            if path.is_symlink():
                raise ValueError(f"Symlink not permitted in copied closure: {path}")
            if not path.is_file() or any(part in {"__pycache__", ".mypy_cache"} for part in path.parts):
                continue
            name = path.relative_to(ROOT).as_posix()
            destination = work / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            copied[name] = digest(destination)
            if copied[name] != digest(path):
                raise ValueError(f"Copy identity differs: {name}")
    return copied


def command(name: str, args: list[str], cwd: Path, output: Path) -> dict[str, Any]:
    """Execute a bounded local replay and retain stdout, stderr and the command."""
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    started = time.perf_counter()
    process = subprocess.run(args, cwd=cwd, env=environment, capture_output=True, text=True, timeout=300, check=False)
    elapsed = time.perf_counter() - started
    logs = output / "logs"
    logs.mkdir(exist_ok=True)
    (logs / (name + ".stdout.txt")).write_text(process.stdout, encoding="utf-8")
    (logs / (name + ".stderr.txt")).write_text(process.stderr, encoding="utf-8")
    receipt = {"stage": name, "command": args, "cwd": str(cwd), "returncode": process.returncode, "seconds": elapsed}
    write_json(logs / (name + ".json"), receipt)
    if process.returncode:
        raise RuntimeError(f"{name} failed with exit {process.returncode}; inspect {logs}")
    print(f"Completed {name} ({elapsed:.2f} s)", flush=True)
    return receipt


def runtime() -> dict[str, Any]:
    """Record the environment without inspecting credentials or other settings."""
    versions: dict[str, str | None] = {}
    for name in ["numpy", "scipy", "pydantic", "cryptography", "numcodecs"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for the inherited local lifecycle controls")
    return {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "node": subprocess.check_output([node, "--version"], text=True).strip(),
        "packages": versions,
        "repository_requested_node": "22.17.1",
        "study_original_node": "24.22.1",
    }


def scientific(value: dict[str, Any]) -> dict[str, Any]:
    """Remove only the explicitly nondeterministic numerical timing field."""
    return {key: item for key, item in value.items() if key != "elapsed_seconds"}


def check_results(work: Path, output: Path) -> dict[str, Any]:
    """Require successful acceptance and exact deterministic economic reproduction."""
    old = read_json(ROOT / "integration/results/frozen-v1/summary.json")
    new = read_json(work / "integration/results/frozen-v1/summary.json")
    if (new["passed"], new["total"]) != (32, 32):
        raise AssertionError("Local interface controls changed")
    controls = [(row["name"], row.get("member"), row["passed"]) for row in new["checks"]]
    if controls != [(row["name"], row.get("member"), row["passed"]) for row in old["checks"]]:
        raise AssertionError("Local interface control identities changed")
    if digest(work / "integration/results/frozen-v1/received-artifact.py") != EXPECTED_INSTRUMENT:
        raise AssertionError("Newly recovered artifact differs")
    expected = read_json(ROOT / "confirmation/results/frozen-v1/summary.json")
    actual = read_json(work / "confirmation/results/reproduction-v1/summary.json")
    keys = [
        "n_compatible_missions",
        "n_semantic_cases",
        "recovered_passed",
        "conventional_passed",
        "ordinary_library_passed",
        "identical_content_output_parity",
        "semantic_passed",
    ]
    if {key: actual[key] for key in keys} != {key: expected[key] for key in keys}:
        raise AssertionError("Scientific acceptance or control counts changed")
    equal = 0
    compared = 0
    for path in sorted((ROOT / "confirmation/results/frozen-v1/compatible").glob("*/*-result.json")):
        relative = path.relative_to(ROOT / "confirmation/results/frozen-v1")
        compared += 1
        equal += scientific(read_json(path)) == scientific(
            read_json(work / "confirmation/results/reproduction-v1" / relative)
        )
    old_refusals = [
        (row["case_id"], row["observed_status"], row["observed_reason"]) for row in expected["semantic_results"]
    ]
    new_refusals = [
        (row["case_id"], row["observed_status"], row["observed_reason"]) for row in actual["semantic_results"]
    ]
    if old_refusals != new_refusals:
        raise AssertionError("Semantic refusal status or reason changed")
    economic_matches = {}
    for filename in ["policy_freeze.json", "results.json", "confirmation.csv", "example_ledger.json"]:
        economic_matches[filename] = digest(ROOT / "economics/results" / filename) == digest(
            work / "economics/results" / filename
        )
    if not all(economic_matches.values()):
        raise AssertionError("Deterministic economic policy, histories, or summary changed")
    economics = read_json(work / "economics/results/results.json")
    if not economics["ordinary_library_exact_parity"] or not economics["all_cash_balances_verified"]:
        raise AssertionError("Economic parity or cash conservation failed")
    if economics["world_rows"] != 13824:
        raise AssertionError("Economic history count changed")
    hosted = read_json(work / "hosted_trials/scoring.json")
    if hosted != read_json(ROOT / "hosted_trials/scoring.json"):
        raise AssertionError("Recorded hosted-output scoring changed")
    audit = read_json(output / "archived-output-audit.json")
    if (
        audit["counts"] != {"recovered": 48, "ordinary_library": 48, "conventional": 48}
        or not audit["all_nan_probes_refused"]
    ):
        raise AssertionError("Stricter archived-output audit changed")
    accounting_log = (output / "logs/accounting-tests.stderr.txt").read_text(encoding="utf-8")
    tests = re.search(r"Ran (\d+) tests", accounting_log)
    if tests is None or int(tests.group(1)) != 8:
        raise AssertionError("Expected eight accounting tests")
    return {
        "native_local_interface_controls": {"passed": new["passed"], "total": new["total"]},
        "newly_recovered_artifact_sha256": EXPECTED_INSTRUMENT,
        "confirmation": {key: actual[key] for key in keys},
        "same_scientific_json_except_elapsed_seconds": {"equal": equal, "compared": compared},
        "scientific_bitwise_comparison_is_diagnostic": "Acceptance uses the declared finite numerical tolerances; clock fields and process receipts are not compared.",
        "semantic_status_and_reason_parity": True,
        "economic_files_byte_identical": economic_matches,
        "simulated_economic_histories": economics["world_rows"],
        "economic_cash_conservation": economics["all_cash_balances_verified"],
        "ordinary_library_economic_parity": economics["ordinary_library_exact_parity"],
        "accounting_tests": {"passed": int(tests.group(1)), "total": 8},
        "recorded_hosted_answers_rescored": {
            arm: {"passed": row["passed"], "total": row["total"]} for arm, row in hosted["arms"].items()
        },
        "hosted_live_trials_rerun": False,
        "archived_output_audit": {"counts": audit["counts"], "nan_probes_refused": audit["all_nan_probes_refused"]},
    }


def main() -> None:
    """Run the read-only original verification and isolated offline replay."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New or empty directory outside the original study tree"
    )
    parser.add_argument(
        "--rebuild-source-arrays",
        action="store_true",
        help="Also decode preserved compressed chunks; requires numcodecs",
    )
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.is_relative_to(ROOT) or ROOT.is_relative_to(destination):
        parser.error("Output must be outside and cannot contain the original study tree")
    if args.output.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
        parser.error("Output must be a new or empty ordinary directory; prior results are never overwritten")
    destination.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "schema": "microscopy-offline-reproduction/v1",
        "started_utc": started,
        "driver_sha256": digest(Path(__file__)),
        "source_root": str(ROOT),
        "output_root": str(destination),
        "runtime": runtime(),
        "scope": "Offline repeated execution and replay of recorded evidence; no new frontier calls, customers, live ENS, production admission, or release qualification.",
        "freshness": "Confirmation tasks were fresh at the original source freeze. This replay reuses those now-disclosed tasks and is not another protected fresh trial.",
        "stages": [],
    }
    try:
        before = verify_originals()
        write_json(destination / "original-identities.json", before)
        work = destination / "workspace"
        copied = copy_inputs(work)
        write_json(destination / "copied-identities.json", copied)
        python = sys.executable

        def run(name: str, arguments: list[str], cwd: Path = work) -> None:
            report["stages"].append(command(name, [python, *arguments], cwd, destination))

        if args.rebuild_source_arrays:
            run("decode-development", ["data/curate_idr.py", "development", "--offline"])
            run("decode-confirmation", ["data/curate_idr.py", "holdout", "--offline"])
            for path, expected in copied.items():
                if path.startswith("data/") and path.endswith(".npy") and digest(work / path) != expected:
                    raise AssertionError("Offline decoded array differs: " + path)
        run(
            "integration",
            [
                "integration/run_integration.py",
                "--artifact",
                "src/microscopy_transfer.py",
                "--out",
                "integration/results/frozen-v1",
            ],
        )
        run("confirmation", ["run_confirmation.py", "--output", "confirmation/results/reproduction-v1"])
        run("accounting-tests", ["-m", "unittest", "-v", "test_accounting"], work / "economics")
        run("economic-development", ["economics/simulate.py", "develop"])
        run("economic-confirmation", ["economics/simulate.py", "confirm"])
        run("hosted-output-rescoring", ["score_hosted_trials.py"])
        run(
            "archived-output-audit",
            [
                str(ROOT / "audit_confirmation.py"),
                "--results",
                str(ROOT / "confirmation/results/frozen-v1"),
                "--output",
                str(destination / "archived-output-audit.json"),
            ],
        )
        report["results"] = check_results(work, destination)
        after = verify_originals()
        if before != after:
            raise AssertionError("Original frozen evidence changed during reproduction")
        report["original_files_verified_before_and_after"] = len(before)
        report["original_frozen_evidence_unchanged"] = True
        report["copied_files"] = len(copied)
        report["source_arrays_rebuilt_from_preserved_chunks"] = args.rebuild_source_arrays
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        report["status"] = "PASS"
        write_json(destination / "REPRODUCTION.json", report)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "receipt": str(destination / "REPRODUCTION.json"),
                    "results": report["results"],
                },
                indent=2,
            )
        )
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = f"{type(error).__name__}: {error}"
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(destination / "REPRODUCTION.json", report)
        raise


if __name__ == "__main__":
    main()
