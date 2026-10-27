# SPDX-License-Identifier: Apache-2.0
"""Adversarial and exact-oracle checks of the finite procurement witness."""

import copy
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mechanism_witness import (  # noqa: E402
    Domain,
    Outcome,
    ScopeError,
    State,
    canonical_replay_equal,
    choose,
    compile_frontier,
    digest,
    exhaustive_optimum,
    finite_check,
    frontier_payload,
    import_frontier,
    negative_cases,
    posted_rule,
    seeded_domain,
    verify_frontier,
)


class MechanismWitnessTests(unittest.TestCase):
    def test_replay_compares_serialized_semantics_and_rejects_changed_values(self) -> None:
        actual = {"prices": (2, 3), "nested": [{"profile": (0, 1), "pass": True}]}
        retained = json.loads(json.dumps(actual))
        self.assertNotEqual(actual, retained)
        self.assertTrue(canonical_replay_equal(actual, retained))
        retained["prices"][1] = 4
        self.assertFalse(canonical_replay_equal(actual, retained))

    def test_exact_known_optimum(self) -> None:
        domain = Domain(((1, 1), (1, 1)), 2)
        solution = choose(compile_frontier(domain), 1, 4)
        self.assertEqual(solution.prices, (0, 1))
        self.assertEqual((solution.numerator, solution.denominator), (6, 4))

    def test_independent_exhaustive_oracle_on_development_domains(self) -> None:
        for seed in range(8):
            domain = seeded_domain(seed, 2 + seed % 2, 3)
            frontier = compile_frontier(domain)
            self.assertTrue(verify_frontier(frontier)["valid"])
            for budget in (0, 2, domain.max_budget):
                dp = choose(frontier, budget, budget + 5)
                oracle = exhaustive_optimum(domain, budget, budget + 5)
                self.assertEqual(dp.numerator, oracle.numerator)
                self.assertEqual(dp.prices, oracle.prices)

    def test_full_finite_truthfulness_individual_rationality_and_budget(self) -> None:
        domain = seeded_domain(51, 3, 4)
        solution = choose(compile_frontier(domain), 7, 14)
        checked = finite_check(domain, posted_rule(domain, solution.prices), 7)
        self.assertTrue(checked["pass"])
        self.assertEqual(checked["profiles"], 125)
        self.assertEqual(checked["deviation_comparisons"], 1500)

    def test_composition_and_vcg_negative_controls_remain_rejected(self) -> None:
        controls = negative_cases()
        for name in ("naive_independent_thresholds", "ordinary_efficient_vcg"):
            self.assertFalse(controls[name]["pass"])
            self.assertGreater(controls[name]["violations"]["budget"], 0)
            self.assertEqual(controls[name]["violations"]["truthfulness"], 0)
        self.assertTrue(controls["admissible_joint_protocol"]["pass"])

    def test_report_dependent_payment_is_not_an_attestation_of_truthfulness(self) -> None:
        domain = Domain(((1, 1, 1), (1, 1, 1)), 4)

        def dishonest(reports: tuple[int, ...]) -> Outcome:
            return Outcome((1, 1), reports)

        checked = finite_check(domain, dishonest, budget=4)
        self.assertFalse(checked["pass"])
        self.assertGreater(checked["maximum_profitable_deviation"], 0)

    def test_corrupt_optimality_certificate_rejected(self) -> None:
        frontier = compile_frontier(seeded_domain(52, 3, 4))
        layers = [list(layer) for layer in frontier.layers]
        layers[2][3] = State(0, (1, 2))
        with self.assertRaises(ScopeError):
            verify_frontier(replace(frontier, layers=tuple(tuple(row) for row in layers)))

    def test_missing_reachable_state_rejected(self) -> None:
        frontier = compile_frontier(seeded_domain(53, 2, 3))
        layers = [list(layer) for layer in frontier.layers]
        layers[1][0] = None
        with self.assertRaises(ScopeError):
            verify_frontier(replace(frontier, layers=tuple(tuple(row) for row in layers)))

    def test_portable_revalidation_and_fresh_query(self) -> None:
        domain = seeded_domain(54, 4, 5)
        original = compile_frontier(domain)
        imported = import_frontier(frontier_payload(original), original.identity, domain.identity)
        for budget, value in ((4, 18), (12, 23), (19, 30)):
            self.assertEqual(choose(original, budget, value), choose(imported, budget, value))

    def test_digest_and_domain_mismatch_rejected(self) -> None:
        frontier = compile_frontier(seeded_domain(55, 3, 4))
        payload = copy.deepcopy(frontier_payload(frontier))
        payload["transitions"] += 1
        with self.assertRaises(ScopeError):
            import_frontier(payload, frontier.identity, frontier.domain.identity)
        with self.assertRaises(ScopeError):
            import_frontier(payload, digest(payload), frontier.domain.identity)
        with self.assertRaises(ScopeError):
            import_frontier(frontier_payload(frontier), frontier.identity, seeded_domain(56, 3, 4).identity)

    def test_domain_scope_is_enforced_before_query(self) -> None:
        domain = seeded_domain(57, 2, 3)
        frontier = compile_frontier(domain)
        for budget in (-1, 7, True):
            with self.assertRaises(ScopeError):
                choose(frontier, budget, 12)
        rule = posted_rule(domain, (2, 2))
        for reports in ((1,), (0, 4), (True, 1), (-1, 2)):
            with self.assertRaises(ScopeError):
                rule(reports)

    def test_explicit_correlated_domain_cannot_be_silently_ignored(self) -> None:
        frontier = compile_frontier(seeded_domain(60, 2, 3))
        payload = frontier_payload(frontier)
        payload["domain"]["correlation"] = "perfect-positive"
        with self.assertRaises(ScopeError):
            import_frontier(payload, digest(payload), frontier.domain.identity)

    def test_no_offer_and_zero_probability_types(self) -> None:
        domain = Domain(((0, 0, 1), (0, 0, 1)), 4)
        frontier = compile_frontier(domain)
        self.assertIsNone(choose(frontier, 1, 100).prices)
        self.assertIsNone(choose(frontier, 4, 0).prices)
        self.assertEqual(choose(frontier, 4, 10).prices, (2, 2))
        self.assertTrue(verify_frontier(frontier)["valid"])

    def test_duplicate_artifact_cannot_create_an_incremental_solution_gain(self) -> None:
        original = compile_frontier(seeded_domain(58, 3, 4))
        first = import_frontier(frontier_payload(original), original.identity, original.domain.identity)
        duplicate = import_frontier(frontier_payload(original), original.identity, original.domain.identity)
        self.assertEqual(first.identity, duplicate.identity)
        self.assertEqual(choose(first, 7, 15).surplus - choose(duplicate, 7, 15).surplus, 0)

    def test_resource_bounds_prevent_exhaustive_overclaim(self) -> None:
        domain = seeded_domain(59, 12, 14)
        with self.assertRaises(ScopeError):
            exhaustive_optimum(domain, 100, 140)
        with self.assertRaises(ScopeError):
            finite_check(domain, posted_rule(domain, (8,) * 12), 100)
        with self.assertRaises(ScopeError):
            Domain(((1, 1),) * 13, 12)


if __name__ == "__main__":
    unittest.main()
