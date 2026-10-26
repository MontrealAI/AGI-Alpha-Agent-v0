# SPDX-License-Identifier: Apache-2.0
"""Development checks for independent source and change preservation."""

import unittest

from conventional import paragraphs, redline, reference_report, text_evidence


class ConventionalEvidenceTests(unittest.TestCase):
    def test_repeated_tokens_keep_exact_source_evidence(self) -> None:
        old = "The Recipient shall return records. The Recipient shall return copies."
        new = "The Recipient shall delete records. The Recipient shall return copies."
        changes = redline(old, new)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["before"]["quote"], "return")
        self.assertEqual(changes[0]["after"]["quote"], "delete")
        for c in changes:
            for field, text in (("before", old), ("after", new)):
                r = c[field]
                self.assertEqual(text[r["start"] : r["end"]], r["quote"])

    def test_insertions_and_deletions_have_valid_empty_spans(self) -> None:
        for old, new in (("", "The Receiver must return copies."), ("The Receiver must return copies.", "")):
            row = redline(old, new)[0]
            for field, text in (("before", old), ("after", new)):
                ref = row[field]
                self.assertEqual(text[ref["start"] : ref["end"]], ref["quote"])

    def test_reference_ambiguity_is_not_resolved_by_first_hit(self) -> None:
        text = "1. Duties survive under section 7.\n7. Duties expire in two years.\n7. Duties never expire."
        report = reference_report(paragraphs("revised", text))
        self.assertEqual(report[0]["status"], "ambiguous")
        self.assertEqual(len(report[0]["targets"]), 2)

    def test_missing_reference_is_explicit(self) -> None:
        text = "1. Recipient must comply with section 99.\n2. Ontario law governs."
        report = reference_report(paragraphs("revised", text))
        self.assertEqual(report[0]["status"], "missing")

    def test_professional_acceptance_is_never_inferred(self) -> None:
        packet = text_evidence(
            {"case_id": "development-only", "original_text": "", "revised_text": "1. A recipient must protect records."}
        )
        self.assertEqual(packet["professional_acceptance"], "unknown")
        self.assertEqual(len(packet["obligations"]), 1)


if __name__ == "__main__":
    unittest.main()
