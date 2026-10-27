# SPDX-License-Identifier: Apache-2.0
"""Independent cash conservation and nonparticipation assertions."""

import copy
import json
import unittest
from pathlib import Path

from economic import cash_path, evaluate, expertise_grid, load_operators, retention_grid, select_participants, tariff_cost


class AccountingTests(unittest.TestCase):
    """Assert contractual identities against hand-computed ledgers."""

    def setUp(self) -> None:
        self.a = json.loads(Path(__file__).with_name("assumptions-v1.json").read_text())
        self.ops = [{"id": str(i), "baseline_cost": 1200., "contingent_cost": 200.,
                     "value_of_information": 1000., "peak_action_reserve": 1200., "valid": True}
                    for i in range(2)]
        self.technical = {"operators": self.ops}

    def test_no_acquisition_revenue(self) -> None:
        result = cash_path(self.a, 2, self.ops, True, False, ("paid", "paid"))
        self.assertEqual(result["collected_service_revenue"], 160.)
        self.assertEqual(result["sensor_paid"], 600.)
        self.assertEqual(result["operating_profit_before_BC"], 50.)
        self.assertEqual(result["end_cash"], 1550.)
        self.assertEqual(result["pass_through_refunded"], 0.)

    def test_common_failure_refunds_all_and_loses_sensor_cost(self) -> None:
        result = cash_path(self.a, 2, self.ops, True, True, ("reject", "reject"))
        self.assertEqual(result["refunds"], 648.)
        self.assertEqual(result["collected_service_revenue"], 0.)
        self.assertEqual(result["operating_profit_before_BC"], -720.)
        self.assertEqual(result["end_cash"], 780.)
        self.assertEqual(result["customer_expected_action_savings"], 0.)

    def test_partial_delivery_and_default(self) -> None:
        result = cash_path(self.a, 2, self.ops, True, False, ("default", "reject"))
        self.assertEqual(result["earned_gross_service_revenue"], 80.)
        self.assertEqual(result["collected_service_revenue"], 24.)
        self.assertEqual(result["bad_debt"], 56.)
        self.assertEqual(result["refunds"], 24.)
        self.assertEqual(result["A_cash_cost"], 115.)
        self.assertEqual(result["operating_profit_before_BC"], -91.)

    def test_finite_event_tree_conserves_probability_and_cash(self) -> None:
        result = evaluate(self.technical, self.a, retain_paths=True)
        self.assertAlmostEqual(result["probability_sum"], 1.)
        for branch in result["paths"]:
            self.assertAlmostEqual(branch["end_cash"], 1500 + branch["operating_profit_before_BC"])
            self.assertAlmostEqual(branch["earned_gross_service_revenue"] - branch["bad_debt"],
                                   branch["collected_service_revenue"])

    def test_all_withdraw_no_sale_and_quote_cost_retained(self) -> None:
        result = evaluate(self.technical, {**self.a, "precommit_withdrawal_probability": 1.})
        self.assertEqual(result["expected"]["pass_through_collected"], 0.)
        self.assertEqual(result["expected"]["collected_service_revenue"], 0.)
        self.assertEqual(result["expected"]["operating_profit_before_BC"], -4.)

    def test_zero_seed_cannot_spend_refundable_deposits_freely(self) -> None:
        result = evaluate(self.technical, {**self.a, "seed_capital": 0.})
        self.assertAlmostEqual(result["liquidity_failure_probability"], 1.)
        self.assertGreater(result["maximum_extra_financing"], 600.)

    def test_buyer_reserve_prevents_participation(self) -> None:
        ops = [{**x, "customer_cash_available": 1300.} for x in self.ops]
        self.assertEqual(select_participants(ops, self.a, True, True), [])

    def test_common_capacity_does_not_create_value_in_ablation(self) -> None:
        result = evaluate(self.technical, self.a, constructed=False, shared=True)
        self.assertEqual(result["launch_probability"], 0.)

    def test_negative_information_value_refused(self) -> None:
        ops = [{**x, "contingent_cost": 1300., "value_of_information": -100.} for x in self.ops]
        self.assertEqual(select_participants(ops, self.a, True, True), [])

    def test_value_identity_and_nonfinite_rejected(self) -> None:
        invalid = copy.deepcopy(self.technical)
        invalid["operators"][0]["value_of_information"] = 900.
        with self.assertRaises(ValueError):
            load_operators(invalid)
        invalid["operators"][0]["value_of_information"] = float("nan")
        with self.assertRaises(ValueError):
            load_operators(invalid)

    def test_equality_grid_is_not_an_assumed_expert_gain(self) -> None:
        rows = [x for x in expertise_grid(self.a) if x["delta_E"] == x["delta_Eplus"] == 0
                and x["matched_resource_budget_row"]]
        self.assertEqual(len(rows), 6)
        for row in rows:
            self.assertEqual(row["U"], row["E"])
            self.assertEqual(row["E"], row["Eplus"])

    def test_retention_zero_gain_rejected_before_assessment(self) -> None:
        for row in retention_grid(self.a):
            if row["assumed_cash_saving_per_fresh_use"] == 0:
                self.assertIsNone(row["minimum_uses_for_strict_positive_increment"])
                self.assertEqual(row["admission_decision"], "reject_before_assessment")

    def test_long_context_and_tariff_units(self) -> None:
        self.assertAlmostEqual(tariff_cost(30000, 10000, self.a["tariffs"]["Astra"]), 0.80)
        self.assertAlmostEqual(tariff_cost(300000, 10000, self.a["tariffs"]["Astra"]), 6.75)

    def test_invalid_probability_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate(self.technical, {**self.a, "common_package_failure_probability": 1.1})


if __name__ == "__main__":
    unittest.main()
