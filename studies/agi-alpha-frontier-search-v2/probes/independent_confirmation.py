"""Verify scoped counterexamples and a known quantum construction.

This is numerical verification, not a new discovery or physical experiment.
The replacement-operator quantum implementation uses a different Kraus basis
from the frozen E submission's Pauli implementation.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def quantum(n: int) -> dict:
    eye = np.eye(2, dtype=complex)
    kraus = []
    for a, b in itertools.product(range(2), repeat=2):
        k = np.zeros((2, 2), complex)
        k[a, b] = 1 / np.sqrt(2)
        kraus.append(k)
    branch = []
    for indices in itertools.product(range(4), repeat=n):
        effective = np.zeros((2, 2), complex)
        for start in range(n):
            product = eye.copy()
            for j in range(n):
                product = kraus[indices[(start + j) % n]] @ product
            effective += product / n
        branch.append(effective)
    vectors = [np.array(x, complex) for x in
               [(1, 0), (0, 1), (1, 1), (1, -1), (1, 1j), (1, -1j)]]
    errors, probabilities = [], []
    for vector in vectors:
        vector /= np.linalg.norm(vector)
        rho = np.outer(vector, vector.conj())
        actual = sum((k @ rho @ k.conj().T for k in branch), np.zeros((2, 2), complex))
        expected = eye / (2 * n) + ((n - 1) / (4 * n)) * rho
        errors.append(float(np.max(np.abs(actual - expected))))
        probabilities.append(float(np.trace(actual).real))
    phi = np.array([1, 0, 0, 1], complex) / np.sqrt(2)
    j = np.zeros((4, 4), complex)
    for k in branch:
        vector = np.kron(k, eye) @ phi
        j += np.outer(vector, vector.conj())
    j /= np.trace(j)
    partial_transpose = j.reshape(2, 2, 2, 2).transpose(0, 3, 2, 1).reshape(4, 4)
    minimum = float(np.linalg.eigvalsh(partial_transpose).min())
    return {
        "channels": n, "kraus_tuples": len(branch),
        "herald_probability": probabilities[0],
        "conditional_fidelity_formula": (n + 1) / (n + 3),
        "choi_partial_transpose_min": minimum,
        "formula_partial_transpose_min": (3 - n) / (2 * (n + 3)),
        "max_six_state_error": max(errors),
        "probability_spread": max(probabilities) - min(probabilities),
        "scope": "known construction; no hardware or channel-capacity claim",
    }


def main() -> None:
    cfg = json.loads((ROOT / "protocol/confirmation_freeze.json").read_text())
    for filename, digest in cfg["frozen_inputs"].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest
    tol = cfg["tolerance"]
    rng = np.random.default_rng(cfg["new_test_seed"])
    spectral = []
    for i in range(cfg["spectral_cases"]):
        h = rng.uniform(0.1, 1, size=tuple(cfg["spectral_shape"]))
        h /= h.sum(axis=1, keepdims=True)
        _, _, vt = np.linalg.svd(h, full_matrices=True)
        rank = int(np.linalg.matrix_rank(h))
        delta = vt[rank] * (0.4 / np.max(np.abs(vt[rank])))
        a, b = np.ones(h.shape[1]), np.ones(h.shape[1]) + delta
        error = float(np.max(np.abs(h @ a - h @ b)))
        assert error < tol and b.min() >= cfg["positive_scene_bound"] - tol
        spectral.append({"case": i, "rank": rank, "nullity": h.shape[1] - rank,
                         "max_measurement_difference": error,
                         "minimum_radiance": float(b.min()),
                         "relative_scene_difference": float(np.linalg.norm(delta) / np.linalg.norm(a))})
    roi = []
    for i in range(cfg["roi_cases"]):
        first = rng.uniform(0.1, 2, size=(2, 2))
        while abs(np.linalg.det(first)) < 0.1:
            first = rng.uniform(0.1, 2, size=(2, 2))
        h = np.column_stack([first, first.sum(axis=1) / 3])
        clear = np.array([1, 1, 0])
        occupied = np.array([0, 0, 3])
        error = float(np.max(np.abs(h @ clear - h @ occupied)))
        assert error < tol and h.min() > 0
        # For known strictly positive H and x>=0, Hx=0 implies x=0.
        roi.append({"case": i, "ROI_index": 2, "clear_scene": clear.tolist(),
                    "occupied_scene": occupied.tolist(), "operator": h.tolist(),
                    "max_measurement_difference": error,
                    "ROI_feasible_interval_at_observation": [0, 3],
                    "valid_certificate_at_this_observation": "unknown",
                    "whole_room_at_zero_observation": "clear under known positive operator"})
    q = [quantum(n) for n in cfg["quantum_n"]]
    for item in q:
        assert item["max_six_state_error"] < tol
        assert abs(item["choi_partial_transpose_min"] - item["formula_partial_transpose_min"]) < tol
    output = {
        "schema": "agialpha.independent-probe-confirmation-result.v1",
        "freeze_sha256": hashlib.sha256((ROOT / "protocol/confirmation_freeze.json").read_bytes()).hexdigest(),
        "scope": cfg["scope"], "spectral": spectral, "regional_clearance": roi,
        "quantum": q, "all_assertions_passed": True,
        "discovery_claim": False, "human_or_customer_trial": False,
        "operational_alpha_measured": False,
    }
    destination = ROOT / "results/independent_confirmation.json"
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"spectral_cases": len(spectral), "regional_cases": len(roi),
                      "quantum_cases": len(q), "all_assertions_passed": True}))


if __name__ == "__main__":
    main()
