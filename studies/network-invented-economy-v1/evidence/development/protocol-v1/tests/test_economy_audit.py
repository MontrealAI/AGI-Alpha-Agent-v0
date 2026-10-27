# SPDX-License-Identifier: Apache-2.0
"""Independent pre-freeze accounting and resource audit.

These checks test conservation and economically consequential refusal behavior.
They do not validate demand, willingness to pay, frontier quality, or an equilibrium.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from types import SimpleNamespace
from unittest import TestCase

from src.simulator import Enterprise, Policy, SCENARIOS, Scenario, Skill, Work, cents, simulate


class EconomyAccountingAudit(TestCase):
    """Reconcile saved records without relying on the simulator's own assertions."""

    @classmethod
    def setUpClass(cls) -> None:
        scenarios = [replace(s, weeks=26, runoff=16) for s in SCENARIOS.values()]
        scenarios.extend([
            replace(Scenario(), name="quota-boundary", weeks=8, runoff=1,
                    quota_input_m=3.0, quota_output_m=0.4, leads_per_week=8.0),
            replace(Scenario(), name="cash-boundary", weeks=8, runoff=1,
                    seed_capital=9750.0, leads_per_week=8.0),
        ])
        cls.runs = [(s, simulate(s, Policy(), 104729, retain=True)) for s in scenarios]

    def test_cash_and_profit_reconcile_including_unpaid_and_terminal_obligations(self) -> None:
        saw_unpaid = False
        saw_terminal_obligation = False
        for scenario, result in self.runs:
            with self.subTest(scenario=scenario.name):
                cash = cents(scenario.seed_capital)
                expenses = collections = paid = 0
                categories = defaultdict(int)
                for row in result["ledger"]:
                    if row["kind"] == "expense":
                        expenses += row["amount_cents"]
                        paid += row["paid_cents"]
                        cash -= row["paid_cents"]
                        categories[row["category"]] += row["amount_cents"]
                        self.assertGreaterEqual(row["amount_cents"], row["paid_cents"])
                    elif row["kind"] == "collection":
                        collections += row["amount_cents"]
                        cash += row["amount_cents"]
                    self.assertEqual(cash, row["cash_cents"])
                    self.assertGreaterEqual(cash, 0)
                self.assertEqual(cash, cents(result["cash"]))
                self.assertEqual(expenses, cents(result["expenses"]))
                self.assertEqual(collections, cents(result["collections"]))
                self.assertEqual(dict(categories), {k: cents(v) for k, v in result["costs"].items()})
                self.assertEqual(cents(result["profit"]), cash - cents(scenario.seed_capital)
                                 - cents(result["closing_obligations"]))
                saw_unpaid |= expenses > paid
                saw_terminal_obligation |= result["closing_obligations"] > 0
        self.assertTrue(saw_unpaid, "the boundary case must exercise incurred unpaid costs")
        self.assertTrue(saw_terminal_obligation, "the boundary case must exercise closing liabilities")

    def test_commitments_are_prefunded_and_cannot_be_reused_as_free_cash(self) -> None:
        for scenario, result in self.runs:
            commitments = {}
            with self.subTest(scenario=scenario.name):
                for row in result["ledger"]:
                    if row["kind"] == "reserve":
                        self.assertNotIn(row["key"], commitments)
                        commitments[row["key"]] = row["amount_cents"]
                        self.assertLessEqual(row["reserved_cents"], row["cash_cents"])
                    elif row["kind"] == "expense" and row.get("key") in commitments:
                        commitments[row["key"]] -= row["amount_cents"]
                        self.assertGreaterEqual(commitments[row["key"]], 0)
                        self.assertEqual(row["paid_cents"], row["amount_cents"],
                                         "prefunded work must not become an unfunded expense")
                    elif row["kind"] == "release":
                        self.assertEqual(row["amount_cents"], commitments.pop(row["key"], 0))
                for week in result["weekly"]:
                    self.assertGreaterEqual(week["available"], 0)
                    self.assertLessEqual(week["available"], max(0, week["cash"] - week["committed"]) + 0.011)

    def test_billed_token_work_matches_weekly_usage_and_finite_quotas(self) -> None:
        for scenario, result in self.runs:
            billed = defaultdict(lambda: [0.0, 0.0])
            for row in result["ledger"]:
                if row["kind"] == "expense":
                    billed[row["week"]][0] += row.get("input_m", 0.0)
                    billed[row["week"]][1] += row.get("output_m", 0.0)
            with self.subTest(scenario=scenario.name):
                for week in result["weekly"]:
                    self.assertAlmostEqual(billed[week["week"]][0], week["input_m"], delta=0.00002)
                    self.assertAlmostEqual(billed[week["week"]][1], week["output_m"], delta=0.00002)
                    self.assertLessEqual(week["input_m"], scenario.quota_input_m + 0.00001)
                    self.assertLessEqual(week["output_m"], scenario.quota_output_m + 0.00001)
                    self.assertGreaterEqual(week["input_m"], -0.00001)
                    self.assertGreaterEqual(week["output_m"], -0.00001)

    def test_receivable_cannot_prefund_a_commitment(self) -> None:
        scenario = replace(Scenario(), weeks=2, leads_per_week=0, setup_cost=0, seed_capital=100)
        enterprise = Enterprise(scenario, Policy(invest=False), 19)
        enterprise.receipts.append({"week": 8, "job": 71, "amount": 10000,
                                    "default": False, "wrong": False})
        enterprise.settle_receipts(7)
        self.assertEqual(enterprise.ledger.cash, 10000)
        self.assertFalse(enterprise.ledger.reserve("too-early", 101, 7))
        enterprise.settle_receipts(8)
        self.assertEqual(enterprise.ledger.cash, 1010000)
        self.assertTrue(enterprise.ledger.reserve("after-collection", 101, 8))

    def test_uncollected_receipts_never_enter_terminal_profit(self) -> None:
        scenario = replace(Scenario(), weeks=1, runoff=0, leads_per_week=0, setup_cost=0)
        enterprise = Enterprise(scenario, Policy(invest=False), 19, retain=True)
        enterprise.receipts.append({"week": 100, "job": 71, "amount": 1000000,
                                    "default": False, "wrong": False})
        result = enterprise.run()
        self.assertEqual(result["receivables"], 1000000)
        self.assertEqual(result["collections"], 0)
        self.assertLess(result["profit"], 0)
        self.assertEqual(cents(result["profit"]), -cents(result["expenses"]))

    def test_cache_write_and_read_billing_does_not_discount_quota(self) -> None:
        work = Work(astra_input=2, astra_cache=3, astra_output=0.7,
                    terra_input=5, terra_cache=7, terra_output=0.11, tools=13)
        scenario = Scenario()
        expected_cached = 2 * 12.5 + 3 * 1 + 0.7 * 50 + 5 * 1.25 + 7 * 0.05 + 0.11 * 5 + 13
        expected_uncached = (2 + 3) * 10 + 0.7 * 50 + (5 + 7) * 1 + 0.11 * 5 + 13
        self.assertAlmostEqual(work.cost(scenario), expected_cached)
        self.assertAlmostEqual(work.cost(replace(scenario, cache_enabled=False)), expected_uncached)
        self.assertEqual(work.input_m, 17)
        self.assertAlmostEqual(work.output_m, 0.81)
        self.assertAlmostEqual(work.cost(replace(scenario, token_cost_factor=2, tool_cost_factor=3)),
                               (expected_cached - 13) * 2 + 13 * 3)

    def test_available_capability_is_not_used_when_transfer_cost_exceeds_reconstruction(self) -> None:
        scenario = replace(Scenario(), agents=2, initial_overlap=0, specialization=0,
                           transfer_validation_factor=100)
        enterprise = Enterprise(scenario, Policy(invest=False), 19)
        skill = Skill((0, 0), 1, 0, 30, 12, True, source_job=81)
        enterprise.skills.append(skill)
        enterprise.jobs = [SimpleNamespace(owner=1) for _ in range(5)]
        lead = {"id": 71, "domain": 0, "depth": 1}
        self.assertTrue(enterprise.eligible(skill, 0, 0, 0, 1))
        owner, _, _, missing, selected = enterprise.plan(lead, 1)
        self.assertEqual(owner, 0)
        self.assertEqual(selected, [])
        self.assertEqual(missing, [0])

    def test_bundle_dependency_and_new_beta_are_checked_at_reuse(self) -> None:
        enterprise = Enterprise(Scenario(), Policy(invest=False), 19)
        keys = ((0, 0), (0, 1))
        skills = [Skill(key, 0, 0, 60, 60, True, source_job=81,
                        bundle_id="joint", bundle_keys=keys) for key in keys]
        enterprise.skills.extend(skills)
        self.assertTrue(enterprise.eligible(skills[0], 1, 0, 0, 1))
        skills[1].active = False
        self.assertFalse(enterprise.eligible(skills[0], 1, 0, 0, 1))
        skills[1].active = True
        self.assertFalse(enterprise.eligible(skills[0], 1, 0, 0, 26),
                         "an old positive assessment cannot authorize reuse under a new Beta")
