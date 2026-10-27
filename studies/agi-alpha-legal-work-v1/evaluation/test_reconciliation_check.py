# SPDX-License-Identifier: Apache-2.0
"""Counterexamples to source substitution, omitted edits and unsupported meaning."""

import copy
import hashlib
import unittest

from reconciliation_check import check


def fixture() -> tuple[dict, dict]:
    original, revised = "A⚖️\nB", "A⚖️\nC"
    case = {
        "case_id": "RECON-DEV",
        "original_text": original,
        "revised_text": revised,
        "amendments": [{"id": "A1", "text": "Synthetic amendment; effect not interpreted."}],
    }
    docs = {"original": original, "revised": revised, "amendment:A1": case["amendments"][0]["text"]}
    packet = {
        "schema": "legal-reconciliation/v1",
        "case_id": case["case_id"],
        "method": "independent development fixture",
        "documents": docs,
        "source_hashes": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in docs.items()},
        "operations": [
            {
                "kind": "replace",
                "original_span": {"document": "original", "start": 0, "end": len(original), "quote": original},
                "revised_span": {"document": "revised", "start": 0, "end": len(revised), "quote": revised},
            }
        ],
        "amendments": [{"document": "amendment:A1", "quote": docs["amendment:A1"], "effect": "NOT_INTERPRETED"}],
        "decision": "TEXT_RECONCILIATION_ONLY",
        "professional_acceptance": "unknown",
        "legal_or_playbook_conclusions": [],
        "proposed_revisions": [],
    }
    return case, packet


class ReconciliationControls(unittest.TestCase):
    def test_valid_alternative_segmentation_does_not_require_difflib(self) -> None:
        case, packet = fixture()
        result = check(case, packet)
        self.assertTrue(result["accepted_independent"])
        self.assertEqual(result["preserved_context_ratio"], {"original": 0, "revised": 0})
        self.assertFalse(result["localization_assessed"])

    def test_unicode_codepoints_and_empty_insertion_span(self) -> None:
        case, packet = fixture()
        case["revised_text"] = "A⚖️\nXB"
        packet["documents"]["revised"] = case["revised_text"]
        packet["source_hashes"]["revised"] = hashlib.sha256(case["revised_text"].encode()).hexdigest()
        packet["operations"] = []
        for kind, old_start, old_end, new_start, new_end in [
            ("equal", 0, 4, 0, 4),
            ("insert", 4, 4, 4, 5),
            ("equal", 4, 5, 5, 6),
        ]:
            packet["operations"].append(
                {
                    "kind": kind,
                    "original_span": {
                        "document": "original",
                        "start": old_start,
                        "end": old_end,
                        "quote": case["original_text"][old_start:old_end],
                    },
                    "revised_span": {
                        "document": "revised",
                        "start": new_start,
                        "end": new_end,
                        "quote": case["revised_text"][new_start:new_end],
                    },
                }
            )
        result = check(case, packet)
        self.assertTrue(result["accepted_independent"])
        self.assertEqual(result["highlighted_original_codepoints"], 0)
        self.assertEqual(result["highlighted_revised_codepoints"], 1)
        self.assertEqual(result["unchanged_codepoints"], 5)

    def test_self_consistent_substituted_source_is_rejected(self) -> None:
        case, packet = fixture()
        packet["documents"]["original"] = "different"
        packet["source_hashes"]["original"] = hashlib.sha256(b"different").hexdigest()
        self.assertIn("ORIGINAL_INPUT_BINDING", check(case, packet)["issues"])

    def test_false_equal_rejected(self) -> None:
        case, packet = fixture()
        packet["operations"][0]["kind"] = "equal"
        self.assertIn("FALSE_OPERATION_LABEL", check(case, packet)["issues"])

    def test_false_insert_rejected(self) -> None:
        case, packet = fixture()
        packet["operations"][0]["kind"] = "insert"
        self.assertIn("FALSE_OPERATION_LABEL", check(case, packet)["issues"])

    def test_unknown_operation_rejected(self) -> None:
        case, packet = fixture()
        packet["operations"][0]["kind"] = "legally-equivalent"
        self.assertIn("OPERATION_KIND", check(case, packet)["issues"])

    def test_omitted_material_cannot_pass(self) -> None:
        case, packet = fixture()
        packet["operations"] = []
        self.assertIn("INCOMPLETE_RECONSTRUCTION", check(case, packet)["issues"])

    def test_duplicate_operations_rejected(self) -> None:
        case, packet = fixture()
        packet["operations"].append(copy.deepcopy(packet["operations"][0]))
        self.assertIn("GAP_OVERLAP_OR_REORDERING", check(case, packet)["issues"])

    def test_bool_offset_rejected(self) -> None:
        case, packet = fixture()
        packet["operations"][0]["original_span"]["start"] = False
        self.assertIn("SOURCE_SPAN", check(case, packet)["issues"])

    def test_cross_document_reference_rejected(self) -> None:
        case, packet = fixture()
        packet["operations"][0]["original_span"]["document"] = "amendment:A1"
        self.assertIn("SOURCE_SPAN", check(case, packet)["issues"])

    def test_duplicate_amendment_rejected(self) -> None:
        case, packet = fixture()
        packet["amendments"].append(copy.deepcopy(packet["amendments"][0]))
        self.assertIn("AMENDMENT_INVENTORY", check(case, packet)["issues"])

    def test_interpreted_amendment_rejected(self) -> None:
        case, packet = fixture()
        packet["amendments"][0]["effect"] = "legally consolidates NDA"
        self.assertIn("AMENDMENT_CHANGED_OR_INTERPRETED", check(case, packet)["issues"])

    def test_semantic_or_professional_claim_rejected(self) -> None:
        case, packet = fixture()
        packet["professional_acceptance"] = "accepted"
        self.assertIn("SEMANTIC_OR_PROFESSIONAL_SCOPE", check(case, packet)["issues"])


if __name__ == "__main__":
    unittest.main()
