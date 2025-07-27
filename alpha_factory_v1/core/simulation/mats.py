# SPDX-License-Identifier: Apache-2.0
"""Minimal multi-objective evolutionary algorithm.

This module implements a tiny subset of the NSGA‑II algorithm. The
``Individual`` dataclass stores genomes and fitness, while
``run_evolution`` executes several generations of crossover and mutation.
It is intentionally lightweight and not a full-featured implementation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterable, List, Tuple
import numpy as np

from alpha_factory_v1.core.evaluators.novelty import NoveltyIndex
from alpha_factory_v1.core.simulation import surrogate_fitness

__all__ = [
    "Individual",
    "Population",
    "evaluate",
    "pareto_front",
    "run_evolution",
]

# Keep per-scenario populations for island-style evolution.
ISLANDS: dict[str, "Population"] = {}
ISLAND_SEEDS: dict[str, int | None] = {}


@dataclass(slots=True)
class Individual:
    genome: List[float]
    fitness: Tuple[float, ...] | None = None
    crowd: float = 0.0
    rank: int = 0
    score: float = 0.0


Population = List[Individual]


def evaluate(
    pop: Population,
    fn: Callable[[List[float]], Tuple[float, ...]],
    novelty: NoveltyIndex | None = None,
    critics: Iterable[Callable[[List[float]], float]] | None = None,
) -> None:
    """Assign fitness scores using ``fn`` plus ``critics`` and optional novelty."""

    for ind in pop:
        base = fn(ind.genome)
        extra = tuple(c(ind.genome) for c in (critics or []))
        if novelty is not None:
            spec = ",".join(f"{g:.3f}" for g in ind.genome)
            div = novelty.divergence(spec)
            ind.fitness = base + extra + (div,)
        else:
            ind.fitness = base + extra

    fits = [ind.fitness or () for ind in pop]
    scores = surrogate_fitness.aggregate(fits)
    for ind, sc in zip(pop, scores):
        ind.score = sc


def _crowding(pop: Population) -> None:
    """Compute the crowding distance for a Pareto front."""

    if not pop or pop[0].fitness is None:
        return
    m = len(pop[0].fitness)
    for ind in pop:
        ind.crowd = 0.0
    for i in range(m):
        pop.sort(key=lambda x: (x.fitness or (0.0,) * m)[i])
        first_fit = pop[0].fitness
        last_fit = pop[-1].fitness
        assert first_fit is not None and last_fit is not None
        pop[0].crowd = pop[-1].crowd = float("inf")
        fmin = first_fit[i]
        fmax = last_fit[i]
        span = fmax - fmin or 1.0
        for j in range(1, len(pop) - 1):
            prev_fit = pop[j - 1].fitness
            next_fit = pop[j + 1].fitness
            assert prev_fit is not None and next_fit is not None
            prev_f = prev_fit[i]
            next_f = next_fit[i]
            pop[j].crowd += (next_f - prev_f) / span


def _non_dominated_sort(pop: Population) -> List[Population]:
    """Group ``pop`` into Pareto fronts."""

    fronts: List[Population] = []
    S: dict[int, list[Individual]] = {id(ind): [] for ind in pop}
    n: dict[int, int] = {id(ind): 0 for ind in pop}
    for ind in pop:
        assert ind.fitness is not None
    for p in pop:
        for q in pop:
            if p is q:
                continue
            assert q.fitness is not None
            assert p.fitness is not None
            if all(pf <= qf for pf, qf in zip(p.fitness, q.fitness)):
                if any(pf < qf for pf, qf in zip(p.fitness, q.fitness)):
                    S[id(p)].append(q)
            elif all(qf <= pf for pf, qf in zip(p.fitness, q.fitness)):
                if any(qf < pf for pf, qf in zip(p.fitness, q.fitness)):
                    n[id(p)] += 1
        if n[id(p)] == 0:
            p.rank = 0
            if not fronts:
                fronts.append([])
            fronts[0].append(p)
    i = 0
    while i < len(fronts):
        nxt: Population = []
        for p in fronts[i]:
            for q in S[id(p)]:
                n[id(q)] -= 1
                if n[id(q)] == 0:
                    q.rank = i + 1
                    nxt.append(q)
        if nxt:
            fronts.append(nxt)
        i += 1
    return fronts


def _evolve_step(
    pop: Population,
    fn: Callable[[List[float]], Tuple[float, ...]],
    *,
    rng: random.Random,
    mutation_rate: float,
    crossover_rate: float,
    novelty: NoveltyIndex | None = None,
    critics: Iterable[Callable[[List[float]], float]] | None = None,
) -> Population:
    """Return the next generation from ``pop`` using NSGA‑II."""

    evaluate(pop, fn, novelty, critics)
    mu = len(pop)
    genome_length = len(pop[0].genome)
    offspring: Population = []
    while len(offspring) < mu:
        a, b = rng.sample(pop, 2)
        if genome_length > 1 and rng.random() < crossover_rate:
            cut = rng.randint(1, genome_length - 1)
            child_genome = a.genome[:cut] + b.genome[cut:]
        else:
            child_genome = list(a.genome)
        if rng.random() < mutation_rate:
            idx = rng.randrange(genome_length)
            child_genome[idx] += rng.uniform(-1, 1)
        offspring.append(Individual(child_genome))
    evaluate(offspring, fn, novelty, critics)
    union = pop + offspring
    fronts = _non_dominated_sort(union)
    new_pop: Population = []
    for front in fronts:
        _crowding(front)
        front.sort(key=lambda x: (-x.rank, -x.crowd))
        for ind in front:
            if len(new_pop) < mu:
                new_pop.append(ind)
    return new_pop


def run_evolution(
    fn: Callable[[List[float]], Tuple[float, ...]],
    genome_length: int,
    *,
    population_size: int = 20,
    mutation_rate: float = 0.1,
    crossover_rate: float = 0.5,
    generations: int = 10,
    seed: int | None = None,
    scenario_hash: str | None = None,
    populations: dict[str, Population] | None = None,
    exchange_interval: int = 5,
    novelty_index: NoveltyIndex | None = None,
    critics: Iterable[Callable[[List[float]], float]] | None = None,
) -> Population:
    """Run an NSGA-II optimisation.

    Args:
        fn: Function evaluating an individual's genome.
        genome_length: Number of float genes per individual.
        population_size: Number of individuals preserved each generation.
        mutation_rate: Probability of mutating a gene during crossover.
        crossover_rate: Probability of performing crossover between parents.
        generations: Number of NSGA-II steps to perform.
        seed: Optional random seed for deterministic behaviour.
        scenario_hash: Key identifying the island population.
        populations: Mapping of existing island populations.
        exchange_interval: Exchange elites every ``exchange_interval`` generations.

    Returns:
        The final population after ``generations`` steps.
    """

    rng = random.Random(seed)
    islands = populations if populations is not None else ISLANDS
    key = scenario_hash or "default"
    novelty = novelty_index

    pop = None if populations is None else islands.get(key)
    ISLAND_SEEDS[key] = seed
    if pop is None:
        pop = [Individual([rng.uniform(-1, 1) for _ in range(genome_length)]) for _ in range(population_size)]
    islands[key] = pop

    for gen in range(generations):
        pop = _evolve_step(
            islands[key],
            fn,
            rng=rng,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            novelty=novelty,
            critics=critics,
        )
        islands[key] = pop
        if exchange_interval and (gen + 1) % exchange_interval == 0 and len(islands) > 1:
            elite_map = {k: pareto_front(p)[:2] for k, p in islands.items()}
            for k, island_pop in islands.items():
                others = [ind for ok, e in elite_map.items() if ok != k for ind in e]
                for ind in others:
                    repl = rng.randrange(len(island_pop))
                    island_pop[repl] = Individual(list(ind.genome))
                evaluate(island_pop, fn, novelty, critics)

    return islands[key]


def pareto_front(pop: Population) -> Population:
    """Return the non-dominated set ranked by crowding distance."""

    if not pop:
        return []

    fits = np.asarray([ind.fitness for ind in pop], dtype=float)
    dominated = np.zeros(len(pop), dtype=bool)
    for i, fi in enumerate(fits):
        dom = np.all(fi <= fits, axis=1) & np.any(fi < fits, axis=1)
        dominated |= dom
        dominated[i] = False
    front = [ind for ind, d in zip(pop, dominated) if not d]
    _crowding(front)
    return sorted(front, key=lambda x: -x.crowd)
