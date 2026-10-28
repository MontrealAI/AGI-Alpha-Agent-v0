# SPDX-License-Identifier: Apache-2.0
"""Independent exact references and exhaustive challenges for bounded tables."""

from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import inspect
import itertools
import json
import math
import random
import time
from collections import defaultdict
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

Table = tuple[tuple[int, ...], ...]


class ReferenceLimit(RuntimeError):
    """A declared reference computation budget was exhausted."""


def normalize_problem(
    rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]]
) -> tuple[tuple[int, ...], tuple[int, ...], Table]:
    """Validate dimensions and nonnegative integer input without casting floats."""
    r, c, u = tuple(rows), tuple(cols), tuple(tuple(row) for row in caps)
    if not r or not c or len(u) != len(r) or any(len(row) != len(c) for row in u):
        raise ValueError("Nonempty matching dimensions are required")
    if any(type(x) is not int or x < 0 for x in (*r, *c, *(x for row in u for x in row))):
        raise ValueError("All entries must be nonnegative integers")
    return r, c, u


def enumerate_tables(
    rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]], max_tables: int = 100000
) -> list[Table]:
    """Enumerate labeled tables by independent cell recursion for small cases."""
    r, c, u = normalize_problem(rows, cols, caps)
    if sum(r) != sum(c):
        return []
    m, n = len(r), len(c)
    row_left, col_left, flat = list(r), list(c), [0] * (m * n)
    found: list[Table] = []

    def visit(pos: int) -> None:
        if pos == m * n:
            if not any(row_left) and not any(col_left):
                if len(found) >= max_tables:
                    raise ReferenceLimit("Enumeration table budget exhausted")
                found.append(tuple(tuple(flat[i * n : (i + 1) * n]) for i in range(m)))
            return
        i, j = divmod(pos, n)
        upper = min(u[i][j], row_left[i], col_left[j])
        lower = max(
            0,
            row_left[i] - sum(min(u[i][k], col_left[k]) for k in range(j + 1, n)),
            col_left[j] - sum(u[k][j] for k in range(i + 1, m)),
        )
        for value in range(lower, upper + 1):
            flat[pos] = value
            row_left[i] -= value
            col_left[j] -= value
            visit(pos + 1)
            row_left[i] += value
            col_left[j] += value

    visit(0)
    return found


def labeled_cell_count(
    rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]], max_states: int = 1000000
) -> dict[str, Any]:
    """Count by conventional cell-wise coefficient extraction without symmetry."""
    r, c, u = normalize_problem(rows, cols, caps)
    start = time.perf_counter()
    states = 0
    m, n = len(r), len(c)

    @functools.cache
    def count(pos: int, remaining_row: int, remaining_col: tuple[int, ...]) -> int:
        nonlocal states
        states += 1
        if states > max_states:
            raise ReferenceLimit("Cell-DP state budget exhausted")
        if pos == m * n:
            return int(remaining_row == 0 and not any(remaining_col))
        i, j = divmod(pos, n)
        upper = min(u[i][j], remaining_row, remaining_col[j])
        lower = max(
            0,
            remaining_row - sum(min(u[i][k], remaining_col[k]) for k in range(j + 1, n)),
            remaining_col[j] - sum(u[k][j] for k in range(i + 1, m)),
        )
        answer = 0
        for value in range(lower, upper + 1):
            child_cols = list(remaining_col)
            child_cols[j] -= value
            next_row = remaining_row - value if j + 1 < n else (r[i + 1] if i + 1 < m else 0)
            answer += count(pos + 1, next_row, tuple(child_cols))
        return answer

    answer = count(0, r[0], c) if sum(r) == sum(c) else 0
    return {"count": answer, "states": states, "seconds": time.perf_counter() - start}


