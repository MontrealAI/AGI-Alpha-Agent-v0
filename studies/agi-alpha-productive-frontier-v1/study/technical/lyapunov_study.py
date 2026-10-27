# SPDX-License-Identifier: Apache-2.0
import argparse, csv, hashlib, json, os, platform, time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import scipy
from scipy.linalg import solve_continuous_lyapunov, eigh, qr
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / "protocol.json").read_text())


def system(p, n=192):
    damping, coupling, heterogeneity, input_scale = p
    x = np.linspace(0, 1, n)
    d = 0.15 + damping * (1 + 0.25 * np.sin(2 * np.pi * x))
    w = coupling * (1 + 0.2 * np.cos(3 * np.pi * x[:-1]))
    v = 0.15 * coupling * heterogeneity * np.ones(n - 2)
    A = -np.diag(d) + np.diag(w, 1) - np.diag(w, -1) + np.diag(v, 2) - np.diag(v, -2)
    B = np.zeros((n, 2))
    B[n // 3, 0] = 1.0
    B[2 * n // 3, 1] = input_scale
    return A, B, float(d.min())


def parameters(seed, count, shift=False):
    rng = np.random.default_rng(seed)
    box = P["shift_box" if shift else "operating_box"]
    return rng.uniform([v[0] for v in box.values()], [v[1] for v in box.values()], (count, 4))


def validate_system(A, B, alpha=None):
    if A.ndim != 2 or A.shape[0] != A.shape[1] or B.ndim != 2 or B.shape[0] != A.shape[0]:
        raise ValueError("Malformed system dimensions")
    if not np.isfinite(A).all() or not np.isfinite(B).all():
        raise ValueError("Nonfinite system")
    if alpha is not None:
        if not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("Positive dissipativity lower bound required")
        S = (A + A.T) / 2
        upper = float(np.max(np.diag(S) + np.sum(np.abs(S), axis=1) - np.abs(np.diag(S))))
        if upper > -alpha + 1e-12 and float(np.linalg.eigvalsh(S)[-1]) > -alpha + 1e-12:
            raise ValueError("Claimed dissipativity lower bound is invalid")


def validate_basis(V, n):
    if V.ndim != 2 or V.shape[0] != n or V.shape[1] > n or V.shape[1] == 0 or not np.isfinite(V).all():
        raise ValueError("Malformed or nonfinite basis")
    if not np.allclose(V.T @ V, np.eye(V.shape[1]), rtol=0, atol=1e-8):
        raise ValueError("Basis must be orthonormal")


def load_basis(path, expected_sha256, n=192):
    if digest(path) != expected_sha256:
        raise ValueError("Artifact digest mismatch")
    V = np.load(path, allow_pickle=False)
    validate_basis(V, n)
    return V


def certified(c):
    return c["relative_trace_certificate"] is not None and c["relative_trace_certificate"] <= 0.01


def exact(A, B):
    validate_system(A, B)
    X = solve_continuous_lyapunov(A, -B @ B.T)
    return (X + X.T) / 2


def certificate(A, B, X, alpha):
    validate_system(A, B, alpha)
    if X.shape != A.shape or not np.isfinite(X).all() or not np.allclose(X, X.T, atol=1e-8, rtol=1e-8):
        raise ValueError("Malformed, nonfinite or nonsymmetric covariance")
    R = A @ X + X @ A.T + B @ B.T
    norm = float(np.linalg.norm(R, "fro"))
    bound = norm / (2 * alpha)
    tr = float(np.trace(X))
    delta = np.sqrt(len(A)) * bound
    rel = float(delta / (tr - delta)) if tr > delta else None
    fro = float(np.linalg.norm(X, "fro"))
    relfro = float(bound / (fro - bound)) if fro > bound else None
    return {
        "residual_fro": norm,
        "absolute_fro_bound": bound,
        "relative_trace_certificate": rel,
        "relative_fro_certificate": relfro,
        "trace": tr,
    }


def project(A, B, V):
    validate_system(A, B)
    validate_basis(V, len(A))
    Ar = V.T @ A @ V
    Br = V.T @ B
    Y = solve_continuous_lyapunov(Ar, -Br @ Br.T)
    X = V @ ((Y + Y.T) / 2) @ V.T
    return X


def pod(solutions, rank):
    S = sum(X for X in solutions)
    vals, vecs = eigh(S)
    return vecs[:, -rank:][:, ::-1]


def krylov_basis(A, B, rank):
    V, _ = qr(B, mode="economic")
    block = V.copy()
    while V.shape[1] < rank:
        W = A @ block
        for _ in range(2):
            W -= V @ (V.T @ W)
        Q, R = qr(W, mode="economic")
        if np.max(np.abs(np.diag(R))) < 1e-12:
            break
        block = Q[:, : min(Q.shape[1], rank - V.shape[1])]
        V = np.column_stack((V, block))
    return V


def adaptive(A, B, alpha, max_rank=96):
    V, _ = qr(B, mode="economic")
    block = V.copy()
    X = None
    cert = None
    while V.shape[1] <= max_rank:
        if V.shape[1] >= 8 and V.shape[1] % 8 == 0:
            X = project(A, B, V)
            cert = certificate(A, B, X, alpha)
            if certified(cert):
                return X, V.shape[1], cert
        if V.shape[1] >= max_rank:
            break
        W = A @ block
        for _ in range(2):
            W -= V @ (V.T @ W)
        Q, R = qr(W, mode="economic")
        if np.max(np.abs(np.diag(R))) < 1e-12:
            break
        block = Q[:, : min(Q.shape[1], max_rank - V.shape[1])]
        V = np.column_stack((V, block))
    if X is None:
        X = project(A, B, V)
        cert = certificate(A, B, X, alpha)
    return X, V.shape[1], cert


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate_set(label, ps, bases, out):
    rows = []
    for i, p in enumerate(ps):
        t = time.perf_counter()
        A, B, alpha = system(p)
        assembly_seconds = time.perf_counter() - t
        t = time.perf_counter()
        Xref = exact(A, B)
        refcert = certificate(A, B, Xref, alpha)
        secs = time.perf_counter() - t
        common = {
            "split": label,
            "case": i,
            "assembly_seconds": assembly_seconds,
            **{f"p{j}": float(x) for j, x in enumerate(p)},
        }
        rows.append(
            {
                **common,
                "method": "schur",
                "seconds": secs + assembly_seconds,
                "rank": len(A),
                "relative_trace_error": 0.0,
                "relative_fro_error": 0.0,
                "accepted": certified(refcert),
                **refcert,
            }
        )
        for name, V in bases.items():
            t = time.perf_counter()
            X = project(A, B, V)
            cert = certificate(A, B, X, alpha)
            secs = time.perf_counter() - t
            errtr = abs(float(np.trace(X - Xref))) / abs(float(np.trace(Xref)))
            errfro = float(np.linalg.norm(X - Xref, "fro") / np.linalg.norm(Xref, "fro"))
            accepted = certified(cert) and errtr <= 0.01 and errfro <= 0.02
            rows.append(
                {
                    **common,
                    "method": name,
                    "seconds": secs + assembly_seconds,
                    "rank": V.shape[1],
                    "relative_trace_error": errtr,
                    "relative_fro_error": errfro,
                    "accepted": bool(accepted),
                    **cert,
                }
            )
        t = time.perf_counter()
        X, rank, cert = adaptive(A, B, alpha)
        secs = time.perf_counter() - t
        errtr = abs(float(np.trace(X - Xref))) / abs(float(np.trace(Xref)))
        errfro = float(np.linalg.norm(X - Xref, "fro") / np.linalg.norm(Xref, "fro"))
        rows.append(
            {
                **common,
                "method": "adaptive_krylov",
                "seconds": secs + assembly_seconds,
                "rank": rank,
                "relative_trace_error": errtr,
                "relative_fro_error": errfro,
                "accepted": bool(certified(cert) and errtr <= 0.01 and errfro <= 0.02),
                **cert,
            }
        )
    with (out / f"{label}.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return rows


def summarize(rows):
    summary = {}
    for name in sorted({r["method"] for r in rows}):
        rs = [r for r in rows if r["method"] == name]
        ts = [r["seconds"] for r in rs]
        summary[name] = {
            "n": len(rs),
            "accepted": sum(r["accepted"] for r in rs),
            "acceptance_rate": float(np.mean([r["accepted"] for r in rs])),
            "seconds_median": float(np.median(ts)),
            "seconds_p95": float(np.quantile(ts, 0.95)),
            "seconds_total": float(sum(ts)),
            "batch32_seconds_mean": float(np.mean(ts) * 32),
            "batch32_seconds_observed": [float(sum(ts[j : j + 32])) for j in range(0, len(ts), 32)],
            "batch32_seconds_p95_proxy": float(np.quantile(ts, 0.95) * 32),
            "max_relative_trace_error": float(max(r["relative_trace_error"] for r in rs)),
            "max_relative_fro_error": float(max(r["relative_fro_error"] for r in rs)),
            "max_trace_certificate": max(
                (r["relative_trace_certificate"] for r in rs if r["relative_trace_certificate"] is not None),
                default=None,
            ),
            "unbounded_trace_certificates": sum(r["relative_trace_certificate"] is None for r in rs),
            "median_rank": float(np.median([r["rank"] for r in rs])),
        }
    return summary


def run(out, validation_rerun=False):
    out.mkdir(exist_ok=True, parents=True)
    work = parameters(P["seeds"]["work"], P["counts"]["work"])
    dev = parameters(P["seeds"]["development"], P["counts"]["development"])
    stage = []
    solutions = []
    for i, p in enumerate(work):
        A, B, _ = system(p)
        t = time.perf_counter()
        X = exact(A, B)
        dt = time.perf_counter() - t
        solutions.append(X)
        stage.append({"category": "A", "stage": "paid_work_snapshot", "case": i, "full_solves": 1, "seconds": dt})
    t = time.perf_counter()
    pre24 = pod(solutions, 24)
    pre48 = pod(solutions, 48)
    dt = time.perf_counter() - t
    stage.append({"category": "B", "stage": "work_retention_fit", "seconds": dt, "full_solves": 0})
    scores = []
    t = time.perf_counter()
    for i, p in enumerate(dev):
        A, B, alpha = system(p)
        X = project(A, B, pre48)
        scores.append((certificate(A, B, X, alpha)["relative_trace_certificate"], i))
    stage.append(
        {"category": "C", "stage": "Gym_candidate_assessment", "seconds": time.perf_counter() - t, "full_solves": 0}
    )
    selection = sorted(scores, reverse=True)[:4]
    gym_solutions = solutions.copy()
    for score, i in selection:
        A, B, _ = system(dev[i])
        t = time.perf_counter()
        X = exact(A, B)
        dt = time.perf_counter() - t
        gym_solutions.append(X)
        stage.append(
            {
                "category": "C",
                "stage": "Gym_add_snapshot",
                "case": i,
                "pre_certificate": score,
                "seconds": dt,
                "full_solves": 1,
            }
        )
    t = time.perf_counter()
    post48 = pod(gym_solutions, 48)
    dt = time.perf_counter() - t
    stage.append({"category": "C", "stage": "Gym_refit", "seconds": dt, "full_solves": 0})
    center = np.array([sum(v) / 2 for v in P["operating_box"].values()])
    A, B, _ = system(center)
    t = time.perf_counter()
    fixed = krylov_basis(A, B, 48)
    dt = time.perf_counter() - t
    stage.append({"category": "B", "stage": "ordinary_library_basis_build", "seconds": dt, "full_solves": 0})
    bases = {"work_pod24": pre24, "work_pod48": pre48, "gym_pod48": post48, "fixed_krylov48": fixed}
    for name, V in bases.items():
        np.save(out / f"{name}.npy", V)
    frozen = {
        "protocol_sha256": digest(ROOT / "protocol.json"),
        "implementation_sha256": digest(__file__),
        "bases": {name: digest(out / f"{name}.npy") for name in bases},
        "selection": selection,
        "stage_costs": stage,
        "confirmation_has_been_run": validation_rerun,
        "run_status": "scoped_revalidation_of_exposed_cases" if validation_rerun else "preconfirmation",
    }
    (out / ("validation_freeze.json" if validation_rerun else "preconfirmation_freeze.json")).write_text(
        json.dumps(frozen, indent=2)
    )
    A, B, alpha = system(center)
    project(A, B, post48)
    adaptive(A, B, alpha)
    exact(A, B)
    allrows = []
    summaries = {}
    for label in ["confirmation", "shift", "prototype"]:
        ps = parameters(P["seeds"][label], P["counts"][label], label == "shift")
        (out / f"{label}_parameters.json").write_text(json.dumps(ps.tolist(), indent=2))
        rows = evaluate_set(label, ps, bases, out)
        allrows.extend(rows)
        summaries[label] = summarize(rows)
    result = {
        "protocol": P,
        "hashes": frozen,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "blas_threads": 1,
        },
        "summary": summaries,
    }
    (out / "technical_results.json").write_text(json.dumps(result, indent=2))
    (out / "stage_costs.json").write_text(json.dumps(stage, indent=2))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--validation-rerun", action="store_true")
    args = ap.parse_args()
    with threadpool_limits(limits=1):
        run(Path(args.out), args.validation_rerun)
