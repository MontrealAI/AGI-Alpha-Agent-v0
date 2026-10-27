# SPDX-License-Identifier: Apache-2.0
"""Exact, bounded procurement-mechanism witness; no model or network execution."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


class ScopeError(ValueError):
    """The requested mechanism is outside the declared finite domain."""


def canonical(value: Any) -> bytes:
    """Encode a research record with deterministic JSON bytes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    """Return a content identity, not a correctness attestation."""
    return hashlib.sha256(canonical(value)).hexdigest()


def integer(value: object, name: str, low: int, high: int) -> int:
    """Validate bounded integers without silently accepting Boolean values."""
    if type(value) is not int or not low <= value <= high:
        raise ScopeError(f"{name} must be an integer in [{low}, {high}]")
    return value


@dataclass(frozen=True)
class Domain:
    """Independent finite private-cost distributions and a public budget ceiling."""

    weights: tuple[tuple[int, ...], ...]
    max_budget: int

    def __post_init__(self) -> None:
        if type(self.weights) is not tuple or not 1 <= len(self.weights) <= 12:
            raise ScopeError("one through twelve suppliers are supported")
        for row in self.weights:
            if type(row) is not tuple or not 2 <= len(row) <= 33:
                raise ScopeError("each cost domain must be the integers zero through at most 32")
            if any(type(w) is not int or w < 0 or w > 1_000_000 for w in row) or not sum(row):
                raise ScopeError("probability weights must be nonnegative integers with positive total")
        integer(self.max_budget, "max_budget", 0, sum(self.max_costs))

    @property
    def max_costs(self) -> tuple[int, ...]:
        return tuple(len(row) - 1 for row in self.weights)

    @property
    def denominator(self) -> int:
        return math.prod(sum(row) for row in self.weights)

    @property
    def cdfs(self) -> tuple[tuple[int, ...], ...]:
        return tuple(tuple(itertools.accumulate(row)) for row in self.weights)

    @property
    def identity(self) -> str:
        return digest({"schema": "independent-cost-domain/v1", "weights": self.weights, "max_budget": self.max_budget})


@dataclass(frozen=True)
class State:
    """A maximizing threshold vector for one prefix and exact total payment."""

    numerator: int
    prices: tuple[int, ...]


@dataclass(frozen=True)
class Frontier:
    """An exact Bellman table with a separately checkable finite certificate."""

    domain: Domain
    layers: tuple[tuple[State | None, ...], ...]
    transitions: int

    @property
    def identity(self) -> str:
        return digest(frontier_payload(self))


@dataclass(frozen=True)
class Solution:
    """A posted-price bundle mechanism or an explicit no-offer action."""

    prices: tuple[int, ...] | None
    budget: int
    value: int
    numerator: int
    denominator: int
    probability_numerator: int
    examined_states: int

    @property
    def surplus(self) -> float:
        return self.numerator / self.denominator

    def record(self) -> dict[str, Any]:
        return {
            "prices": self.prices,
            "budget": self.budget,
            "buyer_value": self.value,
            "expected_buyer_surplus_exact": [self.numerator, self.denominator],
            "expected_buyer_surplus": self.surplus,
            "purchase_probability_exact": [self.probability_numerator, self.denominator],
            "examined_states": self.examined_states,
        }


def compile_frontier(domain: Domain) -> Frontier:
    """Optimize joint acceptance mass for each exact payment by dynamic programming."""
    width = domain.max_budget + 1
    initial: list[State | None] = [None] * width
    initial[0] = State(1, ())
    layers: list[tuple[State | None, ...]] = [tuple(initial)]
    transitions = 0
    for cdf in domain.cdfs:
        previous = layers[-1]
        current: list[State | None] = [None] * width
        for paid, state in enumerate(previous):
            if state is None:
                continue
            for price, mass in enumerate(cdf):
                total = paid + price
                if total >= width:
                    break
                transitions += 1
                candidate = State(state.numerator * mass, state.prices + (price,))
                incumbent = current[total]
                if incumbent is None or candidate.numerator > incumbent.numerator:
                    current[total] = candidate
                elif candidate.numerator == incumbent.numerator and candidate.prices < incumbent.prices:
                    current[total] = candidate
        layers.append(tuple(current))
    return Frontier(domain, tuple(layers), transitions)


