# SPDX-License-Identifier: Apache-2.0
from alpha_factory_v1.core.simulation import mats
from alpha_factory_v1.core.evaluators.novelty import NoveltyIndex
import pytest


@pytest.fixture(autouse=True)
def _reset_islands() -> None:
    mats.ISLANDS.clear()
    mats.ISLAND_SEEDS.clear()


def test_run_evolution_deterministic() -> None:
    def fn(genome: list[float]) -> tuple[float, float]:
        x, y = genome
        return x**2, y**2

    pop1 = mats.run_evolution(fn, 2, population_size=4, generations=3, mutation_rate=0.5, seed=123, novelty_index=None)
    pop2 = mats.run_evolution(fn, 2, population_size=4, generations=3, mutation_rate=0.5, seed=123, novelty_index=None)

    assert [ind.genome for ind in pop1] == [ind.genome for ind in pop2]
    assert any(any(g != 0 for g in ind.genome) for ind in pop1)


def test_run_evolution_evaluates_population() -> None:
    def fn(genome: list[float]) -> tuple[float, float]:
        x, y = genome
        return abs(x), abs(y)

    pop = mats.run_evolution(fn, 2, population_size=3, generations=1, seed=1, novelty_index=None)

    assert len(pop) == 3
    assert all(ind.fitness is not None for ind in pop)


def test_run_evolution_different_seeds() -> None:
    def fn(genome: list[float]) -> tuple[float, float]:
        x, y = genome
        return x**2, y**2

    pop1 = mats.run_evolution(fn, 2, population_size=3, generations=1, seed=1, novelty_index=None)
    pop2 = mats.run_evolution(fn, 2, population_size=3, generations=1, seed=2, novelty_index=None)
    pop1b = mats.run_evolution(fn, 2, population_size=3, generations=1, seed=1, novelty_index=None)

    assert [ind.genome for ind in pop1] != [ind.genome for ind in pop2]
    assert [ind.genome for ind in pop1] == [ind.genome for ind in pop1b]


def test_run_evolution_three_objectives() -> None:
    def fn(genome: list[float]) -> tuple[float, float, float]:
        x, y = genome
        return x**2, y**2, (x + y) ** 2

    pop = mats.run_evolution(fn, 2, population_size=4, generations=2, seed=42, novelty_index=None)

    assert all(len(ind.fitness or ()) == 3 for ind in pop)


def test_pareto_front_after_five_generations() -> None:
    def fn(genome: list[float]) -> tuple[float, float]:
        x, y = genome
        return x**2, y**2

    pop = mats.run_evolution(
        fn,
        2,
        population_size=20,
        generations=5,
        seed=42,
        scenario_hash="test",
        novelty_index=None,
    )
    front = mats.pareto_front(pop)
    assert len(front) >= 10


def test_novelty_divergence_for_elites() -> None:
    pytest.importorskip("sentence_transformers")

    def fn(genome: list[float]) -> tuple[float, float]:
        x, y = genome
        return x**2, y**2

    idx = NoveltyIndex()
    idx.add("0.0,0.0")

    pop = mats.run_evolution(
        fn,
        2,
        population_size=6,
        generations=1,
        seed=1,
        novelty_index=idx,
    )
    front = mats.pareto_front(pop)
    novelties = [ind.fitness[-1] for ind in front]
    assert sum(n > 0.3 for n in novelties) >= len(novelties) - 1
