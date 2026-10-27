#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce the declared-input reserve experiment with three actual MPyC workers.

Synthetic fixtures are public research data. The supervisor deliberately has
all inputs for an independent oracle; it is not a confidential production host.
No live utility inputs or model API calls are made by this program.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config/technical_protocol.json"


def digest(data: bytes) -> str:
    """Hash exact bytes."""
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value: object) -> None:
    """Write a readable deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(path: Path) -> Any:
    """Load a local research artifact."""
    return json.loads(path.read_text())


def groups(max_claims: int) -> list[tuple[int, ...]]:
    """Return the complete declared family, without dropping hard cases."""
    return [s for size in range(1, max_claims + 1) for s in itertools.combinations(range(6), size)]


def generate(protocol: dict[str, Any], cohort: str, destination: Path) -> dict[str, Any]:
    """Generate independent worlds after the specified source freeze.

    Deterministic public fixture nonces are reproducible, not production secrets.
    Asset eligibility is shared across scenarios; outages and retention may vary.
    """
    seed = protocol["seeds"][cohort]
    n = protocol["world_counts"][cohort]
    maximum = protocol["successor_max_claims"] if cohort == "successor_confirmation" else protocol["origin_max_claims"]
    scenarios = groups(maximum)
    rng = random.Random(seed)
    parameters = protocol["generation"]
    owners: list[dict[str, Any]] = [
        {
            "schema": "reserve-mpc-v1",
            "party_id": party,
            "nonce": digest(f"PUBLIC-SYNTHETIC-NONCE:{seed}:{party}".encode()),
            "worlds": [],
        }
        for party in range(3)
    ]
    labels = []
    for world_index in range(n):
        family_index = world_index % len(protocol["world_families"])
        family = protocol["world_families"][family_index]
        probability = parameters["eligibility_probabilities"][family_index]
        labels.append({"world_id": f"{cohort}-{world_index:04d}", "family": family})
        worlds = []
        for _ in range(3):
            eligibility = [[int(rng.random() < probability) for _ in range(6)] for _ in range(2)]
            static = [rng.random() < parameters["static_asset_availability_probability"] for _ in range(2)]
            availability = [
                [
                    int(static[row] and rng.random() >= parameters["scenario_independent_unavailability_probability"])
                    for _ in scenarios
                ]
                for row in range(2)
            ]
            retention = [
                [int(rng.random() < parameters["scenario_retention_probability"]) for _ in scenarios] for _ in range(2)
            ]
            worlds.append({"eligibility": eligibility, "availability": availability, "retention": retention})
        if family == "correlated_unavailability":
            for scenario_index in range(len(scenarios)):
                if rng.random() < parameters["correlated_family_owner_loss_probability"]:
                    unavailable_owner = rng.randrange(3)
                    for row in range(2):
                        worlds[unavailable_owner]["availability"][row][scenario_index] = 0
        for party in range(3):
            owners[party]["worlds"].append(worlds[party])
    private = destination / "private"
    commitments = []
    for party, owner in enumerate(owners):
        path = private / f"party_{party}.json"
        save(path, owner)
        commitments.append(digest(path.read_bytes()))
    manifest = {
        "schema": "reserve-mpc-v1",
        "parties": 3,
        "assets_per_party": 2,
        "demands": 6,
        "max_claims": maximum,
        "scope_id": f"research-{cohort}",
        "scenario_epoch": f"seed-{seed}",
        "world_count": n,
        "scenarios": [{"id": "demand-" + "-".join(map(str, s)), "demand_clients": list(s)} for s in scenarios],
        "input_commitments": commitments,
    }
    save(destination / "manifest.json", manifest)
    save(destination / "labels.json", labels)
    return manifest


def allocation_exists(neighbors: dict[int, list[int]]) -> bool:
    """Independent exhaustive matching oracle; no Hall counts are used."""
    ordered = sorted(neighbors, key=lambda d: (len(neighbors[d]), d))

    def visit(position: int, used: set[int]) -> bool:
        if position == len(ordered):
            return True
        return any(visit(position + 1, used | {asset}) for asset in neighbors[ordered[position]] if asset not in used)

    return visit(0, set())


def cleartext_controls(directory: Path) -> dict[str, Any]:
    """Use all public synthetic inputs only in the research oracle."""
    manifest = load(directory / "manifest.json")
    owners = [load(directory / "private" / f"party_{party}.json") for party in range(3)]
    labels = load(directory / "labels.json")
    results = []
    for index in range(manifest["world_count"]):
        feasible = True
        bilateral = True
        failing_scenarios = []
        for scenario_index, scenario in enumerate(manifest["scenarios"]):
            neighbors: dict[int, list[int]] = {}
            for demand in scenario["demand_clients"]:
                neighbors[demand] = []
                for party in range(3):
                    world = owners[party]["worlds"][index]
                    for row in range(2):
                        if (
                            world["eligibility"][row][demand]
                            and world["availability"][row][scenario_index]
                            and not world["retention"][row][scenario_index]
                        ):
                            neighbors[demand].append(2 * party + row)
            ok = allocation_exists(neighbors)
            feasible = feasible and ok
            bilateral = bilateral and all(neighbors.values())
            if not ok:
                failing_scenarios.append(scenario["id"])
        results.append(
            {
                **labels[index],
                "oracle": int(feasible),
                "bilateral_diagnostic": int(bilateral),
                "failing_scenarios_research_only": failing_scenarios,
            }
        )
    return {
        "scope": "Independent cleartext oracle using synthetic fixtures; never a production output.",
        "worlds": results,
    }


def wilson(successes: int, count: int) -> list[float]:
    """Two-sided 95% Wilson interval for this generator's independent draws."""
    z = 1.959963984540054
    p = successes / count
    denominator = 1 + z * z / count
    middle = (p + z * z / (2 * count)) / denominator
    half = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [max(0.0, middle - half), min(1.0, middle + half)]