def verify_frontier(frontier: Frontier) -> dict[str, int | bool]:
    """Check feasibility, exact witnesses and every Bellman upper-bound inequality."""
    domain, layers = frontier.domain, frontier.layers
    width = domain.max_budget + 1
    if len(layers) != len(domain.weights) + 1 or any(len(layer) != width for layer in layers):
        raise ScopeError("certificate dimensions differ from the authorized domain")
    if layers[0][0] != State(1, ()) or any(state is not None for state in layers[0][1:]):
        raise ScopeError("certificate has an invalid base case")
    cdfs, inequalities, witnesses = domain.cdfs, 0, 0
    for count in range(1, len(layers)):
        for total, state in enumerate(layers[count]):
            if state is not None:
                if len(state.prices) != count or sum(state.prices) != total:
                    raise ScopeError("certificate witness has an invalid payment total")
                mass = 1
                for supplier, price in enumerate(state.prices):
                    integer(price, "posted price", 0, domain.max_costs[supplier])
                    mass *= sum(domain.weights[supplier][: price + 1])
                if type(state.numerator) is not int or state.numerator != mass:
                    raise ScopeError("certificate witness mass is false")
                witnesses += count
            feasible_predecessor = False
            for price in range(min(domain.max_costs[count - 1], total) + 1):
                predecessor = layers[count - 1][total - price]
                if predecessor is None:
                    continue
                feasible_predecessor = True
                inequalities += 1
                if state is None or state.numerator < predecessor.numerator * cdfs[count - 1][price]:
                    raise ScopeError("certificate fails a Bellman upper-bound inequality")
            if state is not None and not feasible_predecessor:
                raise ScopeError("certificate invents an unreachable state")
    return {"valid": True, "bellman_inequalities": inequalities, "witness_products": witnesses}


def choose(frontier: Frontier, budget: int, value: int) -> Solution:
    """Choose the exact optimal declared-family offer after budget/value adaptation."""
    integer(budget, "budget", 0, frontier.domain.max_budget)
    integer(value, "value", 0, 1_000_000_000)
    best = Solution(None, budget, value, 0, frontier.domain.denominator, 0, budget + 1)
    for total, state in enumerate(frontier.layers[-1][: budget + 1]):
        if state is None:
            continue
        score = (value - total) * state.numerator
        if score > best.numerator:
            best = Solution(state.prices, budget, value, score, best.denominator, state.numerator, budget + 1)
    return best


def exhaustive_optimum(domain: Domain, budget: int, value: int, limit: int = 2_000_000) -> Solution:
    """Independently enumerate every posted-price vector as the strong small-domain oracle."""
    integer(budget, "budget", 0, domain.max_budget)
    integer(value, "value", 0, 1_000_000_000)
    count = math.prod(len(row) for row in domain.weights)
    if count > limit:
        raise ScopeError("exhaustive price enumeration exceeds the explicit operation limit")
    best = Solution(None, budget, value, 0, domain.denominator, 0, count)
    for prices in itertools.product(*(range(len(row)) for row in domain.weights)):
        paid = sum(prices)
        if paid > budget:
            continue
        mass = math.prod(sum(row[: price + 1]) for row, price in zip(domain.weights, prices, strict=True))
        score = (value - paid) * mass
        if score > best.numerator or (
            score == best.numerator
            and score > 0
            and best.prices is not None
            and (paid, prices) < (sum(best.prices), best.prices)
        ):
            best = Solution(prices, budget, value, score, domain.denominator, mass, count)
    return best


@dataclass(frozen=True)
class Outcome:
    """Allocation and payment for each supplier; utility is payment minus true cost."""

    allocation: tuple[int, ...]
    payments: tuple[int, ...]


Rule = Callable[[tuple[int, ...]], Outcome]


def posted_rule(domain: Domain, prices: tuple[int, ...] | None) -> Rule:
    """Construct the supported all-or-none posted-price procurement protocol."""
    if prices is not None:
        if len(prices) != len(domain.weights):
            raise ScopeError("one price per supplier is required")
        for i, price in enumerate(prices):
            integer(price, "price", 0, domain.max_costs[i])

    def execute(reports: tuple[int, ...]) -> Outcome:
        if len(reports) != len(domain.weights):
            raise ScopeError("report dimensions differ from the authorized domain")
        for i, report in enumerate(reports):
            integer(report, "reported cost", 0, domain.max_costs[i])
        accepted = prices is not None and all(r <= p for r, p in zip(reports, prices, strict=True))
        return Outcome((1 if accepted else 0,) * len(reports), prices if accepted and prices else (0,) * len(reports))

    return execute


