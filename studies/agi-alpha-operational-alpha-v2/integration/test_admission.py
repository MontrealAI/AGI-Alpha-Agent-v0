# SPDX-License-Identifier: Apache-2.0
"""Boundary checks for buying additional evidence without changing the Alpha gate."""

from __future__ import annotations

import unittest

from admission import assess_if_reachable, historical_hurdle_envelope, research_gate_envelope


class AdmissionEnvelopeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = {
            "maximum_per_use_delta_cents": 10,
            "forecast_eligible_uses": 10,
            "lifecycle_cost_cents": 40,
            "evaluation_cost_cents": 20,
            "maximum_independent_clusters": 6,
        }

    def test_unreachable_does_not_read_assay(self) -> None:
        def forbidden() -> dict[str, object]:
            raise AssertionError("protected future assay was accessed")

        result = assess_if_reachable({**self.spec, "forecast_eligible_uses": 1}, forbidden)
        self.assertFalse(result["assessment_purchased"])
        self.assertEqual(result["assessment_cost_cents"], 0)

    def test_reachable_buys_once_without_admitting(self) -> None:
        calls = []

        def assay() -> dict[str, object]:
            calls.append(1)
            return {"verdict": "reject"}

        result = assess_if_reachable(self.spec, assay)
        self.assertEqual(calls, [1])
        self.assertEqual(result["assessment_cost_cents"], 20)
        self.assertEqual(result["assessment"]["verdict"], "reject")
        self.assertFalse(result["envelope"]["grants_admission"])

    def test_existing_six_cluster_rule_preserved(self) -> None:
        result = research_gate_envelope({**self.spec, "maximum_independent_clusters": 4})
        self.assertFalse(result["reachable"])

    def test_failed_assessment_remains_charged(self) -> None:
        def failed() -> dict[str, object]:
            raise RuntimeError("declared failed assessor")

        result = assess_if_reachable(self.spec, failed)
        self.assertTrue(result["assessment_purchased"])
        self.assertEqual(result["assessment_cost_cents"], 20)
        self.assertEqual(result["assessment"]["verdict"], "assessment-failed")

    def test_cent_boundary_and_fractional_forecast(self) -> None:
        self.assertFalse(research_gate_envelope({**self.spec, "forecast_eligible_uses": "6.0999"})["reachable"])
        self.assertTrue(research_gate_envelope({**self.spec, "forecast_eligible_uses": "6.1"})["reachable"])

    def test_zero_upper_bound_never_positive(self) -> None:
        self.assertFalse(research_gate_envelope({**self.spec, "maximum_per_use_delta_cents": 0})["reachable"])

    def test_invalid_numbers_rejected(self) -> None:
        for value in [True, "nan", "inf", -1]:
            with self.assertRaises(ValueError):
                research_gate_envelope({**self.spec, "forecast_eligible_uses": value})

    def test_legacy_hurdle_strict_zero_cost_boundary(self) -> None:
        spec = {"uses": 0, "transfer": 1, "cap": 10, "fee": 0, "fixed": 0, "hurdle": "1.25"}
        self.assertFalse(historical_hurdle_envelope(spec)["reachable"])
        self.assertTrue(historical_hurdle_envelope({**spec, "uses": 1})["reachable"])

    def test_legacy_hurdle_equality(self) -> None:
        spec = {"uses": 1, "transfer": 1, "cap": 125, "fee": 0, "fixed": 100, "hurdle": "1.25"}
        self.assertTrue(historical_hurdle_envelope(spec)["reachable"])
        self.assertFalse(historical_hurdle_envelope({**spec, "cap": "124.99"})["reachable"])


if __name__ == "__main__":
    unittest.main()
