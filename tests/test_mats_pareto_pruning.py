# SPDX-License-Identifier: Apache-2.0
"""Differential and scalar-oracle checks for ordered Pareto source pruning."""

from __future__ import annotations

import itertools
import math
import random
import unittest
from unittest.mock import patch

import numpy as np

from alpha_factory_v1.core.simulation import mats


def _reference(pop: mats.Population) -> mats.Population:
    """Retain the original all-pairs implementation as a differential oracle."""
    if not pop:
        return []
    fits = np.asarray([ind.fitness for ind in pop], dtype=float)
    dominated = np.zeros(len(pop), dtype=bool)
    for fi in fits:
        dominated |= np.all(fi <= fits, axis=1) & np.any(fi < fits, axis=1)
    front = [ind for ind, lost in zip(pop, dominated) if not lost]
    mats._crowding(front)
    return sorted(front, key=lambda ind: -ind.crowd)


def _population(values: list[tuple[float, ...]]) -> mats.Population:
    return [mats.Individual([float(i)], fitness=row, crowd=11.0, rank=4, score=3.5) for i, row in enumerate(values)]


def _number(value: float) -> str:
    return float(value).hex()


def _snapshot(front: mats.Population, pop: mats.Population) -> tuple[object, ...]:
    return (
        tuple(int(ind.genome[0]) for ind in front),
        tuple(
            (
                tuple(_number(x) for x in ind.genome),
                None if ind.fitness is None else tuple(_number(x) for x in ind.fitness),
                _number(ind.crowd),
                ind.rank,
                ind.score,
            )
            for ind in pop
        ),
    )


def _scalar_members(values: list[tuple[float, ...]]) -> list[int]:
    if not values:
        return []
    rows = np.asarray(values, dtype=float).tolist()
    return [
        i
        for i, row in enumerate(rows)
        if not any(
            j != i and all(a <= b for a, b in zip(other, row)) and any(a < b for a, b in zip(other, row))
            for j, other in enumerate(rows)
        )
    ]