def vcg_complement_rule(domain: Domain, value: int) -> Rule:
    """Implement conventional efficient VCG procurement, without a budget guarantee."""
    integer(value, "value", 0, 1_000_000_000)

    def execute(reports: tuple[int, ...]) -> Outcome:
        if len(reports) != len(domain.weights):
            raise ScopeError("wrong VCG report dimensions")
        for i, report in enumerate(reports):
            integer(report, "reported cost", 0, domain.max_costs[i])
        if sum(reports) > value:
            return Outcome((0,) * len(reports), (0,) * len(reports))
        return Outcome((1,) * len(reports), tuple(value - sum(reports) + r for r in reports))

    return execute


def finite_check(domain: Domain, rule: Rule, budget: int, comparison_limit: int = 2_000_000) -> dict[str, Any]:
    """Check all finite type/report deviations, IR, bundle feasibility and hard budget."""
    integer(budget, "budget", 0, domain.max_budget)
    profiles = math.prod(len(row) for row in domain.weights)
    comparisons = profiles * sum(domain.max_costs)
    if comparisons > comparison_limit:
        raise ScopeError("finite report/deviation enumeration exceeds its explicit limit")
    report_space = tuple(itertools.product(*(range(len(row)) for row in domain.weights)))
    cache = {reports: rule(reports) for reports in report_space}
    defect_names = ("malformed", "budget", "bundle", "individual_rationality", "truthfulness")
    defects: dict[str, int] = dict.fromkeys(defect_names, 0)
    first: dict[str, Any] = {}
    max_regret = 0

    def defect(kind: str, payload: dict[str, Any]) -> None:
        defects[kind] += 1
        first.setdefault(kind, payload)

    for reports, outcome in cache.items():
        if (
            len(outcome.allocation) != len(reports)
            or len(outcome.payments) != len(reports)
            or any(type(x) is not int or x not in (0, 1) for x in outcome.allocation)
            or any(type(p) is not int or p < 0 for p in outcome.payments)
            or any(p and not x for p, x in zip(outcome.payments, outcome.allocation, strict=True))
        ):
            defect("malformed", {"reports": reports})
            continue
        if sum(outcome.payments) > budget:
            defect("budget", {"reports": reports, "payments": outcome.payments, "budget": budget})
        if len(set(outcome.allocation)) > 1:
            defect("bundle", {"reports": reports, "allocation": outcome.allocation})
        for supplier, true_cost in enumerate(reports):
            utility = outcome.payments[supplier] - true_cost * outcome.allocation[supplier]
            if utility < 0:
                defect("individual_rationality", {"reports": reports, "supplier": supplier, "utility": utility})
            for misreport in range(len(domain.weights[supplier])):
                if misreport == true_cost:
                    continue
                changed = reports[:supplier] + (misreport,) + reports[supplier + 1 :]
                alternative = cache[changed]
                regret = alternative.payments[supplier] - true_cost * alternative.allocation[supplier] - utility
                max_regret = max(max_regret, regret)
                if regret > 0:
                    defect(
                        "truthfulness",
                        {"reports": reports, "supplier": supplier, "misreport": misreport, "gain": regret},
                    )
    return {
        "pass": not any(defects.values()),
        "profiles": profiles,
        "deviation_comparisons": comparisons,
        "violations": defects,
        "first_counterexamples": first,
        "maximum_profitable_deviation": max_regret,
        "scope": "all integer costs and reports in the declared finite product domain; unilateral deviations only",
    }


def frontier_payload(frontier: Frontier) -> dict[str, Any]:
    """Produce a portable bounded artifact; its hash alone conveys no correctness."""
    return {
        "schema": "procurement-frontier/v1",
        "domain": {"weights": frontier.domain.weights, "max_budget": frontier.domain.max_budget},
        "layers": [[None if s is None else [s.numerator, s.prices] for s in row] for row in frontier.layers],
        "transitions": frontier.transitions,
    }


