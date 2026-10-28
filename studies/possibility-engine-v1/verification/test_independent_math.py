# SPDX-License-Identifier: Apache-2.0
"""Meaningful checker controls, separate from primary experiment tests."""

from __future__ import annotations

import copy
import itertools
import unittest

from independent_math import construct_graphs, impulse_entry, independent_competitor, response_interval, verify_witness


class IndependentMathTests(unittest.TestCase):
    """Exercise exact invariants, negative controls and uncertainty envelopes."""

    def setUp(self) -> None:
        """Use the independent graph definitions."""
        self.witness = construct_graphs()

    def test_exact_witness(self) -> None:
        """Separate nonisomorphism from matching root transfer."""
        result = verify_witness(self.witness)
        self.assertEqual(result["differing_ordered_joint_port_count"], 100)

    def test_reject_mutated_edge(self) -> None:
        """Do not accept an almost similar graph as the exact witness."""
        graph = self.witness["models"][0]["adjacency"]
        graph[1][3] = graph[3][1] = 0
        with self.assertRaises(AssertionError):
            verify_witness(self.witness)

    def test_single_side_access_has_no_protocol(self) -> None:
        """Adding only actuators or only sensors must remain insufficient."""
        for actuators, sensors in (([0], None), (None, [0])):
            result = independent_competitor(self.witness, [0.1, 0.2, 0.3], (0.8, 1.2), (0.05, 0.15),
                                            (0.95, 1.05), 0.005, actuators, sensors)
            self.assertEqual(result["status"], "no_feasible_protocol")
            self.assertEqual(result["evaluations"], 0)

    def test_identical_models_have_no_protocol(self) -> None:
        """A null hypothesis pair cannot yield an invented discriminating port."""
        self.witness["models"][1] = copy.deepcopy(self.witness["models"][0])
        result = independent_competitor(self.witness, [0.168], (0.8, 1.2), (0.05, 0.15), (0.95, 1.05), 0.005)
        self.assertEqual(result["status"], "no_feasible_protocol")

    def test_high_noise_refusal(self) -> None:
        """Known discrimination becomes infeasible beyond the error budget."""
        result = independent_competitor(self.witness, [0.168], (0.8, 1.2), (0.05, 0.15), (0.95, 1.05), 0.1)
        self.assertEqual(result["status"], "no_feasible_protocol")

    def test_interval_enclosure(self) -> None:
        """Check endpoints and internal stationary point on a development grid."""
        for adjacent, t in itertools.product((0, 1), (0.05, 0.168, 0.4, 0.9)):
            lower, upper = response_interval(adjacent, t, (0.8, 1.2), (0.05, 0.15), (0.95, 1.05))
            for rate, leak, gain in itertools.product((0.8, 0.85, 0.95, 1, 1.15, 1.2), (0.05, 0.1, 0.15),
                                                      (0.95, 1, 1.05)):
                value = impulse_entry(adjacent, False, t, rate, leak, gain)
                self.assertLessEqual(lower, value)
                self.assertLessEqual(value, upper)

    def test_invalid_box_refused(self) -> None:
        """Malformed physical bounds fail explicitly."""
        with self.assertRaises(ValueError):
            response_interval(1, 0.1, (1.2, 0.8), (0.05, 0.15), (0.95, 1.05))


if __name__ == "__main__":
    unittest.main()
