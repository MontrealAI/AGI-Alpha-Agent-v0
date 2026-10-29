# SPDX-License-Identifier: Apache-2.0
"""Verifier unit tests with explicit receipt doubles; NOT real Docker qualification."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import ModuleType

from scripts import validate_invention_sandbox as gate

IMAGE = "python@sha256:" + "a" * 64
REQUEST = {
    "requirements": {"voltage": "voltage"},
    "sources": [],
    "records": [
        {"id": "good", "fields": {"voltage": {"value": "10", "unit": "kV"}}},
        {"id": "bad", "fields": {"voltage": {"value": "10", "unit": "kVA"}}},
    ],
}


def receipt_double():
    return {
        "status": "EXECUTED_UNVERIFIED",
        "executed": True,
        "image": IMAGE,
        "artifact": {
            "outputs": [{"id": "good", "status": "CONSISTENT"}, {"id": "bad", "status": "ABSTAIN"}],
            "trace": [{"record": "good", "op": "emit"}, {"record": "bad", "op": "emit"}],
            "operations": 2,
        },
    }


class QualificationTests(unittest.TestCase):
    def test_independent_units_missing_and_unknown(self):
        for dimension, units in {
            "voltage": {"V", "kV"},
            "apparent_power": {"VA", "kVA", "MVA"},
            "frequency": {"Hz"},
        }.items():
            for unit in ["V", "kV", "VA", "kVA", "MVA", "Hz", "unknown", None]:
                with self.subTest(dimension=dimension, unit=unit):
                    request = {"requirements": {"x": dimension}, "records": [{"id": "x", "fields": {}}]}
                    if unit is not None:
                        request["records"][0]["fields"]["x"] = {"unit": unit}
                    status = "CONSISTENT" if unit in units else "ABSTAIN"
                    self.assertEqual(gate.expected_outputs(request), [{"id": "x", "status": status}])

    def test_receipt_double_matches_oracle(self):
        gate.verify_receipt(receipt_double(), gate.expected_outputs(REQUEST), IMAGE)

    def test_mutated_receipts_refused(self):
        mutations = [
            lambda r: r.update(status="BLOCKED"),
            lambda r: r.update(executed=False),
            lambda r: r.update(image="python:latest"),
            lambda r: r["artifact"].update(outputs=[]),
            lambda r: r["artifact"]["outputs"].reverse(),
            lambda r: r["artifact"]["outputs"].append({"id": "extra", "status": "CONSISTENT"}),
            lambda r: r["artifact"]["outputs"][1].update(status="CONSISTENT"),
            lambda r: r["artifact"]["outputs"][1].update(id="good"),
            lambda r: r["artifact"].update(operations=True),
            lambda r: r["artifact"].update(operations=16385),
            lambda r: r["artifact"].update(trace=[]),
            lambda r: r["artifact"]["trace"][0].update(op="exec"),
            lambda r: r["artifact"]["trace"][0].update(record="unknown"),
            lambda r: r["artifact"].update(extra="unexpected"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                receipt = receipt_double()
                mutate(receipt)
                with self.assertRaises(ValueError):
                    gate.verify_receipt(receipt, gate.expected_outputs(REQUEST), IMAGE)

    def test_vacuous_cohort_rejected(self):
        request = deepcopy(REQUEST)
        request["records"] = request["records"][:1]
        with self.assertRaisesRegex(ValueError, "both consistent and inconsistent"):
            gate.qualify(request, {}, {})

    def test_missing_docker_blocked_without_runtime_import(self):
        evidence = {}
        with patch.object(gate.shutil, "which", return_value=None):
            gate.qualify(REQUEST, {}, evidence)
        self.assertEqual(evidence["status"], "BLOCKED")
        self.assertNotIn("candidate_execution", evidence)
        self.assertEqual(evidence["program_sha256"], gate.digest({}))

    def test_mutable_image_blocked(self):
        evidence = {}
        with (
            patch.object(gate.shutil, "which", return_value="docker"),
            patch.dict(gate.os.environ, {"ALPHA_SANDBOX_IMAGE": "python:latest"}),
        ):
            gate.qualify(REQUEST, {}, evidence)
        self.assertEqual(evidence["status"], "BLOCKED")

    def test_cli_retains_blocked_nonzero_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, program, output = (root / name for name in ["request.json", "program.json", "result.json"])
            request.write_text(json.dumps(REQUEST))
            program.write_text("{}")
            args = [
                "gate",
                "--request",
                str(request),
                "--program",
                str(program),
                "--context",
                str(program),
                "--freeze",
                str(program),
                "--output",
                str(output),
            ]
            with patch("sys.argv", args), patch.object(gate.shutil, "which", return_value=None):
                self.assertEqual(gate.main(), 1)
                original = output.read_bytes()
                self.assertEqual(json.loads(original)["status"], "BLOCKED")
                with self.assertRaises(FileExistsError):
                    gate.main()
                self.assertEqual(output.read_bytes(), original)

    def test_orchestration_with_explicit_runner_doubles(self):
        module_name = "alpha_factory_v1.core.runtime.invention_automation"
        module = ModuleType(module_name)
        module.critic_loop = Mock()
        verifier_name = "contrib.invention_automation.qualify_verify"
        verifier = ModuleType(verifier_name)
        verifier.prove_program = Mock(return_value={"proof": "double"})
        request = deepcopy(REQUEST)
        request["budget"] = {"max_nodes": 128, "max_depth": 20}
        request["baseline"] = {"op": "emit", "status": "CONSISTENT"}
        candidate = receipt_double()
        candidate.update(program_hash=gate.digest({}), records_hash=gate.digest(request["records"]))
        negative = receipt_double()
        negative["artifact"]["outputs"][1]["status"] = "CONSISTENT"
        negative.update(program_hash=gate.digest(request["baseline"]), records_hash=gate.digest(request["records"]))
        flags = {
            key: True
            for key in (
                "freeze_verified",
                "source_freeze_verified",
                "candidate_write_denied_by_os",
                "new_socket_denied_by_os",
            )
        }
        admission = {**flags, "request_hash": gate.digest(request), "candidate_hash": gate.digest(request["baseline"])}
        acceptance = {
            **flags,
            "acceptance": "ACCEPTED",
            "candidate_executed": True,
            "request_hash": gate.digest(request),
            "program_hash": gate.digest({}),
            "execution_hash": gate.digest(candidate),
            "confirmation": False,
            "business_accepted": False,
        }
        cases = [
            (candidate, negative, acceptance, True),
            (candidate, {"status": "BLOCKED"}, acceptance, False),
            ({**candidate, "program_hash": "wrong"}, negative, acceptance, False),
            ({**candidate, "records_hash": "wrong"}, negative, acceptance, False),
            (candidate, negative, {**acceptance, "acceptance": "REJECTED"}, False),
            (candidate, negative, {**acceptance, "execution_hash": "wrong"}, False),
            (candidate, negative, {**acceptance, "new_socket_denied_by_os": False}, False),
        ]
        for index, (execution, control, final, passes) in enumerate(cases):
            with self.subTest(index=index):
                module.critic_loop.execute_bound.side_effect = [execution, control]
                module.critic_loop.verify_role.side_effect = [admission, final]
                evidence = {"status": "FAILED"}
                with (
                    patch.dict("sys.modules", {module_name: module, verifier_name: verifier}),
                    patch.object(gate.shutil, "which", return_value="docker"),
                    patch.dict(gate.os.environ, {"ALPHA_SANDBOX_IMAGE": IMAGE}),
                    patch.object(Path, "read_bytes", return_value=b"source double"),
                ):
                    if not passes:
                        with self.assertRaises(ValueError):
                            gate.qualify(request, {}, evidence, context={}, freeze={})
                    else:
                        gate.qualify(request, {}, evidence, context={}, freeze={})
                self.assertEqual(evidence["status"], "DYNAMIC_COMPONENT_PASS" if passes else "FAILED")
                self.assertEqual(evidence["candidate_execution"], execution)
                self.assertIn("implementation_sha256", evidence)

    def test_unicode_hash_matches_frozen_contract_encoding(self):
        import hashlib

        value = {"text": "é"}
        expected = hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(gate.digest(value), expected)

    def test_duplicate_record_ids_refused(self):
        request = deepcopy(REQUEST)
        request["records"][1]["id"] = "good"
        with self.assertRaises(ValueError):
            gate.expected_outputs(request)


if __name__ == "__main__":
    unittest.main()
