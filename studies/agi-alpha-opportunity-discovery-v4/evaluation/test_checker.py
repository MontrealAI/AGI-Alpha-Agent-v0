# SPDX-License-Identifier: Apache-2.0
"""Adversarial checker tests using only Plate development evidence."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from checker import evaluate
from source_oracle import read_qif

ROOT = Path(__file__).resolve().parent
STUDY = ROOT.parent


class CheckerTests(unittest.TestCase):
    """Reject consequential incorrect reports, not merely malformed JSON."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads((ROOT / "development" / "plate_report_frozen.json").read_text())
        cls.request = STUDY / "data" / "development" / "request.json"
        cls.oracle = ROOT / "development" / "plate_oracle.json"

    def run_mutation(self, change: Callable[[dict[str, Any]], None] | None) -> dict[str, Any]:
        altered = copy.deepcopy(self.report)
        if change is not None:
            change(altered)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(altered))
            return evaluate(self.request, path, self.oracle)

    @staticmethod
    def diameter(report: dict[str, Any]) -> dict[str, Any]:
        return next(x for x in report["facts"]["source_qif"]["characteristics"] if x["kind"] == "Diameter")

    def rejected(self, mutate: Callable[[dict[str, Any]], None], category: str) -> None:
        result = self.run_mutation(mutate)
        self.assertFalse(result["accepted"])
        self.assertIn(category, result["failed_checks_by_category"])

    def test_complete_plate_report_passes(self) -> None:
        self.assertTrue(self.run_mutation(None)["accepted"])

    def test_silent_source_unit_repair_fails(self) -> None:
        self.rejected(
            lambda r: r["facts"]["source_qif"]["primary_linear_unit"].update(factor_to_metre="0.001"),
            "formal_units",
        )

    def test_changed_actual_literal_fails(self) -> None:
        self.rejected(lambda r: self.diameter(r)["actuals"][0].update(raw_value_literal="999"), "source_facts")

    def test_changed_exact_quantity_fails(self) -> None:
        self.rejected(lambda r: self.diameter(r)["actuals"][0]["value"].update(si="0.001"), "quantities")

    def test_omitted_actual_fails(self) -> None:
        self.rejected(lambda r: self.diameter(r)["actuals"].pop(), "completeness")

    def test_lost_result_status_fails(self) -> None:
        self.rejected(
            lambda r: r["facts"]["incoming_qif"]["measurement_results"][0].update(overall_status="PASS"),
            "status_ancestry",
        )

    def test_fabricated_source_reference_fails(self) -> None:
        self.rejected(lambda r: self.diameter(r)["refs"][0].update(line=1), "references")

    def test_false_universal_claim_fails(self) -> None:
        self.rejected(
            lambda r: r["family_proofs"][0].update(all_observed_values_satisfy_destination=True),
            "proof_soundness",
        )

    def test_counterexample_cannot_be_called_measured(self) -> None:
        self.rejected(
            lambda r: r["family_proofs"][0]["interval_counterexample"].update(observed_measurement=True),
            "proof_soundness",
        )

    def test_mission_permission_not_inherited(self) -> None:
        self.rejected(lambda r: r["mission_result"].update(physical_reuse_admitted=True), "guard_separation")

    def test_wrong_feature_trace_fails(self) -> None:
        self.rejected(lambda r: r["traces"][0].update(feature_item_id="999999"), "traces")

    def test_wrong_geometry_fails(self) -> None:
        self.rejected(lambda r: r["geometry"]["cylinders"][0].update(radius_mm=999.0), "geometry")

    def test_blanket_refusal_is_not_an_audit(self) -> None:
        self.rejected(lambda r: r.update(findings=[]), "usefulness")

    def test_missing_evidence_plan_fails(self) -> None:
        self.rejected(lambda r: r.update(repair_requests=[]), "usefulness")

    def test_changed_mission_fails(self) -> None:
        self.rejected(lambda r: r["mission"].update(purpose="physical_release"), "mission_identity")

    def test_unknown_complete_cost_cannot_be_filled(self) -> None:
        self.rejected(lambda r: r["execution"].update(development_and_evaluation_cost_included=True), "execution_scope")

    def test_changed_code_identity_fails(self) -> None:
        self.rejected(lambda r: r["identity"]["files"].update({"proofs.py": "0" * 64}), "instrument_identity")

    def test_parser_rejects_duplicate_ids(self) -> None:
        raw = b'<QIFDocument xmlns="http://qifstandards.org/xsd/qif2" versionQIF="2.1.0"><A id="1"/><B id="1"/></QIFDocument>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.qif"
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                read_qif(path)

    def test_parser_rejects_external_entities(self) -> None:
        raw = b'<!DOCTYPE QIFDocument [<!ENTITY x SYSTEM "file:///private">]><QIFDocument/>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "entity.qif"
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "DTD/entity"):
                read_qif(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
