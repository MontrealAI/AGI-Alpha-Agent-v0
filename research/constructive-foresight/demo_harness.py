# SPDX-License-Identifier: Apache-2.0
"""Two fixed engineering demonstrations; run only after the study source freeze.

Runs a real numerical instrument through unchanged Alpha execution boundaries,
then restores exact recipe bytes from an unchanged Jobs MissionPack and rebuilds
the instrument under a fresh local test fixture. This is not an efficacy trial.
"""
from __future__ import annotations

import time
PROCESS_WALL_START, PROCESS_CPU_START = time.perf_counter(), time.process_time()

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
from threadpoolctl import threadpool_limits

from harness_adapter import run_harness
from independent_checker import inspect_artifact
from numerics import ReadinessInstrument, read_matrix, source_hash

ROOT = Path(__file__).resolve().parent
MATRIX, SEED, Q = "1138_bus", 1701, 4


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def save(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(encoded(value))


def numeric_handler(recipe_path: Path | None = None) -> Callable[[], dict[str, Any]]:
    def run() -> dict[str, Any]:
        started, cpu = time.perf_counter(), time.process_time()
        a, matrix_hash, _ = read_matrix(MATRIX)
        read_end = time.perf_counter()
        truth = np.random.default_rng(SEED).standard_normal((a.shape[0], 16))[:, :Q]
        b = a @ truth
        generated = time.perf_counter()
        if recipe_path is None:
            instrument = ReadinessInstrument(a, matrix_hash)
        else:
            instrument = ReadinessInstrument.restore(recipe_path, a, matrix_hash)
        ready = time.perf_counter()
        x = instrument.solve(b)
        solved = time.perf_counter()
        recipe = {"recipe": instrument.recipe, "recipe_sha256": instrument.recipe_hash,
                  "proof": "preflight only; every new output requires a fresh check", "authority": "none"}
        # Keep the exact numerical JSON inside a string: native Alpha commitments
        # use decimal strings, while the recipe's own hash binds JSON floats.
        recipe_bytes = json.dumps(recipe, sort_keys=True, allow_nan=False).encode()
        artifact = {
            "schema": "writer9-readiness-demo-artifact/v1", "matrix": MATRIX,
            "matrix_sha256": matrix_hash, "numerics_source_sha256": source_hash(),
            "seed": SEED, "q": Q, "x": x.tolist(),
            "recipe_payload_json": recipe_bytes.decode(),
            "recipe_payload_sha256": hashlib.sha256(recipe_bytes).hexdigest(),
            "construction": (
                "fresh factorization" if recipe_path is None
                else "knowledge-only recipe import; fresh factorization and preflight"
            ),
        }
        finished = time.perf_counter()
        return {
            "artifact_content": artifact,
            "evidence_class": "Fixed development engineering demonstration; excluded from comparative trials",
            "timing": {
                "read_hash_parse_seconds": read_end - started, "rhs_generation_seconds": generated - read_end,
                "constructor_total_seconds": ready - generated, "factor_seconds": instrument.factor_seconds,
                "preflight_seconds": instrument.preflight_seconds,
                "recipe_metadata_seconds": instrument.metadata_seconds,
                "constructor_other_seconds": (
                    ready - generated - instrument.factor_seconds
                    - instrument.preflight_seconds - instrument.metadata_seconds
                ),
                "solve_seconds": solved - ready, "serialization_preparation_seconds": finished - solved,
                "total_seconds": finished - started, "cpu_seconds": time.process_time() - cpu,
            },
            "preflight": instrument.preflight, "recipe_sha256": instrument.recipe_hash,
            "restored_from_recipe": recipe_path is not None,
        }
    return run


def check(record: dict[str, Any]) -> dict[str, Any]:
    return inspect_artifact(record, matrix=MATRIX, seed=SEED, q=Q)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    entered_main = time.perf_counter()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_files = {name: ROOT / name for name in (
        "demo_harness.py", "independent_checker.py", "numerics.py", "framework_bridge.mjs",
        "protocol.json", "data/manifest.json",
    )}
    source_snapshot = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_files.items()}
    plan = {"schema": "writer9-native-demo-plan/v1", "matrix": MATRIX, "seed": SEED, "q": Q,
            "fixed_runs": ["initial", "restored"], "source_files": source_snapshot,
            "scope": "Engineering integration only; no forecasting/beneficiary inference",
            "budget": "Exactly two task executions; no automatic retry; charged to full study CPU budget",
            "authority": "Exact public RFC8032 TEST1 fixture; no external authority or independent custody"}
    save(output / "demo-plan.json", plan)
    segments, results = [], {}
    world = {
        "matrix": MATRIX, "manufactured_rhs_seed": SEED, "all_truth_columns": 16, "q": Q,
        "domain": "Fixed bounded scientific computing",
    }
    policy = {"solver": "ReadinessInstrument: conventional SuperLU/COLAMD plus preflight and source-bound recipe",
              "acceptance": json.loads((ROOT / "protocol.json").read_text())["numerical_design"]["acceptance"]}
    with threadpool_limits(limits=1):
        before, cpu = time.perf_counter(), time.process_time()
        initial = run_harness(
            output / "initial", numeric_handler(), check, source_files=source_files,
            world=world, policy=policy, protocol=plan,
            purpose="Qualify the fixed 1138_bus four-RHS instrument before authorizing artifact inspection",
        )
        segments.append({
            "name": "initial_native_run", "wall_seconds": time.perf_counter() - before,
            "cpu_seconds": time.process_time() - cpu,
        })
        results["initial"] = initial
        if initial["proof"]["outcome"] != "pass":
            raise ValueError("Initial instrument failed; restoration is not attempted")

        bridge_path = output / "framework-bridge.json"
        before, cpu = time.perf_counter(), time.process_time()
        child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        command = ["node", str(ROOT / "framework_bridge.mjs"), str(output / "initial/native-receipt.json"),
                   initial["phases"]["formation"]["artifact_path"], str(bridge_path)]
        completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        child_cpu = child_after.ru_utime + child_after.ru_stime - child_before.ru_utime - child_before.ru_stime
        segments.append({"name": "native_route_and_pack_bridge", "wall_seconds": time.perf_counter() - before,
                         "cpu_seconds": time.process_time() - cpu + child_cpu, "child_cpu_seconds": child_cpu})
        save(output / "bridge-process.json", {
            "command": command, "stdout": completed.stdout, "stderr": completed.stderr,
            "returncode": completed.returncode,
        })

        before, cpu = time.perf_counter(), time.process_time()
        bridge = json.loads(bridge_path.read_text())
        restored = bridge["restored"]
        if restored["activeAuthority"] or restored["proofCurrency"] != "absent" or restored["executionEnabled"]:
            raise ValueError("Knowledge restoration must not inherit execution authority or current proof")
        recipes = [entry for entry in restored["artifacts"] if entry["path"] == "numerical-recipe.json"]
        if len(recipes) != 1:
            raise ValueError("Restored pack must contain the exact numerical recipe")
        retained = recipes[0]["content"]
        recipe_bytes = retained["recipePayloadJSON"].encode()
        if hashlib.sha256(recipe_bytes).hexdigest() != retained["recipePayloadSha256"]:
            raise ValueError("Restored recipe bytes changed")
        original = json.loads(Path(initial["phases"]["formation"]["artifact_path"]).read_text())
        if original["recipe_payload_sha256"] != retained["recipePayloadSha256"]:
            raise ValueError("Restored recipe does not belong to the checked artifact")
        recipe_path = output / "imported-recipe.json"
        with recipe_path.open("xb") as stream:
            stream.write(recipe_bytes)
        boundary = {
            "parent_pack_digest": restored["packDigest"], "proposed_successor": bridge["successor"],
            "imported_authority": restored["activeAuthority"],
            "imported_proof_currency": restored["proofCurrency"],
            "execution_enabled_by_import": restored["executionEnabled"],
            "recipe_payload_sha256": retained["recipePayloadSha256"],
            "next_action": (
                "Fresh bounded research fixture, fresh refactorization/preflight, "
                "fresh separate checker, fresh explicit fixture grant"
            ),
        }
        save(output / "restore-boundary.json", boundary)
        segments.append({
            "name": "knowledge_import_and_recipe_retention", "wall_seconds": time.perf_counter() - before,
            "cpu_seconds": time.process_time() - cpu,
        })

        before, cpu = time.perf_counter(), time.process_time()
        restored_receipt = run_harness(
            output / "restored", numeric_handler(recipe_path), check,
            source_files={**source_files, "imported_recipe": recipe_path},
            world={**world, "parent_pack_digest": restored["packDigest"]},
            policy={
                **policy, "restoration": "New fixture; refactor and preflight; imported proof and permission absent",
            },
            protocol=plan,
            purpose="Rebuild and freshly qualify the imported recipe before a new explicit artifact-inspection grant",
        )
        segments.append({
            "name": "restored_native_run_including_refactor", "wall_seconds": time.perf_counter() - before,
            "cpu_seconds": time.process_time() - cpu,
        })
        results["restored"] = restored_receipt
    for name, receipt in results.items():
        if receipt["proof"]["outcome"] != "pass" or not all(
            control["rejected"] and control["handler_counts_unchanged"] for control in receipt["controls"]
        ):
            raise ValueError(f"Required numerical acceptance/authority control failed: {name}")
    if initial["release_digest"] == restored_receipt["release_digest"]:
        raise ValueError("Restored execution must identify a separately bound release")
    for name, path in source_files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != source_snapshot[name]:
            raise ValueError("Source changed during engineering demonstration")
    finished = time.perf_counter()
    elapsed = finished - PROCESS_WALL_START
    python_cpu = time.process_time() - PROCESS_CPU_START
    breakdown = []
    for name, receipt in results.items():
        handler = float(receipt["phases"]["formation"]["timing"]["total_seconds"])
        checking = float(receipt["phases"]["challenge"]["timing"]["total_seconds"])
        segment_name = "initial_native_run" if name == "initial" else "restored_native_run_including_refactor"
        measured_run = next(row for row in segments if row["name"] == segment_name)["wall_seconds"]
        breakdown.append({
            "run": name, "handler_seconds": handler, "checker_seconds": checking,
            "native_orchestration_and_retention_seconds": measured_run - handler - checking,
            "note": "Components partition the native-run segment; do not add them again to top-level totals",
        })
    summary = {"schema": "writer9-native-demo-summary/v1", "matrix": MATRIX, "seed": SEED, "q": Q,
               "evidence_class": "observed engineering integration on real-origin matrix and synthetic RHS",
               "initial_release": initial["release_digest"], "restored_release": restored_receipt["release_digest"],
               "lineage_parent_pack": restored["packDigest"],
               "proof_outcomes": {name: receipt["proof"]["outcome"] for name, receipt in results.items()},
               "authority_controls": {name: receipt["controls"] for name, receipt in results.items()},
               "refactorization_observed": restored_receipt["phases"]["formation"]["restored_from_recipe"],
               "timing": {"import_and_setup_seconds": entered_main - PROCESS_WALL_START,
                          "total_wall_seconds_before_summary_write": elapsed, "python_cpu_seconds": python_cpu,
                          "child_cpu_seconds": child_cpu,
                          "total_cpu_seconds_before_summary_write": python_cpu + child_cpu,
                          "segments": segments, "native_run_decomposition": breakdown,
                          "remaining_python_orchestration_seconds": elapsed - sum(
                              row["wall_seconds"] for row in segments
                          ),
                          "accounting": (
                              "Top-level segments plus remaining orchestration partition wall time. "
                              "Subcomponents are nested and must not be added twice. Includes imports "
                              "and both factor rebuilds; final summary serialization is excluded "
                              "and explicitly bounded by the external process timer."
                          )},
               "cash_payment": None, "external_acceptance": "unobserved", "fleet_runtime_executed": False,
               "limitations": [
                   "One fixed development case; excluded from confirmatory comparisons",
                   "Same operator and public common-control fixture identity",
                   "No independent customer or financial acceptance",
                   "Jobs/Manager routes are synthetic-local, zero cap; no deployed settlement",
                   "No inherited grant or fresh proof from restore",
                   "No forecasting or Mission Alpha verdict from this demonstration",
               ]}
    save(output / "demo-summary.json", summary)
    print(json.dumps({
        "output": str(output), "proof_outcomes": summary["proof_outcomes"],
        "refactorization_observed": summary["refactorization_observed"],
        "total_wall_seconds": elapsed, "total_cpu_seconds": python_cpu + child_cpu,
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if len(sys.argv) == 2:
            destination = Path(sys.argv[1]) / "FAILURE.json"
            if destination.parent.is_dir() and not destination.exists():
                children = resource.getrusage(resource.RUSAGE_CHILDREN)
                save(destination, {
                    "schema": "writer9-demo-failure/v1", "error": type(error).__name__, "message": str(error),
                    "wall_seconds": time.perf_counter() - PROCESS_WALL_START,
                    "python_cpu_seconds": time.process_time() - PROCESS_CPU_START,
                    "child_cpu_seconds": children.ru_utime + children.ru_stime,
                    "automatic_retry": False, "retention": "All partial artifacts retained",
                })
        raise
