# SPDX-License-Identifier: Apache-2.0
"""Experience-trained, residual-corrected reduced PDE solver and sensor relay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

for _thread_var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_var] = "1"

import numpy as np
import scipy
from scipy import sparse
from scipy.fft import dstn, idstn
from scipy.linalg import solve as dense_solve
from scipy.sparse.linalg import LinearOperator, cg, gmres, spilu, splu
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
N = 44
RAW_RESIDUAL = 2e-3
RAW_ERROR = 2e-4
FINAL_RESIDUAL = 2e-8
FINAL_ERROR = 2e-6


def digest(path: Path) -> str:
    """Return the SHA-256 identity of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Write stable human-readable research records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


class Diffusion:
    """Finite-difference heterogeneous diffusion on a unit square, zero boundary."""

    def __init__(self, n: int = N):
        self.n = n
        self.h = 1 / (n + 1)
        xy = np.arange(1, n + 1) * self.h
        self.x, self.y = np.meshgrid(xy, xy, indexing="ij")
        edge = (np.arange(n + 1) + 0.5) * self.h
        ex, ey = np.meshgrid(edge, xy, indexing="ij")
        fx, fy = np.meshgrid(xy, edge, indexing="ij")
        self.wx = np.exp(-((ex - 0.63) ** 2 + (ey - 0.42) ** 2) / 0.035)
        self.wy = np.exp(-((fx - 0.63) ** 2 + (fy - 0.42) ** 2) / 0.035)
        self.reaction = 1 + 0.5 * np.sin(np.pi * self.x) * np.sin(np.pi * self.y)
        self.parts = [
            self._matrix(np.ones_like(self.wx), np.zeros_like(self.wy)),
            self._matrix(np.zeros_like(self.wx), np.ones_like(self.wy)),
            self._matrix(self.wx, self.wy),
            sparse.diags(self.reaction.ravel(), format="csc"),
        ]
        self.eigen = 4 * np.sin(np.pi * np.arange(1, n + 1) / (2 * (n + 1))) ** 2 / self.h**2

    def _matrix(self, ax: np.ndarray, ay: np.ndarray) -> sparse.csc_matrix:
        n = self.n
        idx = np.arange(n * n).reshape(n, n)
        diagonal = (ax[:-1] + ax[1:] + ay[:, :-1] + ay[:, 1:]).ravel() / self.h**2
        rows = [idx.ravel()]
        cols = [idx.ravel()]
        vals = [diagonal]
        for a, i, j in ((ax[1:-1], idx[:-1], idx[1:]), (ay[:, 1:-1], idx[:, :-1], idx[:, 1:])):
            rows.extend([i.ravel(), j.ravel()])
            cols.extend([j.ravel(), i.ravel()])
            vals.extend([-a.ravel() / self.h**2, -a.ravel() / self.h**2])
        return sparse.coo_matrix(
            (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n * n, n * n)
        ).tocsc()

    def matrix(self, spec: dict[str, Any]) -> sparse.csc_matrix:
        return sum((float(c) * a for c, a in zip(spec["theta"], self.parts)), sparse.csc_matrix((self.n**2, self.n**2)))

    def source(self, spec: dict[str, Any]) -> np.ndarray:
        cx, cy, width, secondary = spec["source"]
        g = np.exp(-((self.x - cx) ** 2 + (self.y - cy) ** 2) / (2 * width**2))
        g += secondary * np.sin(np.pi * self.x) * np.sin(2 * np.pi * self.y)
        return g.ravel()

    def check_residual(self, spec: dict[str, Any], solution: np.ndarray, rhs: np.ndarray) -> float:
        """Compute the discrete residual by an independent flux stencil."""
        kx, ky, contrast, reaction = spec["theta"]
        z = np.pad(solution.reshape(self.n, self.n), 1)
        u = z[1:-1, 1:-1]
        ax, ay = kx + contrast * self.wx, ky + contrast * self.wy
        r = ax[:-1] * (u - z[:-2, 1:-1]) + ax[1:] * (u - z[2:, 1:-1])
        r += ay[:, :-1] * (u - z[1:-1, :-2]) + ay[:, 1:] * (u - z[1:-1, 2:])
        r = r / self.h**2 + reaction * self.reaction * u - rhs.reshape(self.n, self.n)
        return float(np.linalg.norm(r) / max(np.linalg.norm(rhs), 1e-30))

    def preconditioner(self, spec: dict[str, Any]) -> LinearOperator:
        """Apply a separable SPD inverse using a discrete sine transform."""
        kx, ky, contrast, reaction = spec["theta"]
        avg = contrast * (self.wx.mean() + self.wy.mean()) / 2
        denominator = (
            (kx + avg) * self.eigen[:, None] + (ky + avg) * self.eigen[None, :] + reaction * self.reaction.mean()
        )

        def apply(v: np.ndarray) -> np.ndarray:
            return idstn(
                dstn(v.reshape(self.n, self.n), type=1, norm="ortho") / denominator, type=1, norm="ortho"
            ).ravel()

        return LinearOperator((self.n**2, self.n**2), matvec=apply)