def import_frontier(payload: dict[str, Any], expected_digest: str, expected_domain: str) -> Frontier:
    """Import and mathematically revalidate a matching bounded artifact."""
    if digest(payload) != expected_digest or payload.get("schema") != "procurement-frontier/v1":
        raise ScopeError("artifact identity or schema mismatch")
    if set(payload) != {"schema", "domain", "layers", "transitions"}:
        raise ScopeError("unexpected artifact fields")
    raw = payload["domain"]
    if not isinstance(raw, dict) or set(raw) != {"weights", "max_budget"}:
        raise ScopeError("unsupported domain fields; correlations and other cost models are outside scope")
    domain = Domain(tuple(tuple(row) for row in raw["weights"]), raw["max_budget"])
    if domain.identity != expected_domain:
        raise ScopeError("recipient distribution/domain mismatch")
    layers = tuple(tuple(None if x is None else State(x[0], tuple(x[1])) for x in row) for row in payload["layers"])
    frontier = Frontier(domain, layers, integer(payload["transitions"], "transitions", 0, 10_000_000))
    verified = verify_frontier(frontier)
    if frontier.transitions != verified["bellman_inequalities"]:
        raise ScopeError("claimed construction operation count does not match the certificate")
    return frontier


def seeded_domain(seed: int, suppliers: int, maximum_cost: int, budget: int | None = None) -> Domain:
    """Generate openly synthetic independent distributions; never customer data."""
    rng = random.Random(seed)
    weights = tuple(tuple(rng.randint(1, 17) for _ in range(maximum_cost + 1)) for _ in range(suppliers))
    return Domain(weights, suppliers * maximum_cost if budget is None else budget)


def negative_cases() -> dict[str, Any]:
    """Preserve decisive failures of naive composition and efficient VCG under a cap."""
    domain = Domain(((1, 1, 1, 1, 1), (1, 1, 1, 1, 1)), 8)

    def independent(reports: tuple[int, ...]) -> Outcome:
        return Outcome(tuple(int(r <= 4) for r in reports), tuple(4 if r <= 4 else 0 for r in reports))

    corrected = choose(compile_frontier(domain), budget=5, value=12)
    return {
        "naive_independent_thresholds": {"prices": [4, 4], **finite_check(domain, independent, budget=5)},
        "ordinary_efficient_vcg": finite_check(domain, vcg_complement_rule(domain, value=12), budget=5),
        "admissible_joint_protocol": {
            "solution": corrected.record(),
            **finite_check(domain, posted_rule(domain, corrected.prices), budget=5),
        },
    }


PROTOCOL: dict[str, Any] = {
    "schema": "mechanism-witness-protocol/v1",
    "question": (
        "Can a reusable exact budget frontier and independently checked mechanism certificate support fresh "
        "budget/value queries without repeatedly constructing the frontier?"
    ),
    "scientific_scope": (
        "Known-method, synthetic software demonstration. No live frontier-model experiment, novel economic theorem, "
        "network authentication, actual procurement, sale or payment."
    ),
    "objective": (
        "maximize expected buyer value minus supplier payments within deterministic all-or-none posted-price bundle "
        "mechanisms, subject to an ex-post hard budget and no-offer option"
    ),
    "assumptions": [
        "independent finite cost distributions",
        "quasilinear supplier utility",
        "one indivisible required component per supplier",
        "no collusion or externalities",
        "declared integer reports",
        "public budget and buyer value",
        "distributions supplied rather than learned",
    ],
    "small_confirmation": {
        "seeds": list(range(261026700, 261026748)),
        "suppliers": "2 + (seed mod 3)",
        "maximum_cost": "3 + (seed mod 3)",
        "budget": "floor(0.65*n*maximum_cost)",
        "buyer_value": "budget + 2 + (seed mod 7)",
    },
    "large_confirmation": {
        "seeds": list(range(261026900, 261026905)),
        "supplier_counts": [4, 6, 8, 10, 12],
        "maximum_costs": [6, 8, 10, 12, 14],
    },
    "reuse_confirmation": {
        "seed": 261027100,
        "suppliers": 6,
        "maximum_cost": 10,
        "receivers": 12,
        "fresh_queries": "budget=18+2*i, value=budget+8+(i mod 4), i=0..11",
        "cold_counterfactual": (
            "every equally capable recipient uses the same exact DP and full certificate checker at its budget"
        ),
        "shared_counterfactual": (
            "creator compiles/checks full frontier; each recipient imports and independently revalidates it, "
            "then queries; report this conservative import cost separately from trusted-attestation scenarios"
        ),
    },
    "acceptance": [
        "all 48 small cases match exact exhaustive optimal objective",
        "all 48 emitted protocols pass exhaustive finite DSIC/IR/budget/bundle checks",
        "all five large Bellman certificates pass",
        "mutated and mismatched artifacts rejected",
        "negative cases remain rejected",
    ],
    "transfer_interpretation": (
        "An artifact can replace repeated construction only when its validated input domain is reusable. "
        "Recipient intelligence and known DP theory are unchanged. Each receiving agent's full mathematical "
        "revalidation is charged; a trusted-attestation reduction is a separate simulated assumption, "
        "not this executed witness."
    ),
    "exclusions": [
        "universal mechanism optimality",
        "arbitrary correlated types",
        "continuous-type numerical extrapolation",
        "multi-dimensional reports",
        "empirical customer acceptance",
        "AI invention success rate",
        "operating-dollar calibration from integer-operation counts",
    ],
}