def _orbit_choices(size: int, limit: int, budget: int) -> Iterator[tuple[int, tuple[int, ...], int]]:
    """Enumerate value histograms and their labeled multinomial multiplicities."""
    buckets = [0] * (limit + 1)

    def visit(value: int, left: int, used: int, ways: int) -> Iterator[tuple[int, tuple[int, ...], int]]:
        if value == 0:
            buckets[0] = left
            yield used, tuple(buckets), ways
            return
        for number in range(min(left, (budget - used) // value) + 1):
            buckets[value] = number
            yield from visit(value - 1, left - number, used + number * value, ways * math.comb(left, number))

    yield from visit(limit, size, 0, 1)


def orbit_count(
    rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]], max_states: int = 1000000,
    collision_target: int | None = None,
) -> dict[str, Any]:
    """Count using conventional permutation orbits of equivalent future columns.

    This independently applies the standard symmetry principle to all future
    cap signatures. It is a strong conventional competitor, not an invention
    claim and not a reproduction of the OpenAI polynomial-time sampler.
    """
    r, c, u = normalize_problem(rows, cols, caps)
    if collision_target is not None and (type(collision_target) is not int or collision_target < 0):
        raise ValueError("Collision target must be a nonnegative integer")
    start = time.perf_counter()
    m, n = len(r), len(c)
    order = sorted(range(m), key=lambda i: (-r[i], u[i]))
    r, u = tuple(r[i] for i in order), tuple(u[i] for i in order)
    signatures = [tuple(tuple(u[k][j] for k in range(i, m)) for j in range(n)) for i in range(m + 1)]
    classes: list[tuple[tuple[int, ...], ...]] = []
    for i in range(m + 1):
        groups: dict[tuple[int, ...], list[int]] = defaultdict(list)
        for j, signature in enumerate(signatures[i]):
            groups[signature].append(j)
        classes.append(tuple(tuple(group) for group in groups.values()))
    states, transitions = 0, 0

    def canonical(i: int, remaining: tuple[int, ...]) -> tuple[int, ...]:
        result = list(remaining)
        for group in classes[i]:
            for j, value in zip(group, sorted(remaining[j] for j in group)):
                result[j] = value
        return tuple(result)

    @functools.cache
    def count(i: int, remaining: tuple[int, ...], collision_left: int | None) -> int:
        nonlocal states, transitions
        states += 1
        if states > max_states:
            raise ReferenceLimit("Orbit-DP state budget exhausted")
        if i == m:
            return int(not any(remaining) and collision_left in (None, 0))
        if sum(remaining) != sum(r[i:]) or any(remaining[j] > sum(signatures[i][j]) for j in range(n)):
            return 0
        grouped: dict[tuple[tuple[int, ...], int], list[int]] = defaultdict(list)
        for j in range(n):
            grouped[(signatures[i][j], remaining[j])].append(j)
        groups = list(grouped.items())
        child = list(remaining)

        def distribute(g: int, budget: int, multiplicity: int, collisions: int) -> int:
            nonlocal transitions
            if g == len(groups):
                if budget:
                    return 0
                transitions += 1
                next_collision = None if collision_left is None else collision_left - collisions
                return multiplicity * count(i + 1, canonical(i + 1, tuple(child)), next_collision)
            (signature, residual), positions = groups[g]
            limit = min(signature[0], residual, budget)
            later_capacity = sum(
                min(key[0][0], key[1]) * len(indices) for key, indices in groups[g + 1 :]
            )
            subtotal = 0
            for used, hist, ways in _orbit_choices(len(positions), limit, budget):
                if budget - used > later_capacity:
                    continue
                next_collisions = collisions + sum(number * value * (value - 1) // 2 for value, number in enumerate(hist))
                if collision_left is not None and next_collisions > collision_left:
                    continue
                values = [residual - value for value, frequency in enumerate(hist) for _ in range(frequency)]
                if any(value > sum(signature[1:]) for value in values):
                    continue
                for j, value in zip(positions, values):
                    child[j] = value
                subtotal += distribute(g + 1, budget - used, multiplicity * ways, next_collisions)
            return subtotal

        return distribute(0, r[i], 1, 0)

    answer = count(0, canonical(0, c), collision_target) if sum(r) == sum(c) else 0
    return {
        "count": answer,
        "states": states,
        "transitions": transitions,
        "seconds": time.perf_counter() - start,
        "algorithm": "independent conventional cap-signature orbit dynamic program",
        "collision_target": collision_target,
    }


def collision_count(
    rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]], target: int,
    max_states: int = 1000000,
) -> dict[str, Any]:
    """Solve a fresh concentration-constrained count without inherited assets."""
    if type(target) is not int or target < 0:
        raise ValueError("Collision target must be a nonnegative integer")
    if target == 0:
        clipped = [[min(value, 1) for value in row] for row in caps]
        result = orbit_count(rows, cols, clipped, max_states)
        result["algorithm"] = "direct conventional binary-cap shortcut for zero collisions"
    else:
        result = orbit_count(rows, cols, caps, max_states, target)
        result["algorithm"] = "direct conventional collision-conditioned orbit DP"
    result["collision_target"] = target
    return result