def execute(directory: Path, port: int, output: Path, authority_directory: Path | None = None) -> dict[str, Any]:
    """Supervise three explicitly started processes; enforce local grant if supplied."""
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    worker = ROOT / "src/mpc_worker.py"
    authority_record = None
    authority = None
    binding = None
    if authority_directory is not None:
        sys.path.insert(0, str(ROOT / "integration"))
        from query_authority import FixtureQueryAuthority, bind_query

        authority = FixtureQueryAuthority(authority_directory)
        binding = bind_query(manifest_path, worker)
        grant = authority.issue(binding)
        authority_record = authority.consume(grant, manifest_path, worker)
    commands = [
        [
            sys.executable,
            "-B",
            str(worker),
            "-M3",
            f"-I{party}",
            "-T1",
            "-K40",
            f"-B{port}",
            "--manifest",
            str(manifest_path),
            "--private-dir",
            str(directory / "private"),
        ]
        for party in range(3)
    ]
    started = time.perf_counter()
    processes: list[subprocess.Popen[str]] = []
    records: list[dict[str, Any]] = []
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        for command in commands:
            processes.append(
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
            )
        deadline = time.monotonic() + 300
        while any(process.poll() is None for process in processes):
            if time.monotonic() > deadline or any(process.poll() not in (None, 0) for process in processes):
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                break
            time.sleep(0.02)
        for party, process in enumerate(processes):
            stdout, stderr = process.communicate(timeout=5)
            (output / f"party_{party}.stdout.txt").write_text(stdout)
            (output / f"party_{party}.stderr.txt").write_text(stderr)
            telemetry = [json.loads(line) for line in stderr.splitlines() if line.startswith("{")]
            records.append(
                {
                    "party_id": party,
                    "process_id": process.pid,
                    "exit_code": process.returncode,
                    "stdout": stdout,
                    "telemetry": telemetry,
                }
            )
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
    wall_seconds = time.perf_counter() - started
    if authority is not None:
        assert binding == bind_query(manifest_path, worker), "Public binding changed during execution"
        assert authority_record is not None
        authority_record["public_receipt"] = authority.public_receipt()
    result = {
        "commands": commands,
        "records": records,
        "wall_seconds": wall_seconds,
        "authority": authority_record,
        "worker_sha256": digest(worker.read_bytes()),
        "manifest_sha256": digest(manifest_path.read_bytes()),
    }
    save(output / "execution.json", result)
    if len(records) != 3 or any(record["exit_code"] for record in records):
        raise RuntimeError("MPC execution failed; all collected outputs are preserved")
    answer = json.loads(records[0]["stdout"])
    assert records[1]["stdout"] == records[2]["stdout"] == ""
    telemetry = [record["telemetry"][-1] for record in records]
    for party, item in enumerate(telemetry):
        assert item["private_files_opened"] == [f"party_{party}.json"]
        assert item["peer_addresses"] == ["127.0.0.1"]
        assert item["status"] == "ok" and item["output_bits_opened"] == load(manifest_path)["world_count"]
    assert sum(t["bytes_sent"] for t in telemetry) == sum(t["bytes_received"] for t in telemetry)
    return {
        "answer": answer,
        "wall_seconds": wall_seconds,
        "total_stream_bytes_sent": sum(t["bytes_sent"] for t in telemetry),
        "total_stream_bytes_received": sum(t["bytes_received"] for t in telemetry),
        "actual_process_ids": [r["process_id"] for r in records],
    }


