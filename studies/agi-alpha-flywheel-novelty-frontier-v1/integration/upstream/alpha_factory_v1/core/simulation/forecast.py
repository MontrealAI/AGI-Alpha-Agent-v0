# SPDX-License-Identifier: Apache-2.0
"""Utility functions for projecting sector disruption.

This module implements a very small toy model using a logistic capability
curve and a thermodynamic trigger based on free energy. The helpers
``forecast_disruptions`` and ``simulate_years`` drive the demo's forecast
visualisations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List

from .sector import Sector
from . import mats
from ..evaluators import lead_time


@dataclass(slots=True)
class ForecastPoint:
    year: int
    capability: float
    affected: List[Sector]


@dataclass(slots=True)
class TrajectoryPoint:
    """Detailed snapshot for a single year."""

    year: int
    capability: float
    sectors: List[Sector]


def logistic_curve(t: float, k: float = 1.0, x0: float = 0.0) -> float:
    """Return a logistic curve value for ``t``.

    Args:
        t: Normalised time value.
        k: Growth rate controlling the steepness.
        x0: Midpoint shift.

    Returns:
        Value in the ``[0, 1]`` range.
    """

    return 1.0 / (1.0 + math.exp(-k * (t - x0)))


def linear_curve(t: float) -> float:
    return max(0.0, min(1.0, t))


def exponential_curve(t: float, k: float = 3.0, x0: float = 0.0) -> float:
    """Return an exponential curve value for ``t``.

    Args:
        t: Normalised time value.
        k: Exponential growth factor.
        x0: Time shift applied before scaling.

    Returns:
        Value in the ``[0, 1]`` range.
    """

    scale = math.exp(k) - 1.0
    val = (math.exp(k * (t - x0)) - 1.0) / scale
    return max(0.0, min(1.0, val))


def capability_growth(
    t: float,
    curve: str = "logistic",
    *,
    k: float | None = None,
    x0: float | None = None,
) -> float:
    """Dispatch to the configured growth curve."""

    if curve == "linear":
        return linear_curve(t)
    if curve == "exponential":
        return exponential_curve(t, k=k or 3.0, x0=x0 or 0.0)
    return logistic_curve(t, k=k or 10.0, x0=x0 or 0.0)


def free_energy(sector: Sector, capability: float) -> float:
    return sector.energy - capability * sector.entropy


def thermodynamic_trigger(sector: Sector, capability: float) -> bool:
    return free_energy(sector, capability) < 0


def _innovation_gain(
    pop_size: int = 6,
    generations: int = 1,
    *,
    seed: int | None = None,
    mut_rate: float = 0.1,
    xover_rate: float = 0.5,
) -> float:
    """Return a small gain from a short MATS run.

    Args:
        pop_size: Number of individuals in the MATS population.
        generations: Number of evolution steps.
        seed: Optional RNG seed for deterministic output.
        mut_rate: Probability of mutating a gene.
        xover_rate: Probability of performing crossover.
    """

    def fn(genome: list[float]) -> tuple[float, float, float, float]:
        x, y = genome
        effectiveness = x**2
        negative_evar = y**2
        complexity = (x + y) ** 2
        history = [1.0, 1.0, 1.0]
        base = lead_time._arima_baseline(history, 3)
        forecast_series = [b + x + y for b in base]
        lead_impr = lead_time.lead_signal_improvement(history, forecast_series, months=3, threshold=1.1)
        lead_penalty = 1.0 - lead_impr
        return effectiveness, negative_evar, complexity, lead_penalty

    pop = mats.run_evolution(
        fn,
        2,
        population_size=pop_size,
        mutation_rate=mut_rate,
        crossover_rate=xover_rate,
        generations=generations,
        seed=seed,
    )
    m = len(pop[0].fitness or ())
    best = min(pop, key=lambda ind: sum(ind.fitness or (0.0,) * m))
    return 0.1 / (1.0 + sum(best.fitness or (0.0,) * m))


def forecast_disruptions(
    sectors: Iterable[Sector],
    horizon: int,
    curve: str = "logistic",
    *,
    k: float | None = None,
    x0: float | None = None,
    pop_size: int = 6,
    generations: int = 1,
    seed: int | None = None,
    mut_rate: float = 0.1,
    xover_rate: float = 0.5,
) -> List[TrajectoryPoint]:
    """Simulate sector trajectories and disruption events.

    Args:
        sectors: Iterable of sectors to simulate.
        horizon: Number of years to simulate.
        curve: Name of the capability growth curve.
        k: Optional curve steepness parameter.
        x0: Optional curve midpoint shift.
        pop_size: Population size for the evolutionary search.
        generations: Number of evolution steps.
        seed: Random seed for deterministic behaviour.
        mut_rate: Probability of mutating a gene.
        xover_rate: Probability of performing crossover.

    Returns:
        List of trajectory points for each simulated year.
    """

    secs = list(sectors)
    results: List[TrajectoryPoint] = []
    for year in range(1, horizon + 1):
        t = year / horizon
        cap = capability_growth(t, curve, k=k, x0=x0)
        affected: List[Sector] = []
        for sec in secs:
            if not sec.disrupted:
                sec.energy *= 1.0 + sec.growth
                if thermodynamic_trigger(sec, cap):
                    sec.disrupted = True
                    sec.energy += _innovation_gain(
                        pop_size,
                        generations,
                        seed=seed,
                        mut_rate=mut_rate,
                        xover_rate=xover_rate,
                    )
                    affected.append(sec)
        snapshot = [Sector(s.name, s.energy, s.entropy, s.growth, s.disrupted) for s in secs]
        results.append(TrajectoryPoint(year, cap, snapshot))
    return results


def simulate_years(sectors: Iterable[Sector], horizon: int) -> List[ForecastPoint]:
    results: List[ForecastPoint] = []
    traj = forecast_disruptions(sectors, horizon)
    for point in traj:
        affected = [s for s in point.sectors if s.disrupted]
        results.append(ForecastPoint(point.year, point.capability, affected))
    return results
