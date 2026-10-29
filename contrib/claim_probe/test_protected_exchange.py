# SPDX-License-Identifier: Apache-2.0
"""Training regressions for actual reserve, receipt, remedy and release controls."""

import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

from alpha_factory_v1.core.runtime.claim_probe import checker, contracts, operator
from alpha_factory_v1.core.runtime.claim_probe.symbolic import ordinary_library
from alpha_factory_v1.core.runtime.claim_probe.protected_exchange import ProtectedExchange

KEY = b"p" * 32


class ProtectedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "exchange.sqlite"
        self.ex = self.open()
        self.task = operator.example()
        self.ex.wallet("b", 20_000_000)
        self.ex.offer("o", "b", 5_000_000, "nonrecourse-simulated", self.task, 20)

    def open(self, opening=10_000_000):
        return ProtectedExchange(
            self.path,
            key=KEY,
            contract="claim-probe/v2",
            validate=contracts.validate,
            check=checker.check,
            opening=opening,
        )

    def tearDown(self):
        self.ex.close()
        self.tmp.cleanup()

    def consent(self, ex=None, ident="o"):
        ex = ex or self.ex
        row = ex.order(ident)
        terms = {k: row[k] for k in ["id", "buyer", "price", "rail", "task_hash", "contract", "deadline"]}
        ex.event(ident, "consent-" + ident, "consent", {"buyer": row["buyer"], "termsHash": contracts.digest(terms)}, 0)

    def fund(self):
        self.consent()
        self.ex.event("o", "fund", "fund", self.ex.provider.issue(self.ex.order("o"), "funded"), 1)

    def prepared(self):
        self.fund()
        self.ex.event("o", "prepare", "prepare", ordinary_library(self.task), 2)

    def released(self):
        self.prepared()
        self.ex.event("o", "release", "release", self.ex.provider.issue(self.ex.order("o"), "cleared"), 3)

    def test_earned_investment_keeps_equity_reserve_intact(self):
        self.released()
        before = self.ex.snapshot()
        self.ex.reserve_investment("build", 4_000_000, 1_000_000)
        held = self.ex.snapshot()
        self.assertEqual(held["reservedInvestment"], 4_000_000)
        self.assertEqual(held["unrestrictedEarned"], before["unrestrictedEarned"] - 4_000_000)
        self.assertEqual(held["equityProtectionBacking"], before["equityProtectionBacking"])
        with self.assertRaises(ValueError):
            self.ex.reserve_investment("overbook", 2_000_000, 1)
        after = self.ex.finish_investment("build", 500_000, "a" * 64)
        self.assertEqual(after["reservedInvestment"], 0)
        self.assertEqual(after["expenses"], 500_000)
        self.assertEqual(after["cash"], before["cash"] - 500_000)
        self.assertEqual(after["equityProtectionBacking"], before["equityProtectionBacking"])
        with self.assertRaises(ValueError):
            self.ex.finish_investment("build", 500_000, "a" * 64)

    def test_unpaid_costs_cannot_be_declared_earned_funds(self):
        self.released()
        self.ex._entry("", "expense", 5_000_000)
        state = self.ex.snapshot()
        self.assertEqual(state["profit"], 0)
        self.assertEqual(state["unrestrictedEarned"], 0)
        with self.assertRaises(ValueError):
            self.ex.reserve_investment("false-profit", 1, 1)

    def test_reservation_can_be_cancelled_after_stop_without_erasing_cost(self):
        self.released()
        self.ex.reserve_investment("build", 1_000_000, 1)
        self.ex.event("o", "late", "late_reversal", {}, 1000)
        self.ex.cancel_investment("build")
        self.ex.cost("failed-research", 100_000)
        self.assertEqual(self.ex.snapshot()["reservedInvestment"], 0)
        self.assertEqual(self.ex.snapshot()["expenses"], 100_000)
        self.assertTrue(self.ex.snapshot()["investmentStopped"])

    def test_no_custody_revenue_or_output_before_assurance(self):
        self.prepared()
        state = self.ex.snapshot()
        self.assertEqual(state["custodyRestricted"], 5_000_000)
        self.assertEqual(state["custodyReserve"], 5_000_000)
        self.assertEqual(state["revenue"], 0)
        with self.assertRaises(PermissionError):
            self.ex.download("o", "b")
        self.ex.event("o", "release", "release", self.ex.provider.issue(self.ex.order("o"), "cleared"), 3)
        self.assertTrue(self.ex.download("o", "b"))

    def test_card_or_time_is_not_finality(self):
        self.ex.db.execute("UPDATE trades SET rail='reversible' WHERE id='o'")
        self.prepared()
        with self.assertRaises(ValueError):
            self.ex.event("o", "release", "release", self.ex.provider.issue(self.ex.order("o"), "cleared"), 10)
        self.ex.event("o", "refund", "refund", {}, 21)
        self.assertEqual(self.ex.snapshot()["revenue"], 0)

    def test_equity_backed_amount_bounded_tail_preserves_earned_funding(self):
        self.released()
        s = self.ex.snapshot()
        self.assertGreater(s["profit"], 0)
        self.assertGreater(s["conditionalEarned"], 0)
        self.assertGreater(s["unrestrictedEarned"], 0)
        self.assertEqual(s["strictEarnedControl"], 0)
        self.assertEqual(s["tailReserve"], 5_200_000)

    def test_late_reversal_applies_and_halts_investment(self):
        self.released()
        self.ex.event("o", "late", "late_reversal", {}, 1000)
        self.assertEqual(self.ex.snapshot()["revenue"], 0)
        self.assertTrue(self.ex.snapshot()["investmentStopped"])

    def test_forgery_and_substitution_refused(self):
        self.consent()
        r = self.ex.provider.issue(self.ex.order("o"), "funded")
        r["payload"]["price"] = "1"
        with self.assertRaises(ValueError):
            self.ex.event("o", "bad", "fund", r, 1)
        self.assertEqual(self.ex.order("o")["state"], "offered")

    def test_cancel_cannot_be_funded(self):
        self.consent()
        self.ex.event("o", "cancel", "cancel", {}, 1)
        with self.assertRaises(ValueError):
            self.ex.event("o", "fund", "fund", self.ex.provider.issue(self.ex.order("o"), "funded"), 2)

    def test_correlated_custody_losses_repaid_once(self):
        self.fund()
        self.ex.event("o", "loss", "custody_loss", {}, 2)
        self.ex.event("o", "refund", "refund", {}, 3)
        s = self.ex.snapshot()
        self.assertEqual(s["profit"], -5_000_000)
        self.assertEqual(s["expensePaid"], 5_000_000)
        self.assertEqual(s["cash"], 5_000_000)
        self.assertEqual(s["payables"], 0)
        self.ex.event("o", "recover", "recover_custody", self.ex.provider.issue(self.ex.order("o"), "recovered"), 4)
        s = self.ex.snapshot()
        self.assertEqual(s["profit"], 0)
        self.assertEqual(s["cash"], 10_000_000)
        self.assertEqual(s["revenue"], 0)
        with self.assertRaises(ValueError):
            self.ex.event(
                "o", "recover-again", "recover_custody", self.ex.provider.issue(self.ex.order("o"), "recovered"), 5
            )

    def test_duplicate_and_interruption(self):
        self.prepared()
        r = self.ex.provider.issue(self.ex.order("o"), "cleared")
        with self.assertRaises(InterruptedError):
            self.ex.event("o", "release", "release", r, 3, crash=True)
        self.assertEqual(self.ex.snapshot()["revenue"], 0)
        self.ex.close()
        self.ex = self.open()
        self.ex.event("o", "release", "release", r, 3)
        self.ex.event("o", "release", "release", r, 3)
        self.assertEqual(self.ex.snapshot()["revenue"], 5_000_000)

    def test_concurrent_orders_cannot_overcommit(self):
        self.consent()
        self.ex.offer("two", "b", 5_000_000, "nonrecourse-simulated", self.task, 20)
        self.consent(ident="two")

        def attempt(ident):
            ex = self.open()
            try:
                ex.event(ident, "fund-" + ident, "fund", ex.provider.issue(ex.order(ident), "funded"), 1)
                return True
            except ValueError:
                return False
            finally:
                ex.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:
            result = list(p.map(attempt, ["o", "two"]))
        self.assertEqual(sum(result), 1)

    def test_same_external_transaction_cannot_back_two_orders(self):
        self.consent()
        self.ex.offer("two", "b", 1_000_000, "nonrecourse-simulated", self.task, 20)
        self.consent(ident="two")
        self.ex.event("o", "fund", "fund", self.ex.provider.issue(self.ex.order("o"), "funded", "same-tx"), 1)
        with self.assertRaises(Exception):
            self.ex.event("two", "fund2", "fund", self.ex.provider.issue(self.ex.order("two"), "funded", "same-tx"), 1)

    def test_external_loss_kept_as_liability(self):
        self.fund()
        self.ex.event("o", "debit", "provider_debit", {"amount": 20_000_000}, 2)
        self.ex.event("o", "loss", "custody_loss", {}, 3)
        self.ex.event("o", "refund", "refund", {}, 4)
        s = self.ex.snapshot()
        self.assertEqual(s["cash"], 0)
        self.assertGreater(s["payables"], 0)
        self.assertEqual(self.ex.order("o")["state"], "refund-due")

    def test_price_floor_covers_fixed_remedy_fee(self):
        with self.assertRaises(ValueError):
            self.ex.offer("below-fee", "b", 199_999, "nonrecourse-simulated", self.task, 20)
        self.ex.offer("at-fee", "b", 200_000, "nonrecourse-simulated", self.task, 20)
        self.assertEqual(int(self.ex.order("at-fee")["price"]), 200_000)


if __name__ == "__main__":
    unittest.main()