def evaluate(directory: Path, execution: dict[str, Any]) -> dict[str, Any]:
    """Report all cases, including failures and weak-control false positives."""
    oracle = cleartext_controls(directory)
    bits = execution["answer"]["all_scenarios_sufficient"]
    assert len(bits) == len(oracle["worlds"])
    for world, bit in zip(oracle["worlds"], bits, strict=True):
        world["mpc"] = bit
        world["agreement"] = bit == world["oracle"]
    rows = oracle["worlds"]
    agreement = sum(row["agreement"] for row in rows)
    families = {}
    for family in sorted({row["family"] for row in rows}):
        selected = [row for row in rows if row["family"] == family]
        families[family] = {
            "count": len(selected),
            "feasible": sum(row["oracle"] for row in selected),
            "mismatches": sum(not row["agreement"] for row in selected),
            "bilateral_false_positives": sum(row["bilateral_diagnostic"] > row["oracle"] for row in selected),
        }
    return {
        "n": len(rows),
        "oracle_agreement": agreement,
        "agreement_wilson95": wilson(agreement, len(rows)),
        "feasible": sum(row["oracle"] for row in rows),
        "infeasible": sum(not row["oracle"] for row in rows),
        "bilateral_false_positives": sum(row["bilateral_diagnostic"] > row["oracle"] for row in rows),
        "families": families,
        "execution": execution,
        "worlds": rows,
        "statistical_boundary": "Intervals concern this synthetic generator, not deployment reliability or utility populations.",
    }


def source_paths() -> list[Path]:
    """Return policy-bearing artifacts to freeze before fresh input generation."""
    paths = [
        PROTOCOL,
        ROOT / "src/study.py",
        ROOT / "src/mpc_worker.py",
        ROOT / "vendor/mpyc-0.11-py3-none-any.whl",
        ROOT / "discovery/selected_opportunity.json",
    ]
    paths += sorted((ROOT / "vendor/mpyc_0_11/mpyc").glob("*.py"))
    paths += sorted((ROOT / "integration").glob("query_authority*.py"))
    paths += sorted((ROOT / "integration/native_vendor").rglob("*.py"))
    paths += [ROOT / "integration/native_source_manifest.json"]
    paths += [ROOT / "config/dependencies.json"]
    paths += sorted((ROOT / "src").glob("challenge_checks.py"))
    return paths


def freeze(destination: Path) -> None:
    """Freeze exact source/config hashes before producing confirmation cases."""
    assert not (ROOT / "data/origin_confirmation").exists(), "Fresh origin inputs already exist"
    assert not (ROOT / "data/successor_confirmation").exists(), "Fresh successor inputs already exist"
    save(
        destination,
        {
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
            "files": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in source_paths()},
            "rule": "Any changed binding requires a prospective new freeze and new confirmation seeds.",
        },
    )


def check_freeze(path: Path) -> None:
    """Fail rather than quietly run a changed policy on protected cases."""
    for name, expected in load(path)["files"].items():
        assert digest((ROOT / name).read_bytes()) == expected, f"Freeze mismatch: {name}"


def main() -> None:
    """CLI for development, freezing, fresh confirmation and ordinary-library replay."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["development", "freeze", "confirm", "library-replay"])
    parser.add_argument("--port", type=int, default=16810)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--authority", action="store_true")
    parser.add_argument("--cohort", choices=["origin_confirmation", "successor_confirmation"])
    args = parser.parse_args()
    if args.command in ("confirm", "library-replay") and not args.authority:
        parser.error("Fresh confirmation and library replay require the explicit --authority local fixture")
    root = args.output_root.resolve()
    protocol = load(PROTOCOL)
    commitment = ROOT / "evidence/technical_freeze.json"
    if args.command == "freeze":
        freeze(commitment)
        print(commitment)
        return
    if args.command != "development":
        check_freeze(commitment)
    cohorts = ["development"] if args.command == "development" else ["origin_confirmation", "successor_confirmation"]
    if args.cohort is not None:
        if args.command not in ("confirm", "library-replay"):
            parser.error("A selected fresh cohort applies only to confirmation or library replay")
        cohorts = [args.cohort]
    for offset, cohort in enumerate(cohorts):
        directory = root / "data" / cohort
        if args.command != "library-replay":
            assert not directory.exists(), f"Refusing to overwrite preserved fixture: {directory}"
            generate(protocol, cohort, directory)
        label = cohort + ("_ordinary_library" if args.command == "library-replay" else "")
        output = root / "results" / label
        with tempfile.TemporaryDirectory(prefix="reserve-query-authority-") as private_temporary:
            authority_directory = Path(private_temporary) / "journal" if args.authority else None
            execution = execute(directory, args.port + 10 * offset, output, authority_directory)
        result = evaluate(directory, execution)
        save(root / "results" / f"{label}.json", result)
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in ["n", "oracle_agreement", "feasible", "infeasible", "bilateral_false_positives"]
                }
            )
        )
        assert result["oracle_agreement"] == result["n"], "Preserved MPC/oracle mismatch"


if __name__ == "__main__":
    main()