def confirmation() -> dict[str, Any]:
    """Run the frozen finite confirmation and retain every prespecified case."""
    small = []
    for seed in PROTOCOL["small_confirmation"]["seeds"]:
        n, maximum = 2 + seed % 3, 3 + seed % 3
        domain = seeded_domain(seed, n, maximum)
        budget = (65 * n * maximum) // 100
        value = budget + 2 + seed % 7
        frontier = compile_frontier(domain)
        certificate = verify_frontier(frontier)
        solution = choose(frontier, budget, value)
        oracle = exhaustive_optimum(domain, budget, value)
        checked = finite_check(domain, posted_rule(domain, solution.prices), budget)
        small.append(
            {
                "seed": seed,
                "domain_hash": domain.identity,
                "suppliers": n,
                "maximum_cost": maximum,
                "solution": solution.record(),
                "oracle_matches": solution.numerator == oracle.numerator,
                "oracle_price_vectors": oracle.examined_states,
                "dp_transitions": frontier.transitions,
                "certificate": certificate,
                "finite_validation": checked,
            }
        )
    large = []
    large_protocol = PROTOCOL["large_confirmation"]
    for seed, n, maximum in zip(
        large_protocol["seeds"], large_protocol["supplier_counts"], large_protocol["maximum_costs"], strict=True
    ):
        domain = seeded_domain(seed, n, maximum)
        frontier = compile_frontier(domain)
        certificate = verify_frontier(frontier)
        budget = (65 * n * maximum) // 100
        solution = choose(frontier, budget, budget + 2 * n)
        large.append(
            {
                "seed": seed,
                "suppliers": n,
                "maximum_cost": maximum,
                "price_vectors_in_declared_family": math.prod(len(row) for row in domain.weights),
                "dp_transitions_executed": frontier.transitions,
                "certificate": certificate,
                "solution": solution.record(),
                "frontier_bytes": len(canonical(frontier_payload(frontier))),
                "finite_profile_enumeration_performed": False,
            }
        )
    domain = seeded_domain(PROTOCOL["reuse_confirmation"]["seed"], 6, 10)
    shared = compile_frontier(domain)
    owner_check = verify_frontier(shared)
    payload = frontier_payload(shared)
    source_identity, domain_identity = shared.identity, domain.identity
    cold_transitions = cold_inequalities = cold_products = query_states = 0
    receiver_checks = receiver_products = receiver_bytes = 0
    queries = []
    for i in range(12):
        budget, value = 18 + 2 * i, 26 + 2 * i + i % 4
        cold_domain = Domain(domain.weights, budget)
        cold = compile_frontier(cold_domain)
        cold_validation = verify_frontier(cold)
        cold_transitions += cold.transitions
        cold_inequalities += int(cold_validation["bellman_inequalities"])
        cold_products += int(cold_validation["witness_products"])
        imported = import_frontier(json.loads(canonical(payload)), source_identity, domain_identity)
        receiver_checks += imported.transitions
        receiver_products += int(owner_check["witness_products"])
        receiver_bytes += len(canonical(payload))
        fresh = choose(imported, budget, value)
        cold_solution = choose(cold, budget, value)
        query_states += fresh.examined_states
        queries.append(
            {
                "receiver": f"recipient-{i + 1}",
                "budget": budget,
                "value": value,
                "identical_to_cold": fresh.numerator == cold_solution.numerator,
                "expected_buyer_surplus": fresh.surplus,
                "selection_states": fresh.examined_states,
            }
        )
    reuse = {
        "queries": queries,
        "all_fresh_queries_match_equal_intelligence_baseline": all(x["identical_to_cold"] for x in queries),
        "cold_counts": {
            "construction_transitions": cold_transitions,
            "certificate_inequalities": cold_inequalities,
            "certificate_witness_multiplications": cold_products,
        },
        "shared_counts_including_creator_and_all_receivers": {
            "construction_transitions": shared.transitions,
            "certificate_inequalities": int(owner_check["bellman_inequalities"]) + receiver_checks,
            "certificate_witness_multiplications": int(owner_check["witness_products"]) + receiver_products,
        },
        "fresh_selection_states_in_both_arms": query_states,
        "recipient_payload_bytes_hashed_in_shared_arm": receiver_bytes,
        "trusted_attestation_scenario_before_selection": {
            "construction_transitions": shared.transitions,
            "certificate_inequalities": int(owner_check["bellman_inequalities"]),
            "certificate_witness_multiplications": int(owner_check["witness_products"]),
        },
        "trusted_attestation_status": (
            "not an executed authorization assumption; graph authentication and trusted validation "
            "are simulated separately"
        ),
        "duplicate_capability_incremental_construction_saved": 0,
        "distinct_domain_no_transfer": (
            "all changed distributions require new certificates; copying the filename does not make them applicable"
        ),
    }
    negatives = negative_cases()
    return {
        "small_cases": small,
        "large_cases": large,
        "recipient_reuse": reuse,
        "preserved_negative_cases": negatives,
        "summary": {
            "small_cases": len(small),
            "exact_oracle_matches": sum(x["oracle_matches"] for x in small),
            "finite_protocol_passes": sum(x["finite_validation"]["pass"] for x in small),
            "finite_profiles_checked": sum(x["finite_validation"]["profiles"] for x in small),
            "unilateral_deviation_comparisons": sum(x["finite_validation"]["deviation_comparisons"] for x in small),
            "large_certificate_passes": len(large),
            "largest_price_space": max(x["price_vectors_in_declared_family"] for x in large),
            "largest_case_dp_transitions": large[-1]["dp_transitions_executed"],
            "naive_composition_rejected": not negatives["naive_independent_thresholds"]["pass"],
            "efficient_vcg_rejected_under_hard_budget": not negatives["ordinary_efficient_vcg"]["pass"],
        },
    }


