# SPDX-License-Identifier: Apache-2.0
"""Adversarial controls on the mechanical evaluator."""

import copy
import unittest

from conventional import FAMILIES, review
from scorer import score

BASE = """SYNTHETIC - NOT FOR EXECUTION
1. Purpose. Each Recipient shall use Confidential Information only to evaluate the business relationship.
2. Confidentiality. Each Recipient must keep information confidential for 24 months after disclosure.
3. Return. Upon request, the Recipient must return or destroy the information within 20 calendar days after request.
4. Compelled Disclosure. If legally compelled to disclose, Recipient must give prior notice to the extent legally permitted.
5. Residuals. Neither Recipient may use residual information retained in unaided memory.
6. Assignment. Neither party may assign this Agreement without the other party's prior written consent.
7. Governing Law. This Agreement is governed by the laws of Ontario, Canada.
8. Representatives. Disclosure to representatives is only on a need-to-know basis; Recipient remains responsible for breaches.
"""


def fixture() -> tuple[dict, dict, dict]:
    case = {
        "case_id": "scorer-development",
        "jurisdiction": "Ontario, Canada",
        "document_family": "commercial mutual NDA",
        "playbook_version": "ONT-NDA-RESEARCH-1.0",
        "source_class": "synthetic",
        "original_text": BASE,
        "revised_text": BASE.replace("24 months", "48 months"),
        "amendments": [],
        "request": "Prepare counsel packet.",
    }
    key = {
        "case_id": case["case_id"],
        "supported_scope": True,
        "expected_statuses": {r: "pass" for r in FAMILIES},
        "required_sources": [],
        "required_escalation_rules": ["R2_CONFIDENTIALITY_TERM"],
    }
    key["expected_statuses"]["R2_CONFIDENTIALITY_TERM"] = "deviation"
    return case, review(case), key


class ScoringControls(unittest.TestCase):
    def test_development_packet_passes(self) -> None:
        case, packet, key = fixture()
        self.assertTrue(score(case, packet, key)["accepted_deterministic"])

    def test_false_material_pass_cannot_hide_in_other_correct_rules(self) -> None:
        case, packet, key = fixture()
        packet["rule_results"][1]["status"] = "pass"
        result = score(case, packet, key)
        self.assertFalse(result["accepted_deterministic"])
        self.assertEqual(result["severity5_false_passes"], 1)
        self.assertEqual(result["rules_correct"], 7)

    def test_source_byte_substitution_rejected(self) -> None:
        case, packet, key = fixture()
        packet["rule_results"][1]["sources"][0]["quote"] += " invented"
        self.assertFalse(score(case, packet, key)["accepted_deterministic"])

    def test_duplicate_rule_cannot_overwrite_wrong_rule(self) -> None:
        case, packet, key = fixture()
        packet["rule_results"].append(copy.deepcopy(packet["rule_results"][0]))
        self.assertFalse(score(case, packet, key)["accepted_deterministic"])

    def test_missing_change_coverage_rejected(self) -> None:
        case, packet, key = fixture()
        packet["changes"] = []
        result = score(case, packet, key)
        self.assertFalse(result["accepted_deterministic"])
        self.assertGreater(result["missing_changed_characters"], 0)

    def test_unearned_professional_acceptance_rejected(self) -> None:
        case, packet, key = fixture()
        packet["professional_acceptance"] = "accepted"
        self.assertFalse(score(case, packet, key)["accepted_deterministic"])

    def test_unsupported_revision_rejected(self) -> None:
        case, packet, key = fixture()
        packet["proposed_revisions"] = [{"text": "All parties waive all claims."}]
        self.assertFalse(score(case, packet, key)["accepted_deterministic"])


if __name__ == "__main__":
    unittest.main()
