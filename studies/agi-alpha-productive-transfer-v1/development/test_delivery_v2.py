# SPDX-License-Identifier: Apache-2.0
"""Behavioral controls for the specific missing-package failure, using synthetic sources."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from delivery_v2 import write_package
from intake import assess_extraction
from test_intake import fixture


class HandoffControls(unittest.TestCase):
    def package(self, unresolved=False):
        raw, ex = fixture()
        if unresolved:
            claim = ex["claims"].pop()
            ex["unresolved"] = [{k: claim[k] for k in ("line", "column", "callee")}]
            ex["unresolved"][0]["reason"] = "Target evidence is missing in this synthetic control."
        result = assess_extraction(raw, ex)
        result["arm"] = "C" if unresolved else "B"
        return raw, result

    def test_unresolved_gets_both_reports_and_source_evidence(self):
        raw, result = self.package(True)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_package(root, raw, result)
            rows = json.loads((root / "call-inventory.json").read_text())
            self.assertEqual(rows[0]["status"], "UNRESOLVED")
            self.assertIn("execute(3, flag=True)", rows[0]["snippet"])
            self.assertIn("#L3", rows[0]["consumerUrl"])
            for lang in ("en", "fr"):
                body = (root / f"report-{lang}.md").read_text()
                self.assertIn("execute", body)
                self.assertIn("UNRESOLVED", body)
                self.assertIn("HOLD", body)

    def test_conflict_is_actionable_without_approval(self):
        raw, result = self.package()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            package = write_package(root, raw, result)
            body = (root / "report-en.md").read_text()
            self.assertIn("revise the arguments", body)
            self.assertIn("run a consumer regression", body)
            self.assertFalse(package["productionApproved"])
            self.assertIsNone(package["completeScopeAccepted"])

    def test_referenced_local_payloads_exist_after_runner_outputs(self):
        raw, result = self.package()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_package(root, raw, result)
            for name in ("receipt.json", "result.json"):
                (root / name).write_text("{}")
            body = (root / "report-en.md").read_text()
            local = [p for p in re.findall(r"\]\(([^)]+)\)", body) if not p.startswith("https://")]
            self.assertTrue(local)
            self.assertTrue(all((root / p).is_file() for p in local))

    def test_unknown_costs_are_not_zero(self):
        raw, result = self.package(True)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_package(root, raw, result)
            costs = json.loads((root / "costs.json").read_text())
            self.assertIsNone(costs["fullyLoadedUsd"])
            self.assertIsNone(costs["recurringUsd"])
            self.assertFalse(costs["completeCostsIdentified"])
            self.assertFalse(costs["currentSessionModelStage"])


if __name__ == "__main__":
    unittest.main()