def frozen_identities() -> dict[str, str]:
    """Bind the experiment to source, tests and the prospective design statement."""
    root = Path(__file__).resolve().parents[1]
    paths = ("src/mechanism_witness.py", "tests/test_mechanism_witness.py", "evidence/mechanism_design.md")
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}


def main() -> None:
    """Freeze first, then execute confirmation without silently replacing a prior result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "confirm", "verify"))
    parser.add_argument(
        "--evidence", type=Path, default=Path(__file__).resolve().parents[1] / "evidence/mechanism_witness.json"
    )
    args = parser.parse_args()
    if args.action == "freeze":
        if args.evidence.exists():
            raise ScopeError("a protocol/result already exists; preserve its identity")
        record = {
            "status": "frozen-before-confirmation",
            "frozen_at_utc": datetime.now(UTC).isoformat(),
            "protocol": PROTOCOL,
            "protocol_sha256": digest(PROTOCOL),
            "source_identities": frozen_identities(),
        }
        args.evidence.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"status": record["status"], "protocol_sha256": record["protocol_sha256"]}))
        return
    record = json.loads(args.evidence.read_text())
    if record["source_identities"] != frozen_identities() or record["protocol_sha256"] != digest(PROTOCOL):
        raise ScopeError("frozen identity changed; do not relabel a changed source as confirmation")
    if args.action == "confirm":
        if record["status"] != "frozen-before-confirmation":
            raise ScopeError("confirmation already exists; use verify for exact replay")
        record["results"] = confirmation()
        record["status"] = "completed-local-synthetic-confirmation"
        record["completed_at_utc"] = datetime.now(UTC).isoformat()
        record["result_sha256"] = digest(record["results"])
        args.evidence.write_text(json.dumps(record, indent=2) + "\n")
    else:
        replay = confirmation()
        if digest(replay) != record["result_sha256"] or replay != record["results"]:
            raise ScopeError("exact replay differs from the retained evidence")
    print(
        json.dumps(
            {
                "status": record["status"],
                "summary": record["results"]["summary"],
                "result_sha256": record["result_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
