# SPDX-License-Identifier: Apache-2.0
"""Plate-only development checks for concrete semantic and mission risks."""

from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

from lxml import etree

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY))

from instrument.audit import audit
from instrument.proofs import prove_family
from instrument.qif_reader import EvidenceError, NS, QIF, decimal


class CoreDevelopment(unittest.TestCase):
    """Checks are development, not independent protected confirmation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = STUDY / "data/development"
        cls.request = json.loads((cls.data / "request.json").read_text())
        cls.policy = json.loads((STUDY / "instrument/policy.json").read_text())
        cls.source = QIF(cls.data / "inputs/Plate_FAIR.qif", "source_qif")
        cls.incoming = QIF(cls.data / "inputs/Plate_incoming.qif", "incoming_qif")
        cls.cf = QIF(cls.data / "inputs/Plate_FAIR.qif", "source_qif", {"name": "mm", "factor_to_metre": "0.001"})
        cls.report = audit(cls.request, cls.data)

    def test_exact_formal_default_is_meter(self) -> None:
        self.assertEqual(self.source.primary["basis"], "QIF_2.1_SI_default")
        self.assertEqual(decimal(self.source.characteristics["71"]["target"]["si"]), decimal("3"))
        self.assertEqual(decimal(self.incoming.characteristics["101"]["target"]["si"]), decimal("0.003"))

    def test_counterfactual_is_separate_and_unadmitted(self) -> None:
        formal, hypothetical = self.report["family_proofs"]
        self.assertFalse(formal["all_observed_values_satisfy_destination"])
        self.assertTrue(hypothetical["all_source_intervals_subset"])
        self.assertTrue(hypothetical["family_all_recorded_values_pass"])
        self.assertEqual(hypothetical["permutation_count"], 6)
        self.assertFalse(hypothetical["physical_reuse_admitted"])
        self.assertEqual(self.source.sha256, self.cf.sha256)
        self.assertFalse(self.report["facts"]["source_qif"]["counterfactual"])

    def test_a_failing_actual_cannot_be_saved_by_interval_implication(self) -> None:
        altered = QIF(self.data / "inputs/Plate_FAIR.qif", "source_qif", {"name": "mm", "factor_to_metre": "0.001"})
        altered.characteristics["71"]["actuals"][0]["value"]["si"] = "0.01"
        proof = prove_family(altered, self.incoming, ["71", "89", "92"], "101", {}, self.policy)
        self.assertTrue(proof["all_source_intervals_subset"])
        self.assertTrue(proof["permutation_invariance_proved"])
        self.assertFalse(proof["family_all_recorded_values_pass"])
        self.assertIsNotNone(proof["observed_numeric_counterexample"])

    def test_actual_geometry_and_complete_trace(self) -> None:
        geometry = self.report["geometry"]
        self.assertEqual(geometry["status"], "executed")
        self.assertEqual(geometry["faces"], 261)
        self.assertEqual(len(geometry["correspondences"]), 18)
        self.assertTrue(all(x["candidates"] for x in geometry["correspondences"]))
        trace = next(x for x in self.report["traces"] if x["actual_id"] == "102")
        self.assertEqual(trace["feature_item_id"], "97")
        self.assertEqual(trace["geometry"]["candidates"][0]["face_index"], 93)
        self.assertTrue(trace["numeric_interval_satisfied"])
        self.assertEqual(trace["measurement_result"]["overall_status"], "FAIL")
        self.assertFalse(trace["physical_release"])

    def test_literal_sign_and_label_scale_counterexample(self) -> None:
        self.assertEqual(self.incoming.characteristics["29"]["tolerance_value_literal"], "-0.13")
        conflicts = [x for x in self.report["findings"] if x["kind"] == "incompatible_uniform_label_scale"]
        self.assertEqual(len(conflicts), 1)
        scales = {x["required_uniform_scale"] for x in conflicts[0]["details"]["pairs"]}
        self.assertIn("0.45", scales)
        self.assertIn("1", scales)

    def test_changed_purpose_never_uses_a_weaker_family_answer(self) -> None:
        for purpose, expected in [("feature_localization", "blocked"), ("physical_release", "unsupported")]:
            request = deepcopy(self.request)
            request["assets"].pop("cad_step")
            request["assets"].pop("reference_owl")
            request["mission"]["purpose"] = purpose
            request["guards"] = {key: "externally_evidenced" for key in request["guards"]}
            report = audit(request, self.data)
            self.assertEqual(report["mission"]["purpose"], purpose)
            self.assertEqual(report["mission_result"]["status"], expected)
            self.assertFalse(report["mission_result"]["physical_reuse_admitted"])
            self.assertFalse(report["family_proofs"][1]["guard_evidence_authenticated"])

    def test_source_digest_change_and_unknown_purpose_fail_closed(self) -> None:
        request = deepcopy(self.request)
        request["assets"]["source_qif"]["sha256"] = "0" * 64
        with self.assertRaises(EvidenceError):
            audit(request, self.data)
        request = deepcopy(self.request)
        request["mission"]["purpose"] = "machine_rework"
        with self.assertRaises(EvidenceError):
            audit(request, self.data)

    def test_unsupported_distance_predicate_not_coerced_to_diameter(self) -> None:
        proof = prove_family(self.cf, self.incoming, ["116"], "177", {}, self.policy)
        self.assertEqual(proof["status"], "unsupported_predicate")
        self.assertFalse(proof["physical_reuse_admitted"])

    def test_record_only_purpose_does_not_need_a_feature_bijection(self) -> None:
        request = deepcopy(self.request)
        request["assets"].pop("cad_step")
        request["assets"].pop("reference_owl")
        request["family"]["source_characteristic_ids"] = ["71", "89"]
        request["mission"]["purpose"] = "recorded_values_all"
        report = audit(request, self.data)
        self.assertEqual(report["mission_result"]["status"], "conditional")
        self.assertTrue(report["family_proofs"][1]["all_observed_values_satisfy_destination"])
        self.assertFalse(report["family_proofs"][1]["family_cardinality_consistent"])
        self.assertNotIn("feature_set_identity", [r["id"] for r in report["repair_requests"]])
        request["mission"]["purpose"] = "family_all"
        report = audit(request, self.data)
        self.assertEqual(report["mission_result"]["status"], "blocked")

    def test_version_and_missing_id_fail_closed(self) -> None:
        data = (self.data / "inputs/Plate_incoming.qif").read_bytes()
        for raw in [
            data.replace(b'versionQIF="2.1.0"', b'versionQIF="3.0.0"'),
            data.replace(
                b"<CharacteristicNominalId>100</CharacteristicNominalId>",
                b"<CharacteristicNominalId>999999</CharacteristicNominalId>",
            ),
        ]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "derived.qif"
                path.write_bytes(raw)
                with self.assertRaises(EvidenceError):
                    QIF(path, "derived_source")

    def test_explicit_per_value_unit_is_not_washed_out_by_repair(self) -> None:
        tree = etree.parse(str(self.data / "inputs/Plate_incoming.qif"))
        target = tree.find(".//q:DiameterCharacteristicNominal[@id='100']/q:TargetValue", NS)
        target.set("linearUnit", "mm")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "derived.qif"
            tree.write(str(path), encoding="utf-8", xml_declaration=True)
            document = QIF(path, "derived_source", {"name": "meter", "factor_to_metre": "1"})
            self.assertEqual(decimal(document.characteristics["101"]["target"]["si"]), decimal("0.003"))


if __name__ == "__main__":
    unittest.main()
