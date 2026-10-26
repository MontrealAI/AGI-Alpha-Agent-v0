# SPDX-License-Identifier: Apache-2.0
"""Small development setup check; no fresh mission or probe execution."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manual_parameterization", ROOT / "curation/assemble_manual_mission.py")
MANUAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANUAL)
PAIR = ROOT / "results/development/native-retained-02/delivery/pair"


class ManualSetup(unittest.TestCase):
    def test_supported_explicit_disposition_and_bilingual_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "package"
            decision = MANUAL.assemble(MANUAL.read(PAIR / "job.json"), PAIR, out, "SCOPED_COMPONENT_PRESERVED")
            self.assertEqual(decision["custody_errors"], [])
            self.assertTrue(decision["manual_disposition"]["checked_against_verifier_evidence"])
            self.assertTrue((out / "README.md").is_file())
            self.assertTrue((out / "README.fr.md").is_file())
            results = MANUAL.read(out / "requirement-results.json")
            for side in ("before", "after"):
                expected = sum(case["status"] == "PASS" for case in results[side])
                self.assertEqual(decision["coverage"][side]["PASS"], expected)
            for row in MANUAL.read(out / "artifact-manifest.json")["files"]:
                self.assertEqual(MANUAL.digest(out / row["path"]), row["sha256"])

    def test_unsupported_operator_disposition_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "rejected"
            with self.assertRaisesRegex(ValueError, "MANUAL_DISPOSITION_UNSUPPORTED"):
                MANUAL.assemble(MANUAL.read(PAIR / "job.json"), PAIR, out, "COMPONENT_REGRESSION")
            self.assertFalse(out.exists())

    def test_existing_packet_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            marker = out / "preserve.txt"
            marker.write_text("original")
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                MANUAL.assemble(MANUAL.read(PAIR / "job.json"), PAIR, out, "SCOPED_COMPONENT_PRESERVED")
            self.assertEqual(marker.read_text(), "original")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ManualSetup))
    print(json.dumps({"tests_run": result.testsRun, "successful": result.wasSuccessful(),
                      "classification": "exposed-development setup controls, not customer jobs"}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
