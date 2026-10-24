# SPDX-License-Identifier: Apache-2.0
"""Independent read-only audit; imports neither experiment module and runs no solver.

All recorded cells are checked for consistency. Algebraic errors are recomputed
only for saved block-0, q=16 first/last columns. This is independently authored
code under common control, not external replication or beneficiary acceptance.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import statistics
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import numpy as np
from scipy.io import mmread
from scipy.sparse import csr_matrix
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
ERRORS = ("relative_residual_l2", "backward_error_linf", "manufactured_forward_error_l2")
LIMITS = ("relative_residual_l2_max", "normwise_backward_error_linf_max", "manufactured_forward_error_l2_max")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def instant(text: str) -> datetime:
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Timestamp lacks timezone")
    return value


class Audit:
    def __init__(self) -> None:
        self.checks = 0
        self.failures: list[str] = []
        self.notes: list[str] = []

    def require(self, condition: Any, label: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(label)

    def number(self, actual: float, expected: float, label: str, rel: float = 2e-10, absolute: float = 1e-12) -> None:
        self.require(math.isfinite(actual) and math.isfinite(expected) and math.isclose(actual, expected, rel_tol=rel, abs_tol=absolute), label)


def independent_matrix(root: Path, entry: dict[str, Any], audit: Audit) -> csr_matrix:
    path = root / "data" / entry.get("file", entry["name"] + ".tar.gz")
    raw = path.read_bytes()
    audit.require(hashlib.sha256(raw).hexdigest() == entry["archive_sha256"], entry["name"] + ": archive hash")
    if path.name.endswith(".tar.gz"):
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            member = archive.getmember(entry["name"] + "/" + entry["name"] + ".mtx")
            if not member.isfile():
                raise ValueError("Matrix archive member is not regular")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError("Matrix archive member missing")
            payload = handle.read()
    else:
        payload = gzip.decompress(raw) if path.suffix == ".gz" else raw
    audit.require(hashlib.sha256(payload).hexdigest() == entry["matrix_sha256"], entry["name"] + ": payload hash")
    matrix = csr_matrix(mmread(io.BytesIO(payload)), dtype=np.float64)
    matrix.sum_duplicates()
    matrix.eliminate_zeros()
    matrix.sort_indices()
    audit.require(matrix.shape == (entry["rows"], entry["rows"]), entry["name"] + ": dimensions")
    audit.require(matrix.nnz == entry["nnz"], entry["name"] + ": nonzeros")
    audit.require(bool(np.isfinite(matrix.data).all()), entry["name"] + ": finite entries")
    return matrix


def independent_errors(matrix: csr_matrix, known: np.ndarray, saved: np.ndarray) -> dict[str, list[float]]:
    """CSR products and scalar sums independently implement the three criteria."""
    right = matrix @ known
    norm_a = float(max(np.asarray(abs(matrix).sum(axis=1)).ravel()))
    values: dict[str, list[float]] = {key: [] for key in ERRORS}
    for index, column in enumerate((0, 15)):
        x, b = saved[:, index], right[:, column]
        residual, difference = b - matrix.dot(x), x - known[:, column]
        def length(v: np.ndarray) -> float:
            return math.sqrt(math.fsum(float(t) * float(t) for t in v))
        tiny = np.finfo(float).tiny
        denominator = norm_a * max(abs(x)) + max(abs(b))
        values["relative_residual_l2"].append(length(residual) / max(length(b), tiny))
        values["backward_error_linf"].append(float(max(abs(residual))) / max(float(denominator), tiny))
        values["manufactured_forward_error_l2"].append(length(difference) / max(length(known[:, column]), tiny))
    return values


def check_phase(root: Path, phase: str, audit: Audit) -> dict[str, Any]:
    protocol = read_json(root / "protocol.json")
    design = protocol["numerical_design"]
    directory = root / "results" / phase
    summary, rows = read_json(directory / "summary.json"), read_rows(directory / "batches.jsonl")
    matrices = read_json(root / "data/manifest.json")["matrices"]
    matrix_hashes = {entry["name"]: entry["matrix_sha256"] for entry in matrices}
    phase_issued, phase_completed = instant(summary["issued_utc"]), instant(summary["completed_utc"])
    audit.require(phase_issued <= phase_completed, phase + ": phase timestamp order")
    for field in ("wall_seconds", "cpu_seconds"):
        audit.require(math.isfinite(summary[field]) and summary[field] >= 0, phase + ": nonnegative " + field)
    blocks = 1 if phase == "development" else design[phase + "_blocks"]
    base = design["development_seed"] if phase == "development" else design[phase + "_seed_base"]
    names, methods, qs = protocol["matrices_in_order"], design["methods"], design["q_values"]
    expected = {(name, block, q, method) for name in names for block in range(blocks) for q in qs for method in methods}
    actual = [(r["matrix"], r["block"], r["q"], r["method"]) for r in rows]
    audit.require(len(actual) == len(set(actual)), phase + ": no duplicate cells")
    audit.require(set(actual) <= expected, phase + ": no unplanned cells")
    audit.require(summary["executed_batches"] == len(rows), phase + ": executed count")
    audit.require(summary["planned_batches"] == len(expected), phase + ": planned count")
    audit.require(summary["unexecuted_batches"] == len(expected - set(actual)), phase + ": unexecuted count")
    if not summary["budget_stopped"]:
        audit.require(set(actual) == expected, phase + ": every planned cell retained")
    audit.require(summary["qualified_batches"] == sum(bool(r["qualified"]) for r in rows), phase + ": qualified count")
    audit.require(summary["source_sha256"] == sha(root / "numerics.py"), phase + ": source unchanged")
    shared_rng: dict[tuple[str, int], float] = {}
    lookup = dict(zip(actual, rows))
    components: Counter[str] = Counter()
    for row in rows:
        label = row["id"]
        name, block, q, method = row["matrix"], row["block"], row["q"], row["method"]
        index = names.index(name)
        seed = base + 100 * index + block
        audit.require(row["phase"] == phase, label + ": phase")
        audit.require(row["matrix_sha256"] == matrix_hashes[name], label + ": exact matrix digest")
        audit.require(row["seed"] == seed and row["matrix_index"] == index, label + ": workload seed")
        audit.require(label == f"{phase}:{name}:{block}:{q}:{method}", label + ": canonical id")
        order = np.random.default_rng(design["order_seed"] + seed + q).permutation(methods).tolist()
        audit.require(order[row["position"]] == method, label + ": randomized order")
        audit.require(instant(row["issued_utc"]) <= instant(row["completed_utc"]), label + ": timestamp order")
        audit.require(phase_issued <= instant(row["issued_utc"]) <= instant(row["completed_utc"]) <= phase_completed, label + ": interval within phase")
        accepted = row["accepted_by_rhs"]
        audit.require(len(accepted) == q and all(type(x) is bool for x in accepted), label + ": acceptance shape")
        computed = []
        for j in range(q):
            values = [row[key][j] for key in ERRORS]
            computed.append(all(x is not None and math.isfinite(x) and 0 <= x <= design["acceptance"][limit] for x, limit in zip(values, LIMITS)))
        audit.require(accepted == computed, label + ": threshold acceptance")
        audit.require(row["accepted_count"] == sum(accepted), label + ": accepted count")
        audit.require(row["qualified"] == all(accepted), label + ": qualified flag")
        if method == "certified_ready" and row["qualified"]:
            audit.require(row["preflight_qualified"] is True, label + ": required preflight")
        keys = ["factor_seconds", "preflight_seconds", "metadata_seconds", "solve_seconds", "validation_seconds", "overhead_seconds"]
        if "rhs_formation_seconds" in row:
            keys.append("rhs_formation_seconds")
        for key in keys + ["response_seconds", "total_seconds", "cpu_seconds"]:
            audit.require(math.isfinite(row[key]) and row[key] >= -1e-12, label + ": nonnegative " + key)
        audit.number(row["total_seconds"], math.fsum(row[k] for k in keys), label + ": timing partition")
        audit.require(row["response_seconds"] <= row["total_seconds"] + 1e-12, label + ": response bounded by paid total")
        if method == "cold_direct":
            audit.number(row["response_seconds"], row["total_seconds"], label + ": cold response includes setup")
        if "setup_seconds" in row:
            audit.number(row["setup_seconds"] + row["response_seconds"], row["total_seconds"], label + ": paid setup")
        shared_key, cost = (name, block), row["rhs_generation_shared_seconds"]
        audit.require(math.isfinite(cost) and cost >= 0, label + ": nonnegative shared generation cost")
        if shared_key in shared_rng:
            audit.number(shared_rng[shared_key], cost, label + ": shared generation cost")
        else:
            shared_rng[shared_key] = cost
        components.update({key: row[key] for key in keys})
    samples = []
    for entry in matrices:
        name = entry["name"]
        matrix = independent_matrix(root, entry, audit)
        known = np.random.default_rng(base + 100 * names.index(name)).standard_normal((matrix.shape[0], 16))
        for method in methods:
            row = lookup.get((name, 0, 16, method))
            if row is None:
                audit.notes.append(f"No sample for unexecuted cell {phase}:{name}:0:16:{method}")
                continue
            path = directory / f"audit_{name}_{method}.npz"
            with np.load(path, allow_pickle=False) as archive:
                saved = archive["x"]
            audit.require(saved.shape == (matrix.shape[0], 2), f"{name}:{method}: saved shape")
            finite = bool(np.isfinite(saved).all())
            if not finite:
                audit.require(not row["qualified"], f"{name}:{method}: nonfinite rejected")
                samples.append({"matrix": name, "method": method, "sha256": sha(path), "finite": False, "qualified": False})
                continue
            errors = independent_errors(matrix, known, saved)
            for j, column in enumerate((0, 15)):
                qualified = all(errors[key][j] <= design["acceptance"][limit] for key, limit in zip(ERRORS, LIMITS))
                audit.require(bool(row["accepted_by_rhs"][column]) == qualified, f"{name}:{method}:{column}: independently qualified")
                for field in ERRORS:
                    logged = row[field][column]
                    audit.require(logged is not None, f"{name}:{method}:{column}: finite metric logged")
                    if logged is not None:
                        # CSR/CSC summation order differs at machine precision.
                        audit.number(logged, errors[field][j], f"{name}:{method}:{column}: independent {field}", rel=0.1, absolute=1e-14 if field != "manufactured_forward_error_l2" else 1e-15)
            samples.append({"matrix": name, "method": method, "sha256": sha(path), "finite": True, **errors})
    batch_total = math.fsum(r["total_seconds"] for r in rows)
    ingestion = math.fsum(x["read_hash_parse_seconds"] for x in summary["ingestion"])
    audit.require(all(math.isfinite(x["read_hash_parse_seconds"]) and x["read_hash_parse_seconds"] >= 0 for x in summary["ingestion"]), phase + ": nonnegative ingestion costs")
    generation = math.fsum(shared_rng.values())
    diagnostic_wall = math.fsum(x["elapsed_seconds"] for x in summary["cg_diagnostics"])
    diagnostic_cpu = math.fsum(x["cpu_seconds"] for x in summary["cg_diagnostics"])
    audit.require(all(math.isfinite(x[k]) and x[k] >= 0 for x in summary["cg_diagnostics"] for k in ("elapsed_seconds", "cpu_seconds")), phase + ": nonnegative diagnostic costs")
    audit.require(batch_total + ingestion + generation + diagnostic_wall <= summary["wall_seconds"] + 1e-9, phase + ": all disjoint timed components fit phase wall")
    audit.require(math.fsum(r["cpu_seconds"] for r in rows) + diagnostic_cpu <= summary["cpu_seconds"] + 1e-9, phase + ": all disjoint measured CPU fits phase total")
    return {"name": phase, "rows": len(rows), "planned_rows": len(expected), "logged_rhs_checks": sum(r["q"] for r in rows),
            "algebraically_recomputed_columns": 2 * len(samples), "retained_failed_batches": sum(not r["qualified"] for r in rows),
            "phase_wall_seconds": summary["wall_seconds"], "phase_cpu_seconds": summary["cpu_seconds"],
            "sum_batch_seconds": batch_total, "sum_batch_components": dict(components), "unique_rhs_generation_seconds": generation,
            "ingestion_seconds": ingestion, "diagnostic_wall_seconds": diagnostic_wall, "diagnostic_cpu_seconds": diagnostic_cpu,
            "campaign_wall_outside_batches_rng_ingestion_seconds": summary["wall_seconds"] - batch_total - generation - ingestion,
            "samples": samples, "batches_sha256": sha(directory / "batches.jsonl"), "summary_sha256": sha(directory / "summary.json")}


def check_forecasts(root: Path, audit: Audit) -> dict[str, Any]:
    protocol = read_json(root / "protocol.json")
    design = protocol["numerical_design"]
    frozen = read_json(root / "results/forecast_freeze.json")
    calibration, confirmation = [read_rows(root / "results" / phase / "batches.jsonl") for phase in ("calibration", "confirmation")]
    for key, path in (("source_sha256", "numerics.py"), ("protocol_sha256", "protocol.json"), ("calibration_sha256", "results/calibration/batches.jsonl")):
        audit.require(frozen[key] == sha(root / path), "forecast: " + key)
    manifest_key = next((key for key in ("data_manifest_sha256", "manifest_sha256") if key in frozen), None)
    audit.require(manifest_key is not None, "forecast: data manifest bound")
    if manifest_key:
        audit.require(frozen[manifest_key] == sha(root / "data/manifest.json"), "forecast: data manifest hash")
    issued = instant(frozen["issued_utc"])
    audit.require(all(instant(r["completed_utc"]) <= issued for r in calibration), "forecast: calibration precedes freeze")
    audit.require(all(issued < instant(r["issued_utc"]) for r in confirmation), "forecast: freeze precedes every confirmation cell")
    summary = read_json(root / "results/confirmation/summary.json")
    audit.require(issued < instant(summary["issued_utc"]), "forecast: phase begins after freeze")
    audit.require(instant(summary["issued_utc"]) <= instant(frozen["valid_launch_until_utc"]), "forecast: launch window")
    audit.require(min(instant(r["issued_utc"]) for r in confirmation) <= instant(frozen["valid_launch_until_utc"]), "forecast: first actual batch within launch window")
    audit.require({r["seed"] for r in calibration}.isdisjoint({r["seed"] for r in confirmation}), "forecast: disjoint seeds")
    expected = {(name, q, method, state, multiplier) for name in protocol["matrices_in_order"] for q in design["q_values"] for method in design["methods"] for state in (["cold"] if method == "cold_direct" else ["cold", "ready"]) for multiplier in design["batch_deadline_multipliers"]}
    actual = [(f["matrix"], f["q"], f["method"], f["state"], f["deadline_multiplier"]) for f in frozen["forecasts"]]
    audit.require(set(actual) == expected and len(actual) == len(expected), "forecast: exact planned targets")
    labels, outcomes, scores, base_scores = [], [], [], []
    bins: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for f in frozen["forecasts"]:
        chosen = [r for r in calibration if (r["matrix"], r["q"], r["method"]) == (f["matrix"], f["q"], f["method"])]
        reference = [r["total_seconds"] for r in calibration if (r["matrix"], r["q"], r["method"]) == (f["matrix"], f["q"], "native_cached")]
        audit.number(f["deadline_seconds"], statistics.median(reference) * f["deadline_multiplier"], "forecast: calibration deadline")
        column = "total_seconds" if f["state"] == "cold" else "response_seconds"
        success = [int(r["qualified"] and r[column] <= f["deadline_seconds"]) for r in chosen]
        labels.extend(success)
        audit.require(len(chosen) == design["calibration_blocks"] == f["calibration_n"], "forecast: calibration size")
        audit.require(sum(success) == f["calibration_successes"], "forecast: success count")
        audit.number(f["probability"], (sum(success) + 1) / (len(success) + 2), "forecast: Beta estimate")
        for row in confirmation:
            if (row["matrix"], row["q"], row["method"]) != (f["matrix"], f["q"], f["method"]):
                continue
            event = int(row["qualified"] and row[column] <= f["deadline_seconds"])
            outcomes.append(event)
            scores.append((f["probability"] - event) ** 2)
            base_scores.append((frozen["base_probability"] - event) ** 2)
            bins[min(9, int(f["probability"] * 10))].append((f["probability"], event))
    audit.number(frozen["base_probability"], (sum(labels) + 1) / (len(labels) + 2), "forecast: pooled constant")
    return {"freeze_sha256": sha(root / "results/forecast_freeze.json"), "issued_utc": frozen["issued_utc"],
            "targets": len(frozen["forecasts"]), "correlated_binary_evaluations": len(outcomes), "brier": statistics.fmean(scores),
            "constant_base_brier": statistics.fmean(base_scores), "event_fraction": statistics.fmean(outcomes),
            "scope": "Local runtime only. Overlapping deadlines, states and q-prefixes are correlated; not independent sample size.",
            "reliability_bins": [{"bin": key, "n": len(values), "mean_forecast": statistics.fmean(p for p, _ in values), "event_fraction": statistics.fmean(y for _, y in values)} for key, values in sorted(bins.items())]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE)
    parser.add_argument("--phase", choices=("development", "calibration", "confirmation"), default="confirmation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = Audit()
    result = {"schema": "writer9-independent-numerical-audit/v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "checker_sha256": sha(Path(__file__)), "runner_imported": False,
              "scope": "Independently authored checker under common operator/environment; no external replication or timestamp authority."}
    with threadpool_limits(limits=1):
        result["phase"] = check_phase(args.root, args.phase, audit)
        if args.phase == "confirmation":
            result["forecasts"] = check_forecasts(args.root, audit)
    result.update({"checks": audit.checks, "passed": not audit.failures, "failures": audit.failures, "notes": audit.notes})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "checks": audit.checks, "failures": audit.failures, "output": str(args.output)}))
    if audit.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
