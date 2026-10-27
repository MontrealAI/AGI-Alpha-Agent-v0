#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent, manually specified preconfirmation MPC boundary challenges.

These public synthetic worlds use no development/confirmation generator or seed.
They test the same fixed finite function, not physical reserve truth or security
against malicious parties. All temporary private-role files are deleted.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import study

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("all_valid_distinct_assets", [1, 1]),
    ("missing_eligibility_for_demand_5", [0, 0]),
    ("unique_asset_withheld", [0, 0]),
    ("single_shared_asset_contention", [0, 0]),
    ("correlated_owner_loss_in_pair_scenario", [0, 0]),
    ("two_universal_assets_pairs_only", [1, 0]),
    ("three_universal_assets", [1, 1]),
    ("withholding_only_when_asset_not_needed", [1, 1]),
]


def sha(path: Path) -> str:
    """Hash exact source or fixture bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_assets(name: str, scenarios: list[tuple[int, ...]]) -> list[dict[str, Any]]:
    """Specify eligibility independently of the worker's Hall formulation."""
    n = len(scenarios)
    identity = [[int(asset == demand) for demand in range(6)] for asset in range(6)]
    eligibility = identity
    if name == "missing_eligibility_for_demand_5":
        eligibility = [[int(asset == demand and demand != 5) for demand in range(6)] for asset in range(6)]
    elif name == "single_shared_asset_contention":
        eligibility = [[int(asset == 0)] * 6 for asset in range(6)]
    elif name == "two_universal_assets_pairs_only":
        eligibility = [[int(asset in (0, 2))] * 6 for asset in range(6)]
    elif name == "three_universal_assets":
        eligibility = [[int(asset in (0, 2, 4))] * 6 for asset in range(6)]
    elif name == "correlated_owner_loss_in_pair_scenario":
        eligibility = [[int(asset in (0, 1, 2))] * 6 for asset in range(6)]
    assets = [
        {
            "eligibility": row,
            "availability": [int(any(row))] * n,
            "retention": [0] * n,
        }
        for row in eligibility
    ]
    if name == "unique_asset_withheld":
        assets[2]["retention"] = [1] * n
    elif name == "correlated_owner_loss_in_pair_scenario":
        # Owner 0 loses BOTH assets together; only owner 1's single spare remains.
        index = scenarios.index((0, 1))
        for asset in (0, 1):
            assets[asset]["availability"][index] = 0
    elif name == "withholding_only_when_asset_not_needed":
        # Asset 0 is needed for demand 0, but withheld only for the unrelated {4,5} event.
        assets[0]["retention"][scenarios.index((4, 5))] = 1
    return assets


def fixtures(directory: Path, maximum: int) -> dict[str, Any]:
    """Write explicit public research fixtures, with no protected-case access."""
    scenarios = study.groups(maximum)
    owners: list[dict[str, Any]] = [
        {
            "schema": "reserve-mpc-v1",
            "party_id": party,
            "nonce": hashlib.sha256(f"PUBLIC-INDEPENDENT-CHALLENGE:{maximum}:{party}".encode()).hexdigest(),
            "worlds": [],
        }
        for party in range(3)
    ]
    labels = []
    for name, _ in CASES:
        assets = case_assets(name, scenarios)
        labels.append({"world_id": name, "family": "manual_adversarial_challenge"})
        for party in range(3):
            owners[party]["worlds"].append(
                {
                    key: [assets[2 * party + row][key] for row in range(2)]
                    for key in ("eligibility", "availability", "retention")
                }
            )
    commitments = []
    for party, owner in enumerate(owners):
        file = directory / "private" / f"party_{party}.json"
        study.save(file, owner)
        commitments.append(sha(file))
    manifest = {
        "schema": "reserve-mpc-v1",
        "parties": 3,
        "assets_per_party": 2,
        "demands": 6,
        "max_claims": maximum,
        "scope_id": f"independent-manual-component-check-max{maximum}",
        "scenario_epoch": "preconfirmation-manual-challenge-v1",
        "world_count": len(CASES),
        "scenarios": [
            {"id": "demand-" + "-".join(map(str, group)), "demand_clients": list(group)} for group in scenarios
        ],
        "input_commitments": commitments,
    }
    study.save(directory / "manifest.json", manifest)
    study.save(directory / "labels.json", labels)
    return {"manifest": manifest, "owner_files": owners, "labels": labels}


