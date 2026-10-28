# SPDX-License-Identifier: Apache-2.0
"""Exact bounded contingency-fiber construction using future-signature symmetry.

The count-DAG and multiplicity principle follow established exact-sampling work.
This implementation is a bounded engineering extension, not an implementation of
OpenAI's asymptotic sampler and not a claim of a new general counting algorithm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

Group = tuple[tuple[int, ...], int, int]
State = tuple[Group, ...]


class ResourceLimit(RuntimeError):
    """The declared construction budget was exceeded; no artifact is accepted."""


def canonical_bytes(value: Any) -> bytes:
    """Return reproducible JSON bytes, without nonfinite numbers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@dataclass(frozen=True)
class Problem:
    """A finite integer fiber with fixed margins and cell upper bounds."""

    rows: tuple[int, ...]
    cols: tuple[int, ...]
    caps: tuple[tuple[int, ...], ...]
    name: str = "custom"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Problem:
        """Validate an untrusted request before constructing a fiber."""
        rows, cols, caps = data.get("rows"), data.get("cols"), data.get("caps")
        if not isinstance(rows, list) or not isinstance(cols, list) or not isinstance(caps, list):
            raise ValueError("rows, cols and caps must be JSON arrays")
        if not 1 <= len(rows) <= 16 or not 1 <= len(cols) <= 96:
            raise ValueError("supported request dimensions: 1..16 rows and 1..96 columns")
        if any(type(x) is not int or x < 0 or x > 10000 for x in rows + cols):
            raise ValueError("margins must be nonnegative integers no greater than 10000")
        if len(caps) != len(rows) or any(not isinstance(row, list) or len(row) != len(cols) for row in caps):
            raise ValueError("caps dimensions must match margins")
        if any(type(x) is not int or x < 0 or x > 16 for row in caps for x in row):
            raise ValueError("cell caps must be integers in 0..16")
        if sum(rows) != sum(cols):
            raise ValueError("row and column totals differ")
        if sum(rows) > 10000:
            raise ValueError("total mass exceeds the supported request boundary")
        name = data.get("name", "custom")
        if not isinstance(name, str) or len(name) > 180:
            raise ValueError("name must be a short string")
        return cls(tuple(rows), tuple(cols), tuple(tuple(row) for row in caps), name)

    def as_dict(self) -> dict[str, Any]:
        """Return the portable problem description."""
        return {"rows": list(self.rows), "cols": list(self.cols), "caps": [list(r) for r in self.caps], "name": self.name}

    def groups(self, row: int, residual: tuple[int, ...]) -> tuple[State, list[list[int]]]:
        """Partition labeled columns only by identical remaining constraints."""
        buckets: dict[tuple[tuple[int, ...], int], list[int]] = defaultdict(list)
        for j, q in enumerate(residual):
            signature = tuple(self.caps[i][j] for i in range(row, len(self.rows)))
            buckets[signature, q].append(j)
        keys = sorted(buckets)
        return tuple((sig, q, len(buckets[sig, q])) for sig, q in keys), [buckets[key] for key in keys]


def multinomial(counts: tuple[int, ...]) -> int:
    """Count distinct permutations of a multiset with exact integers."""
    result, used = 1, 0
    for count in counts:
        result *= math.comb(used + count, count)
        used += count
    return result


def multiset_unrank(counts: tuple[int, ...], rank: int) -> list[int]:
    """Decode a multiset permutation in lexicographic order."""
    choices, output = list(counts), []
    if not 0 <= rank < multinomial(counts):
        raise ValueError("multiset rank outside the permutation set")
    while sum(choices):
        for value, count in enumerate(choices):
            if count == 0:
                continue
            choices[value] -= 1
            block = multinomial(tuple(choices))
            if rank < block:
                output.append(value)
                break
            rank -= block
            choices[value] += 1
    return output


def multiset_rank(values: list[int], counts: tuple[int, ...]) -> int:
    """Encode a labeled row fragment independently of the count recurrence."""
    choices, rank = list(counts), 0
    for actual in values:
        if actual < 0 or actual >= len(choices) or choices[actual] == 0:
            raise ValueError("values do not match the requested multiset")
        for value in range(actual):
            if choices[value]:
                choices[value] -= 1
                rank += multinomial(tuple(choices))
                choices[value] += 1
        choices[actual] -= 1
    if any(choices):
        raise ValueError("incomplete multiset")
    return rank


