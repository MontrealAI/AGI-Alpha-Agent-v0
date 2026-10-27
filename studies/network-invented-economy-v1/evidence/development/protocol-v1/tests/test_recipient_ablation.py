# SPDX-License-Identifier: Apache-2.0
"""Controlled-cost invariants; synthetic fixtures are not frontier observations."""

from dataclasses import replace
from unittest import TestCase

from src.alpha_assessment import AlphaCosts
from src.recipient_ablation import (
    CandidateBundle, LifecyclePlan, RecipientSnapshot, assess_lifecycle, default_beta,
    probe_recipient, required_reuses, run_recipient_ablation, standard_lifecycle, standard_mission,
)
from src.simulator import CORRECTION, RECONSTRUCTION, Scenario, Work


class RecipientAblationTests(TestCase):
    def setUp(self) -> None:
        self.scenario = replace(Scenario(), external_improvement=0, transfer_success=1, harmful_transfer=0)
        self.beta = default_beta()
        self.recipient = RecipientSnapshot("recipient", self.beta)
        self.bundle = CandidateBundle("candidate", self.beta.beta_id)
        self.mission = standard_mission(self.scenario)

    def lifecycle(self, plan: LifecyclePlan, **kwargs) -> dict:
        return assess_lifecycle(self.scenario, (self.recipient,), self.mission, self.bundle, plan, **kwargs)

    def test_equivalent_capabilities_survive_removal_and_prevent_duplicate_gain(self) -> None:
        equivalent = tuple(w.scale(0.10) for w in RECONSTRUCTION)
        recipient = replace(self.recipient, equivalents=equivalent)
        result = probe_recipient(self.scenario, recipient, self.mission, self.bundle)
        self.assertEqual(result["preserved_equivalents"], [0, 1, 2])
        self.assertEqual(set(result["ordinary_component_routes"].values()), {"existing-equivalent"})
        self.assertEqual(result["selected_components"], [])
        self.assertEqual(result["expected_delivery_saving_usd"], 0)
        lifecycle = assess_lifecycle(self.scenario, (recipient,), self.mission, self.bundle,
                                    LifecyclePlan(upfront=AlphaCosts(construction=100), useful_lifetime_weeks=4))
        self.assertEqual(lifecycle["project_net"], -100)
        self.assertFalse(lifecycle["decision"]["accepted"])

    def test_partial_equivalent_is_preserved_while_other_components_can_help(self) -> None:
        recipient = replace(self.recipient, equivalents=(RECONSTRUCTION[0].scale(0.10), None, None))
        result = probe_recipient(self.scenario, recipient, self.mission, self.bundle)
        self.assertEqual(result["ordinary_component_routes"]["0"], "existing-equivalent")
        self.assertEqual(result["selected_components"], [1, 2])
        self.assertGreater(result["expected_delivery_saving_usd"], 0)

    def test_ordinary_experience_and_frontier_improvement_reduce_increment(self) -> None:
        base = probe_recipient(self.scenario, self.recipient, self.mission, self.bundle)
        strong = probe_recipient(self.scenario, replace(self.recipient, ordinary_factors=(0.33, 0.33, 0.33)),
                                 self.mission, self.bundle)
        improved = probe_recipient(self.scenario, self.recipient, self.mission, self.bundle, frontier_factor=0.15)
        self.assertLess(strong["expected_delivery_saving_usd"], base["expected_delivery_saving_usd"])
        self.assertEqual(improved["selected_components"], [])
        self.assertEqual(improved["expected_delivery_saving_usd"], 0)

    def test_failed_and_harmful_transfer_pay_attempt_fallback_and_recovery(self) -> None:
        scenario = replace(self.scenario, transfer_success=0.8, harmful_transfer=0.05)
        result = probe_recipient(scenario, self.recipient, self.mission, self.bundle)
        routes = result["shared_conditional_routes"]
        self.assertTrue(result["selected_components"])
        self.assertAlmostEqual(sum(r["probability"] for r in routes.values()), 1)
        self.assertGreater(routes["failed"]["cost_usd"], result["beta"]["cost_usd"] + CORRECTION.cost(scenario))
        self.assertGreater(routes["harmful"]["cost_usd"], routes["failed"]["cost_usd"])
        self.assertAlmostEqual(result["shared_expected_cost_usd"],
                               sum(r["probability"] * r["cost_usd"] for r in routes.values()), places=7)

    def test_known_failed_transfer_or_excessive_validation_does_not_force_use(self) -> None:
        failed = probe_recipient(replace(self.scenario, transfer_success=0), self.recipient, self.mission, self.bundle)
        costly = probe_recipient(self.scenario, self.recipient, self.mission, self.bundle, validation_overhead=100)
        for result in (failed, costly):
            self.assertEqual(result["selected_components"], [])
            self.assertEqual(result["shared_expected_cost_usd"], result["beta"]["cost_usd"])

    def test_current_status_scope_freshness_and_beta_are_checked(self) -> None:
        cases = ({"status": "revoked"}, {"status": "retired"}, {"status": "candidate"},
                 {"status": "superseded"}, {"beta_id": "obsolete-beta"}, {"domain": 1},
                 {"expires_week": 0}, {"validation_due_week": 0})
        for change in cases:
            with self.subTest(change=change):
                result = probe_recipient(self.scenario, self.recipient, self.mission, replace(self.bundle, **change))
                self.assertTrue(result["eligibility_rejections"])
                self.assertEqual(result["selected_components"], [])

    def test_new_feasibility_is_only_a_fixed_resource_threshold_crossing(self) -> None:
        initial = probe_recipient(self.scenario, self.recipient, self.mission, self.bundle)
        budget = (initial["beta"]["cost_usd"] + initial["shared_expected_cost_usd"]) / 2
        result = probe_recipient(self.scenario, self.recipient, replace(self.mission, available_cash=budget), self.bundle)
        self.assertFalse(result["beta"]["feasible"])
        self.assertEqual(result["newly_feasible_probability"], 1)
        self.assertNotEqual(result["state_hash"], initial["state_hash"])
        self.assertEqual(result["ordinary_component_routes"], initial["ordinary_component_routes"])

    def test_resource_failure_prevents_recommendation_despite_cost_advantage(self) -> None:
        mission = replace(self.mission, input_limit_m=0, output_limit_m=0)
        result = assess_lifecycle(self.scenario, (self.recipient,), mission, self.bundle,
                                  LifecyclePlan(useful_lifetime_weeks=4))
        self.assertGreater(result["project_net"], 0)
        self.assertFalse(result["all_modeled_delivery_routes_feasible"])
        self.assertFalse(result["candidate_is_recommended_now"])

    def test_full_lifecycle_reconciles_without_double_charging_transfer(self) -> None:
        plan = LifecyclePlan(upfront=AlphaCosts(construction=100, validation=20, distribution=10),
                             failed_construction_cost=40, historical_cost=15, weekly_upkeep=3,
                             revalidation_cost=7, revalidation_period_weeks=2, useful_lifetime_weeks=4)
        result = self.lifecycle(plan)
        self.assertEqual(result["complete_lifecycle_cost"], 130 + 15 + 12 + 14)
        self.assertEqual(result["failed_construction_subset"], 40)
        self.assertAlmostEqual(result["project_net"], result["beta_complete_delivery_cost"]
                               - result["shared_complete_delivery_cost"] - result["complete_lifecycle_cost"], places=6)
        self.assertAlmostEqual(result["decision"]["expected_net"], result["project_net"], places=6)
        self.assertEqual(result["assessment"]["costs"]["integration"], 0,
                         "transfer is already included in paired complete delivery costs")
        self.assertAlmostEqual(result["prospective_net"] - result["project_net"], 15)

    def test_joint_bundle_can_pay_shared_fixed_cost_when_components_cannot(self) -> None:
        for kind in range(3):
            candidate = replace(self.bundle, components=(kind,))
            mission = standard_mission(self.scenario, (kind,))
            result = assess_lifecycle(self.scenario, (self.recipient,), mission, candidate,
                                      LifecyclePlan(upfront=AlphaCosts(construction=300, validation=900),
                                                    useful_lifetime_weeks=2, uses_per_week=1))
            self.assertFalse(result["decision"]["accepted"])
        bundle = self.lifecycle(LifecyclePlan(upfront=AlphaCosts(construction=900, validation=900),
                                             useful_lifetime_weeks=2, uses_per_week=1))
        self.assertTrue(bundle["decision"]["accepted"])

    def test_strict_reuse_threshold_does_not_accept_break_even(self) -> None:
        self.assertEqual(required_reuses(100, 10), 11)
        self.assertEqual(required_reuses(100, 12, 2), 11)
        self.assertEqual(required_reuses(0, 10), 1)
        self.assertIsNone(required_reuses(100, 0))
        self.assertIsNone(required_reuses(100, -10))
        self.assertIsNone(required_reuses(100, 2, 2))

    def test_no_reuse_preserves_losses_and_does_not_fake_pairs_for_one_week(self) -> None:
        no_uses = self.lifecycle(LifecyclePlan(upfront=AlphaCosts(construction=100), weekly_upkeep=2,
                                             uses_per_week=0, useful_lifetime_weeks=4))
        self.assertEqual(no_uses["project_net"], -108)
        self.assertIsNone(no_uses["first_positive_lifetime_weeks"])
        self.assertFalse(no_uses["candidate_is_recommended_now"])
        one_week = self.lifecycle(LifecyclePlan(useful_lifetime_weeks=1))
        self.assertIsNone(one_week["assessment"], "one modeled pair cannot be duplicated to satisfy a gate")

    def test_future_savings_cannot_pay_upfront_cost_and_history_is_separate(self) -> None:
        result = self.lifecycle(LifecyclePlan(upfront=AlphaCosts(construction=1000), historical_cost=500,
                                             available_investment_cash=100, useful_lifetime_weeks=8))
        self.assertGreater(result["project_net"], 0)
        self.assertFalse(result["upfront_affordable_without_future_receipts"])
        self.assertEqual(result["additional_upfront_cash_required"], 900)
        self.assertFalse(result["candidate_is_recommended_now"])

    def test_moving_beta_charges_reassessment_or_blocks_stale_candidate(self) -> None:
        scenario = replace(self.scenario, external_improvement=0.5, beta_epoch_weeks=2)
        plan = LifecyclePlan(useful_lifetime_weeks=4, beta_reassessment_cost=11)
        maintained = assess_lifecycle(scenario, (self.recipient,), self.mission, self.bundle, plan)
        stale = assess_lifecycle(scenario, (self.recipient,), self.mission, self.bundle,
                                  replace(plan, reassess_moving_beta=False))
        self.assertEqual(maintained["beta_reassessment_cost"], 22)
        self.assertEqual(stale["beta_reassessment_cost"], 0)
        self.assertEqual(stale["weekly"][1]["expected_saving_per_use"], 0)
        self.assertGreater(maintained["weekly"][1]["expected_saving_per_use"], 0)
        fixed = self.lifecycle(plan)
        self.assertNotEqual(maintained["baseline_path_id"], fixed["baseline_path_id"])

    def test_failed_construction_is_charged_once_in_standard_plan(self) -> None:
        first = standard_lifecycle(self.scenario, self.bundle, failed_attempts=0)
        second = standard_lifecycle(self.scenario, self.bundle, failed_attempts=1)
        self.assertAlmostEqual(second.upfront.construction, first.upfront.construction * 2)
        self.assertAlmostEqual(second.failed_construction_cost, first.upfront.construction)

    def test_binding_determinism_and_declared_five_sweeps(self) -> None:
        a = probe_recipient(self.scenario, self.recipient, self.mission, self.bundle)
        b = probe_recipient(self.scenario, self.recipient, self.mission, self.bundle)
        self.assertEqual(a, b)
        changed = probe_recipient(self.scenario, replace(self.recipient, ordinary_factors=(0.6, 1, 1)),
                                  self.mission, self.bundle)
        self.assertNotEqual(a["state_hash"], changed["state_hash"])
        panel = run_recipient_ablation(self.scenario)
        self.assertEqual(len(panel["sensitivity"]), 25)
        self.assertEqual({row["parameter"] for row in panel["sensitivity"]},
                         {"overlap", "uses_per_week", "validation_overhead", "frontier_improvement", "useful_lifetime_weeks"})
        self.assertEqual(panel["actual_activity"]["collections_usd"], 0)

    def test_invalid_inputs_and_cost_omission_are_rejected(self) -> None:
        for change in ({"ordinary_factors": (1, -1, 1)}, {"equivalents": (Work(tools=-1), None, None)},
                       {"ordinary_factors": (True, 1, 1)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.recipient, **change)
        for change in ({"failed_construction_cost": 1}, {"useful_lifetime_weeks": 0},
                       {"uses_per_week": True}, {"weekly_upkeep": float("nan")}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                LifecyclePlan(**change)
        with self.assertRaises(ValueError):
            replace(self.bundle, components=(0, 0))
        with self.assertRaises(ValueError):
            probe_recipient(self.scenario, self.recipient, self.mission, self.bundle, validation_overhead=-1)

