# SPDX-License-Identifier: Apache-2.0
"""Arithmetic and binding tests; synthetic numbers are not mission observations."""

from __future__ import annotations

import dataclasses
import unittest

from src.alpha_assessment import AlphaAssessment, AlphaCosts, BetaBaseline, evaluate_alpha


class AlphaAssessmentTests(unittest.TestCase):
    def assessment(self, **changes) -> AlphaAssessment:
        return dataclasses.replace(AlphaAssessment(
            beta_id="competent-beta-v1", comparator_capability_set_hash="1" * 64,
            scope=("finite-mechanisms",), paired_gains=(90.0, 110.0), planned_reuse=10.0,
            costs=AlphaCosts(acquisition=25, construction=100, validation=25, integration=20,
                             operating=10, risk=10, maintenance=10, migration=10, distribution=10),
            uncertainty_margin_per_use=20.0, source_kind="simulation-fixture",
            protocol_id="synthetic-paired-fixture-v1", evidence_hash="2" * 64,
        ), **changes)

    def test_full_lifecycle_arithmetic_and_uncertainty(self) -> None:
        assessment = self.assessment()
        result = evaluate_alpha(assessment)
        self.assertEqual(assessment.costs.total, 220)
        self.assertEqual((result.lower_net, result.expected_net, result.upper_net), (580, 780, 980))
        self.assertTrue(result.accepted)

    def test_positive_gross_gain_novelty_or_zero_net_do_not_admit(self) -> None:
        for costs in (1000, 1001):
            result = evaluate_alpha(self.assessment(costs=AlphaCosts(construction=costs),
                                                     uncertainty_margin_per_use=0))
            self.assertFalse(result.accepted)
        self.assertFalse(evaluate_alpha(self.assessment(uncertainty_margin_per_use=90)).accepted)
        self.assertFalse(evaluate_alpha(self.assessment(planned_reuse=0)).accepted)
        self.assertFalse(evaluate_alpha(self.assessment(redundant=True)).accepted)

    def test_complementary_bundle_need_not_make_components_profitable(self) -> None:
        component_a = self.assessment(paired_gains=(0.0, 0.0), costs=AlphaCosts(construction=100))
        component_b = self.assessment(paired_gains=(0.0, 0.0), costs=AlphaCosts(construction=100))
        bundle = self.assessment(paired_gains=(90.0, 110.0),
                                 costs=AlphaCosts(construction=200, validation=50, integration=50),
                                 dependency_hashes=("3" * 64, "4" * 64))
        self.assertFalse(evaluate_alpha(component_a).accepted)
        self.assertFalse(evaluate_alpha(component_b).accepted)
        self.assertTrue(evaluate_alpha(bundle).accepted)

    def test_explicit_probe_weights_do_not_create_pseudo_observations(self) -> None:
        assessment = self.assessment(paired_gains=(10.0, 100.0), paired_weights=(0.9, 0.1),
                                     costs=AlphaCosts(), uncertainty_margin_per_use=0, planned_reuse=1)
        self.assertEqual(evaluate_alpha(assessment).expected_net, 19)

    def test_beta_scope_dependency_and_cost_changes_change_binding(self) -> None:
        original = self.assessment()
        for changes in ({"beta_id": "competent-beta-v2"}, {"scope": ("new-scope",)},
                        {"dependency_hashes": ("3" * 64,)}, {"costs": AlphaCosts(construction=221)},
                        {"comparator_capability_set_hash": "3" * 64}, {"evidence_hash": "4" * 64}):
            with self.subTest(changes=changes):
                self.assertNotEqual(original.hash, self.assessment(**changes).hash)
        baseline = BetaBaseline("v1", "1" * 64, "competent fixture", "simulation-fixture")
        self.assertNotEqual(baseline.hash, dataclasses.replace(baseline, configuration_hash="2" * 64).hash)

    def test_malformed_or_nonfinite_inputs_are_rejected(self) -> None:
        for changes in ({"paired_gains": ()}, {"paired_gains": (1,)}, {"paired_gains": (1, float("nan"))},
                        {"planned_reuse": -1}, {"planned_reuse": True}, {"uncertainty_margin_per_use": -1},
                        {"scope": []}, {"scope": ("x", "x")}, {"evidence_hash": "label"},
                        {"source_kind": "actual-sales-because-simulated"}, {"dependency_hashes": ["1" * 64]},
                        {"paired_weights": (1,)}, {"paired_weights": (0, 0)}, {"paired_weights": (-1, 2)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.assessment(**changes)
        for value in (-1, float("inf"), True):
            with self.subTest(cost=value), self.assertRaises(ValueError):
                AlphaCosts(risk=value)


if __name__ == "__main__":
    unittest.main()
