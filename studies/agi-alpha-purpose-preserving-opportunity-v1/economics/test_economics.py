# SPDX-License-Identifier: Apache-2.0
"""Independent accounting identities and evidence-boundary checks."""

import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

from economics import choose_offer, construction_case, service_case


class AccountingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = json.loads(Path(__file__).with_name("inputs.json").read_text())

    def world(self, name: str) -> dict[str, Any]:
        return next(w for w in self.inputs["worlds"] if w["id"] == name)

    def test_cash_accrual_conservation_for_every_event(self) -> None:
        for config in ("H", "U", "E", "E+"):
            for world in self.inputs["worlds"]:
                result, rows = service_case(self.inputs, config, world, 400, 0.5)
                capital = Decimal(str(self.inputs["service"]["starting_capital_usd"]))
                for row in rows:

                    def money(key: str) -> Decimal:
                        return Decimal(str(row[key]))

                    assets = money("cash_usd") + money("receivable_usd")
                    equity = capital + money("revenue_usd") - money("expense_usd")
                    self.assertEqual(assets, equity + money("deferred_usd"))
                self.assertEqual(result["refund_obligation_usd"], 0)

    def test_deposit_is_not_revenue_and_acceptance_is_not_collection(self) -> None:
        result, rows = service_case(self.inputs, "E", self.world("accepted"), 400, 0.5)
        deposit = next(r for r in rows if r["event"] == "refundable_deposit")
        acceptance = next(r for r in rows if r["revenue_delta_usd"] > 0)
        self.assertEqual((deposit["revenue_usd"], deposit["deferred_usd"]), (0, 200))
        self.assertEqual((acceptance["cash_delta_usd"], acceptance["receivable_usd"]), (0, 200))
        self.assertEqual((result["earned_revenue_usd"], result["accrued_profit_usd"]), (400, 95))

    def test_default_is_not_a_second_cash_payment(self) -> None:
        result, rows = service_case(self.inputs, "E", self.world("payment_default"), 400, 0.5)
        loss = next(r for r in rows if r["event"] == "uncollected_balance_writeoff")
        self.assertEqual((loss["cash_delta_usd"], loss["expense_delta_usd"]), (0, 200))
        self.assertEqual((result["ending_cash_usd"], result["accrued_profit_usd"]), (295, -105))

    def test_failed_partial_and_late_reports_do_not_relax_original_acceptance(self) -> None:
        for name in ("common_technical_failure", "partial_delivery", "missed_deadline"):
            result, rows = service_case(self.inputs, "E", self.world(name), 400, 0.5)
            self.assertFalse(result["accepted_original_obligation"])
            self.assertEqual((result["earned_revenue_usd"], result["refunds_usd"]), (0, 200))
            refund = next(r for r in rows if r["event"] == "refund")
            self.assertEqual(refund["expense_delta_usd"], 0)

    def test_paid_job_learning_is_charged_once(self) -> None:
        before, _ = service_case(self.inputs, "E", self.world("accepted"), 400, 0.5)
        altered = copy.deepcopy(self.inputs)
        altered["service"]["workflows"]["E"]["paid_job_learning_hours_included"] = 0
        after, _ = service_case(altered, "E", self.world("accepted"), 400, 0.5)
        self.assertEqual(before["costs_usd"], after["costs_usd"])
        self.assertEqual(before["costs_usd"]["A"], 305)

    def test_refundable_prefunding_does_not_remove_full_refund_reserve(self) -> None:
        for deposit in (0, 0.5):
            result, _ = service_case(self.inputs, "E", self.world("accepted"), 400, deposit)
            self.assertEqual(result["minimum_initial_capital_usd"], 325)

    def test_no_gain_assigned_and_unprofitable_optional_investment_stops(self) -> None:
        ordinary, _ = choose_offer(self.inputs, "U")
        expert, _ = choose_offer(self.inputs, "E")
        retained, _ = choose_offer(self.inputs, "E+")
        self.assertEqual(ordinary["expected_full_contribution_usd"], expert["expected_full_contribution_usd"])
        self.assertEqual(expert["expected_full_contribution_usd"], 28.6625)
        self.assertEqual(retained["conditional_decision"], "stop")

    def test_missing_acceptance_blocks_revenue(self) -> None:
        self.inputs["external_acceptance"]["technical_report_accepted"] = None
        result, _ = service_case(self.inputs, "E", self.world("accepted"), 400, 0.5)
        self.assertEqual((result["earned_revenue_usd"], result["refunds_usd"]), (0, 200))

    def test_shared_construction_required_for_delivery_is_A_not_optional_C(self) -> None:
        result = construction_case(self.inputs, True, True, self.world("accepted"))
        self.assertEqual(result["costs_usd"], {"A": 6800, "B": 0, "C": 0})
        self.assertEqual(result["accrued_profit_usd"], 200)
        self.assertGreater(result["prefunding_shortfall_usd"], 0)
        blocked = construction_case(self.inputs, False, False, self.world("accepted"))
        self.assertFalse(blocked["accepted_original_obligation"])
        self.assertEqual(blocked["gross_collections_usd"], 0)


if __name__ == "__main__":
    unittest.main()