def occupancies(n: int, lo: int, hi: int, budget: int) -> Iterator[tuple[tuple[int, ...], int]]:
    """Enumerate feasible occupancy histograms instead of labeled allocations."""
    counts = [0] * (hi + 1)

    def walk(value: int, left: int, mass: int) -> Iterator[tuple[tuple[int, ...], int]]:
        if mass + value * left > budget:
            return
        if value == hi:
            counts[value] = left
            yield tuple(counts), mass + value * left
            return
        for number in range(left + 1):
            counts[value] = number
            yield from walk(value + 1, left - number, mass + value * number)

    yield from walk(lo, n, 0)


@dataclass(frozen=True)
class Edge:
    """A row occupancy decision, its label multiplicity and successor state."""

    allocations: tuple[tuple[int, ...], ...]
    child: int
    multiplicity: int
    collisions: int


@dataclass
class Node:
    """One row of a count DAG; zero-count children are not retained as edges."""

    row: int
    groups: State
    count: int
    edges: list[Edge]


class Fiber:
    """Compile, serialize, rank and sample a finite constrained table family."""

    def __init__(self, problem: Problem, max_states: int = 100000, max_edges: int = 1500000, seconds: float = 30.0):
        self.problem = problem
        self.max_states, self.max_edges, self.seconds = max_states, max_edges, seconds
        self.nodes: list[Node] = []
        self.memo: dict[tuple[int, State], int] = {}
        self.root = -1
        self.attempted_edges = 0
        self.compile_seconds = 0.0
        self._start = 0.0

    def _check_budget(self) -> None:
        if len(self.nodes) >= self.max_states or self.attempted_edges >= self.max_edges:
            raise ResourceLimit("construction state/transition budget exceeded")
        if time.perf_counter() - self._start > self.seconds:
            raise ResourceLimit("construction time budget exceeded")

    def compile(self) -> Fiber:
        """Construct the complete count DAG, or fail explicitly without a delivery."""
        self.nodes, self.memo, self.attempted_edges = [], {}, 0
        self._start = time.perf_counter()
        initial, _ = self.problem.groups(0, self.problem.cols)
        self.root = self._visit(0, initial)
        self.compile_seconds = time.perf_counter() - self._start
        return self

    def _visit(self, row: int, groups: State) -> int:
        key = row, groups
        if key in self.memo:
            return self.memo[key]
        self._check_budget()
        node_id = len(self.nodes)
        self.memo[key] = node_id
        node = Node(row, groups, 0, [])
        self.nodes.append(node)
        if any(q < 0 or q > sum(sig) for sig, q, _ in groups):
            return node_id
        if sum(q * n for _, q, n in groups) != sum(self.problem.rows[row:]):
            return node_id
        if row == len(self.problem.rows):
            node.count = 1
            return node_id
        target = self.problem.rows[row]
        options = []
        minimums, maximums = [], []
        for sig, q, n in groups:
            lo, hi = max(0, q - sum(sig[1:])), min(q, sig[0])
            if lo > hi:
                return node_id
            group_options = []
            for counts, mass in occupancies(n, lo, hi, target):
                group_options.append((counts, mass, multinomial(counts)))
                if len(group_options) % 256 == 0:
                    self._check_budget()
            options.append(group_options)
            minimums.append(n * lo)
            maximums.append(n * hi)
        if not sum(minimums) <= target <= sum(maximums):
            return node_id

        def combine(g: int, mass: int, mult: int, allocated: list[tuple[int, ...]]) -> None:
            if g == len(groups):
                if mass != target:
                    return
                self.attempted_edges += 1
                if self.attempted_edges % 128 == 0:
                    self._check_budget()
                successor: dict[tuple[tuple[int, ...], int], int] = defaultdict(int)
                collisions = 0
                for (sig, q, _), counts in zip(groups, allocated):
                    for x, number in enumerate(counts):
                        if number:
                            successor[sig[1:], q - x] += number
                            collisions += number * x * (x - 1) // 2
                next_groups = tuple((sig, q, n) for (sig, q), n in sorted(successor.items()))
                child = self._visit(row + 1, next_groups)
                child_count = self.nodes[child].count
                if child_count:
                    node.edges.append(Edge(tuple(allocated), child, mult, collisions))
                    node.count += mult * child_count
                return
            lower, upper = sum(minimums[g + 1 :]), sum(maximums[g + 1 :])
            for counts, value, permutations in options[g]:
                if mass + value + lower <= target <= mass + value + upper:
                    combine(g + 1, mass + value, mult * permutations, allocated + [counts])

        combine(0, 0, 1, [])
        return node_id

    @property
    def count(self) -> int:
        """Number of labeled tables, rather than the number of quotient states."""
        if self.root < 0:
            raise ValueError("compile the instrument before use")
        return self.nodes[self.root].count

    def _decode(self, rank: int, conditioned: dict[tuple[int, int], int] | None = None,
                collision_target: int | None = None) -> list[list[int]]:
        node_id, residual, table = self.root, list(self.problem.cols), []
        remaining = collision_target
        total = self.count if conditioned is None else conditioned.get((self.root, int(remaining)), 0)
        if type(rank) is not int or not 0 <= rank < total:
            raise ValueError("rank must be an integer in the delivered fiber")
        while self.nodes[node_id].row < len(self.problem.rows):
            node = self.nodes[node_id]
            state, labels = self.problem.groups(node.row, tuple(residual))
            if state != node.groups:
                raise ValueError("artifact state mismatch")
            chosen, child_count = None, 0
            for edge in node.edges:
                child_count = (self.nodes[edge.child].count if conditioned is None else
                               conditioned.get((edge.child, int(remaining) - edge.collisions), 0))
                block = edge.multiplicity * child_count
                if rank < block:
                    chosen = edge
                    break
                rank -= block
            if chosen is None or child_count == 0:
                raise ValueError("corrupt count recurrence")
            permutation_rank, rank = divmod(rank, child_count)
            radices = [multinomial(c) for c in chosen.allocations]
            group_ranks = [0] * len(radices)
            for g in range(len(radices) - 1, -1, -1):
                permutation_rank, group_ranks[g] = divmod(permutation_rank, radices[g])
            values = [0] * len(residual)
            for indices, counts, group_rank in zip(labels, chosen.allocations, group_ranks):
                for j, value in zip(indices, multiset_unrank(counts, group_rank)):
                    values[j] = value
                    residual[j] -= value
            table.append(values)
            if remaining is not None:
                remaining -= chosen.collisions
            node_id = chosen.child
        return table

    def unrank(self, rank: int) -> list[list[int]]:
        """Construct a unique table from an integer, using no rejection sampling."""
        return self._decode(rank)

    def rank(self, table: list[list[int]]) -> int:
        """Return the inverse hierarchical rank of a valid table."""
        issues = validate_table(self.problem, table)
        if issues:
            raise ValueError("; ".join(issues))
        residual = list(self.problem.cols)

        def visit(node_id: int) -> int:
            node = self.nodes[node_id]
            if node.row == len(self.problem.rows):
                return 0
            _, labels = self.problem.groups(node.row, tuple(residual))
            offset = 0
            for edge in node.edges:
                fits = True
                arrangement = 0
                for indices, counts in zip(labels, edge.allocations):
                    values = [table[node.row][j] for j in indices]
                    actual = tuple(values.count(x) for x in range(len(counts)))
                    if actual != counts or any(x >= len(counts) for x in values):
                        fits = False
                        break
                    arrangement = arrangement * multinomial(counts) + multiset_rank(values, counts)
                if fits:
                    for j, value in enumerate(table[node.row]):
                        residual[j] -= value
                    return offset + arrangement * self.nodes[edge.child].count + visit(edge.child)
                offset += edge.multiplicity * self.nodes[edge.child].count
            raise ValueError("valid table missing from the compiled instrument")

        return visit(self.root)

    def sample(self, size: int, seed: int) -> list[list[list[int]]]:
        """Draw reproducible IID uniform ranks, then construct their tables."""
        if type(size) is not int or not 0 <= size <= 100000:
            raise ValueError("sample size must be an integer in 0..100000")
        if self.count == 0:
            raise ValueError("empty fiber: no samples can be delivered")
        rng = random.Random(seed)
        return [self.unrank(rng.randrange(self.count)) for _ in range(size)]

    def collision_distribution(self) -> tuple[dict[int, int], dict[tuple[int, int], int]]:
        """Construct an exact concentration instrument from inherited transitions.

        Collisions are sum(x*(x-1)/2) across cells. This is a new query on the
        delivered family, not evidence of statistical realism or a new theorem.
        """
        counts: dict[tuple[int, int], int] = {}

        @lru_cache(None)
        def visit(node_id: int) -> dict[int, int]:
            node = self.nodes[node_id]
            if node.row == len(self.problem.rows):
                result = {0: node.count} if node.count else {}
            else:
                result: dict[int, int] = defaultdict(int)
                for edge in node.edges:
                    for value, count in visit(edge.child).items():
                        result[value + edge.collisions] += edge.multiplicity * count
                result = dict(result)
            for value, count in result.items():
                counts[node_id, value] = count
            return result

        return visit(self.root), counts

    def conditioned_sample(self, collision_target: int, size: int, seed: int) -> list[list[list[int]]]:
        """Generate an exact rare-event ensemble without rejection or new compilation."""
        if type(collision_target) is not int or collision_target < 0:
            raise ValueError("concentration must be a nonnegative integer")
        distribution, counts = self.collision_distribution()
        count = distribution.get(collision_target, 0)
        if count == 0:
            raise ValueError("requested concentration level is infeasible")
        if type(size) is not int or not 0 <= size <= 100000:
            raise ValueError("sample size must be an integer in 0..100000")
        rng = random.Random(seed)
        return [self._decode(rng.randrange(count), counts, collision_target) for _ in range(size)]

    def as_dict(self) -> dict[str, Any]:
        """Export a data-only reusable instrument; large integers use decimal strings."""
        body = {
            "schema": "agi-alpha-fiber-v1", "problem": self.problem.as_dict(), "root": self.root,
            "nodes": [{"row": n.row, "groups": [[list(s), q, k] for s, q, k in n.groups], "count": str(n.count),
                       "edges": [{"allocations": [list(c) for c in e.allocations], "child": e.child,
                                  "multiplicity": str(e.multiplicity), "collisions": e.collisions} for e in n.edges]}
                      for n in self.nodes],
        }
        return {**body, "sha256": hashlib.sha256(canonical_bytes(body)).hexdigest()}

    @classmethod
    def from_dict(cls, data: dict[str, Any], expected_sha256: str | None = None) -> Fiber:
        """Load an inherited instrument, checking its mathematical representation.

        A separately trusted issuance digest permits reuse after full structural
        validation. Without that external binding, rebuild and compare the
        complete artifact: a self-supplied hash does not prove edge completeness.
        """
        body = {k: v for k, v in data.items() if k != "sha256"}
        if data.get("schema") != "agi-alpha-fiber-v1" or hashlib.sha256(canonical_bytes(body)).hexdigest() != data.get("sha256"):
            raise ValueError("instrument schema or integrity digest is invalid")
        if expected_sha256 is not None and data.get("sha256") != expected_sha256:
            raise ValueError("instrument differs from the separately retained issuance digest")
        instrument = cls(Problem.from_dict(data["problem"]))
        if not isinstance(data.get("nodes"), list) or len(data["nodes"]) > 100000:
            raise ValueError("instrument has too many states")
        instrument.nodes = [Node(n["row"], tuple((tuple(s), q, k) for s, q, k in n["groups"]), int(n["count"]),
                                 [Edge(tuple(tuple(c) for c in e["allocations"]), e["child"], int(e["multiplicity"]),
                                       e["collisions"]) for e in n["edges"]]) for n in data["nodes"]]
        instrument.root = data["root"]
        if type(instrument.root) is not int or not 0 <= instrument.root < len(instrument.nodes):
            raise ValueError("invalid instrument root")
        initial, _ = instrument.problem.groups(0, instrument.problem.cols)
        if instrument.nodes[instrument.root].row != 0 or instrument.nodes[instrument.root].groups != initial:
            raise ValueError("root does not match the problem")
        seen_states: set[tuple[int, State]] = set()
        for node in instrument.nodes:
            if type(node.row) is not int or node.row < 0 or node.row > len(instrument.problem.rows) or node.count < 0:
                raise ValueError("invalid state")
            key = node.row, node.groups
            if key in seen_states:
                raise ValueError("duplicated state")
            seen_states.add(key)
            if any(type(q) is not int or type(k) is not int or q < 0 or k <= 0 or
                   len(s) != len(instrument.problem.rows) - node.row or
                   any(type(x) is not int or x < 0 or x > 16 for x in s) for s, q, k in node.groups):
                raise ValueError("invalid state groups")
            if sum(k for _, _, k in node.groups) != len(instrument.problem.cols):
                raise ValueError("state has the wrong number of columns")
            if tuple(sorted(node.groups)) != node.groups or len({(s, q) for s, q, _ in node.groups}) != len(node.groups):
                raise ValueError("state groups must be sorted and unique")
            feasible = (all(q <= sum(s) for s, q, _ in node.groups) and
                        sum(q * k for _, q, k in node.groups) == sum(instrument.problem.rows[node.row:]))
            if not feasible and (node.count or node.edges):
                raise ValueError("infeasible state has positive mass")
            if node.row == len(instrument.problem.rows):
                if node.edges or node.count != int(feasible):
                    raise ValueError("invalid terminal mass")
            seen_allocations: set[tuple[tuple[int, ...], ...]] = set()
            for edge in node.edges:
                if (type(edge.child) is not int or not 0 <= edge.child < len(instrument.nodes) or
                        instrument.nodes[edge.child].row != node.row + 1):
                    raise ValueError("invalid DAG edge")
                if len(edge.allocations) != len(node.groups) or edge.allocations in seen_allocations:
                    raise ValueError("missing or duplicated group allocation")
                seen_allocations.add(edge.allocations)
                next_groups: dict[tuple[tuple[int, ...], int], int] = defaultdict(int)
                mass, collisions = 0, 0
                for (sig, q, k), counts in zip(node.groups, edge.allocations):
                    if (not counts or any(type(x) is not int or x < 0 for x in counts) or
                            sum(counts) != k or len(counts) != min(q, sig[0]) + 1):
                        raise ValueError("invalid occupancy histogram")
                    for value, number in enumerate(counts):
                        if number:
                            if q - value > sum(sig[1:]):
                                raise ValueError("allocation leaves an impossible future")
                            next_groups[sig[1:], q - value] += number
                            mass += value * number
                            collisions += number * value * (value - 1) // 2
                child_groups = tuple((sig, q, k) for (sig, q), k in sorted(next_groups.items()))
                if child_groups != instrument.nodes[edge.child].groups or mass != instrument.problem.rows[node.row]:
                    raise ValueError("edge does not construct its stated child")
                if type(edge.collisions) is not int or edge.collisions != collisions:
                    raise ValueError("invalid concentration statistic")
                if edge.multiplicity != math.prod(multinomial(c) for c in edge.allocations):
                    raise ValueError("invalid multiplicity")
            if node.row < len(instrument.problem.rows):
                if node.count != sum(e.multiplicity * instrument.nodes[e.child].count for e in node.edges):
                    raise ValueError("count recurrence is inconsistent")
        if expected_sha256 is None:
            rebuilt = cls(instrument.problem).compile()
            if rebuilt.as_dict()["sha256"] != data["sha256"]:
                raise ValueError("untrusted artifact differs from complete reconstruction")
        return instrument


