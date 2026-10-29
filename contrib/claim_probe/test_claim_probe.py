# SPDX-License-Identifier: Apache-2.0
"""Meaningful exact-math, evidence and operator refusal regressions."""

import copy
import json
from fractions import Fraction as Q
from pathlib import Path
import tempfile
import unittest

from alpha_factory_v1.core.runtime.claim_probe import checker, contracts, instrument, operator
from contrib.claim_probe.comparators import ordinary_library


def task(coefficients, domain=("0", "1"), **limits):
    out = operator.example()
    out["coefficients"] = [str(x) for x in coefficients]
    out["domain"] = list(domain)
    out["limits"].update(limits)
    return out


class ClaimProbeTests(unittest.TestCase):
    def test_interior_counterexample(self):
        t = operator.example()
        r = instrument.probe(t)
        self.assertEqual(r["status"], "REFUTED")
        self.assertLess(Q(r["witness"]["value"]), 0)
        self.assertTrue(checker.check(t, r)["accepted"])

    def test_global_proof(self):
        for c in [[1], [0], [1, 2, 1], [2, -2, 1]]:
            with self.subTest(c=c):
                t = task(c)
                r = instrument.probe(t)
                self.assertEqual(r["status"], "PROVED")
                self.assertTrue(checker.check(t, r)["accepted"])

    def test_exact_sign_reference(self):
        cases = [
            ([0, 0, 1], True),
            ([0, 1], False),
            ([1, -2, 1], True),
            ([4, 0, -4, 0, 1], True),
            ([-1, 0, 1], False),
            ([0, 0, -1], False),
        ]
        for c, expected in cases:
            with self.subTest(c=c):
                self.assertEqual(checker.globally_nonnegative(list(map(Q, c)), Q(-2), Q(2)), expected)

    def test_boundary_roots(self):
        for c in [[0, 1], [0, 1, -1], [1, -1]]:
            self.assertTrue(checker.globally_nonnegative(list(map(Q, c)), Q(0), Q(1)))

    def test_strong_library_handles_irrational_tangency(self):
        t = task([4, 0, -4, 0, 1], domain=("0", "2"), cells=16, depth=8)
        self.assertEqual(instrument.probe(t)["status"], "UNKNOWN")
        r = ordinary_library(t)
        self.assertEqual(r["status"], "PROVED")
        self.assertTrue(checker.check(t, r)["accepted"])

    def test_no_relaxed_threshold(self):
        t = task([1])
        t["claim"] = "mostly-nonnegative"
        with self.assertRaises(ValueError):
            instrument.probe(t)

    def test_limits_return_unknown(self):
        t = task(["2499/10000", -1, 1], cells=1, depth=0)
        r = instrument.probe(t)
        self.assertIn(r["status"], {"REFUTED", "UNKNOWN"})
        self.assertTrue(checker.check(t, r)["accepted"])

    def test_tampered_witness(self):
        t = operator.example()
        r = instrument.probe(t)
        r["witness"]["value"] = "-9000"
        self.assertFalse(checker.check(t, r)["accepted"])

    def test_tampered_source(self):
        t = task([1])
        r = instrument.probe(t)
        t["sources"].append("https://example.org/changed")
        self.assertFalse(checker.check(t, r)["accepted"])

    def test_cover_gaps_overlaps_and_lower_bound(self):
        t = task([1, 0, 1])
        original = instrument.probe(t)
        for change in ["gap", "overlap", "bound"]:
            r = copy.deepcopy(original)
            if change == "bound":
                r["cover"][0]["lowerBound"] = "999"
            else:
                r["cover"] = [
                    {"interval": ["0", "1/3"], "lowerBound": "1"},
                    {"interval": ["1/2" if change == "gap" else "1/4", "1"], "lowerBound": "1"},
                ]
            self.assertFalse(checker.check(t, r)["accepted"])

    def test_no_physical_claim_from_exact_model(self):
        t = task([1])
        r = instrument.probe(t)
        r["physicalQualified"] = True
        self.assertFalse(checker.check(t, r)["accepted"])

    def test_unknown_is_not_proof(self):
        t = task([4, 0, -4, 0, 1], ("0", "2"), cells=1, depth=0)
        r = instrument.probe(t)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertFalse(checker.check(t, r)["decisive"])
        r["status"] = "PROVED"
        self.assertFalse(checker.check(t, r)["accepted"])

    def test_json_collision_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "task.json"
            contracts.write_new(p, operator.example())
            original = p.read_bytes()
            with self.assertRaises(FileExistsError):
                contracts.write_new(p, {})
            self.assertEqual(original, p.read_bytes())
            q = Path(tmp) / "link.json"
            q.symlink_to(p)
            with self.assertRaises(ValueError):
                contracts.read(q)
            p.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(ValueError):
                contracts.read(p)

    def test_malformed_rationals_and_bounds(self):
        for coefficients in [[1.2], [True], ["1/0"], ["NaN"], ["1"] * 10]:
            t = task([1])
            t["coefficients"] = coefficients
            with self.assertRaises(ValueError):
                contracts.validate(t)
        with self.assertRaises(ValueError):
            instrument.probe(task([1], ("1", "0")))

    def test_wrong_strong_control_proof_rejected(self):
        t = operator.example()
        r = ordinary_library(t)
        r.update(status="PROVED", witness=None)
        self.assertFalse(checker.check(t, r)["accepted"])

    def test_checker_does_not_import_constructor(self):
        source = Path(checker.__file__).read_text()
        self.assertNotIn("from .instrument", source)
        self.assertNotIn("import sympy", source)


if __name__ == "__main__":
    unittest.main()