def sample(seed: int, count: int, family: str) -> list[dict[str, Any]]:
    """Generate cases without referring to a learned artifact or its outcomes."""
    rng = np.random.default_rng(seed)
    cases = []
    for i in range(count):
        if family == "thermal":
            theta = [rng.uniform(0.8, 2), rng.uniform(0.8, 2), rng.uniform(0, 1), rng.uniform(0, 3)]
            src = [rng.uniform(0.36, 0.64), rng.uniform(0.36, 0.64), rng.uniform(0.17, 0.24), 0.0]
        elif family == "transfer":
            theta = [rng.uniform(0.4, 3.5), rng.uniform(0.4, 3.5), rng.uniform(0, 3), rng.uniform(0, 14)]
            src = [rng.uniform(0.22, 0.78), rng.uniform(0.22, 0.78), rng.uniform(0.11, 0.23), rng.uniform(-0.25, 0.25)]
        elif family == "ood":
            theta = [rng.uniform(0.08, 0.25), rng.uniform(5, 9), rng.uniform(5, 12), rng.uniform(20, 50)]
            src = [rng.uniform(0.08, 0.92), rng.uniform(0.08, 0.92), rng.uniform(0.025, 0.055), rng.uniform(-0.6, 0.6)]
        else:
            raise ValueError(f"Unknown family {family}")
        cases.append({"case_id": f"{family}-{seed}-{i}", "family": family, "theta": theta, "source": src})
    return cases


def orthogonal_append(basis: np.ndarray, value: np.ndarray) -> np.ndarray:
    """Update a reusable numeric basis using observed solved fields."""
    residual = value.copy()
    for _ in range(2):
        residual -= basis @ (basis.T @ residual)
    norm = np.linalg.norm(residual)
    if norm < 1e-13 * max(np.linalg.norm(value), 1e-30):
        return basis
    return np.column_stack((basis, residual / norm))


class Reduced:
    """A numerical checkpoint and its online affine projected operators."""

    def __init__(self, domain: Diffusion, basis: np.ndarray):
        self.basis = basis
        self.projected = [basis.T @ (a @ basis) for a in domain.parts]

    def raw(self, spec: dict[str, Any], rhs: np.ndarray) -> np.ndarray:
        matrix = sum(c * a for c, a in zip(spec["theta"], self.projected))
        coeff = dense_solve(matrix, self.basis.T @ rhs, assume_a="pos", check_finite=False)
        return self.basis @ coeff