def collision_distribution_direct(
    rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]], max_states: int = 1000000,
) -> dict[str, Any]:
    """Compute the full collision histogram by a fresh conventional semiring DP."""
    r, c, u = normalize_problem(rows, cols, caps)
    started = time.perf_counter()
    order = sorted(range(len(r)), key=lambda i: (-r[i], u[i]))
    r, u = tuple(r[i] for i in order), tuple(u[i] for i in order)
    m, n = len(r), len(c)
    signatures = [tuple(tuple(u[k][j] for k in range(i, m)) for j in range(n)) for i in range(m + 1)]
    states, transitions = 0, 0

    def canonical(i: int, residual: tuple[int, ...]) -> tuple[int, ...]:
        grouped: dict[tuple[int, ...], list[int]] = defaultdict(list)
        for j, signature in enumerate(signatures[i]):
            grouped[signature].append(j)
        answer = list(residual)
        for indices in grouped.values():
            for j, value in zip(indices, sorted(residual[j] for j in indices)):
                answer[j] = value
        return tuple(answer)

    @functools.cache
    def histogram(i: int, residual: tuple[int, ...]) -> dict[int, int]:
        nonlocal states, transitions
        states += 1
        if states > max_states:
            raise ReferenceLimit("Direct distribution state budget exhausted")
        if i == m:
            return {0: 1} if not any(residual) else {}
        if sum(residual) != sum(r[i:]) or any(residual[j] > sum(signatures[i][j]) for j in range(n)):
            return {}
        groups: dict[tuple[tuple[int, ...], int], list[int]] = defaultdict(list)
        for j in range(n):
            groups[signatures[i][j], residual[j]].append(j)
        ordered = list(groups.items())
        child = list(residual)
        answer: dict[int, int] = defaultdict(int)

        def visit(g: int, budget: int, mult: int, collision: int) -> None:
            nonlocal transitions
            if g == len(ordered):
                if budget:
                    return
                transitions += 1
                for value, count in histogram(i + 1, canonical(i + 1, tuple(child))).items():
                    answer[value + collision] += mult * count
                return
            (signature, remaining), indices = ordered[g]
            later_capacity = sum(min(key[0][0], key[1]) * len(js) for key, js in ordered[g + 1 :])
            for used, occupancy, ways in _orbit_choices(len(indices), min(remaining, signature[0], budget), budget):
                if budget - used > later_capacity:
                    continue
                values = [remaining - value for value, frequency in enumerate(occupancy) for _ in range(frequency)]
                if any(value > sum(signature[1:]) for value in values):
                    continue
                for j, value in zip(indices, values):
                    child[j] = value
                new_collision = collision + sum(num * value * (value - 1) // 2 for value, num in enumerate(occupancy))
                visit(g + 1, budget - used, mult * ways, new_collision)

        visit(0, r[i], 1, 0)
        return dict(answer)

    distribution = histogram(0, canonical(0, c)) if sum(r) == sum(c) else {}
    return {"distribution": distribution, "count": sum(distribution.values()), "states": states,
            "transitions": transitions, "seconds": time.perf_counter() - started,
            "algorithm": "fresh conventional orbit semiring DP, no inherited count DAG"}


def unsafe_sorted_count(rows: Sequence[int], cols: Sequence[int], caps: Sequence[Sequence[int]]) -> int:
    """Intentionally invalid global sorting, retained only as a negative control."""
    r, c, u = normalize_problem(rows, cols, caps)

    @functools.cache
    def count(i: int, remaining: tuple[int, ...]) -> int:
        if i == len(r):
            return int(not any(remaining))
        answer = 0
        for row in itertools.product(*(range(min(u[i][j], remaining[j]) + 1) for j in range(len(c)))):
            if sum(row) == r[i]:
                answer += count(i + 1, tuple(sorted(remaining[j] - row[j] for j in range(len(c)))))
        return answer

    return count(0, tuple(sorted(c)))


def finches_problem() -> dict[str, Any]:
    """Return the published Miller--Harrison Table 4 margins and exact count."""
    rows = [14, 13, 14, 10, 12, 2, 10, 1, 10, 11, 6, 2, 17]
    cols = [4, 4, 11, 10, 10, 8, 9, 10, 8, 9, 3, 10, 4, 7, 9, 3, 3]
    return {
        "name": "Darwin finches published 13 by 17 binary table",
        "rows": rows,
        "cols": cols,
        "caps": [[1] * len(cols) for _ in rows],
        "published_count": 67149106137567626,
        "source": "https://jwmi.github.io/publications/Exact_matrix.pdf",
        "source_location": "Table 4; section 4.1, pages 12-13 in manuscript",
    }


def self_check() -> dict[str, Any]:
    """Cross-check exhaustive tiny fibers and a published real-data count."""
    rng = random.Random(902108277)
    cases: list[dict[str, Any]] = []
    for mode in ("binary", "bounded"):
        for number in range(48):
            m, n = rng.randint(2, 4), rng.randint(2, 4)
            cap_max = 1 if mode == "binary" else 2
            caps = [[rng.randint(0, cap_max) for _ in range(n)] for _ in range(m)]
            witness = [[rng.randint(0, caps[i][j]) for j in range(n)] for i in range(m)]
            rows = [sum(row) for row in witness]
            cols = [sum(witness[i][j] for i in range(m)) for j in range(n)]
            if number % 4 == 0:
                rows[rng.randrange(m)] += 1
                cols[rng.randrange(n)] += 1
            tables = enumerate_tables(rows, cols, caps)
            ordinary = labeled_cell_count(rows, cols, caps)
            conventional = orbit_count(rows, cols, caps)
            if len(tables) != ordinary["count"] or len(tables) != conventional["count"]:
                raise AssertionError({"rows": rows, "cols": cols, "caps": caps, "expected": len(tables),
                                      "labeled": ordinary, "orbit": conventional})
            cases.append({"mode": mode, "rows": rows, "cols": cols, "caps": caps,
                          "count": len(tables), "cell_states": ordinary["states"],
                          "orbit_states": conventional["states"]})
    fixtures = [
        ([3] * 3, [3] * 3, [[2] * 3 for _ in range(3)]),
        ([2] * 4, [2] * 4, [[1] * 4 for _ in range(4)]),
        ([4] * 4, [4] * 4, [[2] * 4 for _ in range(4)]),
        ([4] * 3, [3] * 4, [[2] * 4 for _ in range(3)]),
        ([1] * 3, [1] * 3, [[0, 0, 1], [1, 1, 0], [1, 1, 0]]),
        ([1] * 3, [1] * 3, [[0, 0, 1], [0, 0, 1], [0, 0, 1]]),
        ([3] * 3, [3] * 3, [[0, 2, 2], [2, 0, 2], [2, 2, 0]]),
        ([3] * 4, [3] * 4, [[0 if i == j else 2 for j in range(4)] for i in range(4)]),
    ]
    for rows, cols, caps in fixtures:
        tables = enumerate_tables(rows, cols, caps)
        ordinary = labeled_cell_count(rows, cols, caps)
        conventional = orbit_count(rows, cols, caps)
        if len(tables) != ordinary["count"] or len(tables) != conventional["count"]:
            raise AssertionError("Fixed nontrivial reference fixture failed")
        cases.append({"mode": "nontrivial_fixed", "rows": rows, "cols": cols, "caps": caps,
                      "count": len(tables), "cell_states": ordinary["states"],
                      "orbit_states": conventional["states"]})
    counterexample: dict[str, Any] | None = None
    for bits in itertools.product((0, 1), repeat=9):
        caps = [list(bits[i * 3 : (i + 1) * 3]) for i in range(3)]
        rows, cols = [1, 1, 1], [1, 1, 1]
        truth = len(enumerate_tables(rows, cols, caps))
        wrong = unsafe_sorted_count(rows, cols, caps)
        if truth > 1 and truth != wrong:
            counterexample = {"rows": rows, "cols": cols, "caps": caps, "true_count": truth,
                              "unsafe_global_sort_count": wrong}
            break
    if counterexample is None:
        raise AssertionError("The unsafe negative control unexpectedly passed")
    finches = finches_problem()
    conventional = orbit_count(finches["rows"], finches["cols"], finches["caps"])
    if conventional["count"] != finches["published_count"]:
        raise AssertionError("Published finch count did not reproduce")
    return {"checks": len(cases), "tiny_cases": cases, "unsafe_sort_counterexample": counterexample,
            "published_finches": {**finches, "reference_result": conventional},
            "scope": "algorithmic reference checks; no economic, model-comparison, or novelty claim"}


def kernel_review() -> dict[str, Any]:
    """Challenge the separate kernel using exhaustive reference table sets."""
    import kernel

    references = self_check()
    checked = []
    accepts_digest = "expected_sha256" in inspect.signature(kernel.Fiber.from_dict).parameters

    def load(asset: dict[str, Any], trusted: bool = True) -> Any:
        if accepts_digest and trusted:
            return kernel.Fiber.from_dict(asset, expected_sha256=asset["sha256"])
        return kernel.Fiber.from_dict(asset)

    for case in references["tiny_cases"]:
        expected = set(enumerate_tables(case["rows"], case["cols"], case["caps"]))
        problem = kernel.Problem.from_dict(case)
        fiber = kernel.Fiber(problem).compile()
        if fiber.count != len(expected):
            raise AssertionError({"problem": case, "expected": len(expected), "got": fiber.count})
        actual = {tuple(map(tuple, fiber.unrank(i))) for i in range(fiber.count)}
        if actual != expected:
            raise AssertionError("Unrank did not produce exactly the exhaustive table set")
        for i in range(fiber.count):
            if fiber.rank(fiber.unrank(i)) != i:
                raise AssertionError("Rank-unrank inverse failed")
        asset = fiber.as_dict()
        restored = load(asset)
        if restored.count != len(expected):
            raise AssertionError("Restored count disagrees")
        actual_hist: dict[int, int] = defaultdict(int)
        for table in expected:
            value = sum(x * (x - 1) // 2 for row in table for x in row)
            actual_hist[value] += 1
        distribution, condition_states = restored.collision_distribution()
        if distribution != dict(actual_hist):
            raise AssertionError("Inherited concentration polynomial differs from exhaustive histogram")
        direct_distribution = collision_distribution_direct(case["rows"], case["cols"], case["caps"])
        if direct_distribution["distribution"] != dict(actual_hist):
            raise AssertionError("Fresh conventional semiring histogram differs from exhaustive histogram")
        for target, count in actual_hist.items():
            independent = collision_count(case["rows"], case["cols"], case["caps"], target)
            if independent["count"] != count:
                raise AssertionError("Direct conventional concentration count failed")
            expected_subset = {table for table in expected
                               if sum(x * (x - 1) // 2 for row in table for x in row) == target}
            decoded = {tuple(map(tuple, restored._decode(i, condition_states, target))) for i in range(count)}
            if decoded != expected_subset:
                raise AssertionError("Conditional unrank was not a bijection")
            for sample in restored.conditioned_sample(target, min(10, count), 10717 + target):
                if tuple(map(tuple, sample)) not in expected_subset:
                    raise AssertionError("Conditioned sample violated the declared law support")
        if fiber.count:
            for i in {0, fiber.count // 2, fiber.count - 1}:
                if restored.unrank(i) != fiber.unrank(i):
                    raise AssertionError("Serialization changed rank order")
        checked.append({"count": fiber.count, "concentration_levels": len(actual_hist),
                        "enumerated_rank_checks": fiber.count, "mode": case["mode"]})
    fixture = kernel.Fiber(kernel.Problem((2, 2), (2, 2), ((2, 2), (2, 2)))).compile().as_dict()
    mutation_results = []
    for mutation in ("collision", "multiplicity", "root_groups", "self_loop", "terminal_count", "missing_edge"):
        corrupted = copy.deepcopy(fixture)
        root = corrupted["nodes"][corrupted["root"]]
        if mutation == "collision":
            root["edges"][0]["collisions"] += 1
        elif mutation == "multiplicity":
            root["edges"][0]["multiplicity"] = str(int(root["edges"][0]["multiplicity"]) + 1)
        elif mutation == "root_groups":
            root["groups"][0][1] += 1
        elif mutation == "self_loop":
            root["edges"][0]["child"] = corrupted["root"]
        elif mutation == "terminal_count":
            next(node for node in corrupted["nodes"] if node["row"] == 2)["count"] = "2"
        else:
            removed = root["edges"].pop()
            root["count"] = str(int(root["count"]) - int(removed["multiplicity"]) *
                                int(corrupted["nodes"][removed["child"]]["count"]))
        body = {key: value for key, value in corrupted.items() if key != "sha256"}
        corrupted["sha256"] = hashlib.sha256(kernel.canonical_bytes(body)).hexdigest()
        try:
            load(corrupted, trusted=False)
        except (ValueError, TypeError, KeyError, IndexError) as error:
            mutation_results.append({"mutation": mutation, "rejected": True, "reason": str(error)})
        else:
            mutation_results.append({"mutation": mutation, "rejected": False})
    return {
        "kernel_sha256": hashlib.sha256(Path(kernel.__file__).read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases": len(checked), "exhaustive_rank_checks": sum(case["count"] for case in checked),
        "checked": checked, "mutations": mutation_results,
        "all_mutations_rejected": all(item["rejected"] for item in mutation_results),
        "trusted_receipt_api_present": accepts_digest,
        "boundary": "independent code and enumerative oracle; not external peer review or model comparison",
    }


def main() -> None:
    """Run the independent references from a JSON file or the self-check suite."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--kernel-review", action="store_true")
    args = parser.parse_args()
    if args.kernel_review:
        result = kernel_review()
    elif args.problem:
        problem = json.loads(args.problem.read_text())
        result = {
            "cell": labeled_cell_count(problem["rows"], problem["cols"], problem["caps"]),
            "orbit": orbit_count(problem["rows"], problem["cols"], problem["caps"]),
        }
    else:
        result = self_check()
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
