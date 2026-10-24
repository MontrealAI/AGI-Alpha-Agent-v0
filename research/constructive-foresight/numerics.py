# SPDX-License-Identifier: Apache-2.0
"""Bounded, source-bound sparse readiness experiment; no network or external authority."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import platform
import tarfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import numpy as np
import scipy
from scipy.io import mmread
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import LinearOperator, cg, splu
from threadpoolctl import threadpool_info, threadpool_limits

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / "protocol.json").read_text())
N = P["numerical_design"]
TOL = N["acceptance"]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def source_hash() -> str:
    return digest(Path(__file__).read_bytes())


def read_matrix(name: str) -> tuple[csc_matrix, str, dict[str, float]]:
    """Load one exact frozen file; archive extraction never writes a member path."""
    start = time.perf_counter()
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    row = next(row for row in manifest["matrices"] if row["name"] == name)
    path = ROOT / "data" / row.get("file", f"{name}.tar.gz")
    raw = path.read_bytes()
    if digest(raw) != row["archive_sha256"]:
        raise ValueError("Matrix source bytes changed")
    if path.name.endswith(".tar.gz"):
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            member = archive.getmember(f"{name}/{name}.mtx")
            handle = archive.extractfile(member)
            if handle is None or not member.isfile():
                raise ValueError("Matrix member unavailable")
            data = handle.read()
    elif path.name.endswith(".gz"):
        data = gzip.decompress(raw)
    else:
        data = raw
    if digest(data) != row["matrix_sha256"]:
        raise ValueError("Matrix payload bytes changed")
    a = csc_matrix(mmread(io.BytesIO(data)), dtype=np.float64)
    a.sum_duplicates()
    a.eliminate_zeros()
    a.sort_indices()
    if a.shape != (row["rows"], row["rows"]) or a.nnz != row["nnz"]:
        raise ValueError("Matrix dimensions/nonzeros differ from frozen metadata")
    return a, row["matrix_sha256"], {"read_hash_parse_seconds": time.perf_counter() - start}


def quality(a: csc_matrix, b: np.ndarray, x: np.ndarray, truth: np.ndarray) -> dict[str, Any]:
    """Check every column; backward residual is not a forward-error certificate."""
    if x.ndim == 1:
        x, b, truth = x[:, None], b[:, None], truth[:, None]
    finite = np.all(np.isfinite(x), axis=0)
    r = b - a @ x
    anorm = float(np.max(np.asarray(abs(a).sum(axis=1))))
    residual = np.linalg.norm(r, axis=0) / np.maximum(np.linalg.norm(b, axis=0), np.finfo(float).tiny)
    denominator = anorm * np.max(abs(x), axis=0) + np.max(abs(b), axis=0)
    backward = np.max(abs(r), axis=0) / np.maximum(denominator, np.finfo(float).tiny)
    forward = np.linalg.norm(x - truth, axis=0) / np.maximum(np.linalg.norm(truth, axis=0), np.finfo(float).tiny)
    accepted = finite & (residual <= TOL["relative_residual_l2_max"]) & (
        backward <= TOL["normwise_backward_error_linf_max"]) & (forward <= TOL["manufactured_forward_error_l2_max"])
    def clean(values: np.ndarray) -> list[float | None]:
        return [float(v) if np.isfinite(v) else None for v in values]
    return {"relative_residual_l2": clean(residual), "backward_error_linf": clean(backward),
            "manufactured_forward_error_l2": clean(forward), "accepted_by_rhs": accepted.tolist(),
            "qualified": bool(np.all(accepted)), "accepted_count": int(accepted.sum())}


class ReadinessInstrument:
    """Cache a conventional solver under a portable recipe and fresh finite checks."""
    def __init__(self, a: csc_matrix, matrix_hash: str):
        self.a, self.matrix_hash = a, matrix_hash
        before = time.perf_counter()
        self.factor = splu(a, permc_spec="COLAMD")
        self.factor_seconds = time.perf_counter() - before
        before = time.perf_counter()
        truth = np.random.default_rng(770001).standard_normal((a.shape[0], 2))
        b = a @ truth
        x = self.factor.solve(b)
        self.preflight = quality(a, b, x, truth)
        self.preflight_seconds = time.perf_counter() - before
        before = time.perf_counter()
        self.recipe = {"schema": "readiness-recipe/v1", "matrix_sha256": matrix_hash,
                       "source_sha256": source_hash(), "solver": "SuperLU/COLAMD/float64",
                       "scipy_version": scipy.__version__, "numpy_version": np.__version__,
                       "preflight_seed": 770001, "preflight_rhs": 2, "acceptance": TOL,
                       "restoration": "refactorize and revalidate; no serialized factor",
                       "authority": "none", "preflight": self.preflight}
        self.recipe_hash = digest(json.dumps(self.recipe, sort_keys=True, allow_nan=False).encode())
        self.metadata_seconds = time.perf_counter() - before

    def solve(self, b: np.ndarray) -> np.ndarray:
        if not self.preflight["qualified"]:
            raise ValueError("Unqualified preflight")
        return self.factor.solve(b)

    def export(self, path: Path) -> None:
        write_json(path, {"recipe": self.recipe, "recipe_sha256": self.recipe_hash,
                          "proof": "preflight only; every new output requires a fresh check", "authority": "none"})

    @classmethod
    def restore(cls, path: Path, a: csc_matrix, matrix_hash: str) -> "ReadinessInstrument":
        payload = json.loads(path.read_text())
        recipe = payload["recipe"]
        if digest(json.dumps(recipe, sort_keys=True, allow_nan=False).encode()) != payload["recipe_sha256"]:
            raise ValueError("Corrupt recipe")
        if recipe["matrix_sha256"] != matrix_hash or recipe["source_sha256"] != source_hash():
            raise ValueError("Stale source or matrix")
        if recipe["scipy_version"] != scipy.__version__ or recipe["numpy_version"] != np.__version__:
            raise ValueError("Stale environment")
        if recipe["acceptance"] != TOL or payload["authority"] != "none":
            raise ValueError("Unexpected authority or acceptance policy")
        return cls(a, matrix_hash)


def run_batch(a: csc_matrix, ahash: str, truth: np.ndarray, method: str) -> tuple[dict[str, Any], np.ndarray]:
    start, cpu = time.perf_counter(), time.process_time()
    issued = utc()
    before = time.perf_counter()
    b = a @ truth
    rhs_formation_s = time.perf_counter() - before
    factor_s = preflight_s = metadata_s = solve_s = 0.0
    preflight_ok = True
    recipe_hash = None
    if method == "certified_ready":
        instrument = ReadinessInstrument(a, ahash)
        factor_s, preflight_s, metadata_s = instrument.factor_seconds, instrument.preflight_seconds, instrument.metadata_seconds
        preflight_ok, recipe_hash = instrument.preflight["qualified"], instrument.recipe_hash
        ready = time.perf_counter()
        solve_start = time.perf_counter()
        x = instrument.solve(b) if preflight_ok else np.full_like(truth, np.nan)
        solve_s = time.perf_counter() - solve_start
    elif method == "native_cached":
        before = time.perf_counter()
        factor = splu(a, permc_spec="COLAMD")
        factor_s = time.perf_counter() - before
        ready = time.perf_counter()
        before = time.perf_counter()
        x = factor.solve(b)
        solve_s = time.perf_counter() - before
    elif method == "cold_direct":
        ready = start
        columns = []
        for j in range(truth.shape[1]):
            before = time.perf_counter()
            factor = splu(a, permc_spec="COLAMD")
            factor_s += time.perf_counter() - before
            before = time.perf_counter()
            columns.append(factor.solve(b[:, j]))
            solve_s += time.perf_counter() - before
        x = np.column_stack(columns)
    else:
        raise ValueError("Unknown solver arm")
    before = time.perf_counter()
    checked = quality(a, b, x, truth)
    verify_s = time.perf_counter() - before
    end = time.perf_counter()
    row = {"issued_utc": issued, "completed_utc": utc(), "method": method, "matrix_sha256": ahash,
           "recipe_sha256": recipe_hash, "factor_seconds": factor_s, "preflight_seconds": preflight_s,
           "metadata_seconds": metadata_s, "solve_seconds": solve_s, "validation_seconds": verify_s,
           "rhs_formation_seconds": rhs_formation_s,
           "response_seconds": end - ready, "total_seconds": end - start,
           "cpu_seconds": time.process_time() - cpu, "preflight_qualified": preflight_ok, **checked}
    row["overhead_seconds"] = row["total_seconds"] - sum(row[k] for k in (
        "factor_seconds", "preflight_seconds", "metadata_seconds", "solve_seconds", "validation_seconds", "rhs_formation_seconds"))
    return row, x


def run_phase(phase: str, output: Path) -> None:
    """Execute one fixed phase exactly once; all planned unfinished cells remain explicit."""
    if output.exists():
        raise FileExistsError("Never overwrite an experiment phase")
    output.mkdir(parents=True)
    phase_start, phase_cpu = time.perf_counter(), time.process_time()
    phase_issued = utc()
    if phase == "confirmation":
        freeze = json.loads((ROOT / "results/forecast_freeze.json").read_text())
        if freeze["source_sha256"] != source_hash() or freeze["protocol_sha256"] != digest((ROOT / "protocol.json").read_bytes()):
            raise ValueError("Source changed after forecast freeze")
        if freeze["data_manifest_sha256"] != digest((ROOT / "data/manifest.json").read_bytes()):
            raise ValueError("Data manifest changed after forecast freeze")
        if freeze["calibration_sha256"] != digest((ROOT / "results/calibration/batches.jsonl").read_bytes()):
            raise ValueError("Calibration data changed after forecast freeze")
        if datetime.now(timezone.utc) > datetime.fromisoformat(freeze["valid_launch_until_utc"]):
            raise ValueError("Frozen forecast launch window expired")
    blocks = 1 if phase == "development" else N[f"{phase}_blocks"]
    base = N["development_seed"] if phase == "development" else N[f"{phase}_seed_base"]
    rows, diagnostic, ingestions, stopped = [], [], [], False
    previous_cpu = sum(json.loads(path.read_text()).get("cpu_seconds", 0.0)
                       for path in (ROOT / "results").glob("*/summary.json"))
    def budget_reached() -> bool:
        return (time.perf_counter() - phase_start >= N["wall_budget_seconds_per_phase"] or
                previous_cpu + time.process_time() - phase_cpu >= N["whole_study_cpu_budget_seconds"])
    for index, name in enumerate(P["matrices_in_order"]):
        a, ahash, ingestion = read_matrix(name)
        ingestions.append({"matrix": name, "rows": a.shape[0], "nnz": a.nnz, **ingestion})
        for block in range(blocks):
            seed = base + 100 * index + block
            before = time.perf_counter()
            all_truth = np.random.default_rng(seed).standard_normal((a.shape[0], 16))
            generation_s = time.perf_counter() - before
            for q in N["q_values"]:
                order = np.random.default_rng(N["order_seed"] + seed + q).permutation(N["methods"]).tolist()
                for position, method in enumerate(order):
                    if budget_reached():
                        stopped = True
                        break
                    attempt_start, attempt_cpu = time.perf_counter(), time.process_time()
                    attempt_utc = utc()
                    try:
                        row, x = run_batch(a, ahash, all_truth[:, :q], method)
                    except Exception as error:
                        elapsed = time.perf_counter() - attempt_start
                        row = {"issued_utc": attempt_utc, "completed_utc": utc(), "method": method,
                               "matrix_sha256": ahash, "recipe_sha256": None, "factor_seconds": 0.0,
                               "preflight_seconds": 0.0, "metadata_seconds": 0.0, "solve_seconds": 0.0,
                               "validation_seconds": 0.0, "rhs_formation_seconds": 0.0,
                               "overhead_seconds": elapsed, "total_seconds": elapsed, "response_seconds": elapsed,
                               "cpu_seconds": time.process_time() - attempt_cpu, "preflight_qualified": False,
                               "qualified": False, "accepted_count": 0, "accepted_by_rhs": [False] * q,
                               "relative_residual_l2": [None] * q, "backward_error_linf": [None] * q,
                               "manufactured_forward_error_l2": [None] * q,
                               "error": type(error).__name__ + ": " + str(error),
                               "failed_cost_scope": "All attempt cost retained as overhead; inner stage decomposition unavailable"}
                        x = np.full_like(all_truth[:, :q], np.nan)
                    row.update({"phase": phase, "matrix": name, "matrix_index": index, "block": block,
                                "q": q, "seed": seed, "position": position, "rhs_generation_shared_seconds": generation_s,
                                "id": f"{phase}:{name}:{block}:{q}:{method}"})
                    rows.append(row)
                    with (output / "batches.jsonl").open("a") as handle:
                        handle.write(json.dumps(row, allow_nan=False) + "\n")
                    if block == 0 and q == 16:
                        np.savez_compressed(output / f"audit_{name}_{method}.npz", x=x[:, [0, 15]])
                if stopped:
                    break
            if stopped:
                break
        if stopped:
            break
        if budget_reached():
            stopped = True
            break
        truth = np.random.default_rng(base + 100 * index).standard_normal((a.shape[0], 16))[:, 0]
        b = a @ truth
        before, cpu = time.perf_counter(), time.process_time()
        preconditioner = LinearOperator(a.shape, matvec=lambda v: v / a.diagonal())
        try:
            x, info = cg(a, b, rtol=1e-10, atol=0.0, maxiter=400, M=preconditioner)
            check = quality(a, b, x, truth)
            diagnostic.append({"matrix": name, "info": int(info), "elapsed_seconds": time.perf_counter() - before,
                               "cpu_seconds": time.process_time() - cpu, **check,
                               "diagnostic_only": True, "qualified_solver_exit": bool(info == 0),
                               "overall_qualified": bool(info == 0 and check["qualified"])})
        except Exception as error:
            diagnostic.append({"matrix": name, "info": None, "elapsed_seconds": time.perf_counter() - before,
                               "cpu_seconds": time.process_time() - cpu, "diagnostic_only": True,
                               "overall_qualified": False, "error": type(error).__name__ + ": " + str(error)})
    summary = {"phase": phase, "issued_utc": phase_issued, "completed_utc": utc(),
               "source_sha256": source_hash(), "planned_batches": 4 * blocks * 3 * 3,
               "executed_batches": len(rows), "qualified_batches": sum(row["qualified"] for row in rows),
               "budget_stopped": stopped, "unexecuted_batches": 4 * blocks * 3 * 3 - len(rows),
               "prior_numerical_cpu_seconds": previous_cpu, "planned_diagnostics": 4,
               "executed_diagnostics": len(diagnostic),
               "wall_seconds": time.perf_counter() - phase_start, "cpu_seconds": time.process_time() - phase_cpu,
               "ingestion": ingestions, "cg_diagnostics": diagnostic,
               "environment": {"python": platform.python_version(), "platform": platform.platform(),
                               "scipy": scipy.__version__, "numpy": np.__version__,
                               "threadpools": json.loads(json.dumps(threadpool_info(), default=lambda value: {"unserializable_type": type(value).__name__}))}}
    write_json(output / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("phase", "executed_batches", "qualified_batches", "wall_seconds", "budget_stopped")}))


def freeze_forecasts() -> None:
    """Issue every prospective local prediction before opening any confirmation seed."""
    target = ROOT / "results/forecast_freeze.json"
    if target.exists() or (ROOT / "results/confirmation").exists():
        raise FileExistsError("Forecast freeze is immutable")
    calibration_path = ROOT / "results/calibration/batches.jsonl"
    rows = [json.loads(line) for line in calibration_path.read_text().splitlines()]
    expected = {(name, block, q, method) for name in P["matrices_in_order"]
                for block in range(N["calibration_blocks"]) for q in N["q_values"] for method in N["methods"]}
    actual = {(r["matrix"], r["block"], r["q"], r["method"]) for r in rows}
    if actual != expected or len(rows) != len(expected):
        raise ValueError("Incomplete or duplicate calibration; no prospective freeze permitted")
    calibration_summary = json.loads((ROOT / "results/calibration/summary.json").read_text())
    if calibration_summary["source_sha256"] != source_hash() or calibration_summary["budget_stopped"]:
        raise ValueError("Calibration source mismatch or budget stop")
    forecasts, primitives, labels = [], [], []
    for name in P["matrices_in_order"]:
        for q in N["q_values"]:
            scale = float(np.median([r["total_seconds"] for r in rows if r["matrix"] == name and r["q"] == q and r["method"] == "native_cached"]))
            for method in N["methods"]:
                chosen = [r for r in rows if r["matrix"] == name and r["q"] == q and r["method"] == method]
                for state in (["cold"] if method == "cold_direct" else ["cold", "ready"]):
                    column = "total_seconds" if state == "cold" else "response_seconds"
                    for multiplier in N["batch_deadline_multipliers"]:
                        deadline = scale * multiplier
                        outcomes = [int(r["qualified"] and r[column] <= deadline) for r in chosen]
                        labels.extend(outcomes)
                        forecasts.append({"matrix": name, "q": q, "method": method, "state": state,
                                          "deadline_multiplier": multiplier, "deadline_seconds": deadline,
                                          "probability": (sum(outcomes) + 1) / (len(outcomes) + 2),
                                          "calibration_n": len(outcomes), "calibration_successes": sum(outcomes)})
        cold = [r for r in rows if r["matrix"] == name and r["method"] == "cold_direct" and r["q"] == 16]
        ready = [r for r in rows if r["matrix"] == name and r["method"] == "certified_ready" and r["q"] == 16]
        values = {"build_samples_seconds": [r["factor_seconds"] + r["preflight_seconds"] + r["metadata_seconds"] for r in ready],
                  "cold_samples_seconds": [(r["factor_seconds"] + r["solve_seconds"] + r["overhead_seconds"] + r["rhs_formation_seconds"]) / 16 for r in cold],
                  "ready_samples_seconds": [(r["solve_seconds"] + r["overhead_seconds"] + r["rhs_formation_seconds"]) / 16 for r in ready],
                  "validation_samples_seconds": [r["validation_seconds"] / 16 for r in ready]}
        primitives.append({"matrix": name, **values,
                           **{key.replace("_samples", ""): float(np.median(value)) for key, value in values.items()},
                           "cold_success_rate": sum(r["accepted_count"] for r in cold) / (16 * len(cold)),
                           "ready_success_rate": sum(r["accepted_count"] for r in ready) / (16 * len(ready))})
    now = datetime.now(timezone.utc)
    write_json(target, {"schema": "prospective-local-forecasts/v1", "issued_utc": now.isoformat(),
                        "valid_launch_until_utc": (now + timedelta(minutes=30)).isoformat(),
                        "source_sha256": source_hash(), "protocol_sha256": digest((ROOT / "protocol.json").read_bytes()),
                        "data_manifest_sha256": digest((ROOT / "data/manifest.json").read_bytes()),
                        "calibration_sha256": digest(calibration_path.read_bytes()),
                        "base_probability": (sum(labels) + 1) / (len(labels) + 2), "forecasts": forecasts,
                        "target": "qualified local computation by actual execution start plus frozen elapsed deadline",
                        "external_adoption": "pending; no customer outcome generated"})
    write_json(ROOT / "results/primitives.json", {"source": "calibration only", "matrices": primitives})
    print(json.dumps({"forecasts": len(forecasts), "freeze_sha256": digest(target.read_bytes()), "issued_utc": now.isoformat()}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["development", "calibration", "confirmation", "freeze"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.phase == "freeze":
            freeze_forecasts()
        else:
            run_phase(args.phase, args.output or ROOT / "results" / args.phase)


if __name__ == "__main__":
    main()
