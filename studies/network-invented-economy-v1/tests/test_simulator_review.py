# SPDX-License-Identifier: Apache-2.0
"""Independent regressions for concrete pre-freeze economic/lifecycle findings."""

from __future__ import annotations

from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch

from src.simulator import (
    Candidate, Enterprise, INTEGRATION, Job, Ledger, Policy, PRODUCTION, Scenario, Skill, VALIDATION, Work,
)


class IndependentSimulatorReview(TestCase):
    """Check implications that should hold independently of random profit outcomes."""

    def enterprise(self, **changes) -> Enterprise:
        scenario = replace(Scenario(), agents=2, initial_overlap=0.0, specialization=0.0, **changes)
        enterprise = Enterprise(scenario, Policy(pricing="fixed", price_ratio=0.5, invest=False), 19, retain=True)
        enterprise.input_budget = enterprise.output_budget = 100000.0
        return enterprise

    @staticmethod
    def lead(jid: int = 1, depth: int = 2) -> dict:
        return {"id": jid, "domain": 0, "depth": depth, "value": 2.0, "urgency": 0.03, "human_quality": 0.95}

    def sell_recipient(self, enterprise: Enterprise, skill: Skill, jid: int = 1) -> Job:
        selected_plan = (1, PRODUCTION[1] + INTEGRATION, VALIDATION[1].scale(0.65), [0], [skill])
        with patch.object(enterprise, "plan", return_value=selected_plan), \
             patch.object(enterprise, "utilities", return_value=[10.0, -10.0, -10.0, -10.0]):
            enterprise.sell(self.lead(jid), 1)
        self.assertEqual(enterprise.stats["orders"], jid)
        return enterprise.jobs[-1]

    def test_failed_transfer_has_no_retained_falsifier_privilege(self) -> None:
        enterprise = self.enterprise(transfer_success=0.0, harmful_transfer=0.0)
        skill = Skill((0, 1), 0, 0, 30, 12, True, source_job=100)
        enterprise.skills.append(skill)
        job = self.sell_recipient(enterprise, skill)
        self.assertIn(1, job.missing, "failed transfer must reconstruct and face reconstruction error")
        self.assertNotIn(skill, job.selected, "failed adaptation cannot remain an effective retained capability")
        self.assertEqual(job.transferred, 0, "failed transfer cannot count as a useful-recipient transfer")
        self.assertGreaterEqual(job.validation.cost(enterprise.s), VALIDATION[1].cost(enterprise.s))

    def test_harmful_adaptation_does_not_silently_heal_on_second_job(self) -> None:
        enterprise = self.enterprise(transfer_success=1.0, harmful_transfer=1.0)
        skill = Skill((0, 1), 0, 0, 30, 12, True, source_job=100)
        enterprise.skills.append(skill)
        first = self.sell_recipient(enterprise, skill)
        second = self.sell_recipient(enterprise, skill, 2)
        self.assertTrue(first.wrong_components or skill not in first.selected)
        self.assertTrue(second.wrong_components or skill not in second.selected,
                        "persistent adaptation must stay harmful or be rejected/corrected at a cost")

    def test_revoked_skill_cannot_enter_actual_production(self) -> None:
        enterprise = self.enterprise()
        skill = Skill((0, 0), 0, 0, 30, 12, True, source_job=100)
        enterprise.skills.append(skill)
        with patch.object(enterprise, "utilities", return_value=[10.0, -10.0, -10.0, -10.0]):
            enterprise.sell(self.lead(depth=1), 1)
        self.assertEqual(enterprise.stats["orders"], 1)
        self.assertIn(skill, enterprise.jobs[-1].selected)
        skill.active = False
        enterprise.input_budget = enterprise.output_budget = 100000.0
        enterprise.work_jobs(2)
        self.assertFalse(any(skill in job.selected and job.stage != "production" for job in enterprise.jobs),
                         "order-time selection does not authorize use after revocation")

    def test_due_but_unperformed_revalidation_is_not_current(self) -> None:
        enterprise = self.enterprise()
        skill = Skill((0, 0), 0, 0, 30, 2, True, source_job=100)
        self.assertFalse(enterprise.eligible(skill, 0, 0, 0, 2),
                         "a due revalidation that could not run cannot authorize new reuse")

    def test_duplicate_availability_does_not_force_costly_use(self) -> None:
        enterprise = self.enterprise()
        enterprise.arm = "duplicate"
        enterprise.skills.append(Skill((0, 0), 0, 0, 30, 12, True, source_job=100))
        _, _, _, missing, selected = enterprise.plan(self.lead(depth=1), 1)
        self.assertEqual(selected, [], "duplicate negative control must retain optional rational use")
        self.assertEqual(missing, [0])

    def test_unpaid_obligations_reduce_available_investment_cash(self) -> None:
        ledger = Ledger(10.0)
        self.assertFalse(ledger.spend(20.0, 0, "contractual-obligation"))
        ledger.receive(15.0, 1, "customer")
        self.assertLessEqual(ledger.available(), 5.0,
                             "unpaid incurred obligations cannot be spent as free investment resources")

    def test_active_runoff_work_pays_continuing_operating_overhead(self) -> None:
        enterprise = self.enterprise(weeks=1, runoff=4, leads_per_week=0.0)
        work = Work(astra_input=1.0, astra_output=0.1, tools=5.0, latency=10.0)
        job = Job(77, 0, 1, 1, 10000.0, 20000.0, 0, 30, work, VALIDATION[0], [0], [], 0)
        job.start("production", work)
        enterprise.ledger.reserve("job-77", 5000.0, 0)
        enterprise.jobs.append(job)
        result = enterprise.run()
        charged_weeks = {row["week"] for row in result["ledger"]
                         if row.get("category") == "infrastructure_access_storage"}
        self.assertEqual(charged_weeks, {1, 2, 3, 4, 5},
                         "unfinished production continues to require infrastructure during runoff")

    def test_hidden_correctness_does_not_instantly_change_public_trust(self) -> None:
        trusts = []
        for true_correct in (True, False):
            enterprise = self.enterprise(repeat_probability=0.0)
            job = Job(77, 0, 1, 1, 10000.0, 20000.0, 0, 30, PRODUCTION[0], VALIDATION[0], [], [], 0,
                      true_correct=true_correct)
            enterprise.jobs.append(job)
            enterprise.complete(job, 2, True)
            trusts.append(enterprise.trust)
        self.assertEqual(trusts[0], trusts[1],
                         "identical observed validation/delivery must not reveal hidden correctness before discovery")

    def test_alpha_comparator_includes_already_available_equivalent_capability(self) -> None:
        enterprise = self.enterprise(transfer_success=1.0, harmful_transfer=0.0,
                                     maintenance_per_skill=0.0, distribution_fixed=0.0, member_overhead=0.0)
        enterprise.skills.append(Skill((0, 0), 0, 0, 30, 12, True, source_job=100))
        candidate = Candidate((0, 0), 0, 101, 1, "redundant-same-owner-capability", True)
        result = enterprise.alpha_assess([candidate], 1, 0)
        self.assertFalse(result["decision"]["accepted"],
                         "a hash listing an existing capability must also affect the actual paired comparator")

    def test_paired_costs_reconcile_without_double_charging(self) -> None:
        enterprise = self.enterprise()
        candidate = Candidate((0, 1), 0, 101, 1, "new-falsifier", True)
        result = enterprise.alpha_assess([candidate], 1, 100)
        self.assertEqual(len(result["paired_probes"]), enterprise.s.agents * 3)
        for probe in result["paired_probes"]:
            declared_net = (probe["gross_gain_before_incremental_costs"] - probe["incremental_integration"]
                            - probe["incremental_operating"] - probe["incremental_risk"])
            self.assertAlmostEqual(declared_net, probe["baseline_delivery_cost"] - probe["proposed_delivery_cost"])
        self.assertEqual(result["assessment"]["source_kind"], "simulation")

    def test_continuation_excludes_only_exact_asset_and_respects_remaining_life(self) -> None:
        enterprise = self.enterprise()
        original = Skill((0, 0), 0, 0, 30, 12, True, source_job=100)
        alternative = Skill((0, 0), 0, 0, 30, 12, True, source_job=200)
        enterprise.skills.extend((original, alternative))
        candidate = Candidate((0, 0), 0, 100, 1, "continuation", True)
        result = enterprise.alpha_assess([candidate], 1, 0, True, remaining_life=2)
        self.assertEqual(result["horizon"], 2)
        self.assertFalse(result["decision"]["accepted"],
                         "an equivalent separate admitted asset remains in the continuation comparator")
        self.assertTrue(any(method["identity"] == [[0, 0], 0, 200]
                            for probe in result["paired_probes"] for method in probe["baseline_methods"]))

    def test_alpha_decision_cannot_read_hidden_technical_validity(self) -> None:
        enterprise = self.enterprise()
        existing = Skill((0, 1), 1, 0, 30, 12, True, source_job=100)
        enterprise.skills.append(existing)
        candidate = Candidate((0, 0), 0, 101, 1, "paired-probe", True)
        observed = enterprise.alpha_assess([candidate], 1, 0)
        existing.valid = False
        unseen_change = enterprise.alpha_assess([replace(candidate, task_valid=False)], 1, 0)
        self.assertEqual(observed, unseen_change,
                         "technical false passes remain latent rather than giving investment a correctness oracle")
