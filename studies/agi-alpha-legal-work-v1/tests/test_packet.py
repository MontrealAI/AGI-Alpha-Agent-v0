# SPDX-License-Identifier: Apache-2.0
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legal_packet import check_packet, packet


class PacketControls(unittest.TestCase):
    def case(self, number: int = 2) -> dict:
        return json.loads((ROOT / f"inputs/development/DEV-{number:02}.json").read_text())

    def test_reference_asset(self):
        for n, rid in [(3, "R2_CONFIDENTIALITY_TERM"), (4, "R3_RETURN_DEADLINE")]:
            c = self.case(n)
            b = {r["rule_id"]: r for r in packet(c, "B")["rule_results"]}
            acquired = {r["rule_id"]: r for r in packet(c, "C1")["rule_results"]}
            self.assertEqual(b[rid]["status"], "uncertain")
            self.assertEqual(acquired[rid]["status"], "pass")
            self.assertGreaterEqual(len(acquired[rid]["sources"]), 2)

    def test_amendment_asset(self):
        c = self.case(5)
        r = packet(c, "C")
        self.assertEqual(
            next(x for x in r["rule_results"] if x["rule_id"] == "R2_CONFIDENTIALITY_TERM")["status"], "deviation"
        )
        self.assertEqual(len(r["superseded_passages"]), 1)
        self.assertEqual(check_packet(c, r), [])

    def test_conflicting_amendments_escalate(self):
        c = self.case(5)
        c["amendments"].append({"id": "A2", "text": c["amendments"][0]["text"].replace("60 months", "12 months")})
        self.assertTrue(all(r["status"] == "uncertain" for r in packet(c, "C")["rule_results"]))

    def test_conflicting_replacements_inside_one_amendment(self):
        c = self.case(5)
        c["amendments"][0]["text"] += (
            '\nSection 2 is replaced in its entirety with: "2. Confidentiality. Each Recipient must keep the Confidential Information confidential for 12 months after disclosure."'
        )
        self.assertTrue(all(r["status"] == "uncertain" for r in packet(c, "C")["rule_results"]))

    def test_unparsed_amendment_cannot_leave_false_pass(self):
        c = self.case(5)
        c["amendments"][0]["text"] += "\nIn addition, Section 7 is amended to require the governing law of New York."
        self.assertTrue(all(r["status"] == "uncertain" for r in packet(c, "C")["rule_results"]))

    def test_duplicate_rule_and_boolean_offset_refuse(self):
        c = self.case()
        r = packet(c, "C")
        r["rule_results"].append(copy.deepcopy(r["rule_results"][0]))
        self.assertIn("RULE_COMPLETENESS", check_packet(c, r))
        r = packet(c, "C")
        r["rule_results"][0]["sources"][0]["start"] = True
        self.assertIn("SOURCE_SPAN_MISMATCH", check_packet(c, r))

    def test_missing_reference_escalates(self):
        c = self.case(4)
        c["revised_text"] = c["revised_text"].replace("Section 9", "Section 99")
        r = packet(c, "C")
        self.assertEqual(
            next(x for x in r["rule_results"] if x["rule_id"] == "R3_RETURN_DEADLINE")["status"], "uncertain"
        )
        self.assertTrue(any(x["code"] == "UNRESOLVED_REFERENCE" for x in r["escalations"]))

    def test_historical_scope_cannot_authorize_new_playbook(self):
        c = self.case()
        c["playbook_version"] = "ONT-NDA-RESEARCH-2.0"
        r = packet(c, "C")
        self.assertFalse(r["supported_scope"])
        self.assertTrue(all(x["status"] == "out_of_scope" for x in r["rule_results"]))

    def test_non_synthetic_intake_refuses(self):
        c = self.case()
        c["source_class"] = "confidential-client"
        with self.assertRaisesRegex(ValueError, "SYNTHETIC"):
            packet(c, "C")

    def test_forged_quote_and_hash_refuse(self):
        c = self.case()
        r = packet(c, "C")
        damaged = copy.deepcopy(r)
        damaged["rule_results"][0]["sources"][0]["quote"] = "Not in the document"
        self.assertIn("SOURCE_SPAN_MISMATCH", check_packet(c, damaged))
        damaged = copy.deepcopy(r)
        damaged["source_hashes"]["revised"] = "0" * 64
        self.assertIn("SOURCE_HASH_MISMATCH", check_packet(c, damaged))

    def test_no_professional_acceptance_or_drafting(self):
        c = self.case()
        c["request"] += " Is this enforceable and should we sign?"
        r = packet(c, "C")
        self.assertEqual(r["professional_acceptance"], "unknown")
        self.assertEqual(r["proposed_revisions"], [])
        self.assertTrue(any(x["code"] == "REQUEST_OUT_OF_SCOPE" for x in r["escalations"]))


if __name__ == "__main__":
    unittest.main()
