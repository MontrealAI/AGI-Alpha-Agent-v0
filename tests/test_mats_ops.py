# SPDX-License-Identifier: Apache-2.0
import unittest
import random

from alpha_factory_v1.core.simulation import GaussianParam
from alpha_factory_v1.core.simulation import mats


def _diversity(pop: list[mats.Individual]) -> float:
    if len(pop) < 2:
        return 0.0
    dists = []
    for i, pop in enumerate(pop):
        for j in range(i + 1, len(pop)):
            a = pop[i].genome
            b = pop[j].genome
            d = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
            dists.append(d)
    return sum(dists) / len(dists)


class TestMatsOps(unittest.TestCase):
    def test_gaussian_param_bounds_and_diversity(self) -> None:
        rng = random.Random(123)
        pop = [mats.Individual([rng.uniform(-0.05, 0.05) for _ in range(2)]) for _ in range(10)]
        base_div = _diversity(pop)
        op = GaussianParam(std=0.3, rng=rng)
        mutated = [mats.Individual(op(ind.genome)) for ind in pop]
        after_div = _diversity(mutated)
        for ind in mutated:
            for gene in ind.genome:
                self.assertGreaterEqual(gene, -1.0)
                self.assertLessEqual(gene, 1.0)
        self.assertGreater(after_div, base_div * 1.3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
