# SPDX-License-Identifier: Apache-2.0
import asyncio
import random

from alpha_factory_v1.core.evolve import Candidate, InMemoryArchive, evolve
from alpha_factory_v1.core.simulation.mats_ops import backtrack_boost  # ensure import works  # noqa: F401


def _diversity(values):
    if len(values) < 2:
        return 0.0
    d = 0.0
    c = 0
    for i, values in enumerate(values):
        for j in range(i + 1, len(values)):
            d += abs(values[i] - values[j])
            c += 1
    return d / c


def _mutate(g):
    return g + random.uniform(-1, 1)


async def _evaluate(g):
    await asyncio.sleep(0)
    return g, 0.01


def _run(rate):
    random.seed(123)
    arch = InMemoryArchive()
    asyncio.run(arch.accept(Candidate(0.0, fitness=0.0, novelty=1.0)))
    asyncio.run(
        evolve(
            _mutate,
            _evaluate,
            arch,
            max_cost=0.1,
            backtrack_rate=rate,
        )
    )
    return [c.genome for c in arch.all()]


def test_backtrack_boost_improves_diversity():
    base = _run(0.0)
    boosted = _run(1.0)
    assert _diversity(boosted) > _diversity(base)