class ResidualGym:
    """A finite experience environment with explicit observations and budgets."""

    def __init__(self, domain: Diffusion, initial: np.ndarray, pool: list[dict[str, Any]], budget: int = 32):
        if type(budget) is not int or not 1 <= budget <= 32 or len(pool) < budget:
            raise ValueError("A Gym campaign requires 1..32 actions and enough distinct training cases")
        self.domain, self.initial, self.pool, self.budget = domain, initial.copy(), pool, budget
        self.reset()

    def reset(self) -> dict[str, Any]:
        self.basis = self.initial.copy()
        self.available = list(range(len(self.pool)))
        self.remaining = self.budget
        self.history: list[dict[str, Any]] = []
        return {"remaining_actions": self.remaining, "rank": self.basis.shape[1], "terminated": False}

    def observe(self) -> dict[str, Any]:
        if self.remaining == 0:
            return {"remaining_actions": 0, "terminated": True, "candidate_indices": [], "residuals": []}
        model = Reduced(self.domain, self.basis)
        scores = [
            self.domain.check_residual(
                self.pool[i],
                model.raw(self.pool[i], self.domain.source(self.pool[i])),
                self.domain.source(self.pool[i]),
            )
            for i in self.available
        ]
        return {
            "remaining_actions": self.remaining,
            "terminated": False,
            "candidate_indices": self.available.copy(),
            "residuals": scores,
            "rank": self.basis.shape[1],
        }

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        if self.remaining <= 0:
            raise ValueError("Gym terminated: action budget exhausted")
        if (
            action.get("kind") != "solve_and_enrich"
            or type(action.get("index")) is not int
            or action.get("index") not in self.available
        ):
            raise ValueError("Action is not an available training-pool solve")
        chosen = int(action["index"])
        value, solve_s = reference_solve(self.domain, self.pool[chosen])
        tick = time.perf_counter()
        self.basis = orthogonal_append(self.basis, value)
        update_s = time.perf_counter() - tick
        self.available.remove(chosen)
        self.remaining -= 1
        receipt = {
            "selected_case": self.pool[chosen],
            "solve_s": solve_s,
            "update_s": update_s,
            "rank": self.basis.shape[1],
            "remaining_actions": self.remaining,
            "terminated": self.remaining == 0,
            "action": action,
        }
        self.history.append(receipt)
        return receipt


def execute(
    domain: Diffusion,
    spec: dict[str, Any],
    method: str,
    reduced: Reduced | None,
    reference: np.ndarray,
    reference_s: float,
) -> tuple[dict[str, Any], np.ndarray]:
    """Execute one method, charge setup and verify with the separate stencil."""
    started = time.perf_counter()
    cpu_started = time.process_time()
    used_method = method
    if method == "improved_generalist":
        used_method = "direct" if min(spec["theta"][:2]) < 0.3 or spec["theta"][2] > 4 else "spectral_pcg"
    matrix, rhs = domain.matrix(spec), domain.source(spec)
    assembly_s = time.perf_counter() - started
    setup_s, iterations, raw = 0.0, 0, None

    def step(_: Any) -> None:
        nonlocal iterations
        iterations += 1

    solve_start = time.perf_counter()
    info = 0
    if used_method == "direct":
        tick = time.perf_counter()
        factor = splu(matrix)
        setup_s = time.perf_counter() - tick
        solution = factor.solve(rhs)
    elif used_method == "ilu_gmres":
        tick = time.perf_counter()
        factor = spilu(matrix, drop_tol=1e-3, fill_factor=8)
        preconditioner = LinearOperator(matrix.shape, factor.solve)
        setup_s = time.perf_counter() - tick
        solution, info = gmres(
            matrix,
            rhs,
            M=preconditioner,
            rtol=1e-10,
            atol=0,
            restart=40,
            maxiter=15,
            callback=step,
            callback_type="pr_norm",
        )
    elif used_method in {"spectral_pcg", "v1", "v2"}:
        tick = time.perf_counter()
        preconditioner = domain.preconditioner(spec)
        setup_s = time.perf_counter() - tick
        initial = None
        if reduced is not None:
            raw = reduced.raw(spec, rhs)
            initial = raw
        solution, info = cg(matrix, rhs, x0=initial, M=preconditioner, rtol=1e-10, atol=0, maxiter=600, callback=step)
    else:
        raise ValueError(method)
    solve_s = time.perf_counter() - solve_start - setup_s
    tick = time.perf_counter()
    residual = domain.check_residual(spec, solution, rhs)
    kx, ky, _, reaction = spec["theta"]
    coercivity = (kx + ky) * domain.eigen[0] + reaction * float(domain.reaction.min())
    error_bound = residual * float(np.linalg.norm(rhs)) / coercivity
    certified_denominator = float(np.linalg.norm(solution)) - error_bound
    relative_bound = error_bound / certified_denominator if certified_denominator > 0 else None
    verify_s = time.perf_counter() - tick
    complete_cpu_s = time.process_time() - cpu_started
    error = float(np.linalg.norm(solution - reference) / max(np.linalg.norm(reference), 1e-30))
    raw_residual = domain.check_residual(spec, raw, rhs) if raw is not None else None
    raw_error = float(np.linalg.norm(raw - reference) / np.linalg.norm(reference)) if raw is not None else None
    row = {
        "case_id": spec["case_id"],
        "family": spec["family"],
        "method": method,
        "solver_implementation": used_method,
        "assembly_s": assembly_s,
        "setup_s": setup_s,
        "solve_s": solve_s,
        "verify_s": verify_s,
        "complete_s": assembly_s + setup_s + solve_s + verify_s,
        "complete_cpu_s": complete_cpu_s,
        "assessment_reference_s": reference_s,
        "iterations": iterations,
        "relative_residual": residual,
        "relative_error": error,
        "discrete_absolute_error_bound": error_bound,
        "discrete_relative_error_bound": relative_bound,
        "coercivity_lower_bound": coercivity,
        "accepted": bool(info == 0 and residual <= FINAL_RESIDUAL and error <= FINAL_ERROR),
        "raw_relative_residual": raw_residual,
        "raw_relative_error": raw_error,
        "raw_accepted": bool(raw is not None and raw_residual <= RAW_RESIDUAL and raw_error <= RAW_ERROR),
        "fallback": False,
        "correction_used": bool(raw is not None),
        "solver_info": int(info),
        "grid_n": domain.n,
        "degrees_of_freedom": domain.n**2,
        "reference_is_research_assessment": True,
    }
    return row, solution


