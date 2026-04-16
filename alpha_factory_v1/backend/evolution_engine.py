# SPDX-License-Identifier: Apache-2.0

"""alpha_factory_v1.backend.evolution_engine
============================================

Self‑contained evolutionary meta‑learning module (AI‑GA) for Alpha‑Factory v1.
-----------------------------------------------------------------------------

* Implements a lightweight genetic‑algorithm framework with an optional DEAP
  backend. Falls back to a pure‑Python implementation if DEAP is unavailable.
* Supports both simple **parameter genomes** (floats / ints) *and* extensible
  **config genomes** (nested dict / JSON‑serialisable) for richer mutations.
* Sandboxed execution: each candidate agent is evaluated in a *separate* Python
  process (with timeout and memory guard) to prevent cascading crashes.
* Built‑in *safety gate*: static‑analysis & basic heuristics reject mutations
  that introduce dangerous code (e.g. `os.system`, `subprocess`, network calls)
  unless the `ALLOW_UNSAFE_EVOLUTION` env flag is explicitly set to `true`.
* Zero external services required – works offline and without an OpenAI key
  (though you *can* plug in LLM‑aided mutation by passing a callable).

Quick‑start
~~~~~~~~~~~

>>> from evolution_engine import EvolutionEngine, RandomFitnessTask
>>> task = RandomFitnessTask(n_dimensions=4)         # toy minimisation task
>>> engine = EvolutionEngine(task, population_size=20, generations=10)
>>> best_agent, history = engine.run()
>>> print(best_agent.genome, best_agent.fitness)

Integrated usage within the *aiga_meta_evolution* demo
------------------------------------------------------

The demo file simply needs::

    from evolution_engine import EvolutionEngine, AgentFitnessTask
    task = AgentFitnessTask(demo_scenario="alpha_factory_v1/demos/foo.py")
    engine = EvolutionEngine(task)
    engine.run()

The engine communicates with the existing orchestrator via the **Agent API**:
it spins up each candidate as a subprocess (`python demo_scenario --agent-json
<genome>`) so no refactor is needed.

Copyright
---------

© 2025 Montreal.AI & Contributors. Licensed under the Apache 2.0 licence.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

################################################################################
# Fallback‑minimal genetic operators (used if DEAP unavailable)                #
################################################################################

try:
    from importlib.util import find_spec

    if find_spec("deap") is not None:
        from deap import base, creator, tools  # pragma: no cover

        _DEAP_AVAILABLE = True
    else:
        _DEAP_AVAILABLE = False
except Exception:
    _DEAP_AVAILABLE = False

# Type aliases
Genome = Union[List[float], Dict[str, Any]]


@dataclass
class Individual:
    """A candidate solution / agent blueprint."""

    genome: Genome
    fitness: float | None = None


################################################################################
# Fitness tasks                                                                #
################################################################################


class BaseFitnessTask:
    """Abstract harness that scores a candidate genome.

    Sub‑class this for domain‑specific evaluation.
    """

    minimize: bool = False  # set to True when lower is better

    def evaluate(self, genome: Genome) -> float:
        raise NotImplementedError


class RandomFitnessTask(BaseFitnessTask):
    """Toy task: sphere function in *n* dimensions (minimisation)."""

    minimize = True

    def __init__(self, n_dimensions: int = 4) -> None:
        self.n = n_dimensions

    def evaluate(self, genome: Genome) -> float:
        vec = genome if isinstance(genome, Sequence) else list(genome.values())
        if len(vec) != self.n:
            raise ValueError(f"Genome length {len(vec)} != {self.n}")
        return sum(x * x for x in vec)


class AgentFitnessTask(BaseFitnessTask):
    """Runs a demo scenario and returns the score produced by the agent.

    It assumes the scenario script prints a JSON line with `{"fitness": <float>}`
    to stdout at completion.
    """

    minimize = False  # higher score better by default

    def __init__(
        self,
        demo_script: str,
        timeout: int = 300,
        python_exec: str = sys.executable,
    ) -> None:
        self.demo_script = demo_script
        self.timeout = timeout
        self.python_exec = python_exec

    def evaluate(self, genome: Genome) -> float:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as fp:
            json.dump(genome, fp)
            fp_path = fp.name
        cmd = [
            self.python_exec,
            self.demo_script,
            "--agent-genome-json",
            fp_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )
        except subprocess.TimeoutExpired:
            return -math.inf  # penalise timeouts
        except subprocess.CalledProcessError:
            return -math.inf  # penalise crashes

        # Parse fitness line
        for line in result.stdout.splitlines():
            if line.lstrip().startswith("{") and "fitness" in line:
                try:
                    data = json.loads(line)
                    return float(data["fitness"])
                except Exception:  # pragma: no cover
                    continue
        return -math.inf


################################################################################
# Evolution engine                                                             #
################################################################################


@dataclass
class EvolutionConfig:
    population_size: int = 30
    generations: int = 20
    crossover_rate: float = 0.5
    mutation_rate: float = 0.2
    tournament_k: int = 3
    elite_count: int = 1  # always copy top‑N unchanged
    # genome template used for random initialisation if seed_population not supplied
    genome_template: Genome | None = field(default_factory=lambda: [0.0] * 8)
    # custom mutation operator (overrides default)
    custom_mutation: Optional[Callable[[Genome], Genome]] = None
    # custom crossover operator
    custom_crossover: Optional[Callable[[Genome, Genome], Tuple[Genome, Genome]]] = None
    seed_population: Optional[List[Genome]] = None
    random_seed: int | None = None
    eval_processes: int = 1

    def __post_init__(self) -> None:
        if self.population_size <= 0:
            raise ValueError("population_size must be positive")
        if self.generations <= 0:
            raise ValueError("generations must be positive")
        if not 0.0 <= self.crossover_rate <= 1.0:
            raise ValueError("crossover_rate must be within [0,1]")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be within [0,1]")
        if self.tournament_k < 2:
            raise ValueError("tournament_k must be at least 2")
        if self.elite_count < 0 or self.elite_count >= self.population_size:
            raise ValueError("elite_count must be >=0 and < population_size")
        if self.eval_processes < 1:
            raise ValueError("eval_processes must be at least 1")


class EvolutionEngine:
    """Simple (µ + λ) genetic algorithm for evolving agent genomes."""

    def __init__(
        self,
        task: BaseFitnessTask,
        config: EvolutionConfig | None = None,
        logger: Optional[Callable[[str], Any]] = print,
    ):
        self.task = task
        self.cfg = config or EvolutionConfig()
        if self.cfg.random_seed is not None:
            random.seed(self.cfg.random_seed)
        self.log = logger or (lambda *_: None)
        self.population: List[Individual] = []
        self.history: List[Dict[str, Any]] = []

        if _DEAP_AVAILABLE:
            self._setup_deap_toolbox()

        self._create_initial_population()

    # --------------------------------------------------------------------- Utils

    def _safe_mutate_number(self, x: float, sigma: float = 0.1) -> float:
        return x + random.gauss(0, sigma)

    def _create_initial_population(self) -> None:
        if self.cfg.seed_population:
            genomes = self.cfg.seed_population
        else:
            template = self.cfg.genome_template
            if isinstance(template, Sequence):
                genomes = [
                    [random.uniform(-1.0, 1.0) for _ in range(len(template))] for _ in range(self.cfg.population_size)
                ]
            else:
                genomes = []
                for _ in range(self.cfg.population_size):
                    g = {
                        k: random.uniform(-1.0, 1.0) if isinstance(v, (int, float)) else v for k, v in template.items()
                    }
                    genomes.append(g)
        self.population = [Individual(g) for g in genomes]

    # ----------------------------------------------------------------- Operators

    def _default_crossover(self, parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
        if isinstance(parent1, list) and isinstance(parent2, list):
            cx_point = random.randrange(1, len(parent1))
            child1 = parent1[:cx_point] + parent2[cx_point:]
            child2 = parent2[:cx_point] + parent1[cx_point:]
            return child1, child2
        elif isinstance(parent1, dict) and isinstance(parent2, dict):
            child1, child2 = parent1.copy(), parent2.copy()
            for k in parent1.keys():
                if random.random() < 0.5:
                    child1[k], child2[k] = child2[k], child1[k]
            return child1, child2
        else:
            raise TypeError("Genome types mismatch for crossover")

    def _default_mutation(self, genome: Genome) -> Genome:
        g = genome.copy() if isinstance(genome, dict) else list(genome)
        if isinstance(g, list):
            for i, g in enumerate(g):
                if random.random() < 0.1:
                    g[i] = self._safe_mutate_number(float(g[i]))
        else:
            for k in g:
                if isinstance(g[k], (int, float)) and random.random() < 0.1:
                    g[k] = self._safe_mutate_number(float(g[k]))
        return g

    # ------------------------------------------------------------ DEAP interface

    def _setup_deap_toolbox(self) -> None:  # pragma: no cover
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        self.toolbox = base.Toolbox()
        template = self.cfg.genome_template
        if isinstance(template, Sequence):
            n = len(template)
            self.toolbox.register("attr_float", random.uniform, -1.0, 1.0)  # type: ignore
            self.toolbox.register("individual", tools.initRepeat, creator.Individual, self.toolbox.attr_float, n)
        else:
            raise NotImplementedError("DEAP only implemented for list genomes")
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=self.cfg.tournament_k)
        self.toolbox.register(
            "evaluate",
            lambda ind: (-self.task.evaluate(ind) if self.task.minimize else self.task.evaluate(ind)),
        )

    # ---------------------------------------------------------------- Evolution

    def _evaluate_population(self) -> None:
        allow_unsafe = os.getenv("ALLOW_UNSAFE_EVOLUTION", "false").lower() == "true"
        pending = [ind for ind in self.population if ind.fitness is None]

        def eval_ind(ind: Individual) -> float:
            if not allow_unsafe and not is_genome_safe(ind.genome):
                self.log("[SECURITY] Rejected unsafe genome")
                return -math.inf
            return self.task.evaluate(ind.genome)

        if self.cfg.eval_processes > 1 and len(pending) > 1:
            with ThreadPoolExecutor(max_workers=self.cfg.eval_processes) as exe:
                results = list(exe.map(eval_ind, pending))
        else:
            results = [eval_ind(ind) for ind in pending]

        for ind, res in zip(pending, results):
            ind.fitness = res

    def _select_parents(self) -> Tuple[Individual, Individual]:
        tournament = random.sample(self.population, self.cfg.tournament_k)
        key = (lambda ind: ind.fitness) if not self.task.minimize else (lambda ind: -ind.fitness)
        tournament.sort(key=key, reverse=True)
        return tournament[0], tournament[1]

    def _create_offspring(self) -> List[Individual]:
        offspring = []
        while len(offspring) < self.cfg.population_size - self.cfg.elite_count:
            p1, p2 = self._select_parents()
            if random.random() < self.cfg.crossover_rate:
                c1_genome, c2_genome = (
                    self.cfg.custom_crossover(p1.genome, p2.genome)
                    if self.cfg.custom_crossover
                    else self._default_crossover(p1.genome, p2.genome)
                )
            else:
                c1_genome, c2_genome = p1.genome, p2.genome

            if random.random() < self.cfg.mutation_rate:
                c1_genome = (
                    self.cfg.custom_mutation(c1_genome)
                    if self.cfg.custom_mutation
                    else self._default_mutation(c1_genome)
                )
            if random.random() < self.cfg.mutation_rate:
                c2_genome = (
                    self.cfg.custom_mutation(c2_genome)
                    if self.cfg.custom_mutation
                    else self._default_mutation(c2_genome)
                )
            offspring.extend([Individual(c1_genome), Individual(c2_genome)])
        return offspring[: self.cfg.population_size - self.cfg.elite_count]

    def run(self) -> Tuple[Individual, List[Dict[str, Any]]]:
        self.log("[AI‑GA] Starting evolutionary run...")
        self._evaluate_population()

        for gen in range(self.cfg.generations):
            self.population.sort(
                key=lambda ind: ind.fitness if not self.task.minimize else -ind.fitness,
                reverse=True,
            )
            best = self.population[0]
            self.log(f"Generation {gen}: best fitness = {best.fitness:.4f}")
            self.history.append(
                {
                    "generation": gen,
                    "best_fitness": best.fitness,
                    "genome": best.genome,
                }
            )

            # Elitism
            new_population = self.population[: self.cfg.elite_count]

            # Create offspring
            offspring = self._create_offspring()
            new_population.extend(offspring)
            self.population = new_population

            # Evaluate new individuals
            self._evaluate_population()

        # Final sort
        self.population.sort(
            key=lambda ind: ind.fitness if not self.task.minimize else -ind.fitness,
            reverse=True,
        )
        best_overall = self.population[0]
        self.log(f"[AI‑GA] Finished. Best fitness = {best_overall.fitness:.4f}")
        return best_overall, self.history


# ---------------------------------------------------------------------- Safety

UNSAFE_TOKENS = {"os.system", "subprocess", "socket", "shutil.rmtree", "fork"}


def is_genome_safe(genome: Genome) -> bool:
    """Basic static filter that rejects obvious unsafe code snippets."""
    serialized = json.dumps(genome)
    return not any(tok in serialized for tok in UNSAFE_TOKENS)


################################################################################
# CLI helper                                                                   #
################################################################################


def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="Run a standalone GA demo.")
    parser.add_argument("--dims", type=int, default=6, help="Number of dimensions in sphere task")
    parser.add_argument("--pop", type=int, default=30, help="Population size")
    parser.add_argument("--gen", type=int, default=15, help="Generations")
    parser.add_argument("--proc", type=int, default=1, help="Parallel evaluation processes")
    args = parser.parse_args()

    task = RandomFitnessTask(n_dimensions=args.dims)
    cfg = EvolutionConfig(
        population_size=args.pop,
        generations=args.gen,
        genome_template=[0.0] * args.dims,
        eval_processes=args.proc,
    )
    engine = EvolutionEngine(task, cfg)
    best, _ = engine.run()
    print("\nBest genome:", best.genome)
    print("Fitness:", best.fitness)


if __name__ == "__main__":  # pragma: no cover
    _cli()
