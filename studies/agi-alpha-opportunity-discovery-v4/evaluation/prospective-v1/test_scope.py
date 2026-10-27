# SPDX-License-Identifier: Apache-2.0
"""Plate-only tests of the new source-binding adapter, before prospective calls."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from checker_v0_1_1 import evaluate


class ScopeTests(unittest.TestCase):
    """Verify that nonempty but incorrect binding objects cannot pass."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.development = ROOT.parent.parent / "data" / "development" / "revision_0_1_1"
        cls.report = json.loads((cls.development / "report_0_1_1.json").read_text())

    def receipt(self, mutate: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        report = copy.deepcopy(self.report)
        target = next(r for r in report["repair_requests"] if r["id"] == "feature_set_identity")["affected"]
        if mutate is not None:
            mutate(target)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(report))
            return evaluate(
                self.development / "request_0_1_1.json",
                path,
                ROOT / "development" / "plate_oracle_0_1_1.json",
            )

    def rejected(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        receipt = self.receipt(mutate)
        self.assertFalse(receipt["accepted"])
        self.assertIn("prospective_bindings", receipt["failed_checks_by_category"])

    def test_plate_binding_accepted(self) -> None:
        self.assertTrue(self.receipt()["accepted"])

    def test_empty_documents_rejected(self) -> None:
        self.rejected(lambda a: a.update(documents=[]))

    def test_wrong_source_identity_rejected(self) -> None:
        self.rejected(lambda a: a["documents"][0].update(sha256="0" * 64))

    def test_fictitious_obligation_rejected(self) -> None:
        self.rejected(lambda a: a["documents"][0]["characteristic_obligations"][0].update(characteristic_id="999999"))

    def test_scope_is_not_correspondence(self) -> None:
        self.rejected(lambda a: a.update(correspondence_established=True))

    def test_scope_is_bound_to_current_mission(self) -> None:
        self.rejected(lambda a: a["mission"].update(sha256="0" * 64))


if __name__ == "__main__":
    unittest.main(verbosity=2)
