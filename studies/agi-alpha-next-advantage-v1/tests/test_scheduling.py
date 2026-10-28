# SPDX-License-Identifier: Apache-2.0
"""Directed integrity checks for the numerical study's acceptance boundary."""

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scheduling import RULES, cp_sat, dispatch, incumbent, make_instance, risk_score, solve, verify


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = make_instance(812, small=True)
        self.schedule = dispatch(self.case, RULES[0])

    def test_all_jobs_and_hard_constraints(self) -> None:
        self.assertTrue(verify(self.case, self.schedule)["valid"])
        self.assertTrue(verify(self.case, incumbent(self.case))["valid"])

    def test_duplicate_job_is_rejected(self) -> None:
        changed = copy.deepcopy(self.schedule)
        changed["jobs"][0]["job"] = changed["jobs"][1]["job"]
        self.assertFalse(verify(self.case, changed)["valid"])

    def test_processing_shortcut_is_rejected(self) -> None:
        changed = copy.deepcopy(self.schedule)
        changed["jobs"][0]["finish"] -= 0.01
        self.assertFalse(verify(self.case, changed)["valid"])

    def test_release_shortcut_is_rejected(self) -> None:
        changed = copy.deepcopy(self.schedule)
        row = changed["jobs"][0]
        row["start"] = -1
        row["finish"] = row["start"] + self.case["p"][row["job"]][row["machine"]]
        self.assertFalse(verify(self.case, changed)["valid"])

    def test_nonfinite_is_rejected(self) -> None:
        changed = copy.deepcopy(self.schedule)
        changed["jobs"][0]["finish"] = float("nan")
        self.assertFalse(verify(self.case, changed)["valid"])

    def test_zero_uncertainty_matches_independent_nominal_objective(self) -> None:
        factors = np.ones((8, self.case["n"], self.case["m"]))
        self.assertAlmostEqual(risk_score(self.case, self.schedule, factors)["objective"], verify(self.case, self.schedule)["objective"])

    def test_same_budget_and_reproducible_policy_transfer(self) -> None:
        policy = {"theta": RULES[1].tolist()}
        a = solve(self.case, policy, "composed", "nominal", 16)
        b = solve(self.case, copy.deepcopy(policy), "composed", "nominal", 16)
        c = solve(self.case, None, "beta", "nominal", 16)
        self.assertEqual(a["schedule"], b["schedule"])
        self.assertEqual(a["evals"], c["evals"])

    def test_hidden_disturbance_truth_cannot_change_solver_action(self) -> None:
        changed = copy.deepcopy(self.case)
        changed["duration_sigma_true"] = [999.0] * changed["m"]
        a = solve(self.case, None, "beta", "robust", 16)
        b = solve(changed, None, "beta", "robust", 16)
        self.assertEqual(a["schedule"], b["schedule"])
        self.assertEqual(a["candidate_scores"], b["candidate_scores"])

    @unittest.skipUnless(importlib.util.find_spec("ortools"), "optional OR-Tools not installed")
    def test_cp_sat_preserves_or_improves_warm_start(self) -> None:
        result = cp_sat(self.case, self.schedule, 0.08)
        self.assertTrue(result["verification"]["valid"])
        self.assertLessEqual(result["verification"]["objective"], verify(self.case, self.schedule)["objective"])


if __name__ == "__main__":
    unittest.main()