def invalid_refusals(root: Path, port: int) -> list[dict[str, Any]]:
    """Require malformed input to fail before another party is available."""
    results = []
    marker = "PRIVATE_TEST_MARKER_MUST_NOT_BE_ECHOED"
    for index, name in enumerate(("unknown_private_field", "incomplete_scenario_family", "owner_commitment_mismatch")):
        directory = root / name
        fixture = fixtures(directory, 2)
        manifest = fixture["manifest"]
        owner_path = directory / "private/party_0.json"
        owner = fixture["owner_files"][0]
        if name == "unknown_private_field":
            owner["worlds"][0]["secret_location"] = marker
            study.save(owner_path, owner)
            manifest["input_commitments"][0] = sha(owner_path)
        elif name == "incomplete_scenario_family":
            manifest["scenarios"].pop()
        else:
            owner["worlds"][0]["eligibility"][0][0] = 0
            study.save(owner_path, owner)
        study.save(directory / "manifest.json", manifest)
        command = [
            sys.executable,
            "-B",
            str(ROOT / "src/mpc_worker.py"),
            "-M3",
            "-I0",
            "-T1",
            "-K40",
            f"-B{port + 10 * index}",
            "--manifest",
            str(directory / "manifest.json"),
            "--private-dir",
            str(directory / "private"),
        ]
        run = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )
        errors = [json.loads(line) for line in run.stderr.splitlines() if line.startswith("{")]
        passed = (
            run.returncode != 0
            and run.stdout == ""
            and marker not in run.stderr
            and any(e.get("event") == "mpc_worker_error" for e in errors)
        )
        results.append(
            {
                "case": name,
                "passed": passed,
                "exit_code": run.returncode,
                "stdout": run.stdout,
                "stderr": run.stderr,
                "other_parties_started": False,
            }
        )
    return results


def main() -> None:
    """Run all manual challenges without altering study sources or protected cases."""
    receipt: dict[str, Any] = {
        "schema": "agialpha.independent-mpc-challenges.v1",
        "provenance": "Independently hand-constructed before fresh confirmation; no held-out generator seeds or results accessed.",
        "scope": "Actual local MPC component execution; no query authority, production secrecy, field input truth or market claim.",
        "worker_sha256": sha(ROOT / "src/mpc_worker.py"),
        "driver_sha256": sha(ROOT / "src/study.py"),
        "challenge_source_sha256": sha(Path(__file__)),
        "runs": [],
    }
    temporary: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="independent-reserve-challenges-") as tmp:
            temporary = Path(tmp)
            for maximum in (2, 3):
                directory = temporary / f"max{maximum}"
                fixture = fixtures(directory, maximum)
                output = directory / "execution"
                execution = study.execute(directory, 17550 + 10 * maximum, output)
                evaluation = study.evaluate(directory, execution)
                evaluation["driver_wilson95_inapplicable_for_inference"] = evaluation.pop("agreement_wilson95")
                evaluation["statistical_boundary"] = (
                    "These cases are manually selected deterministic challenges, not independent random population draws. "
                    "The driver-supplied Wilson interval is preserved only as an inapplicable diagnostic; "
                    "no sampling-based coverage or population inference is claimed."
                )
                expected = [pair[maximum - 2] for _, pair in CASES]
                actual = execution["answer"]["all_scenarios_sufficient"]
                oracle = [row["oracle"] for row in evaluation["worlds"]]
                receipt["runs"].append(
                    {
                        "max_claims": maximum,
                        "scenario_count": len(fixture["manifest"]["scenarios"]),
                        "case_names": [name for name, _ in CASES],
                        "expected_bits_independently_specified": expected,
                        "actual_mpc_bits": actual,
                        "backtracking_oracle_bits": oracle,
                        "passed": actual == oracle == expected,
                        "evaluation": evaluation,
                        "process_evidence": study.load(output / "execution.json"),
                        "fixture": fixture,
                    }
                )
            receipt["invalid_refusals"] = invalid_refusals(temporary / "invalid", 17650)
    except Exception as exc:
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    receipt["temporary_copy_deleted"] = temporary is None or not temporary.exists()
    receipt["passed"] = (
        "error" not in receipt
        and len(receipt["runs"]) == 2
        and all(run["passed"] for run in receipt["runs"])
        and all(run["passed"] for run in receipt.get("invalid_refusals", []))
        and receipt["temporary_copy_deleted"]
    )
    study.save(ROOT / "evidence/challenge_checks.json", receipt)
    print(
        json.dumps(
            {
                "passed": receipt["passed"],
                "structured_mpc_worlds": sum(len(run["actual_mpc_bits"]) for run in receipt["runs"]),
                "invalid_refusals": len(receipt.get("invalid_refusals", [])),
                "error": receipt.get("error"),
            },
            indent=2,
        )
    )
    raise SystemExit(0 if receipt["passed"] else 1)


if __name__ == "__main__":
    main()