class ParetoPruningTests(unittest.TestCase):
    """Preserve identities, order, crowding side effects, and numeric semantics."""

    def check_case(self, values: list[tuple[float, ...]]) -> None:
        old, new = _population(values), _population(values)
        identities = [id(ind) for ind in new]
        with np.errstate(all="ignore"):
            expected, actual = _reference(old), mats.pareto_front(new)
        self.assertEqual(_snapshot(expected, old), _snapshot(actual, new))
        self.assertEqual(sorted(int(ind.genome[0]) for ind in actual), _scalar_members(values))
        self.assertEqual(identities, [id(ind) for ind in new])
        self.assertTrue(all(any(ind is source for source in new) for ind in actual))

    def test_empty_and_singleton(self) -> None:
        self.check_case([])
        self.check_case([(2.0, 3.0)])

    def test_duplicates_and_crowding_ties(self) -> None:
        self.check_case([(1.0, 2.0)] * 12)
        self.check_case([(0.0, 2.0), (1.0, 1.0), (1.0, 1.0), (2.0, 0.0), (0.0, 2.0), (2.0, 0.0)])

    def test_forward_and_reverse_chains(self) -> None:
        for seq in (range(100), range(99, -1, -1)):
            self.check_case([(float(i), float(i), float(i)) for i in seq])

    def test_tradeoffs_and_equal_first_coordinate(self) -> None:
        self.check_case([(float(i), float(-i)) for i in range(100)])
        self.check_case([(0.0, float(i), float(100 - i)) for i in range(100)])
        self.check_case([(0.0, float(i), float(i)) for i in range(50, -1, -1)])

    def test_nonfinite_and_signed_zero(self) -> None:
        cases = [
            [(math.nan, 1.0), (1.0, math.nan), (0.0, 0.0), (1.0, 1.0)],
            [(math.nan, math.nan)] * 10,
            [(-math.inf, 1.0), (0.0, 0.0), (1.0, math.inf), (math.inf, math.inf), (-math.inf, -math.inf)],
            [(-0.0, 0.0), (0.0, -0.0), (1.0, 0.0)],
            [(0.0, 5e-324), (5e-324, 0.0), (1e-323, 1e-323)],
            [(1e308, -1e308), (-1e308, 1e308), (0.0, 0.0)],
        ]
        for values in cases:
            with self.subTest(values=values):
                self.check_case(values)

    def test_empty_objectives_and_one_dimension(self) -> None:
        self.check_case([(), (), ()])
        self.check_case([(float(i),) for i in (3, 1, 1, 2, -7, 5, -7)])

    def test_float_coercion_and_numpy_scalars(self) -> None:
        self.check_case([(2**60 + i, 2**60 - i) for i in range(12)])
        self.check_case([(np.float32(0.1), np.int64(3)), (np.float64(0.2), np.int32(2)), (0.3, 4.0)])

    def test_aliased_individuals(self) -> None:
        snapshots = []
        for fn in (_reference, mats.pareto_front):
            pop = _population([(1.0, 1.0), (2.0, 2.0), (0.0, 2.0)])
            pop.append(pop[0])
            snapshots.append(_snapshot(fn(pop), pop))
        self.assertEqual(snapshots[0], snapshots[1])

    def test_dominated_metadata_stays_unchanged(self) -> None:
        pop = _population([(0.0, 2.0), (1.0, 1.0), (2.0, 0.0), (3.0, 3.0)])
        mats.pareto_front(pop)
        self.assertEqual(pop[-1].crowd, 11.0)
        self.assertTrue(all(ind.rank == 4 and ind.score == 3.5 for ind in pop))

    def test_invalid_shapes_preserve_error_types(self) -> None:
        cases: list[list[tuple[float, ...] | None]] = [[(1.0, 2.0), (1.0,)], [None, None]]
        for values in cases:
            errors = []
            for fn in (_reference, mats.pareto_front):
                pop = [mats.Individual([float(i)], fitness=row) for i, row in enumerate(values)]
                try:
                    fn(pop)
                except Exception as exc:
                    errors.append(type(exc))
                else:
                    self.fail("Both implementations must reject this unsupported shape")
            self.assertEqual(errors[0], errors[1])

    def test_exhaustive_small_populations(self) -> None:
        count = 0
        for coordinates, dimension in (((-1.0, 0.0, 1.0), 2), ((0.0, 1.0), 3)):
            points = list(itertools.product(coordinates, repeat=dimension))
            for size in range(5):
                for values in itertools.product(points, repeat=size):
                    self.check_case(list(values))
                    count += 1
        self.assertEqual(count, 12062)

    def test_seeded_populations_and_nonfinite_inputs(self) -> None:
        rng = random.Random(20261019)
        for _ in range(400):
            size, dimension = rng.randrange(1, 81), rng.randrange(1, 9)
            self.check_case([tuple(float(rng.randrange(-12, 13)) for _ in range(dimension)) for _ in range(size)])
        choices = [-math.inf, -1.0, -0.0, 0.0, 1.0, math.inf, math.nan]
        for _ in range(100):
            self.check_case([tuple(rng.choice(choices) for _ in range(4)) for _ in range(rng.randrange(1, 40))])

    def test_input_permutations(self) -> None:
        points = [(0.0, 3.0), (1.0, 2.0), (2.0, 1.0), (3.0, 0.0), (4.0, 4.0)]
        for values in itertools.permutations(points):
            self.check_case(list(values))

    def test_actual_source_passes_skip_dominated_chain(self) -> None:
        pop = _population([(float(i), float(i)) for i in range(100, 0, -1)])
        with patch.object(mats.np, "all", wraps=mats.np.all) as all_rows:
            result = mats.pareto_front(pop)
        self.assertEqual(len(result), 1)
        self.assertEqual(all_rows.call_count, 1)

    def test_actual_source_passes_keep_every_tradeoff(self) -> None:
        pop = _population([(float(i), float(-i)) for i in range(100)])
        with patch.object(mats.np, "all", wraps=mats.np.all) as all_rows:
            result = mats.pareto_front(pop)
        self.assertEqual(len(result), 100)
        self.assertEqual(all_rows.call_count, 100)


if __name__ == "__main__":
    unittest.main()
