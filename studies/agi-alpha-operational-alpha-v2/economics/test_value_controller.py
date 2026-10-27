# SPDX-License-Identifier: Apache-2.0
"""Ensure HOLD is exact existing expert operation, not a cost or authority bypass."""

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("value_controller", HERE / "value_controller.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
E = V.original()
CONFIG = json.loads((HERE / "protocol.json").read_text())
PILOT = E.load_pilot(HERE / "results/pilot_input.json")
CHOICE = {"price_ratio": 0.5, "reserve_days": 3}


class ValueControllerTests(unittest.TestCase):
    def test_hold_exactly_reuses_expert_e(self):
        for policy in V.OPTIONAL:
            original = E.simulate(PILOT, CONFIG, 25, "reference", "expert_E", CHOICE, True)
            held = V.execute(E, PILOT, CONFIG, 25, "reference", policy, {**CHOICE, "mode": "hold"}, True)
            for key in ("requested_policy", "operative_policy", "controller_mode"):
                held.pop(key)
            held["policy"] = "expert_E"
            self.assertEqual(original, held)
            self.assertEqual(held["diagnostics"]["assessments"], 0)
            self.assertEqual(held["diagnostics"]["gym_attempts"], 0)

    def test_assess_exactly_reuses_original_policy(self):
        for policy in V.OPTIONAL:
            original = E.simulate(PILOT, CONFIG, 83, "reference", policy, CHOICE, True)
            adapted = V.execute(E, PILOT, CONFIG, 83, "reference", policy, {**CHOICE, "mode": "assess"}, True)
            for key in ("requested_policy", "operative_policy", "controller_mode"):
                adapted.pop(key)
            self.assertEqual(original, adapted)

    def test_graph_and_same_content_library_match_in_both_modes(self):
        for mode in ("hold", "assess"):
            a = V.execute(E, PILOT, CONFIG, 12, "reference", "shared_retention", {**CHOICE, "mode": mode}, True)
            b = V.execute(E, PILOT, CONFIG, 12, "reference", "library_retention", {**CHOICE, "mode": mode}, True)
            for key in ("policy", "requested_policy", "operative_policy"):
                a.pop(key)
                b.pop(key)
            self.assertEqual(a, b)

    def test_control_cannot_silently_change_to_hold(self):
        with self.assertRaises(ValueError):
            V.execute(E, PILOT, CONFIG, 1, "reference", "ordinary_U", {**CHOICE, "mode": "hold"})


if __name__ == "__main__":
    unittest.main()
