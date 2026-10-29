# SPDX-License-Identifier: Apache-2.0
"""Source-grounded reduced models; numerical investigations, not physical data."""

from __future__ import annotations

import math
import random
from typing import Any

from .instrument import SCHEMA

SOURCES = {
    "catalyst": "https://doi.org/10.1007/s42452-024-06385-0",
    "membrane": "https://doi.org/10.1016/j.mex.2024.102858",
    "photovoltaic": "https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/singlediode.html",
}


def signal(family: str, parameters: list[float], action: dict[str, Any], independent: bool = False) -> float:
    if family == "catalyst":
        activity, diffusion = parameters
        radius, concentration = float(action["radius"]), float(action["concentration"])
        phi = radius * math.sqrt(activity / diffusion)
        if independent:
            n = 1000

            def integrand(x: float) -> float:
                return x * math.sinh(phi * x) / math.sinh(phi)

            return (
                activity
                * concentration
                / (1 + concentration)
                * (integrand(1) + sum((4 if i % 2 else 2) * integrand(i / n) for i in range(1, n)))
                / n
            )
        eta = 3 / phi**2 * (phi / math.tanh(phi) - 1) if phi > 1e-3 else 1 - phi**2 / 15
        return activity * concentration / (1 + concentration) * eta
    if family == "membrane":
        diffusion, solubility = parameters
        thickness = float(action["thickness"])
        elapsed = float(action["time"])
        if elapsed == 0:
            return diffusion * solubility / thickness
        if independent:
            import numpy as np
            from scipy.linalg import solve_banded  # type: ignore[import-untyped]

            n = 80
            steps = 800
            dx = thickness / n
            dt = elapsed / steps
            r = diffusion * dt / dx**2
            band = np.zeros((3, n - 1))
            band[0, 1:] = -r
            band[1, :] = 1 + 2 * r
            band[2, :-1] = -r
            values = np.zeros(n - 1)
            for _ in range(steps):
                values[0] += r * solubility
                values = solve_banded((1, 1), band, values, check_finite=False)
            return float(diffusion * values[-1] / dx)
        ratio = diffusion * elapsed / thickness**2
        terms = 160 if independent else 80
        fractional = 1 + 2 * sum((-1) ** n * math.exp(-n * n * math.pi**2 * ratio) for n in range(1, terms))
        return float(diffusion * solubility / thickness * fractional)
    if family == "photovoltaic":
        series, shunt = parameters
        voltage, irradiance = float(action["voltage"]), float(action["irradiance"])

        def residual(current: float) -> float:
            junction = voltage + current * series
            return 5 * irradiance - 1e-7 * math.expm1(junction / 1.5) - junction / shunt - current

        lo, hi = -10.0, 6.0
        if not independent:
            from scipy.optimize import brentq  # type: ignore[import-untyped]

            return float(brentq(residual, lo, hi, xtol=1e-12))
        for _ in range(90):
            mid = (lo + hi) / 2
            if residual(mid) > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    raise ValueError("unsupported model family")


def make_task(family: str, seed: int, variant: int = 0) -> tuple[dict[str, Any], dict[str, Any]]:
    rng = random.Random(seed)
    if family == "catalyst":
        params = [[0.8, 0.02], [1.2, 0.012], [1.6, 0.008], [0.6, 0.1], [1.8, 0.2], [1.0, 0.05]]
        actions = [{"radius": r, "concentration": c} for r in [0.1, 0.7, 2.0] for c in [0.2, 2.0, 8.0]]
        decisions = ["regenerate" if p[0] < 1.1 else "reduce_particle" for p in params]
        noise = 0.012
    elif family == "membrane":
        params = [[0.2, 5.0], [0.5, 2.0], [1.0, 1.0], [2.0, 0.5], [0.25, 2.0], [0.5, 1.0]]
        actions = [
            {"thickness": thickness_value, "time": t} for thickness_value in [1.0, 2.0, 3.0] for t in [0.0, 0.2, 1.0]
        ]
        decisions = ["diffusion_limited" if p[0] < 0.6 else "sorption_limited" for p in params]
        noise = 0.015
    elif family == "photovoltaic":
        params = [[0.1, 150.0], [0.5, 150.0], [0.1, 20.0], [0.5, 20.0], [0.25, 60.0], [0.7, 60.0]]
        actions = [{"voltage": v, "irradiance": g} for v in [0.0, 12.0, 22.0] for g in [0.25, 0.6, 1.0]]
        decisions = ["shunt_loss" if p[1] <= 60 else "series_loss" for p in params]
        noise = 0.035
    else:
        raise ValueError("family")
    rng.shuffle(actions)
    if variant % 4 == 1:
        actions = [
            a
            for a in actions
            if (
                a.get("time", 1) == 0
                if family == "membrane"
                else a.get("radius", 0.1) > 0.5
                if family == "catalyst"
                else a.get("voltage", 0) > 0
            )
        ]
    if variant % 4 == 2:
        noise *= 6
    if variant % 4 == 3:
        actions = actions[:3]
    models: list[dict[str, Any]] = [{"id": f"m{i}", "decision": d} for i, d in enumerate(decisions)]
    exps: list[dict[str, Any]] = []
    for i, action in enumerate(actions):
        prediction = {}
        for j, parameter in enumerate(params):
            value = signal(family, parameter, action)
            prediction[f"m{j}"] = [f"{value - noise:.10f}", f"{value + noise:.10f}"]
        exps.append({"id": f"e{i}", "cost": rng.randint(1, 5), "prediction": prediction, "action": action})
    task = {
        "schema": SCHEMA,
        "id": f"{family}-{seed}-{variant}",
        "source": SOURCES[family],
        "models": models,
        "experiments": exps,
        "budget": sum(e["cost"] for e in exps) if variant % 4 != 3 else 2,
        "assumptions": [
            "Finite candidate models; model completeness unverified",
            "Bounded noise assumed, not calibrated",
            "Costs are experimental units, not money",
            "No physical sensors or plant actuation",
        ],
    }
    private = {"family": family, "parameters": params, "truth": rng.randrange(len(params)), "noise": noise}
    return task, private


def investigate(task: dict[str, Any], private: dict[str, Any], selected: list[str]) -> dict[str, str]:
    outputs = {}
    for experiment in task["experiments"]:
        if experiment["id"] in selected:
            result = signal(
                private["family"], private["parameters"][private["truth"]], experiment["action"], independent=True
            )
            outputs[experiment["id"]] = f"{result:.10f}"
    return outputs
