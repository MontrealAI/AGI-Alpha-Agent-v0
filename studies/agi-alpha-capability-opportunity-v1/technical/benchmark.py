# SPDX-License-Identifier: Apache-2.0
"""Synthetic scientific-software oracle and separate fresh evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from scipy.stats import qmc

from learning import DIMENSION, EXPONENTS, WIDTH, features


FAMILY_SEED = 417038
TARGET_RESPONSE = 2.0
COST_CEILING = 1.2


def family_support(seed: int = FAMILY_SEED) -> np.ndarray:
    """Hidden recurring support used to generate synthetic simulator families."""
    rng = np.random.default_rng(seed)
    nonlinear = np.flatnonzero(EXPONENTS.sum(axis=1) >= 2)
    return np.sort(rng.choice(nonlinear, size=20, replace=False))


def points(seed: int, count: int) -> np.ndarray:
    return 2 * qmc.LatinHypercube(d=DIMENSION, seed=seed).random(count) - 1


@dataclass
class Oracle:
    """Only query() observations enter the learner; private coefficients belong to the scorer."""

    coefficients: np.ndarray
    calls: int = 0

    def query(self, candidates: np.ndarray) -> np.ndarray:
        self.calls += len(candidates)
        return features(candidates) @ self.coefficients


def make_task(seed: int, regime: str) -> tuple[Oracle, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    recurring = family_support()
    outside = np.setdiff1d(np.arange(1, WIDTH), recurring)
    if regime == "compatible":
        support = rng.choice(recurring, 8, replace=False)
    elif regime == "partial_shift":
        support = np.concatenate([rng.choice(recurring, 6, replace=False), rng.choice(outside, 2, replace=False)])
    elif regime == "novel_family":
        support = rng.choice(outside, 8, replace=False)
    else:
        raise ValueError(regime)
    coefficients = np.zeros(WIDTH)
    coefficients[0] = 0.2
    weights = rng.uniform(0.5, 1.5, 8) * rng.choice([-1.0, 1.0], 8)
    coefficients[support] = weights / np.linalg.norm(weights)
    return Oracle(coefficients), {"seed": seed, "regime": regime, "active_support": np.sort(support).tolist()}


@lru_cache(maxsize=256)
def audit_truth(seed: int, count: int, coefficients: tuple[float, ...]) -> np.ndarray:
    return features(points(seed, count)) @ np.asarray(coefficients)


def evaluate(model: np.ndarray, oracle: Oracle, seed: int, chosen_override: int | None = None) -> dict[str, Any]:
    """Fresh prediction, inverse-design and fault localization are distinct useful outputs."""
    validation_points = points(seed + 610_003, 384)
    phi = features(validation_points)
    truth = audit_truth(seed +610_003,384,tuple(oracle.coefficients))
    prediction = phi @ model
    nrmse = float(np.sqrt(np.mean((prediction - truth) ** 2)) / max(np.std(truth), 0.2))
    max_error = float(np.max(np.abs(prediction - truth)))

    plans = points(seed + 720_007, 512)
    plan_features = features(plans)
    plan_truth = audit_truth(seed+720_007,512,tuple(oracle.coefficients))
    predicted_response = plan_features @ model
    costs = 0.2 + np.mean((plans + 1) ** 2, axis=1)
    target = TARGET_RESPONSE
    feasible = np.flatnonzero((plan_truth >= target) & (costs <= COST_CEILING))
    proposal_options = np.flatnonzero((predicted_response >= target + 0.01) & (costs <= COST_CEILING))
    optimum = int(feasible[np.argmin(costs[feasible])]) if len(feasible) else -1
    chosen = chosen_override if chosen_override is not None else (int(proposal_options[np.argmin(costs[proposal_options])]) if len(proposal_options) else -1)
    if chosen >= 0:
        design_feasible = bool(plan_truth[chosen] >= target and costs[chosen] <= COST_CEILING)
        regret = float(max(0, costs[chosen] - costs[optimum]) / costs[optimum]) if optimum >= 0 else 1.0
    else:
        chosen, design_feasible, regret = -1, False, 1.0
    design_accepted = bool(design_feasible)

    fault_rng = np.random.default_rng(seed + 830_009)
    active = np.flatnonzero(np.abs(oracle.coefficients[1:]) > 1e-8) + 1
    fault = int(fault_rng.choice(active))
    probes = points(seed + 940_009, 16)
    probe_features = features(probes)
    faulty_coefficients = oracle.coefficients.copy()
    faulty_coefficients[fault] += 0.35
    measurements = audit_truth(seed+940_009,16,tuple(faulty_coefficients))
    residual = measurements[:12] - probe_features[:12] @ model
    fault_templates = probe_features[:12, 1:]
    amplitudes = fault_templates.T @ residual / np.maximum(np.sum(fault_templates**2, axis=0), 1e-12)
    template_errors = np.sum((residual[:, None] - fault_templates * amplitudes) ** 2, axis=0)
    predicted_fault = 1 + int(np.argmin(template_errors))
    estimated_amplitude = float(amplitudes[predicted_fault - 1])
    diagnostic_residual = float(np.sqrt(np.mean((measurements[12:] - probe_features[12:] @ model - estimated_amplitude * probe_features[12:, predicted_fault]) ** 2)))
    paired_residual = measurements[:12] - probe_features[:12] @ oracle.coefficients
    paired_amplitudes = fault_templates.T @ paired_residual / np.maximum(np.sum(fault_templates**2, axis=0), 1e-12)
    paired_errors = np.sum((paired_residual[:, None] - fault_templates * paired_amplitudes) ** 2, axis=0)
    paired_fault = 1 + int(np.argmin(paired_errors))
    paired_error = float(np.sqrt(np.mean((measurements[12:] - probe_features[12:] @ oracle.coefficients - paired_amplitudes[paired_fault - 1] * probe_features[12:, paired_fault]) ** 2)))
    fault_correct = predicted_fault == fault
    diagnosis_accepted = bool(fault_correct and diagnostic_residual <= 0.02)
    return {
        "prediction_nrmse": nrmse,
        "prediction_max_absolute_error": max_error,
        "prediction_accepted": nrmse <= 0.01,
        "design_feasible": design_feasible,
        "design_regret": regret,
        "design_accepted": design_accepted,
        "chosen_plan": chosen,
        "chosen_plan_inputs": plans[chosen].tolist() if chosen>=0 else None,
        "chosen_plan_cost": float(costs[chosen]) if chosen >= 0 else None,
        "chosen_plan_true_response": float(plan_truth[chosen]) if chosen >= 0 else None,
        "optimal_plan": optimum,
        "optimal_plan_cost": float(costs[optimum]) if optimum >= 0 else None,
        "menu_has_feasible_plan": optimum >= 0,
        "target_response": TARGET_RESPONSE,
        "cost_ceiling": COST_CEILING,
        "diagnosis_correct": bool(fault_correct),
        "diagnosis_accepted": diagnosis_accepted,
        "diagnostic_residual": diagnostic_residual,
        "diagnosis_extra_calls": 16,
        "paired_diagnosis_extra_calls": 32,
        "paired_diagnosis_accepted": bool(paired_fault == fault and paired_error <=0.02),
        "predicted_fault_term": predicted_fault,
        "true_fault_term": fault,
        "accepted": design_accepted,
        "combined_research_accepted": bool(nrmse <=0.01 and design_accepted),
        "independent_scorer_calls": 896,
    }
