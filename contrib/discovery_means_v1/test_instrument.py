# SPDX-License-Identifier: Apache-2.0
"""Development tests for adaptive policy feasibility and refusal boundaries."""

import copy
import json
import unittest
from pathlib import Path

from discovery_means.instrument import advance, solve, validate, verify


class InstrumentTests(unittest.TestCase):
    """Exercise the actual construction and independently replay its policy."""

    def setUp(self) -> None:
        self.problem = json.loads((Path(__file__).parent / "examples/adaptive.json").read_text())

    def test_contingent_budget(self) -> None:
        result = solve(self.problem)
        self.assertEqual((result["status"], result["worst_cost"], result["worst_depth"]), ("optimal", 3, 2))
        self.assertTrue(verify(self.problem, result)["accepted_policy"])
        self.assertEqual(result["policy"]["experiment"], "screen")
        self.assertEqual(
            advance(self.problem, result, [{"experiment": "screen", "outcome": "R2"}])["next_experiment"], "right"
        )

    def test_complete_observation(self) -> None:
        rows = [{"experiment": "screen", "outcome": "R"}, {"experiment": "right", "outcome": "c2"}]
        self.assertEqual(advance(self.problem, solve(self.problem), rows)["identified_hypothesis"], "H2")

    def test_noise_overlap_refuses(self) -> None:
        self.problem["experiments"][2]["outcomes"]["H3"] = ["c", "d"]
        result = solve(self.problem)
        self.assertEqual(result["status"], "infeasible")
        self.assertIn(["H2", "H3"], result["unresolved_pairs"])

    def test_search_cap_honest(self) -> None:
        self.problem["max_states"] = 1
        result = solve(self.problem)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["complete"])
        self.assertFalse(verify(self.problem, result)["accepted_policy"])

    def test_disallowed_probe(self) -> None:
        self.problem["experiments"][2]["allowed"] = False
        self.assertEqual(solve(self.problem)["status"], "infeasible")

    def test_cost_and_depth_caps(self) -> None:
        self.problem["max_cost"] = 2
        self.assertEqual(solve(self.problem)["status"], "infeasible")
        self.problem["max_cost"], self.problem["max_experiments"] = 4, 1
        self.assertEqual(solve(self.problem)["status"], "infeasible")

    def test_tampered_policy(self) -> None:
        result = solve(self.problem)
        result["worst_cost"] = 2
        self.assertFalse(verify(self.problem, result)["accepted_policy"])
        result = solve(self.problem)
        del result["policy"]["branches"]["R2"]
        self.assertFalse(verify(self.problem, result)["accepted_policy"])

    def test_unmodeled_and_wrong_order_refuse(self) -> None:
        result = solve(self.problem)
        for row in ({"experiment": "screen", "outcome": "other"}, {"experiment": "right", "outcome": "c"}):
            with self.assertRaises(ValueError):
                advance(self.problem, result, [row])

    def test_closed_schema(self) -> None:
        self.problem["execute"] = "untrusted command"
        with self.assertRaises(ValueError):
            validate(self.problem)

    def test_bool_cost_and_incomplete_model(self) -> None:
        self.problem["experiments"][0]["cost"] = True
        with self.assertRaises(ValueError):
            validate(self.problem)
        self.problem["experiments"][0]["cost"] = 1
        del self.problem["experiments"][0]["outcomes"]["H0"]
        with self.assertRaises(ValueError):
            validate(self.problem)

    def test_expanded_output_cap_honest(self) -> None:
        hypotheses = [f"H{i}" for i in range(8)]
        problem = {
            "hypotheses": hypotheses,
            "max_cost": 7,
            "max_experiments": 7,
            "experiments": [
                {
                    "id": f"e{i}",
                    "cost": 1,
                    "allowed": True,
                    "outcomes": {h: [f"{int(h == f'H{i}')}_{s}" for s in range(8)] for h in hypotheses},
                }
                for i in range(7)
            ],
        }
        result = solve(problem)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["stopping_reason"], "expanded policy output cap")

    def test_changed_problem_refuses(self) -> None:
        result = solve(self.problem)
        changed = copy.deepcopy(self.problem)
        changed["max_cost"] = 4
        self.assertFalse(verify(changed, result)["accepted_policy"])


if __name__ == "__main__":
    unittest.main()
