# SPDX-License-Identifier: Apache-2.0
"""Pre-freeze tests for the newly funded joint-variable constructor."""

import copy
import unittest

from alpha_factory_v1.core.runtime.claim_probe import contracts, joint, joint_check


def joint_task(coefficients):
    return {
        "schema": "agialpha/joint-affine-claim/v1",
        "id": "joint-training",
        "variables": ["x", "y"],
        "coefficients": list(map(str, coefficients)),
        "domain": [["0", "1"], ["0", "1"]],
        "sources": ["https://www.nist.gov/mml/mmsd/data-and-ai-driven-materials-science-group/autonomous-methods"],
        "claim": "nonnegative-throughout-box",
        "scope": "declared-mathematical-model-only",
    }


class JointTests(unittest.TestCase):
    def test_resource_metadata_cannot_be_negative_or_nonfinite(self):
        t = joint_task([1, 0, 0, 0])
        r = joint.construct(t)
        for bad in [-1, True, float("nan"), float("inf")]:
            wrong = copy.deepcopy(r)
            wrong["elapsedSeconds"] = bad
            self.assertFalse(joint_check.check_joint(t, wrong)["accepted"])

    def test_coupled_counterexample(self):
        t = joint_task([1, -1, -1, 0])
        r = joint.construct_and_check(t)
        self.assertTrue(r["verification"]["accepted"])
        self.assertEqual(r["artifact"]["status"], "REFUTED")
        self.assertEqual(r["artifact"]["minimum"], "-1")

    def test_joint_continuum_proof(self):
        t = joint_task([1, 2, -1, 5])
        r = joint.construct_and_check(t)
        self.assertTrue(r["verification"]["accepted"])
        self.assertEqual(r["artifact"]["status"], "PROVED")

    def test_general_box_not_only_unit_cube(self):
        t = joint_task([3, 2, -1, 4])
        t["domain"] = [["-2", "1/2"], ["-3/2", "2"]]
        r = joint.construct(t)
        self.assertTrue(joint_check.check_joint(t, r)["accepted"])

    def test_source_and_witness_tampering(self):
        t = joint_task([1, -1, -1, 0])
        r = joint.construct(t)
        wrong = copy.deepcopy(r)
        wrong["minimum"] = "0"
        self.assertFalse(joint_check.check_joint(t, wrong)["accepted"])
        wrong = copy.deepcopy(r)
        wrong["minimizer"] = ["0", "0"]
        self.assertFalse(joint_check.check_joint(t, wrong)["accepted"])
        t["id"] = "changed"
        self.assertFalse(joint_check.check_joint(t, r)["accepted"])

    def test_old_schema_cannot_silently_accept_joint_claim(self):
        with self.assertRaises(ValueError):
            contracts.validate(joint_task([1, 0, 0, 0]))

    def test_model_class_and_dimension_refusals(self):
        t = joint_task([1, 0, 0, 0])
        t["coefficients"].append("1")
        with self.assertRaises(ValueError):
            joint.construct(t)
        t = joint_task([1, 0, 0, 0])
        t["variables"] = ["x", "x"]
        with self.assertRaises(ValueError):
            joint.construct(t)
        t = joint_task([1, 0, 0, 0])
        t["claim"] = "safe-physical-assembly"
        with self.assertRaises(ValueError):
            joint.construct(t)


if __name__ == "__main__":
    unittest.main()
