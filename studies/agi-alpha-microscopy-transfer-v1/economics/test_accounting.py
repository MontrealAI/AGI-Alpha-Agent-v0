import json
import unittest
from pathlib import Path

from simulate import Ledger, Policy, simulate


class AccountingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((Path(__file__).parent / "config.json").read_text())
        self.policy = Policy("established", 200, 0.5, 1)

    def test_seed_is_not_income_and_deposit_is_not_available(self) -> None:
        ledger = Ledger(100, 10)
        before = ledger.available
        ledger.deposit(80, "job")
        self.assertEqual(ledger.available, before)
        ledger.settle(80, 0, False, 0, "failed job")
        result = ledger.output()
        self.assertEqual(result["net_collections"], 0)
        self.assertEqual(result["settled_cash_contribution"], 0)
        self.assertEqual(result["ending_cash"], 100)

    def test_default_is_not_also_refund(self) -> None:
        ledger = Ledger(100, 0)
        ledger.deposit(30, "job")
        ledger.settle(30, 100, True, 2, "job")
        result = ledger.output()
        self.assertEqual(result["bad_debt"], 70)
        self.assertEqual(result["refunds"], 0)
        self.assertEqual(result["net_collections"], 30)

    def test_partial_milestone_refunds_only_unearned_deposit(self) -> None:
        ledger = Ledger(100, 0)
        ledger.deposit(60, "job")
        ledger.settle(60, 25, False, 2, "job")
        result = ledger.output()
        self.assertEqual(result["refunds"], 35)
        self.assertEqual(result["earned_revenue"], 25)
        self.assertEqual(result["bad_debt"], 0)

    def test_uncollected_future_receipt_cannot_fund_work(self) -> None:
        ledger = Ledger(20, 0)
        ledger.settle(0, 100, False, 10, "accepted job")
        self.assertFalse(ledger.spend(50, "B", "retention"))
        ledger.advance(10)
        self.assertTrue(ledger.spend(50, "B", "retention"))
        self.assertEqual(ledger.output()["B_cash"], 50)

    def test_unaffordable_origin_is_not_delivered(self) -> None:
        result = simulate(self.config, {"seed_capital": 350}, self.policy, 10, "E+")
        self.assertFalse(result["origin_accepted"])
        self.assertEqual(result["net_collections"], 0)
        self.assertEqual(result["economic_surplus"], 0)

    def test_zero_gain_rejects_and_charges_screen_once(self) -> None:
        before = simulate(self.config, {}, self.policy, 99, "E")
        after = simulate(self.config, {}, self.policy, 99, "E+")
        self.assertFalse(after["retained"])
        self.assertEqual(after["B_cash"], 5)
        self.assertEqual(after["C_cash"], 0)
        self.assertEqual(after["A_cash"], before["A_cash"])
        self.assertEqual(after["economic_surplus"], before["economic_surplus"] - 5)

    def test_same_content_has_exact_library_parity(self) -> None:
        config = {"forecast_retained_saving_hours": 0.5, "actual_retained_saving_hours": 0.5}
        left = simulate(self.config, config, self.policy, 121, "E+")
        right = simulate(self.config, config, self.policy, 121, "ordinary_library")
        left.pop("arm")
        right.pop("arm")
        self.assertEqual(left, right)

    def test_conservation_in_many_adverse_histories(self) -> None:
        for seed in range(60):
            for route in ["established", "technical_only", "coordination_only", "combined"]:
                result = simulate(
                    self.config, {"common_failure_probability": 0.4}, Policy(route, 200, 0.5, 1), seed, "E+"
                )
                self.assertTrue(result["cash_balance_verified"])
                self.assertGreaterEqual(result["minimum_available_funds"], 0)
                self.assertGreaterEqual(result["bad_debt"], -0.01)
                self.assertAlmostEqual(
                    result["ending_cash"], result["seed_capital"] + result["settled_cash_contribution"], places=2
                )


if __name__ == "__main__":
    unittest.main()
