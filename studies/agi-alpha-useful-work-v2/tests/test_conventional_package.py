# SPDX-License-Identifier: Apache-2.0
"""Development-only custody controls on real conventional execution receipts."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("conventional_package", ROOT / "src/conventional_package.py")
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)
PAIR = ROOT / "results/development/conventional-pair-01"


class CustodyControls(unittest.TestCase):
    def setUp(self):
        self.receipt = PACKAGE.read(PAIR / "before-execution.json")
        self.inputs = [ROOT / "src/conventional_probe.py", ROOT / "protocol/component-contract.json"]
        self.output = PAIR / "before-observations.json"

    def check_receipt(self, receipt):
        return PACKAGE.receipt_check(receipt, self.inputs, self.output, {0, 1}, "test")

    def test_real_receipt_is_complete(self):
        self.assertEqual(self.check_receipt(self.receipt), [])

    def test_missing_output_binding_rejected(self):
        changed = copy.deepcopy(self.receipt)
        changed["output_identities"] = []
        self.assertIn("test:unbound_output", self.check_receipt(changed))

    def test_wrong_worker_hash_rejected(self):
        changed = copy.deepcopy(self.receipt)
        for field in ("input_identities_before", "input_identities_after"):
            for entry in changed[field]:
                if Path(entry["path"]).resolve() == self.inputs[0].resolve():
                    entry["sha256"] = "0" * 64
        self.assertIn("test:unbound_input:conventional_probe.py", self.check_receipt(changed))

    def test_timeout_cannot_accept_even_with_output(self):
        changed = copy.deepcopy(self.receipt)
        changed["timed_out"] = True
        self.assertIn("test:execution_receipt_incomplete", self.check_receipt(changed))

    def test_input_mutation_cannot_accept(self):
        changed = copy.deepcopy(self.receipt)
        changed["input_identities_after"] = []
        self.assertIn("test:execution_receipt_incomplete", self.check_receipt(changed))

    def test_launcher_error_cannot_accept(self):
        changed = copy.deepcopy(self.receipt)
        changed["launcher_error"] = "Synthetic control: launch failure"
        self.assertIn("test:execution_receipt_incomplete", self.check_receipt(changed))

    def test_verifier_negative_exit_retains_complete_custody(self):
        # This is a declared receipt-control fixture, not a fabricated real run.
        changed = PACKAGE.read(PAIR / "after-verification-execution.json")
        changed["exit_code"] = 2
        changed["complete_success"] = False
        checks = PACKAGE.receipt_check(changed, [ROOT / "src/verify_component.py"],
                                       PAIR / "after-verification.json", {0, 2}, "verifier-control")
        self.assertEqual(checks, [])

    def test_boolean_exit_is_not_an_integer_exit(self):
        changed = copy.deepcopy(self.receipt)
        changed["exit_code"] = False
        self.assertIn("test:execution_receipt_incomplete", self.check_receipt(changed))

    def test_complete_positive_package_and_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "package"
            result = PACKAGE.assemble(PACKAGE.read(PAIR / "job.json"), PAIR, out)
            self.assertEqual(result["decision"], "SCOPED_COMPONENT_PRESERVED")
            self.assertEqual(result["custody_errors"], [])
            manifest = PACKAGE.read(out / "artifact-manifest.json")
            for entry in manifest["files"]:
                path = out / entry["path"]
                self.assertEqual(PACKAGE.sha(path), entry["sha256"])
                self.assertEqual(path.stat().st_size, entry["bytes"])

    def test_missing_pair_produces_inspectable_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "package"
            result = PACKAGE.assemble(PACKAGE.read(PAIR / "job.json"), Path(folder) / "missing", out)
            self.assertEqual(result["decision"], "INCOMPLETE_HOLD")
            self.assertTrue(result["custody_errors"])
            self.assertTrue((out / "artifact-manifest.json").is_file())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            marker = out / "marker.txt"
            marker.write_text("preserve")
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                PACKAGE.assemble(PACKAGE.read(PAIR / "job.json"), PAIR, out)
            self.assertEqual(marker.read_text(), "preserve")


def main():
    global PAIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", type=Path, default=PAIR)
    args = parser.parse_args()
    PAIR = args.pair.resolve()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CustodyControls))
    print(json.dumps({"tests_run": result.testsRun, "errors": len(result.errors),
                      "failures": len(result.failures), "successful": result.wasSuccessful(),
                      "classification": "development validation controls, not customer jobs"}))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
