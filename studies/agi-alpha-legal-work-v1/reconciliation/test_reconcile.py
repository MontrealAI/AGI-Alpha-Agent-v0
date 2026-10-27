# SPDX-License-Identifier: Apache-2.0
"""Focused controls for source conservation and untrusted input identity."""

from __future__ import annotations

import copy
import unittest
from typing import Any

from reconcile import produce, verify


class ReconciliationControls(unittest.TestCase):
    def case(self) -> dict[str, Any]:
        return {
            "case_id": "DEV-RC",
            "source_class": "synthetic",
            "original_text": "1. Café 🌌\n2. Keep.\n",
            "revised_text": "2. Keep.\n1. Café 🌌 — changed.\n",
            "amendments": [{"id": "A1", "text": "Separate amendment. Do not infer precedence."}],
        }

    def test_both_methods_conserve_unicode_and_movement(self) -> None:
        for method in ["characters", "lines"]:
            packet = produce(self.case(), method)
            self.assertEqual(verify(packet), [])

    def test_refuses_path_escape(self) -> None:
        case = self.case()
        case["case_id"] = "../outside"
        with self.assertRaisesRegex(ValueError, "CASE_ID"):
            produce(case)

    def test_empty_to_insert_and_deletion(self) -> None:
        for old, new in [("", "new 🌌"), ("old", ""), ("", "")]:
            case = self.case()
            case.update(original_text=old, revised_text=new)
            for method in ["characters", "lines"]:
                self.assertEqual(verify(produce(case, method)), [])

    def test_rejects_hash_inventory_and_changed_quotes(self) -> None:
        packet = produce(self.case())
        packet["source_hashes"]["unknown"] = "0" * 64
        self.assertIn("HASH", verify(packet))
        packet = produce(self.case())
        packet["operations"][0]["original_span"]["quote"] += "x"
        self.assertIn("SPAN", verify(packet))

    def test_rejects_false_operation_and_lost_amendment(self) -> None:
        original = produce(self.case())
        position = next(index for index, item in enumerate(original["operations"]) if item["kind"] == "equal")
        for kind in ["invented", "insert", "delete"]:
            packet = copy.deepcopy(original)
            packet["operations"][position]["kind"] = kind
            self.assertTrue(verify(packet))
        packet = copy.deepcopy(original)
        packet["amendments"] = []
        self.assertIn("AMENDMENT_INVENTORY", verify(packet))


if __name__ == "__main__":
    unittest.main()