def reference_solve(domain: Diffusion, spec: dict[str, Any]) -> tuple[np.ndarray, float]:
    tick = time.perf_counter()
    value = splu(domain.matrix(spec)).solve(domain.source(spec))
    return value, time.perf_counter() - tick


def evaluate(
    domain: Diffusion,
    cases: list[dict[str, Any]],
    artifacts: dict[str, Reduced],
    split: str,
    methods: list[str] | None = None,
    solution_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Pair all methods on identical cases, rotating execution order."""
    methods = methods or ["direct", "ilu_gmres", "spectral_pcg", "v1", "v2", "improved_generalist"]
    rows, solutions = [], {}
    for index, spec in enumerate(cases):
        reference, ref_s = reference_solve(domain, spec)
        if solution_path is not None:
            solutions[spec["case_id"] + "__reference"] = reference
        order = methods[index % len(methods) :] + methods[: index % len(methods)]
        for method in order:
            row, value = execute(domain, spec, method, artifacts.get(method), reference, ref_s)
            row["split"] = split
            rows.append(row)
            if solution_path is not None:
                solutions[spec["case_id"] + "__" + method] = value
    if solution_path is not None:
        np.savez_compressed(solution_path, **solutions)
    return rows


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize complete-case results without excluding failures."""
    result = {}
    for method in sorted({r["method"] for r in rows}):
        select = [r for r in rows if r["method"] == method]
        result[method] = {
            "count": len(select),
            "accepted": sum(r["accepted"] for r in select),
            "mean_complete_s": float(np.mean([r["complete_s"] for r in select])),
            "total_complete_s": sum(r["complete_s"] for r in select),
            "mean_iterations": float(np.mean([r["iterations"] for r in select])),
            "raw_accepted": sum(r["raw_accepted"] for r in select),
            "mean_raw_error": float(
                np.mean([r["raw_relative_error"] for r in select if r["raw_relative_error"] is not None])
            )
            if any(r["raw_relative_error"] is not None for r in select)
            else None,
        }
    return result


def train(domain: Diffusion, out: Path) -> dict[str, Any]:
    """Develop numeric checkpoints from founder work and bounded residual practice."""
    artifacts_dir = out / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    basis = np.empty((domain.n**2, 0))
    records, founder_fields, founder_receipts = [], [], []
    paid_s, gym_s, paid_cpu_s, gym_cpu_s = 0.0, 0.0, 0.0, 0.0
    founder = sample(2026102701, 12, "thermal")
    for spec in founder:
        tick = time.perf_counter()
        cpu_tick = time.process_time()
        value, solve_s = reference_solve(domain, spec)
        basis = orthogonal_append(basis, value)
        residual = domain.check_residual(spec, value, domain.source(spec))
        total = time.perf_counter() - tick
        cpu_total = time.process_time() - cpu_tick
        paid_s += total
        paid_cpu_s += cpu_total
        founder_fields.append(value)
        founder_receipts.append(
            {
                "case_id": spec["case_id"],
                "max_discrete_temperature": float(value.max()),
                "mean_discrete_temperature": float(value.mean()),
                "relative_residual": residual,
                "accepted": bool(residual <= FINAL_RESIDUAL),
            }
        )
        records.append(
            {
                "stage": "paid_founder",
                "rank": basis.shape[1],
                "selected_case": spec,
                "solve_s": solve_s,
                "update_and_verify_s": total - solve_s,
                "total_s": total,
                "cpu_s": cpu_total,
            }
        )
    save_tick = time.perf_counter()
    np.save(artifacts_dir / "v1.npy", basis)
    np.save(artifacts_dir / "founder_fields.npy", np.stack(founder_fields))
    founder_artifact_write_s = time.perf_counter() - save_tick
    paid_s += founder_artifact_write_s
    write_json(
        out / "founder_mission.json",
        {
            "beneficiary": "Scientific software engineer commissioning a reusable thermal response solver",
            "deliverable": "Verified discrete temperature fields and response envelope for twelve specified operating scenarios",
            "acceptance": "All input scenarios solved, no boundary or source requirement changed, independent relative residual <=2e-8",
            "physical_scope": "Computational model only; no measured material data, real customer or physical product",
            "records": founder_receipts,
            "fields_file": "artifacts/founder_fields.npy",
            "basis_retained_after_delivery": "artifacts/v1.npy",
            "total_delivery_and_update_s": paid_s,
        },
    )
    pool = sample(2026102702, 72, "transfer")
    gym = ResidualGym(domain, basis, pool)
    checkpoints = []
    for _ in range(32):
        tick = time.perf_counter()
        cpu_tick = time.process_time()
        observation = gym.observe()
        chosen_position = int(np.argmax(observation["residuals"]))
        chosen = observation["candidate_indices"][chosen_position]
        score = observation["residuals"][chosen_position]
        receipt = gym.step({"kind": "solve_and_enrich", "index": chosen})
        solve_s, basis = receipt["solve_s"], gym.basis
        total = time.perf_counter() - tick
        gym_s += total
        cpu_total = time.process_time() - cpu_tick
        gym_cpu_s += cpu_total
        rank = basis.shape[1]
        records.append(
            {
                "stage": "gym",
                "rank": rank,
                "selected_case": pool[chosen],
                "observation_residual": score,
                "observations": len(observation["residuals"]),
                "solve_s": solve_s,
                "update_and_observation_s": total - solve_s,
                "total_s": total,
                "cpu_s": cpu_total,
                "remaining_actions": receipt["remaining_actions"],
                "terminated": receipt["terminated"],
            }
        )
        if rank in [20, 28, 36, 44]:
            np.save(artifacts_dir / f"candidate-r{rank}.npy", basis)
            checkpoints.append(rank)
    write_json(
        out / "training.json",
        {
            "records": records,
            "founder_cases": founder,
            "gym_pool": pool,
            "paid_founder_snapshot_s": paid_s,
            "extra_gym_s": gym_s,
            "paid_founder_cpu_s": paid_cpu_s,
            "extra_gym_cpu_s": gym_cpu_s,
            "founder_artifact_write_s": founder_artifact_write_s,
            "candidate_ranks": checkpoints,
            "training_algorithm": "max-residual greedy enrichment",
        },
    )
    return {
        "paid_founder_snapshot_s": paid_s,
        "extra_gym_s": gym_s,
        "candidate_ranks": checkpoints,
        "paid_founder_cpu_s": paid_cpu_s,
        "extra_gym_cpu_s": gym_cpu_s,
        "founder_artifact_write_s": founder_artifact_write_s,
    }


def greedy_sensors(fields: np.ndarray, count: int) -> tuple[np.ndarray, float]:
    """Choose sensor locations from candidate field variability, without truth."""
    tick = time.perf_counter()
    centered = fields - fields.mean(axis=1, keepdims=True)
    u, s, _ = np.linalg.svd(centered, full_matrices=False)
    features = u[:, :6] * s[:6]
    features /= max(float(np.linalg.norm(features)), 1e-30)
    info = np.eye(features.shape[1]) * 1e-6
    chosen: list[int] = []
    for _ in range(count):
        scores = np.sum((features @ np.linalg.inv(info)) * features, axis=1)
        if chosen:
            scores[chosen] = -1
        idx = int(np.argmax(scores))
        chosen.append(idx)
        info += np.outer(features[idx], features[idx])
    return np.array(chosen), time.perf_counter() - tick


def composition(
    domain: Diffusion, seed: int, artifacts: dict[str, Reduced], baseline: str, split: str, count: int = 6
) -> dict[str, Any]:
    """Run a sensor/inverse mission and component ablations on shared fields."""
    rng = np.random.default_rng(seed)
    all_rows, trials, payloads = [], [], []
    coords = np.array([[0.25, 0.25], [0.25, 0.75], [0.5, 0.35], [0.5, 0.65], [0.75, 0.25], [0.75, 0.75]])
    fixed = np.array([int(x * (domain.n - 1)) * domain.n + int(y * (domain.n - 1)) for x, y in coords])
    for trial in range(count):
        source = [rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.7), rng.uniform(0.13, 0.22), rng.uniform(-0.15, 0.15)]
        k_values = np.array([0.5, 0.9, 1.5, 2.5])
        contrast, reaction = rng.uniform(0.4, 2.6), rng.uniform(2, 12)
        cases = [
            {
                "case_id": f"inverse-{seed}-{trial}-{i * 4 + j}",
                "family": "composition",
                "theta": [float(kx), float(ky), contrast, reaction],
                "source": source,
            }
            for i, kx in enumerate(k_values)
            for j, ky in enumerate(k_values)
        ]
        true_idx = int(rng.integers(16))
        reference_fields, reference_costs = zip(*(reference_solve(domain, spec) for spec in cases))
        reference = np.column_stack(reference_fields)
        sensor_count = 2 if trial % 2 == 0 else 6
        noise_fraction = 0.05 if sensor_count == 2 else 0.018
        noise_sd = float(np.max(np.abs(reference[:, true_idx])) * noise_fraction)
        noise = rng.normal(0, noise_sd, domain.n**2)
        field_bundles: dict[str, np.ndarray] = {}
        method_costs: dict[str, float] = {}
        method_ok: dict[str, bool] = {}
        for method in [baseline, "v1", "v2"]:
            fields = []
            method_rows = []
            for i, spec in enumerate(cases):
                row, field = execute(domain, spec, method, artifacts.get(method), reference[:, i], reference_costs[i])
                row["split"] = split
                all_rows.append(row)
                method_rows.append(row)
                fields.append(field)
            field_bundles[method] = np.column_stack(fields)
            method_costs[method] = sum(r["complete_s"] for r in method_rows)
            method_ok[method] = all(r["accepted"] for r in method_rows)
        for method, design, label in [
            (baseline, "fixed", "fixed_sensor_ablation"),
            ("v2", "fixed", "solver_only"),
            (baseline, "d_optimal", "competent_generalist"),
            ("v2", "d_optimal", "combination"),
            ("v1", "d_optimal", "v1_combination"),
        ]:
            tick = time.perf_counter()
            if design == "fixed":
                selected, design_s = fixed[[1, 4]] if sensor_count == 2 else fixed, 0.0
            else:
                selected, design_s = greedy_sensors(field_bundles[method], sensor_count)
            observation = reference[selected, true_idx] + noise[selected]
            misfits = ((field_bundles[method][selected] - observation[:, None]) ** 2).sum(axis=0)
            inferred = int(np.argmin(misfits))
            true_theta = np.array(cases[true_idx]["theta"][:2])
            inferred_theta = np.array(cases[inferred]["theta"][:2])
            parameter_error = float(np.linalg.norm(np.log(inferred_theta / true_theta)))
            inverse_s = time.perf_counter() - tick - design_s
            trials.append(
                {
                    "case_id": f"inverse-{seed}-{trial}",
                    "family": "composition",
                    "split": split,
                    "method": label,
                    "solver": method,
                    "sensor_design": design,
                    "sensor_count": sensor_count,
                    "true_theta": true_theta.tolist(),
                    "inferred_theta": inferred_theta.tolist(),
                    "parameter_error": parameter_error,
                    "acceptable_inference": bool(inferred == true_idx),
                    "forward_fields_accepted": method_ok[method],
                    "accepted": bool(inferred == true_idx and method_ok[method]),
                    "forward_s": method_costs[method],
                    "design_s": design_s,
                    "inverse_s": inverse_s,
                    "complete_s": method_costs[method] + design_s + inverse_s,
                    "selected_sensor_indices": selected.tolist(),
                    "noise_sd": noise_sd,
                    "noise_fraction_of_peak": noise_fraction,
                    "finite_candidate_grid": 16,
                    "same_forward_calls_and_sensors": True,
                }
            )
        payloads.append(
            {
                "case_id": f"inverse-{seed}-{trial}",
                "source": source,
                "true_index": true_idx,
                "contrast": contrast,
                "reaction": reaction,
                "candidate_thetas": [c["theta"] for c in cases],
            }
        )
    return {
        "solver_records": all_rows,
        "mission_records": trials,
        "missions": payloads,
        "note": "Ablations reuse measured forward results but charge full forward costs to every policy."
        " Generalist plus design is an equally funded ordinary-tool competitor."
        " One factorization per distinct matrix; factor reuse is valid within each solve and is never prohibited.",
    }


