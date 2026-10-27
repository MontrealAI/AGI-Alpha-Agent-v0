# SPDX-License-Identifier: Apache-2.0
"""Accounting, coupling, evidence, and decision boundary controls."""

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


E = module("run_economics")
P = module("prescreen_experiment")
CONFIG = json.loads((HERE / "protocol.json").read_text())
PILOT = {
    "arms": {
        arm: {"accepted": 4, "attempted": 4, "elapsed_seconds": 500, "operations": 20} for arm in ("U", "E", "E_plus")
    }
}
CHOICE = {"price_ratio": 0.5, "reserve_days": 7}


class EconomicTests(unittest.TestCase):
    def test_equal_evidence_does_not_manufacture_quality_advantage(self):
        for seed in range(30):
            self.assertEqual(len(set(E.quality_draw(PILOT, seed).values())), 1)

    def test_primary_costs_ignore_observed_elapsed(self):
        changed = json.loads(json.dumps(PILOT))
        changed["arms"]["E"]["elapsed_seconds"] = 999999
        a = E.simulate(PILOT, CONFIG, 77, "reference", "expert_E", CHOICE)
        b = E.simulate(changed, CONFIG, 77, "reference", "expert_E", CHOICE)
        self.assertEqual(a, b)

    def test_identical_content_library_matches_graph(self):
        for seed in range(10):
            a = E.simulate(PILOT, CONFIG, seed, "reference", "shared_retention", CHOICE, True)
            b = E.simulate(PILOT, CONFIG, seed, "reference", "library_retention", CHOICE, True)
            a.pop("policy")
            b.pop("policy")
            self.assertEqual(a, b)

    def test_cash_cost_obligations_and_actual_unknown(self):
        for policy in E.POLICIES:
            row = E.simulate(PILOT, CONFIG, 444, "reference", policy, CHOICE, True)
            self.assertEqual(row["cash_cents"], row["seed_capital_cents"] + row["profit_cents"])
            self.assertEqual(row["profit_cents"], row["net_collections_cents"] - row["total_cost_cents"])
            self.assertEqual(row["obligations_cents"], 0)
            self.assertIsNone(row["actual_complete_cost_cents"])
            self.assertIsNone(row["actual_profit_cents"])
            self.assertEqual(row["actual_collections_cents"], 0)
            self.assertTrue(all(set(value) == set(E.CATEGORIES) for value in row["costs_cents"].values()))

    def test_unique_expense_ids_and_original_task_retries(self):
        row = E.simulate(PILOT, CONFIG, 12, "reference", "ordinary_U", CHOICE, True)
        expenses = [item["activity"] for item in row["events"] if item["kind"] == "cost"]
        self.assertEqual(len(expenses), len(set(expenses)))
        for item in row["events"]:
            if item["kind"] == "delivery":
                self.assertEqual(item["job"], item["original_task_id"])
            if item["kind"] == "day-close":
                self.assertGreaterEqual(item["capacity_unused"], 0)

    def test_no_economic_premium_for_same_quality(self):
        ordinary = E.simulate(PILOT, CONFIG, 9, "reference", "ordinary_U", CHOICE)
        expert = E.simulate(PILOT, CONFIG, 9, "reference", "expert_E", CHOICE)
        self.assertEqual(ordinary["accepted"], expert["accepted"])
        self.assertEqual(ordinary["net_collections_cents"], expert["net_collections_cents"])
        self.assertEqual(expert["profit_cents"] - ordinary["profit_cents"], -CONFIG["expert_method_setup_cents"])

    def test_failed_jobs_have_incurred_cost(self):
        bad = {"arms": {arm: {"accepted": 0, "attempted": 4} for arm in ("U", "E", "E_plus")}}
        row = E.simulate(bad, CONFIG, 33, "reference", "ordinary_U", CHOICE, True)
        self.assertGreater(row["failed"], 0)
        self.assertGreater(row["costs_cents"]["A"]["correction"], 0)

    def test_new_offer_not_claimed_for_failed_primary_contract(self):
        bad = {"arms": {arm: {"accepted": 3, "attempted": 4} for arm in ("U", "E", "E_plus")}}
        row = E.simulate(bad, CONFIG, 57, "reference", "expert_E", CHOICE, True)
        self.assertEqual(row["diagnostics"]["prototype_attempts"], 0)

    def test_prospective_reachable_screen_never_buys_impossible(self):
        for seed in range(80):
            row = P.execute(seed, "reachable_first")
            self.assertEqual(row["unreachable_assessments"], 0)
            self.assertEqual(row["cash_cents"], 20000 + row["net_cents"])

    def test_old_screen_can_buy_impossible_assessment(self):
        self.assertGreater(sum(P.execute(seed, "old_screen")["unreachable_assessments"] for seed in range(20)), 0)

    def test_assessment_failure_cost_not_erased(self):
        rows = [P.execute(seed, "old_screen") for seed in range(30)]
        self.assertGreater(sum(row["assessment_failures"] for row in rows), 0)
        self.assertTrue(all(row["cost_cents"] >= 200 * row["assessments"] for row in rows))

    def test_same_observed_capability_allows_same_bundle(self):
        for seed in range(10):
            a = E.simulate(PILOT, CONFIG, seed, "reference", "ordinary_U", CHOICE)
            b = E.simulate(PILOT, CONFIG, seed, "reference", "expert_E", CHOICE)
            self.assertEqual(a["diagnostics"]["prototype_attempts"], b["diagnostics"]["prototype_attempts"])
            self.assertEqual(a["diagnostics"]["prototype_failures"], b["diagnostics"]["prototype_failures"])


if __name__ == "__main__":
    unittest.main()
