# SPDX-License-Identifier: Apache-2.0
"""Executable empirical structure learning; no access to benchmark answer coefficients."""

from __future__ import annotations

import itertools
import warnings
from typing import Any

import numpy as np
from scipy.linalg import qr
from sklearn.linear_model import ARDRegression


DIMENSION = 10
DEGREE = 3
EXPONENTS = [tuple([0] * DIMENSION)]
for degree in range(1, DEGREE + 1):
    for indices in itertools.combinations_with_replacement(range(DIMENSION), degree):
        powers = [0] * DIMENSION
        for index in indices:
            powers[index] += 1
        EXPONENTS.append(tuple(powers))
EXPONENTS = np.asarray(EXPONENTS, dtype=int)
WIDTH = len(EXPONENTS)


def features(points: np.ndarray) -> np.ndarray:
    """Known generic degree-three Legendre feature library, identical for all policies."""
    x = np.asarray(points)
    powers = [np.ones_like(x), np.sqrt(3) * x, np.sqrt(5) * (3 * x**2 - 1) / 2]
    powers.append(np.sqrt(7) * (5 * x**3 - 3 * x) / 2)
    result = np.ones((len(x), WIDTH))
    for dim in range(DIMENSION):
        for degree in range(1, DEGREE + 1):
            result[:, EXPONENTS[:, dim] == degree] *= powers[degree][:, dim, None]
    return result


def d_optimal_order(points: np.ndarray, support: list[int] | None = None) -> np.ndarray:
    """Greedy pivoted-QR volume design on a public, unevaluated candidate point pool."""
    matrix = features(points)
    if support is not None:
        matrix = matrix[:, support]
    _, _, pivots = qr(matrix.T, mode="economic", pivoting=True, check_finite=False)
    return pivots


def omp_path(matrix: np.ndarray, target: np.ndarray, maximum: int) -> dict[int, np.ndarray]:
    """Ordinary orthogonal matching pursuit with column normalization and full refits."""
    norms = np.linalg.norm(matrix, axis=0)
    norms = np.maximum(norms, 1e-12)
    scaled = matrix / norms
    residual = target.copy()
    selected: list[int] = []
    results: dict[int, np.ndarray] = {}
    for _ in range(min(maximum, matrix.shape[0] - 1, matrix.shape[1])):
        correlations = np.abs(scaled.T @ residual)
        correlations[selected] = -1
        column = int(np.argmax(correlations))
        selected.append(column)
        coef = np.linalg.lstsq(matrix[:, selected], target, rcond=1e-10)[0]
        residual = target - matrix[:, selected] @ coef
        full = np.zeros(matrix.shape[1])
        full[selected] = coef
        results[len(selected)] = full
        if np.linalg.norm(residual) < 1e-10:
            break
    return results


def ridge(matrix: np.ndarray, target: np.ndarray, penalty: float) -> np.ndarray:
    """Dual ridge solve handles the full underdetermined feature library."""
    gram = matrix @ matrix.T
    return matrix.T @ np.linalg.solve(gram + penalty * np.eye(len(matrix)), target)


def ard(matrix: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Automatic relevance determination is a strong ordinary sparse baseline."""
    norms = np.maximum(np.sqrt(np.mean(matrix**2, axis=0)), 1e-8)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        estimator = ARDRegression(max_iter=160, tol=1e-4, fit_intercept=False, threshold_lambda=1e5)
        estimator.fit(matrix / norms, target)
    return estimator.coef_ / norms


def fit_portfolio(
    train: np.ndarray,
    values: np.ndarray,
    visible_validation: np.ndarray,
    validation_values: np.ndarray,
    support: list[int] | None = None,
    include_ard: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Select using visible validation only, then refit that method with all paid observations."""
    indices = np.asarray(support if support is not None else np.arange(WIDTH), dtype=int)
    a = train[:, indices]
    v = visible_validation[:, indices]
    scale = max(float(np.std(validation_values)), 0.2)
    candidates: list[tuple[float, str, float, np.ndarray]] = []
    for size, coefficients in omp_path(a, values, min(32, len(a) - 1)).items():
        error = float(np.sqrt(np.mean((v @ coefficients - validation_values) ** 2)) / scale)
        candidates.append((error, "omp", float(size), coefficients))
    for penalty in [1e-8, 1e-3, 0.1, 10.0]:
        coefficients = ridge(a, values, penalty)
        error = float(np.sqrt(np.mean((v @ coefficients - validation_values) ** 2)) / scale)
        candidates.append((error, "ridge", penalty, coefficients))
    if include_ard:
        coefficients = ard(a, values)
        error = float(np.sqrt(np.mean((v @ coefficients - validation_values) ** 2)) / scale)
        candidates.append((error, "ard", 0.0, coefficients))
    error, kind, parameter, _ = min(candidates, key=lambda item: item[0])
    combined = np.concatenate([a, v])
    combined_y = np.concatenate([values, validation_values])
    if kind == "omp":
        path = omp_path(combined, combined_y, int(parameter))
        coefficients = path[max(path)]
    elif kind == "ridge":
        coefficients = ridge(combined, combined_y, parameter)
    else:
        coefficients = ard(combined, combined_y)
    full = np.zeros(WIDTH)
    full[indices] = coefficients
    return full, {"selected_method": kind, "selected_parameter": parameter, "visible_validation_nrmse": error}


def fit_guarded(
    train: np.ndarray,
    values: np.ndarray,
    validation: np.ndarray,
    validation_values: np.ndarray,
    support: list[int] | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """A failed inherited representation falls back to the full ordinary portfolio."""
    model, metadata = fit_portfolio(train, values, validation, validation_values, support)
    metadata["prior_rejected"] = False
    if support is not None and metadata["visible_validation_nrmse"] > 0.08:
        ordinary, ordinary_metadata = fit_portfolio(train, values, validation, validation_values)
        if ordinary_metadata["visible_validation_nrmse"] < metadata["visible_validation_nrmse"]:
            model = ordinary
            metadata = {**ordinary_metadata, "prior_rejected": True}
    return model, metadata


def learn_artifact(experience_models: list[np.ndarray], version: str) -> dict[str, Any]:
    """Automated update retains empirical nonzero features, not hidden generator supports."""
    counts = np.sum([np.abs(model) > 1e-3 for model in experience_models], axis=0)
    support = np.flatnonzero(counts > 0).tolist()
    return {
        "schema": "agi-alpha-empirical-motif-prior-v1",
        "version": version,
        "support": support,
        "frequency": counts.tolist(),
        "experience_jobs": len(experience_models),
        "feature_library": "10 inputs, total degree <=3, orthonormal Legendre terms",
        "scope": "Recurring empirical interaction supports; coefficients are always learned afresh",
        "rights": "Researcher-created synthetic data; Apache-2.0 implementation",
        "learning": "Independent-job sparse regression followed by union/count update",
        "limitations": "No guarantee for novel or shifted support; validation guard and refit required",
    }