def warmup(domain: Diffusion) -> None:
    """Warm all numerical code paths before paired timings."""
    spec = sample(2026102799, 1, "thermal")[0]
    reference, ref_s = reference_solve(domain, spec)
    basis = orthogonal_append(np.empty((domain.n**2, 0)), reference)
    reduced = Reduced(domain, basis)
    for method in ["direct", "ilu_gmres", "spectral_pcg", "v1"]:
        execute(domain, spec, method, reduced if method == "v1" else None, reference, ref_s)


def develop(out: Path) -> None:
    """Run development only; final seeds are supplied later by the study owner."""
    development_started = time.perf_counter()
    if (out / "results.json").exists():
        raise ValueError("Refuse to overwrite development history; use a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    tick = time.perf_counter()
    domain = Diffusion()
    domain_build_s = time.perf_counter() - tick
    tick = time.perf_counter()
    warmup(domain)
    warmup_s = time.perf_counter() - tick
    training = train(domain, out)
    cases = sample(2026102711, 8, "thermal") + sample(2026102712, 12, "transfer")
    v1 = Reduced(domain, np.load(out / "artifacts/v1.npy"))
    candidate_rows, evaluations = [], []
    tick = time.perf_counter()
    for rank in training["candidate_ranks"]:
        v2 = Reduced(domain, np.load(out / f"artifacts/candidate-r{rank}.npy"))
        rows = evaluate(domain, cases, {"v1": v1, "v2": v2}, "development", ["v2"])
        score = aggregate(rows)["v2"]
        candidate_rows.append(
            {"rank": rank, **score, "artifact_sha256": digest(out / f"artifacts/candidate-r{rank}.npy")}
        )
        evaluations.extend([{**r, "candidate_rank": rank} for r in rows])
    assessment_s = time.perf_counter() - tick
    selected = sorted(
        candidate_rows, key=lambda r: (-r["accepted"], -r["raw_accepted"], r["mean_raw_error"], r["rank"])
    )[0]
    rank = selected["rank"]
    (out / "artifacts/v2.npy").write_bytes((out / f"artifacts/candidate-r{rank}.npy").read_bytes())
    v2 = Reduced(domain, np.load(out / "artifacts/v2.npy"))
    tick = time.perf_counter()
    rows = evaluate(domain, cases, {"v1": v1, "v2": v2}, "development", solution_path=out / "solutions.npz")
    baseline_selection_assessment_s = time.perf_counter() - tick
    summaries = aggregate(rows)
    baseline = min(["direct", "ilu_gmres", "spectral_pcg"], key=lambda m: summaries[m]["mean_complete_s"])
    ood_rows = evaluate(domain, sample(2026102713, 8, "ood"), {"v1": v1, "v2": v2}, "development_ood")
    comp = composition(domain, 2026102714, {"v1": v1, "v2": v2}, baseline, "development", count=6)
    selection = {
        "selected_rank": rank,
        "baseline": baseline,
        "selection_rule": "Maximum exact accepted count, raw accepted count, lowest mean raw error, then rank."
        " Primary ordinary baseline minimizes development mean full runtime among direct, ILU-GMRES, spectral-PCG.",
        "candidates": candidate_rows,
        "v1_sha256": digest(out / "artifacts/v1.npy"),
        "v2_sha256": digest(out / "artifacts/v2.npy"),
        "all_candidate_assessment_s": assessment_s,
        "baseline_selection_assessment_s": baseline_selection_assessment_s,
        "domain_build_s": domain_build_s,
        "warmup_s": warmup_s,
        **training,
    }
    write_json(out / "selection.json", selection)
    write_json(out / "candidate_assessment.json", evaluations)
    write_json(
        out / "results.json",
        {
            "records": rows,
            "summary": summaries,
            "ood_records": ood_rows,
            "ood_summary": aggregate(ood_rows),
            "composition": comp,
            "selection": selection,
            "environment": environment(),
            "phase": "development",
            "source_sha256": digest(Path(__file__)),
            "development_total_s": time.perf_counter() - development_started,
        },
    )
    print(json.dumps({"phase": "development", "selection": selection, "summary": summaries}, indent=2))


def environment() -> dict[str, Any]:
    """Record versions and computational boundaries."""
    return {
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "blas_threads": 1,
        "grid_n": N,
        "model_calls": 0,
        "live_ens_authentication": False,
        "physical_validation": False,
        "provenance": "Researcher-constructed learning system; numeric bases are updated by executed experience.",
    }


def confirm(out: Path, development: Path, seed: int, count: int) -> None:
    """Execute a frozen policy on previously unused supplied confirmation seeds."""
    if out.exists() and (out / "results.json").exists():
        raise ValueError("Refuse to overwrite confirmation evidence")
    selection = json.loads((development / "selection.json").read_text())
    for version in ["v1", "v2"]:
        if digest(development / f"artifacts/{version}.npy") != selection[f"{version}_sha256"]:
            raise ValueError("Artifact identity changed after selection")
    out.mkdir(parents=True, exist_ok=True)
    tick = time.perf_counter()
    domain = Diffusion()
    domain_build_s = time.perf_counter() - tick
    tick = time.perf_counter()
    warmup(domain)
    warmup_s = time.perf_counter() - tick
    artifacts, artifact_build_by_version_s = {}, {}
    for version in ["v1", "v2"]:
        tick = time.perf_counter()
        artifacts[version] = Reduced(domain, np.load(development / f"artifacts/{version}.npy"))
        artifact_build_by_version_s[version] = time.perf_counter() - tick
    artifact_build_s = sum(artifact_build_by_version_s.values())
    cases = sample(seed, count, "thermal") + sample(seed + 1, count, "transfer")
    write_json(out / "case_manifest.json", {"seed": seed, "count_per_family": count, "cases": cases})
    rows = evaluate(domain, cases, artifacts, "confirmation", solution_path=out / "solutions.npz")
    ood = sample(seed + 2, count, "ood")
    write_json(out / "ood_case_manifest.json", {"seed": seed + 2, "cases": ood})
    ood_rows = evaluate(domain, ood, artifacts, "confirmation_ood", solution_path=out / "ood_solutions.npz")
    comp = composition(domain, seed + 3, artifacts, selection["baseline"], "confirmation", count=max(12, count // 2))
    for row in rows + ood_rows + comp["solver_records"]:
        if row["method"] in ["v1", "v2"]:
            row["artifact_sha256"] = selection[f"{row['method']}_sha256"]
    result = {
        "records": rows,
        "summary": aggregate(rows),
        "ood_records": ood_rows,
        "ood_summary": aggregate(ood_rows),
        "composition": comp,
        "selection": selection,
        "artifact_build_s": artifact_build_s,
        "artifact_build_by_version_s": artifact_build_by_version_s,
        "domain_build_s": domain_build_s,
        "warmup_s": warmup_s,
        "environment": environment(),
        "phase": "confirmation",
        "seed": seed,
        "source_sha256": digest(Path(__file__)),
        "confirmation_case_sha256": digest(out / "case_manifest.json"),
    }
    write_json(out / "results.json", result)
    print(
        json.dumps(
            {
                "phase": "confirmation",
                "summary": result["summary"],
                "ood_summary": result["ood_summary"],
                "composition_trials": len(comp["mission_records"]),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["develop", "confirm"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--development", type=Path, default=HERE / "technical_dev")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--count", type=int, default=24)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.phase == "develop":
            develop(args.out)
        else:
            if args.seed is None or 2026102700 <= args.seed <= 2026102800:
                parser.error("A distinct root-supplied confirmation seed is required")
            confirm(args.out, args.development, args.seed, args.count)


if __name__ == "__main__":
    main()
