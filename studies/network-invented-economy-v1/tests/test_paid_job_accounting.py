# SPDX-License-Identifier: Apache-2.0
"""Independent v2 regressions for paid-job learning, retention and optional R&D.

The deterministic fixture conditions exercise the intended paths; their favorable
outcomes are not scientific confirmation or evidence of customer demand.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch

from src.simulator import (
    Candidate, Enterprise, Job, Policy, PRODUCTION, RETENTION, Scenario, VALIDATION, cents, simulate,
)


class PaidJobAccountingAudit(TestCase):
    """Historical A is recorded once; B and C make distinct prospective decisions."""

    @staticmethod
    def scenario(**changes) -> Scenario:
        base = replace(
            Scenario(), weeks=30, runoff=8, agents=2, diversity=1,
            initial_overlap=0, specialization=0, depth_weights=(1, 0, 0),
            leads_per_week=8, demand_value=2, initial_trust=0.9,
            invention_probability=1, shareable_probability=1,
            retention_generalization_success=1, asset_defect_probability=0,
            admission_false_rejection=0, default_probability=0,
            ordinary_learning_rate=0, copying_hazard=0, external_improvement=0,
            obsolete_hazard=0, revalidation_failure=0, maintenance_per_skill=0,
            distribution_per_skill=0,
        )
        return replace(base, **changes)

    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = [
            simulate(cls.scenario(), Policy(invest=False, reserve_weeks=0), 19, "network", True),
            simulate(cls.scenario(), Policy(invest=True, reserve_weeks=0), 19, "network_no_invest", True),
        ]

    def enterprise(self, *, invest=False, arm="network", **changes) -> Enterprise:
        enterprise = Enterprise(self.scenario(**changes),
                                Policy(invest=invest, reserve_weeks=0, max_investment_share=1),
                                19, arm, True)
        enterprise.input_budget = enterprise.output_budget = 100000
        return enterprise

    @staticmethod
    def candidate(source_cost: float = 900, learned: bool = True) -> Candidate:
        return Candidate((0, 0), 0, 81, 1, "campaign-81", True, learned, source_cost)

    def test_historical_job_cost_cannot_change_prospective_alpha(self) -> None:
        enterprise = self.enterprise()
        results = []
        for source_cost in (0, 900, 1000000):
            candidate = self.candidate(source_cost)
            results.append(enterprise.alpha_assess([candidate], 2, enterprise.retention_cost([candidate])))
        self.assertTrue(results[0]["decision"]["accepted"], "fixture must exercise an admissible retention")
        for result in results[1:]:
            self.assertEqual(result["assessment"], results[0]["assessment"])
            self.assertEqual(result["decision"], results[0]["decision"])
            self.assertEqual(result["paired_probes"], results[0]["paired_probes"])
        self.assertEqual([r["already_charged_job_cost_memo"] for r in results], [0, 900, 1000000])
        self.assertEqual(results[0]["assessment"]["costs"]["construction"], 0)

    def test_source_job_memo_is_not_multiplied_by_components(self) -> None:
        enterprise = self.enterprise()
        candidates = [self.candidate(), replace(self.candidate(), key=(0, 1))]
        result = enterprise.alpha_assess(candidates, 2, enterprise.retention_cost(candidates))
        self.assertEqual(result["already_charged_job_cost_memo"], 900)
        self.assertEqual(result["assessment"]["costs"]["construction"], 0)

    def test_every_actual_expense_enters_exactly_one_cost_book(self) -> None:
        for result in self.runs:
            with self.subTest(arm=result["arm"]):
                totals = defaultdict(int)
                expenses = [row for row in result["ledger"] if row["kind"] == "expense"]
                for row in expenses:
                    self.assertIn(row["book"], {"job", "retention", "investment", "common"})
                    totals[row["book"]] += row["amount_cents"]
                    if row["category"] in {"production", "validation", "correction", "packaging"}:
                        self.assertEqual(row["book"], "job")
                    if row["category"].startswith("retention_"):
                        self.assertEqual(row["book"], "retention")
                self.assertEqual(sum(totals.values()), cents(result["expenses"]))
                for book, amount in result["cost_books"].items():
                    self.assertEqual(totals[book], cents(amount))
                self.assertEqual(cents(result["profit"]), cents(result["cash"])
                                 - cents(result["seed_capital"]) - cents(result["closing_obligations"]))

    def test_paid_job_retention_runs_when_optional_investment_is_disabled(self) -> None:
        for result in self.runs:
            with self.subTest(arm=result["arm"]):
                self.assertGreater(result["retention_count"], 0)
                self.assertGreater(result["stats"].get("admitted_from_paid_work", 0), 0)
                self.assertEqual(result["investment_count"], 0)
                self.assertEqual(result["cost_books"]["investment"], 0)
                self.assertTrue(all(skill["origin"] == "paid-job-retention" for skill in result["skills"]))
                for record in result["retention_records"]:
                    self.assertEqual(record["paid_job_cost_recharged"], 0)
                    self.assertGreater(record["source_job_paid_cost"], 0)
                    self.assertEqual(record["prospective_incremental_retention"], record["cost"])

    def test_learned_asset_never_enters_optional_construction_catalog(self) -> None:
        enterprise = self.enterprise(invest=True)
        candidate = self.candidate()
        enterprise.candidates[(0, 0, 0)] = candidate

        class ForbiddenConstruction:
            def __getitem__(self, index):
                raise AssertionError("a learned paid-job asset must not be rebuilt through optional CONSTRUCTION")

        before = len(enterprise.ledger.records)
        with patch("src.simulator.CONSTRUCTION", ForbiddenConstruction()):
            enterprise.evaluate_investment(4)
            self.assertEqual(len(enterprise.ledger.records), before)
            enterprise.evaluate_retention(4)
            self.assertEqual(len(enterprise.pending_investments), 1)
            self.assertEqual(enterprise.pending_investments[0]["book"], "retention")
            self.assertAlmostEqual(enterprise.pending_investments[0]["cost"],
                                   RETENTION[0].cost(enterprise.s) * enterprise.s.retention_cost_factor)
            enterprise.build_skills(5)
        self.assertEqual(enterprise.investments, [])
        self.assertFalse(any(row.get("category") == "capability_search_build_confirm_migrate"
                             for row in enterprise.ledger.records))

    def test_future_receipt_cannot_fund_additional_retention(self) -> None:
        enterprise = self.enterprise(seed_capital=100, setup_cost=0)
        enterprise.ledger.spend(20, 1, "production", "job-81")
        enterprise.candidates[(0, 0, 0)] = self.candidate(20)
        enterprise.receipts.append({"week": 8, "job": 81, "amount": 10000,
                                    "default": False, "wrong": False})
        enterprise.settle_receipts(7)
        enterprise.evaluate_retention(7)
        self.assertEqual(enterprise.retentions, [])
        self.assertEqual(enterprise.pending_investments, [])
        self.assertFalse(any(row["kind"] == "collection" for row in enterprise.ledger.records))
        self.assertLess(enterprise.ledger.cash, cents(100))
        enterprise.settle_receipts(8)
        enterprise.evaluate_retention(8)
        self.assertEqual(len(enterprise.retentions), 1)
        self.assertEqual(enterprise.retentions[0]["source_job_paid_cost"], 20,
                         "customer collection is not the source-job cost memo")

    def test_learning_memo_is_nonadditive_and_bounded_by_actual_production_cost(self) -> None:
        for result in self.runs:
            production = defaultdict(int)
            for row in result["ledger"]:
                if row["kind"] == "expense" and row["category"] == "production":
                    production[row["key"]] += row["amount_cents"]
            with self.subTest(arm=result["arm"]):
                self.assertGreater(result["paid_job_learning_cost_memo"], 0)
                for outcome in result["outcomes"]:
                    memo = cents(outcome["learning_cost_already_in_job"])
                    self.assertGreaterEqual(memo, 0)
                    self.assertLessEqual(memo, production[f"job-{outcome['job']}"] + 1)
                self.assertEqual(cents(result["paid_job_learning_cost_memo"]),
                                 sum(cents(x["learning_cost_already_in_job"]) for x in result["outcomes"]))
                expenses = [row for row in result["ledger"] if row["kind"] == "expense"]
                self.assertEqual(sum(row["amount_cents"] for row in expenses), cents(result["expenses"]))
                self.assertFalse(any("learning" in row["category"] for row in expenses),
                                 "learning memo must not become an additional expense after production")

    def test_later_paid_learning_is_not_shadowed_by_an_unlearned_rd_direction(self) -> None:
        for arm in ("network", "network_no_invest"):
            with self.subTest(arm=arm):
                enterprise = self.enterprise(invest=True, arm=arm, invention_probability=0.48)
                jobs = [Job(jid, 0, 1, 1, 10000, 20000, 0, 30, PRODUCTION[0], VALIDATION[0], [0], [], 0,
                            true_correct=True) for jid in (81, 82)]

                def insight(seed, *keys):
                    if keys[0] == "invention":
                        return 0.55 if keys[1] == 81 else 0.10
                    return 0.01

                with patch("src.simulator.uniform", insight):
                    enterprise.ledger.spend(400, 1, "production", "job-81")
                    enterprise.generate_candidates(jobs[0], 2)
                    if arm == "network":
                        self.assertFalse(enterprise.candidates[(0, 0, 0)].learned_during_job)
                    else:
                        self.assertNotIn((0, 0, 0), enterprise.candidates,
                                         "the no-investment arm has no need to queue a new-R&D direction")
                    enterprise.ledger.spend(500, 3, "production", "job-82")
                    enterprise.generate_candidates(jobs[1], 4)
                candidate = enterprise.candidates[(0, 0, 0)]
                self.assertTrue(candidate.learned_during_job,
                                "a stale optional-R&D direction must not block later paid-job learning")
                self.assertEqual(candidate.source_job, 82)
                self.assertEqual(candidate.source_job_direct_cost, 500)
                if arm == "network":
                    self.assertTrue(any(event.get("job") == 81 for event in enterprise.events),
                                    "earlier provenance must remain in history after candidate replacement")
                enterprise.evaluate_retention(4)
                self.assertEqual(len(enterprise.retentions), 1)