def validate_table(problem: Problem, table: Any) -> list[str]:
    """Check delivered cells directly, without trusting the construction algorithm."""
    if not isinstance(table, list) or len(table) != len(problem.rows):
        return ["row dimension mismatch"]
    if any(not isinstance(row, list) or len(row) != len(problem.cols) for row in table):
        return ["column dimension mismatch"]
    if any(type(x) is not int for row in table for x in row):
        return ["noninteger cell"]
    errors = []
    if any(sum(row) != target for row, target in zip(table, problem.rows)):
        errors.append("row margins mismatch")
    if any(sum(row[j] for row in table) != target for j, target in enumerate(problem.cols)):
        errors.append("column margins mismatch")
    if any(x < 0 or x > problem.caps[i][j] for i, row in enumerate(table) for j, x in enumerate(row)):
        errors.append("cell bound violated")
    return errors


def main() -> None:
    """Build a complete useful delivery from a request, or emit an explicit refusal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--seconds", type=float, default=30.0)
    args = parser.parse_args()
    problem = Problem.from_dict(json.loads(args.request.read_text()))
    started = time.perf_counter()
    try:
        fiber = Fiber(problem, seconds=args.seconds).compile()
        if fiber.count == 0:
            raise ValueError("empty fiber: no feasible table satisfies this request")
        samples = fiber.sample(args.samples, args.seed)
        if any(validate_table(problem, table) for table in samples):
            raise RuntimeError("independent cell acceptance check failed")
        args.output.mkdir(parents=True, exist_ok=True)
        asset = fiber.as_dict()
        (args.output / "instrument.json").write_text(json.dumps(asset, separators=(",", ":")))
        (args.output / "tables.json").write_text(json.dumps(samples))
        receipt = {"status": "accepted_computational_delivery", "commercial_transaction": "simulated_only",
                   "actual_revenue_usd": 0, "count": str(fiber.count), "states": len(fiber.nodes),
                   "edges": sum(len(n.edges) for n in fiber.nodes), "accepted_tables": len(samples),
                   "compile_seconds": fiber.compile_seconds, "elapsed_seconds": time.perf_counter() - started,
                   "asset_sha256": asset["sha256"], "law": "uniform_over_labeled_feasible_tables",
                   "limitations": ["no demand proof", "no real-world distribution guarantee", "bounded input domain",
                                   "not a new general counting theorem", "no privacy guarantee"]}
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt, indent=2))
    except (ResourceLimit, ValueError) as error:
        print(json.dumps({"status": "refused", "reason": str(error), "actual_revenue_usd": 0}))
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
