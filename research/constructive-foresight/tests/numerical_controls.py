# SPDX-License-Identifier: Apache-2.0
"""Post-confirmation functional controls for the unchanged numerical instrument.

Only 1138_bus and engineering seed 1701 are used. This is neither another
confirmation run nor an independent implementation of the numerical checker.
The outer process records child startup, work, shutdown, and complete child CPU.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = (
    "numerics.py", "protocol.json", "data/manifest.json", "data/1138_bus.mtx.gz",
    "results/forecast_freeze.json", "results/calibration/batches.jsonl",
    "results/confirmation/batches.jsonl", "results/confirmation/summary.json",
)
CRITERIA = {
    "relative_residual_l2": "relative_residual_l2_max",
    "backward_error_linf": "normwise_backward_error_linf_max",
    "manufactured_forward_error_l2": "manufactured_forward_error_l2_max",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict[str, str]:
    return {name: sha(ROOT / name) for name in PROTECTED}


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def recipe_digest(recipe: dict[str, Any]) -> str:
    payload = json.dumps(recipe, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def run_controls(output: Path) -> int:
    """Observe fixed positive and negative controls, retaining every outcome."""
    started, cpu_started, issued = time.perf_counter(), time.process_time(), utc()
    before = snapshot()
    reports: list[dict[str, Any]] = []
    failures: list[str] = []
    result: dict[str, Any] = {
        "schema": "writer9-post-confirmation-numerical-controls/v1",
        "issued_utc": issued,
        "scope": "Post-confirmation functional controls; not prospective confirmation or independent solver validation",
        "matrix": "1138_bus", "engineering_seed": 1701, "rhs_count": 16,
        "fixed_instrument_preflight_seed": 770001,
        "fixed_instrument_preflight_rhs_per_construction": 2,
        "test_source_sha256": sha(Path(__file__)), "hashes_before": before,
        "prior_observation_review": {
            "reviewed": ["tests/harness_probe.py", "tests/harness_negative_probe.py", "engineering", "evidence"],
            "already_observed": "Separate 2-by-2 wrong-output authority probe and native positive restoration",
            "missing_observations": [
                "all-zero output", "NaN output", "wrong matrix recipe", "stale source recipe",
                "stale environment recipe", "stale acceptance recipe", "unauthorized recipe envelope",
            ],
            "prior_restore_reference": "evidence/native-demo-001/demo-summary.json",
        },
    }

    def record(name: str, passed: bool, **observed: Any) -> None:
        reports.append({"name": name, "passed": bool(passed), **observed})
        if not passed:
            failures.append(name)

    try:
        frozen = json.loads((ROOT / "results/forecast_freeze.json").read_text())
        expected = {
            "numerics.py": frozen["source_sha256"],
            "protocol.json": frozen["protocol_sha256"],
            "data/manifest.json": frozen["data_manifest_sha256"],
        }
        if any(before[name] != expected_hash for name, expected_hash in expected.items()):
            raise RuntimeError("Frozen source, protocol, or manifest differs before controls")
        confirmation = json.loads((ROOT / "results/confirmation/summary.json").read_text())
        completed = datetime.fromisoformat(confirmation["completed_utc"])
        if completed >= datetime.fromisoformat(issued):
            raise RuntimeError("Controls must start after numerical confirmation")
        result["frozen_expected_hashes"] = expected
        result["numerical_confirmation_completed_utc"] = confirmation["completed_utc"]
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT))
        import numerics

        np = numerics.np
        with numerics.threadpool_limits(limits=1):
            matrix, matrix_hash, ingestion = numerics.read_matrix("1138_bus")
            truth = np.random.default_rng(1701).standard_normal((matrix.shape[0], 16))
            right = matrix @ truth
            result.update({
                "matrix_sha256": matrix_hash, "matrix_shape": list(matrix.shape), "matrix_nnz": matrix.nnz,
                "ingestion": ingestion, "acceptance": dict(numerics.TOL),
                "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                "scipy": numerics.scipy.__version__},
                "truth_sha256": hashlib.sha256(truth.tobytes()).hexdigest(),
                "rhs_sha256": hashlib.sha256(right.tobytes()).hexdigest(),
            })
            with tempfile.TemporaryDirectory(prefix="writer9-numerical-controls-") as temporary:
                directory = Path(temporary)
                initial = numerics.ReadinessInstrument(matrix, matrix_hash)
                initial_report = numerics.quality(matrix, right, initial.solve(right), truth)
                valid_path = directory / "valid-recipe.json"
                initial.export(valid_path)
                valid = json.loads(valid_path.read_text())
                valid_integrity = recipe_digest(valid["recipe"]) == valid["recipe_sha256"]
                record(
                    "valid_initial_recipe", valid_integrity and initial.preflight["qualified"]
                    and initial_report["qualified"] and valid["authority"] == "none",
                    recipe_payload=valid, integrity_valid=valid_integrity,
                    preflight_report=initial.preflight, solve_report=initial_report,
                    factor_seconds=initial.factor_seconds, preflight_seconds=initial.preflight_seconds,
                    metadata_seconds=initial.metadata_seconds,
                )

                for name, wrong in (("all_zero_output", np.zeros_like(truth)),
                                    ("nan_output", np.full_like(truth, np.nan))):
                    observed = numerics.quality(matrix, right, wrong, truth)
                    criteria = {}
                    for metric, limit in CRITERIA.items():
                        values = observed[metric]
                        rejected = [v is None or not math.isfinite(v) or v > numerics.TOL[limit] for v in values]
                        criteria[metric] = {"threshold": numerics.TOL[limit], "values": values,
                                            "rejected_by_rhs": rejected}
                    passed = (not observed["qualified"] and observed["accepted_count"] == 0
                              and observed["accepted_by_rhs"] == [False] * 16
                              and all(all(item["rejected_by_rhs"]) for item in criteria.values()))
                    record(name, passed, quality_report=observed, criterion_reports=criteria,
                           output_finite_by_rhs=np.all(np.isfinite(wrong), axis=0).tolist(),
                           nonfinite_serialization="Nonfinite metrics are null, as returned by the frozen checker")

                mutations = (
                    ("wrong_matrix_hash", ("recipe", "matrix_sha256"), "0" * 64, "Stale source or matrix"),
                    ("stale_source", ("recipe", "source_sha256"), "0" * 64, "Stale source or matrix"),
                    ("stale_numpy_environment", ("recipe", "numpy_version"), "control-stale", "Stale environment"),
                    ("stale_scipy_environment", ("recipe", "scipy_version"), "control-stale", "Stale environment"),
                    ("stale_acceptance", ("recipe", "acceptance", "relative_residual_l2_max"),
                     numerics.TOL["relative_residual_l2_max"] * 10, "Unexpected authority or acceptance policy"),
                    ("unauthorized_recipe_envelope", ("authority",), "control-only-unapproved",
                     "Unexpected authority or acceptance policy"),
                )
                for name, field_path, changed_value, expected_message in mutations:
                    mutated = copy.deepcopy(valid)
                    node = mutated
                    for field in field_path[:-1]:
                        node = node[field]
                    original_value = node[field_path[-1]]
                    node[field_path[-1]] = changed_value
                    mutated["recipe_sha256"] = recipe_digest(mutated["recipe"])
                    control_path = directory / (name + ".json")
                    write_new(control_path, mutated)
                    observation = {
                        "changed_field": ".".join(field_path), "original_value": original_value,
                        "changed_value": changed_value, "recipe_payload": mutated,
                        "recipe_integrity_recomputed": True,
                        "recipe_integrity_valid": recipe_digest(mutated["recipe"]) == mutated["recipe_sha256"],
                        "expected_exception": {"type": "ValueError", "message": expected_message},
                    }
                    try:
                        numerics.ReadinessInstrument.restore(control_path, matrix, matrix_hash)
                    except ValueError as error:
                        exact = type(error) is ValueError and str(error) == expected_message
                        record(name, exact, **observation,
                               observed_exception={"type": type(error).__name__, "message": str(error)},
                               rejection_reason_matched=exact)
                    except Exception as error:
                        record(name, False, **observation, unexpected_exception={
                            "type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
                        })
                    else:
                        record(name, False, **observation, observed_exception=None,
                               failure="Invalid recipe was accepted")

                restored = numerics.ReadinessInstrument.restore(valid_path, matrix, matrix_hash)
                restored_report = numerics.quality(matrix, right, restored.solve(right), truth)
                fresh_factor = restored.factor is not initial.factor
                fresh_preflight = restored.preflight is not initial.preflight
                record(
                    "valid_actual_restore_with_fresh_factor_and_preflight",
                    fresh_factor and fresh_preflight and restored.factor_seconds > 0
                    and restored.preflight_seconds > 0 and restored.preflight["qualified"]
                    and restored_report["qualified"],
                    distinct_instrument=restored is not initial, distinct_factor_object=fresh_factor,
                    distinct_preflight_report=fresh_preflight, recipe=restored.recipe,
                    recipe_sha256=restored.recipe_hash, preflight_report=restored.preflight,
                    solve_report=restored_report, factor_seconds=restored.factor_seconds,
                    preflight_seconds=restored.preflight_seconds, metadata_seconds=restored.metadata_seconds,
                    serialized_factor_used=False,
                )
    except Exception as error:
        failures.append("unexpected_setup_or_execution_error")
        result["unexpected_error"] = {
            "type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
        }
    after = snapshot()
    if before != after:
        failures.append("protected_source_protocol_or_data_changed")
    result.update({
        "completed_utc": utc(), "internal_wall_seconds": time.perf_counter() - started,
        "internal_cpu_seconds": time.process_time() - cpu_started, "hashes_after": after,
        "protected_files_unchanged": before == after, "controls": reports,
        "controls_observed": len(reports), "failures": failures,
        "passed": not failures and len(reports) == 10,
        "accounting": "Internal intervals are subsets of the external child-process timing; do not add twice",
    })
    write_new(output, result)
    print(json.dumps({"passed": result["passed"], "controls": len(reports), "failures": failures,
                      "output": str(output)}, allow_nan=False))
    return 0 if result["passed"] else 1


def launch(output: Path, process_output: Path) -> int:
    """Measure one child invocation externally and never overwrite an attempt."""
    if output.exists() or process_output.exists():
        raise FileExistsError("Existing attempts are immutable; choose distinct output paths for a new attempt")
    before = snapshot()
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--output", str(output)]
    environment = os.environ.copy()
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[key] = "1"
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started, issued = time.perf_counter(), utc()
    launch_error = None
    try:
        process = subprocess.run(
            command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60, check=False
        )
        returncode, stdout, stderr = process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as error:
        returncode = None
        stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout or ""
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or ""
        launch_error = {"type": type(error).__name__, "message": str(error)}
    except Exception as error:
        returncode, stdout, stderr = None, "", ""
        launch_error = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    elapsed, completed = time.perf_counter() - started, utc()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    after = snapshot()
    user_cpu = usage_after.ru_utime - usage_before.ru_utime
    system_cpu = usage_after.ru_stime - usage_before.ru_stime
    if not output.exists():
        write_new(output, {
            "schema": "writer9-post-confirmation-numerical-controls/v1", "passed": False,
            "failures": ["child_did_not_retain_control_report"], "launch_error": launch_error,
            "issued_utc": issued, "completed_utc": completed, "stdout": stdout, "stderr": stderr,
            "hashes_before": before, "hashes_after": after,
        })
    observation = json.loads(output.read_text())
    passed = returncode == 0 and observation["passed"] and before == after
    timing = {
        "schema": "writer9-external-process-timing/v1", "phase": "post-confirmation functional controls",
        "command": command, "issued_utc": issued, "completed_utc": completed,
        "wall_seconds": elapsed, "child_user_cpu_seconds": user_cpu,
        "child_system_cpu_seconds": system_cpu, "child_cpu_seconds": user_cpu + system_cpu,
        "maximum_resident_set_native": usage_after.ru_maxrss,
        "maximum_resident_set_units": "KiB on Linux", "platform": platform.system(),
        "returncode": returncode, "stdout": stdout, "stderr": stderr, "launch_error": launch_error,
        "hashes_before": before, "hashes_after": after, "protected_files_unchanged": before == after,
        "test_source_sha256": sha(Path(__file__)), "report_sha256": sha(output) if output.exists() else None,
        "passed": passed,
        "accounting": (
            "External child measurement includes Python startup/shutdown and imports. "
            "Internal times are subsets. Launcher CPU is excluded."
        ),
    }
    write_new(process_output, timing)
    print(json.dumps({"passed": passed, "output": str(output), "process_output": str(process_output),
                      "wall_seconds": elapsed, "child_cpu_seconds": user_cpu + system_cpu}, allow_nan=False))
    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/numerical-controls.json")
    parser.add_argument("--process-output", type=Path, default=ROOT / "evidence/numerical-controls-process.json")
    args = parser.parse_args()
    code = run_controls(args.output.resolve()) if args.child else launch(
        args.output.resolve(), args.process_output.resolve()
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
