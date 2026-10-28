# SPDX-License-Identifier: Apache-2.0
"""Bounded executable falsification probe for a Crouzeix-2 exp(A)v compiler.

This implements ordinary shifted Taylor polynomial actions. It claims neither
algorithmic novelty nor floating-point certification. Analytical truncation
bounds are evaluated with ordinary floating-point arithmetic; observed errors
use scipy.linalg.expm as a numerical reference. The produced vectors are real
computational outputs, not certificates used as a substitute for production.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import scipy
from scipy.linalg import expm
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import LinearOperator, expm_multiply


ROOT = Path(__file__).resolve().parent
CONFIG = {
    "seed": 32520261028,
    "sizes": [16, 32, 64, 128],
    "families": [
        {"name": "jordan", "upper": 1.0, "lower": 0.0},
        {"name": "symmetric_diffusion", "upper": 1.0, "lower": 1.0},
        {"name": "convection_diffusion_4", "upper": 4.0, "lower": 1.0},
        {"name": "convection_diffusion_12", "upper": 12.0, "lower": 1.0},
    ],
    "times": [0.25, 1.0, 4.0],
    "absolute_tolerances_unit_vector": [1e-6, 1e-10, 1e-12],
    "timing_repetitions": 5,
    "decision": "Advance only with a substantive gain beyond existing specialized bounds and executable production.",
    "reference": "scipy.linalg.expm; numerical reference, not a rigorous interval oracle",
    "scipy_tolerance": "Stock expm_multiply has no public tolerance parameter and generally computes more accurately.",
    "rounding": "Analytical truncation bounds only; no certified total floating-point error.",
}


def radius_upper(n: int, upper: float, lower: float) -> float:
    """Upper-enclose the numerical radius of positive tridiagonal Toeplitz B.

    w(B)=(upper+lower)*cos(pi/(n+1)). The rational Taylor bound used here
    is rigorous over the exact rational inputs; its final float conversion
    is rounded upward. This does not certify subsequent floating arithmetic.
    """
    pi_lower = Fraction(314159265358979323846264338327950288, 10**35)
    x = pi_lower / (n + 1)
    cosine_upper = 1 - x*x/2 + x**4/24
    radius = Fraction(upper + lower) * cosine_upper
    return float(np.nextafter(float(radius), math.inf))


def log_tail_bound(degree: int, radius: float, shift: float, constant: float) -> float:
    """Bound exp(shift)*C*sum_{k>d} radius**k/k! by a geometric tail."""
    if radius == 0:
        return -math.inf
    if degree + 2 <= radius:
        return math.inf
    return (
        shift + math.log(constant) + (degree + 1) * math.log(radius)
        - math.lgamma(degree + 2) - math.log1p(-radius / (degree + 2))
    )


def select_degree(radius: float, shift: float, tolerance: float, constant: float) -> int:
    """Choose the first degree meeting this fixed analytical tail criterion."""
    for degree in range(10000):
        if log_tail_bound(degree, radius, shift, constant) <= math.log(tolerance):
            return degree
    raise RuntimeError("Declared degree budget exceeded")


def polynomial_action(b: csr_matrix, shift: float, vector: np.ndarray, degree: int) -> np.ndarray:
    """Actually produce exp(shift)*Taylor_degree(B)*vector with degree matvecs."""
    term = vector.copy()
    result = term.copy()
    for k in range(1, degree + 1):
        term = (b @ term) / k
        result += term
    return math.exp(shift) * result


def production_call(
    b: csr_matrix, shift: float, vector: np.ndarray, tolerance: float,
    radius: float, constant: float, nilpotent_degree: int | None = None,
) -> tuple[np.ndarray, int]:
    """Callable compiler and production operator, including degree selection."""
    degree = select_degree(radius, shift, tolerance, constant)
    if nilpotent_degree is not None:
        degree = min(degree, nilpotent_degree)
    return polynomial_action(b, shift, vector, degree), degree


def timed(function: Any, repetitions: int) -> tuple[Any, float]:
    """Warm a callable once, then report median time of independent calls."""
    value = function()
    timings = []
    for _ in range(repetitions):
        start = time.perf_counter()
        value = function()
        timings.append(time.perf_counter() - start)
    return value, median(timings)


def counted_scipy(a: csr_matrix, vector: np.ndarray, trace: float) -> dict[str, int]:
    """Count forward and transpose column-equivalent products in a SciPy call."""
    counts = {"forward_vector_equivalents": 0, "transpose_vector_equivalents": 0}

    def forward(x: np.ndarray) -> np.ndarray:
        counts["forward_vector_equivalents"] += 1 if x.ndim == 1 else x.shape[1]
        return a @ x

    def backward(x: np.ndarray) -> np.ndarray:
        counts["transpose_vector_equivalents"] += 1 if x.ndim == 1 else x.shape[1]
        return a.T @ x

    operator = LinearOperator(a.shape, matvec=forward, rmatvec=backward,
                              matmat=forward, rmatmat=backward, dtype=a.dtype)
    expm_multiply(operator, vector, traceA=trace)
    return counts


def run() -> dict[str, Any]:
    """Write the declared grid before measurements, then execute all outputs."""
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    frozen = {"declared_at": datetime.now(timezone.utc).isoformat(),
              "source_sha256": source_sha, "configuration": CONFIG}
    (ROOT / "matrix_probe_protocol.json").write_text(json.dumps(frozen, indent=2) + "\n")
    rng = np.random.default_rng(CONFIG["seed"])
    rows = []
    outputs: dict[str, np.ndarray] = {}
    for family in CONFIG["families"]:
        for n in CONFIG["sizes"]:
            vector = rng.standard_normal(n)
            vector /= np.linalg.norm(vector)
            for interval in CONFIG["times"]:
                upper = family["upper"] * interval
                lower = family["lower"] * interval
                norm_bound = upper + lower
                shift = -norm_bound
                b = diags([lower*np.ones(n-1), upper*np.ones(n-1)], [-1, 1], shape=(n,n), format="csr")
                a = b + diags([np.full(n, shift)], [0], format="csr")
                radius = radius_upper(n, upper, lower)
                reference = expm(a.toarray()) @ vector
                scipy_value, scipy_seconds = timed(lambda: expm_multiply(a, vector, traceA=n*shift),
                                                   CONFIG["timing_repetitions"])
                scipy_error = float(np.linalg.norm(scipy_value - reference))
                scipy_counts = counted_scipy(a, vector, n*shift)
                for tolerance in CONFIG["absolute_tolerances_unit_vector"]:
                    methods = {
                        "general_complete_2017": (radius, 1 + math.sqrt(2), None),
                        "general_crouzeix_2": (radius, 2.0, None),
                        "conventional_norm_or_special": (
                            radius if family["name"] == "symmetric_diffusion" else norm_bound,
                            1.0, n-1 if family["name"] == "jordan" else None,
                        ),
                    }
                    record: dict[str, Any] = {
                        "family": family["name"], "n": n, "t": interval,
                        "tolerance": tolerance, "numerical_radius_upper": radius,
                        "operator_norm_upper": norm_bound,
                        "scipy_seconds": scipy_seconds, "scipy_error": scipy_error,
                        "scipy_counts": scipy_counts, "methods": {},
                    }
                    for name, (bound_radius, constant, nilpotent_degree) in methods.items():
                        (output, degree), seconds = timed(
                            lambda br=bound_radius, cc=constant, nd=nilpotent_degree:
                                production_call(b, shift, vector, tolerance, br, cc, nd),
                            CONFIG["timing_repetitions"],
                        )
                        error = float(np.linalg.norm(output-reference))
                        record["methods"][name] = {
                            "degree_matvecs": degree, "compile_plus_action_seconds": seconds,
                            "absolute_error": error, "observed_tolerance_pass": error <= tolerance,
                            "analytical_truncation_bound": (
                                0.0 if nilpotent_degree is not None and degree == nilpotent_degree
                                else math.exp(log_tail_bound(degree, bound_radius, shift, constant))
                            ),
                        }
                        if n == 32 and interval == 1.0 and tolerance == 1e-10:
                            key = family["name"] + "__" + name
                            outputs[key] = output
                            outputs[family["name"] + "__input"] = vector
                            outputs[family["name"] + "__reference"] = reference
                    rows.append(record)
    np.savez(ROOT / "produced_matrix_actions.npz", **outputs)
    old_d = [r["methods"]["general_complete_2017"]["degree_matvecs"] for r in rows]
    new_d = [r["methods"]["general_crouzeix_2"]["degree_matvecs"] for r in rows]
    conventional_d = [r["methods"]["conventional_norm_or_special"]["degree_matvecs"] for r in rows]
    nonnormal = [r for r in rows if r["family"].startswith("convection")]
    summary = {
        "cases": len(rows), "distinct_matrices": len(rows)//3,
        "all_observed_tolerances_pass": all(m["observed_tolerance_pass"] for r in rows for m in r["methods"].values()),
        "new_vs_2017_cases_reducing_degree": sum(n < o for n,o in zip(new_d,old_d)),
        "new_vs_2017_max_degree_reduction": max(o-n for n,o in zip(new_d,old_d)),
        "new_vs_2017_total_matvecs": {"old": sum(old_d), "new": sum(new_d)},
        "new_vs_conventional_cases_reducing_degree": sum(n < c for n,c in zip(new_d,conventional_d)),
        "new_vs_conventional_cases_equal_degree": sum(n == c for n,c in zip(new_d,conventional_d)),
        "new_vs_conventional_cases_more_degree": sum(n > c for n,c in zip(new_d,conventional_d)),
        "nonnormal_new_vs_conventional_degree_wins": sum(
            r["methods"]["general_crouzeix_2"]["degree_matvecs"] < r["methods"]["conventional_norm_or_special"]["degree_matvecs"]
            for r in nonnormal),
        "nonnormal_cases": len(nonnormal),
        "new_vs_2017_median_runtime_ratio": median(
            r["methods"]["general_crouzeix_2"]["compile_plus_action_seconds"] /
            r["methods"]["general_complete_2017"]["compile_plus_action_seconds"] for r in rows),
        "new_vs_conventional_median_runtime_ratio": median(
            r["methods"]["general_crouzeix_2"]["compile_plus_action_seconds"] /
            r["methods"]["conventional_norm_or_special"]["compile_plus_action_seconds"] for r in rows),
        "new_vs_scipy_median_runtime_ratio": median(
            r["methods"]["general_crouzeix_2"]["compile_plus_action_seconds"] / r["scipy_seconds"] for r in rows),
    }
    result = {"protocol": frozen, "runtime": {"python": platform.python_version(),
              "numpy": np.__version__, "scipy": scipy.__version__}, "summary": summary, "rows": rows}
    (ROOT / "matrix_probe_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return result


if __name__ == "__main__":
    run()
