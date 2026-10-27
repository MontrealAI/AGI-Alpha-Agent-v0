# SPDX-License-Identifier: Apache-2.0
"""Boundary checks for conditional escrow, participation and historical accounting."""

import copy
import importlib.util
import json
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("arrangement_checker", HERE / "checker.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
PROTOCOL = json.loads((HERE / "PROTOCOL.json").read_text())


def fixture():
    inputs = C.diagnostic_inputs(PROTOCOL, 30000, "0", False)
    plan = {
        "technical": True,
        "coordinated": True,
        "participants": ["P1", "P2", "P3"],
        "price_cents": 30000,
        "finance": "post_acceptance",
    }
    return plan, inputs


def historical(core, buyers=4):
    ids = [str(i) for i in range(buyers)]
    inputs = {
        "participants": [
            {
                "id": i,
                "mission_value_cents": 36000000,
                "outside_surplus_cents": 0,
                "adaptation_cents": 7500000,
                "support_cents": 0,
                "common_value_cents": 0,
            }
            for i in ids
        ],
        "core_cents": core * 100,
        "adaptation_saving": "0",
        "common_independently_useful": False,
        "common_fraction": "0",
        "coordination_cents": 0,
        "retention_B_cents": 0,
        "exploration_C_cents": 0,
        "opening_cash_cents": 90000000,
        "protected_reserve_cents": 0,
        "hypothetical_rights_cleared": True,
        "batch_adaptations": True,
    }
    plan = {
        "technical": True,
        "coordinated": True,
        "participants": ids,
        "price_cents": 30000000,
        "finance": "post_acceptance",
    }
    worlds = [
        {"id": "success", "common_ok": True, "weight": "4/5"},
        {"id": "failure", "common_ok": False, "weight": "1/5"},
    ]
    return C.evaluate(plan, inputs, worlds, True)


class CheckerTests(unittest.TestCase):
    def test_refundable_escrow_does_not_fund_preacceptance_work(self):
        plan, inputs = fixture()
        normal = C.simulate(plan, inputs, {"id": "success", "common_ok": True})
        plan["finance"] = "refundable_escrow"
        escrow = C.simulate(plan, inputs, {"id": "success", "common_ok": True})
        self.assertEqual(normal["required_opening_cash_cents"], escrow["required_opening_cash_cents"])
        first = escrow["events"][0]
        self.assertEqual(first["cash_delta_cents"], first["escrow_delta_cents"])
        self.assertEqual(escrow["contribution_cents"], normal["contribution_cents"])

    def test_common_failure_returns_principal_and_retains_cost(self):
        plan, inputs = fixture()
        plan["finance"] = "refundable_escrow"
        result = C.simulate(plan, inputs, {"id": "common_failure", "common_ok": False})
        self.assertEqual(result["net_earned_collections_cents"], 0)
        self.assertEqual(result["contribution_cents"], -32000)
        self.assertEqual(result["final_escrow_liability_cents"], 0)

    def test_unearned_or_useless_common_milestone_refused(self):
        plan, inputs = fixture()
        plan["finance"] = "accepted_milestone_escrow"
        with self.assertRaises(ValueError):
            C.simulate(plan, inputs, {"id": "success", "common_ok": True})

    def test_explicit_useful_milestone_can_change_cash_prefix(self):
        plan, inputs = fixture()
        inputs["common_independently_useful"] = True
        for p in inputs["participants"]:
            p["common_value_cents"] = 20000
        old = C.simulate(plan, inputs, {"id": "success", "common_ok": True})
        plan["finance"] = "accepted_milestone_escrow"
        staged = C.simulate(plan, inputs, {"id": "success", "common_ok": True})
        self.assertLess(staged["required_opening_cash_cents"], old["required_opening_cash_cents"])
        self.assertEqual(staged["contribution_cents"], old["contribution_cents"])

    def test_common_core_counted_once_and_b_c_distinct(self):
        plan, inputs = fixture()
        inputs.update(retention_B_cents=1200, exploration_C_cents=700)
        result = C.simulate(plan, inputs, {"id": "success", "common_ok": True})
        self.assertEqual(result["costs_cents"], {"A": 70000, "B": 1200, "C": 700})
        self.assertEqual(sum(e["kind"] == "required-common-construction-once" for e in result["events"]), 1)

    def test_unpaid_invoice_not_cash_revenue(self):
        plan, inputs = fixture()
        result = C.simulate(plan, inputs, {"id": "default", "common_ok": True, "default": ["P3"]})
        self.assertEqual(result["unpaid_or_defaulted_receivables_cents"], 30000)
        self.assertEqual(result["net_earned_collections_cents"], 60000)
        self.assertEqual(result["contribution_cents"], -10000)

    def test_partial_acceptance_and_withdrawal_keep_sunk_common_cost(self):
        plan, inputs = fixture()
        plan["finance"] = "refundable_escrow"
        result = C.simulate(
            plan, inputs, {"id": "withdraw-fail", "common_ok": True, "withdraw": ["P1"], "fail": ["P3"]}
        )
        self.assertEqual(result["buyer_payment_cents"]["P1"], 0)
        self.assertEqual(result["buyer_payment_cents"]["P3"], 0)
        self.assertEqual(result["costs_cents"]["A"], 64000)
        self.assertLess(result["contribution_cents"], 0)

    def test_customer_outside_option_and_rights_are_gates(self):
        plan, inputs = fixture()
        inputs["opening_cash_cents"] = 1000000
        inputs["participants"][0]["outside_surplus_cents"] = 1000000
        inputs["hypothetical_rights_cleared"] = False
        result = C.evaluate(plan, inputs)
        self.assertIn("participant-outside-option-not-met", result["reasons"])
        self.assertIn("rights-not-cleared", result["reasons"])
        self.assertFalse(result["conditional_admissible"])

    def test_historical_foundation_numbers_are_separate_regressions(self):
        result = historical(600000)
        self.assertEqual(Fraction(**result["expected_contribution_cents"]), 12000000)
        self.assertEqual(result["success_contribution_cents"], 30000000)
        self.assertEqual(result["required_opening_cash_cents"], 90000000)
        expensive = historical(300000, 2)
        cheaper = historical(150000, 2)
        self.assertEqual(Fraction(**expensive["expected_contribution_cents"]), 6000000)
        self.assertEqual(expensive["required_opening_cash_cents"], 45000000)
        self.assertEqual(Fraction(**cheaper["expected_contribution_cents"]), 21000000)
        self.assertEqual(cheaper["required_opening_cash_cents"], 30000000)

    def test_reject_fractional_cash_or_invalid_saving(self):
        with self.assertRaises(ValueError):
            C.money(Fraction(1, 2))
        with self.assertRaises(ValueError):
            C.money(True)
        plan, inputs = fixture()
        inputs["adaptation_saving"] = "3/2"
        with self.assertRaises(ValueError):
            C.simulate(plan, inputs, {"id": "success", "common_ok": True})


if __name__ == "__main__":
    unittest.main()
