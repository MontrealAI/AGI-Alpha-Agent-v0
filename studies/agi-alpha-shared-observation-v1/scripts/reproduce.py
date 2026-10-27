# SPDX-License-Identifier: Apache-2.0
"""Replay the bounded study in a new directory without replacing recorded evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> Any:
    """Read one JSON record."""
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, record: Any) -> None:
    """Write a generated record below the new reproduction directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    """Require an ordinary file and return its SHA-256."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"ordinary file required: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs() -> tuple[set[str], list[dict[str, Any]]]:
    """Check both frozen scientific inputs and the unchanged native source closure."""
    sources: set[str] = set()
    checks = []
    for freeze_name in ["evidence/technical-freeze-v1_0_1.json", "evaluation/reference-freeze-v1.json"]:
        sources.add(freeze_name)
        freeze = read(ROOT / freeze_name)
        for name, entry in freeze["files"].items():
            expected = entry["sha256"] if isinstance(entry, dict) else entry
            if digest(ROOT / name) != expected:
                raise ValueError(f"frozen source mismatch: {name}")
            sources.add(name)
        checks.append({"name": freeze_name, "passed": True, "files": len(freeze["files"])})
    manifest = read(ROOT / "evaluation/protected/cases/manifest.json")
    for case in manifest["cases"]:
        name = "evaluation/protected/cases/" + case["filename"]
        if digest(ROOT / name) != case["sha256"]:
            raise ValueError(f"protected input mismatch: {name}")
        sources.add(name)
    checks.append({"name": "released-protected-input-identities", "passed": True, "files": len(manifest["cases"])})
    for name, key in [("integration/custody.json", "copied_files"), ("integration/source_manifest.json", "files")]:
        rows = read(ROOT / name)[key]
        for row in rows:
            path = ROOT / "integration" / row["local_path"]
            if digest(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
                raise ValueError(f"native source custody mismatch: {row['local_path']}")
        checks.append({"name": name, "passed": True, "files": len(rows)})
    for directory in ["capability", "economics", "evaluation"]:
        sources.update(str(path.relative_to(ROOT)) for path in (ROOT / directory).glob("*.py"))
    sources.add("data/origin.json")
    sources.add("scripts/reproduce.py")
    sources.update(
        str(path.relative_to(ROOT))
        for path in (ROOT / "integration").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return sources, checks


def main() -> int:
    """Execute original CLIs and compare deterministic scientific and ledger results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory; relative paths are resolved from the study root.")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (ROOT / (args.output or Path("reproduction") / stamp)).resolve()
    if output == ROOT or (output.is_relative_to(ROOT) and output.relative_to(ROOT).parts[0] != "reproduction"):
        parser.error("inside this study, output must be a new directory below reproduction/")
    if output.exists():
        parser.error("output already exists; choose a new directory to preserve previous runs")
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        parser.error("this repository supports Python 3.11–3.13")
    if shutil.which("node") is None:
        parser.error("Node.js is required by the unchanged research lifecycle; nothing will be installed")
    dependencies = {name: importlib.metadata.version(name) for name in ("cryptography", "pydantic")}
    if dependencies["pydantic"].split(".")[0] != "2":
        parser.error("the pinned native closure requires Pydantic 2")
    sources, checks = verify_inputs()
    source_hashes = {name: digest(ROOT / name) for name in sorted(sources)}
    output.mkdir(parents=True, exist_ok=False)
    stage = output / "workspace"
    for name in sorted(sources):
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    save(
        output / "source-manifest.json", {"schema": "shared-observation-reproduction-inputs/v1", "files": source_hashes}
    )
    (stage / "results").mkdir()
    (stage / "evaluation/origin-check").mkdir()
    commands: list[dict[str, Any]] = []
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    started = time.perf_counter()
    error = None

    def run(name: str, arguments: list[str]) -> None:
        begin = time.perf_counter()
        process = subprocess.run(
            [sys.executable, *arguments],
            cwd=stage,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        logs = output / "logs"
        logs.mkdir(exist_ok=True)
        (logs / f"{name}.stdout.txt").write_text(process.stdout)
        (logs / f"{name}.stderr.txt").write_text(process.stderr)
        commands.append(
            {
                "name": name,
                "cwd": "workspace",
                "command": ["python", *arguments],
                "returncode": process.returncode,
                "elapsed_seconds": time.perf_counter() - begin,
                "stdout": f"logs/{name}.stdout.txt",
                "stderr": f"logs/{name}.stderr.txt",
            }
        )
        if process.returncode != 0:
            raise RuntimeError(f"{name} failed with exit {process.returncode}; inspect preserved logs")

    def compare(name: str, current: Any, original: Any) -> None:
        checks.append({"name": name, "passed": current == original})

    try:
        run(
            "origin",
            [
                "capability/compiler.py",
                "--mission",
                "data/origin.json",
                "--output",
                "results/origin.json",
                "--profile",
                "capability/sensor_profile.json",
            ],
        )
        run(
            "origin-reference",
            [
                "evaluation/reference.py",
                "--mission",
                "data/origin.json",
                "--output",
                "evaluation/origin-check/reference.json",
            ],
        )
        run(
            "origin-check",
            [
                "evaluation/reference.py",
                "--mission",
                "data/origin.json",
                "--candidate",
                "results/origin.json",
                "--output",
                "evaluation/origin-check/check.json",
            ],
        )
        run(
            "confirmation",
            ["evaluation/run_confirmation.py", "--root", ".", "--output-dir", "evaluation/confirmation-v1"],
        )
        run(
            "origin-economics",
            [
                "economics/economic.py",
                "results/origin.json",
                "--assumptions",
                "economics/assumptions-v1.json",
                "--output",
                "results/economics",
            ],
        )
        run(
            "confirmation-economics",
            ["economics/confirm_economics.py", "evaluation/confirmation-v1", "--output", "results/economics"],
        )
        run("inverse-diagnostic", ["economics/inverse_diagnostic.py"])
        run("input-contract-probes", ["evaluation/run_input_probes.py"])
        run("information-bound", ["evaluation/check_information_bound.py"])
        run("accounting-assertions", ["economics/test_economic.py"])
        run("bundle-controls", ["integration/test_bundle.py"])
        run(
            "recipient-and-native-conformance",
            [
                "integration/transfer_recipient.py",
                "--compiler",
                "capability/compiler.py",
                "--profile",
                "capability/sensor_profile.json",
                "--mission",
                "evaluation/protected/cases/confirmation-041.json",
                "--out",
                "evidence/recipient-transfer",
                "--checker",
                "evaluation/reference.py",
            ],
        )
        run(
            "native-economic-reconciliation",
            [
                "integration/prepare_native_reference.py",
                "--assumptions",
                "economics/assumptions-v1.json",
                "--events",
                "results/economics/event_tree.json",
                "--out",
                "evidence/native-economics",
            ],
        )
        origin = read(stage / "results/economics/summary.json")
        fresh = read(stage / "results/economics/confirmation_summary.json")
        assumptions = read(stage / "economics/assumptions-v1.json")
        origin_profit = origin["factorial"]["T1_A1_joint"]["operating_profit_before_BC"]
        fresh_profit = fresh["sum_expected_quote_and_operating_profit"]
        campaign = {
            "B_and_C_primary_decision": "not_admitted_no_observed_incremental_cash_gain",
            "actual_customer_revenue": 0,
            "actual_total_research_cost": None,
            "additional_B_retention_if_admitted": assumptions["B_retention_admission_cost"],
            "additional_C_if_chosen": assumptions["C_optional_calibration_cost"],
            "all_48_fresh_quote_and_operating_contribution": fresh_profit,
            "evidence": "synthetic_campaign_aggregate_not_actual_cash_or_market_sample",
            "modeled_campaign_contribution_before_optional_BC": origin_profit + fresh_profit,
            "origin_expected_operating_contribution": origin_profit,
        }
        save(stage / "results/economics/campaign_summary.json", campaign)
        paths = [
            "results/origin.json",
            "evaluation/origin-check/reference.json",
            "evaluation/origin-check/check.json",
            "evaluation/information-bound-check.json",
            "results/economics/economic_results.json",
            "results/economics/summary.json",
            "results/economics/event_tree.json",
            "results/economics/confirmation_summary.json",
            "results/economics/inverse_diagnostic.json",
            "results/economics/campaign_summary.json",
        ]
        for name in paths:
            current, original = read(stage / name), read(ROOT / name)
            if name == "results/origin.json":
                compare(
                    "origin-historical-scientific-body",
                    {key: value for key, value in current.items() if key != "compiler_sha256"},
                    original,
                )
                compare("origin-frozen-cli-output", current, read(ROOT / "evaluation/origin-check/candidate.json"))
                compare(
                    "origin-compiler-hash-binding", current["compiler_sha256"], digest(stage / "capability/compiler.py")
                )
            elif name == "results/economics/economic_results.json":
                compare(
                    "economic-source-hash-current", current["technical_sha256"], digest(stage / "results/origin.json")
                )
                compare(
                    "economic-source-hash-historical",
                    original["technical_sha256"],
                    digest(ROOT / "results/origin.json"),
                )
                compare(
                    "economic-result-beyond-source-hash",
                    {key: value for key, value in current.items() if key != "technical_sha256"},
                    {key: value for key, value in original.items() if key != "technical_sha256"},
                )
            else:
                compare(name, current, original)
        manifest = read(stage / "evaluation/protected/cases/manifest.json")
        comparisons = []
        for case in manifest["cases"]:
            for filename in ["candidate.json", "reference.json", "check.json"]:
                relative = f"evaluation/confirmation-v1/{case['case_id']}/{filename}"
                comparisons.append(read(stage / relative) == read(ROOT / relative))
        checks.append(
            {
                "name": "all-confirmation-scientific-records",
                "passed": all(comparisons),
                "compared": len(comparisons),
                "matching": sum(comparisons),
            }
        )
        compare(
            "sensitivity-csv",
            (stage / "results/economics/sensitivity.csv").read_text(),
            (ROOT / "results/economics/sensitivity.csv").read_text(),
        )
        current_probes = read(stage / "evaluation/input-probes-v1/summary.json")
        original_probes = read(ROOT / "evaluation/input-probes-v1/summary.json")
        compare("input-contract-probes", current_probes["rows"], original_probes["rows"])
        transfer = read(stage / "evidence/recipient-transfer/summary.json")
        original_transfer = read(ROOT / "evidence/recipient-transfer-v1_0_1/summary.json")
        compare("recipient-output", transfer["recipient_result"], original_transfer["recipient_result"])
        compare("ordinary-library-parity", transfer["ordinary_library_result"], transfer["recipient_result"])
        compare("identical-retained-bundle", transfer["artifact"]["sha256"], original_transfer["artifact"]["sha256"])
        compare("recipient-checks", transfer["passed"], transfer["total"])
        native = read(stage / "evidence/recipient-transfer/conformance/summary.json")
        compare("native-fixture-conformance", native["passed"], native["total"])
        ledger = read(stage / "evidence/native-economics/reconciliation.json")
        original_ledger = read(ROOT / "evidence/native-economics-v1/reconciliation.json")
        compare("native-economic-reconciliation", ledger["passed"], ledger["total"])
        compare("native-service-ledger", ledger["native_report"], original_ledger["native_report"])
        checks.append(
            {
                "name": "authority-and-real-money-boundaries",
                "passed": transfer["execution_authorized"] is False
                and transfer["production_admission"] is False
                and transfer["actual_customer_collections_usd"] == 0
                and ledger["actual_collections_usd"] == 0,
            }
        )
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    checks.append(
        {
            "name": "original-source-files-unchanged",
            "passed": all(digest(ROOT / name) == expected for name, expected in source_hashes.items()),
        }
    )
    passed = error is None and all(check["passed"] for check in checks)
    receipt = {
        "schema": "shared-observation-reproduction/v1",
        "status": "pass" if passed else "fail",
        "evidence_type": "REPLAY_OF_RELEASED_FROZEN_INPUTS_NOT_NEW_FRESH_EVIDENCE",
        "python": sys.version.split()[0],
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        "dependencies": dependencies,
        "source_files": len(source_hashes),
        "source_manifest": "source-manifest.json",
        "commands": commands,
        "checks": checks,
        "passed": sum(check["passed"] for check in checks),
        "total": len(checks),
        "error": error,
        "elapsed_seconds": time.perf_counter() - started,
        "comparison_policy": "Scientific JSON content and declared ledger reports match. Historical origin lacks the later CLI compiler_sha256 field: compare its scientific body, compare exact frozen CLI candidate separately, and check each economic technical_sha256 against its own input. Timestamps, paths, process IDs, ephemeral keys and elapsed times need not match.",
        "actual_customer_collections_usd": 0,
        "production_authority": False,
        "full_repository_hooks": "NOT_RUN: bounded study replay only; no provisioning or external publication.",
    }
    save(output / "receipt.json", receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "passed": receipt["passed"],
                "total": receipt["total"],
                "commands": len(commands),
                "receipt": str(output / "receipt.json"),
                "error": error,
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
