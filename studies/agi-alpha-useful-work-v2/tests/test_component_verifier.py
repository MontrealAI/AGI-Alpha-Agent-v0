# SPDX-License-Identifier: Apache-2.0
"""Synthetic verifier controls only; no consumer/dependency execution or outcomes."""

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("independent_verifier", ROOT / "src/verify_component.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class VerifierControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="component-verifier-control-")
        self.addCleanup(self.tmp.cleanup)
        self.outdir = Path(self.tmp.name)
        self.contract_path = ROOT / "protocol/component-contract.json"
        contract_raw = self.contract_path.read_bytes()
        self.contract = json.loads(contract_raw)
        self.profile = next(
            p
            for p in json.loads((ROOT / "protocol/component-projections.json").read_text())["profiles"]
            if p["id"] == "native-fastapi-bridge-v2"
        )
        api_raw = (ROOT / "data/consumer/api.py").read_bytes()
        api = api_raw.decode()
        slices = []
        names = {
            "MAX_REQUEST_BYTES",
            "BODY_TIMEOUT_SECONDS",
            "SECURITY_HEADERS",
            "RequestBoundary",
            "Review",
            "Control",
        }
        for node in ast.parse(api).body:
            present = (
                {node.name}
                if isinstance(node, ast.ClassDef)
                else {t.id for t in node.targets if isinstance(t, ast.Name)}
                if isinstance(node, ast.Assign)
                else set()
            )
            if present & names:
                slices.append(
                    {
                        "names": sorted(present & names),
                        "start_line": node.lineno,
                        "end_line": node.end_lineno,
                        "sha256": sha(ast.get_source_segment(api, node).encode()),
                    }
                )
        rows = []
        for case in self.contract["cases"]:
            observed = copy.deepcopy(case["expected"])
            observed.pop("security_headers_required", None)
            observed.pop("materialized_nonfinite_tokens", None)
            if case["kind"] == "asgi":
                body = b"".join(
                    c["text"].encode() if "text" in c else bytes([c["byte"]]) * c["count"]
                    for c in case["input"]["chunks"]
                )
                observed.update(
                    {
                        "input_bytes": len(body),
                        "input_body_sha256": sha(body),
                        "response_starts": 1 if observed["response_present"] else 0,
                        "headers": [[k, v] for k, v in self.contract["security_headers"].items()]
                        if observed["response_present"]
                        else [],
                        "response_body_utf8": json.dumps({"error": observed["error"]})
                        if observed["error"]
                        else "{}"
                        if observed["response_present"]
                        else "",
                        "receive_calls": 0,
                    }
                )
            else:
                observed["materialized_nonfinite"] = [
                    {
                        **item,
                        "actual_type": "float",
                        "actual_repr": {"NaN": "nan", "Infinity": "inf", "-Infinity": "-inf"}[item["token"]],
                    }
                    for item in case["input"].get("nonfinite_overrides", [])
                ]
                if not observed["accepted"]:
                    observed.update(
                        {
                            "error_type": "ValidationError",
                            "errors": [
                                {"type": "synthetic_control_only", "loc": [], "msg": "Synthetic rejection capture"}
                            ],
                        }
                    )
            rows.append(
                {
                    "id": case["id"],
                    "kind": case["kind"],
                    "observation": observed,
                    "execution_error": None,
                    "wall_seconds": 15.01 if case["id"] == "asgi.actual-timeout" else 0.001,
                    "cpu_seconds": 0.0001,
                }
            )
        versions = {name: "synthetic-control-version" for name in self.profile["required_packages"]}
        self.environment = {
            "schema": "component-environment-preparation/v1",
            "complete": True,
            "error": None,
            "application_qualified": False,
            "consumer_executed": False,
            "fastapi_import_bridge": {
                "Request_identity": True,
                "Request_module": "starlette.requests",
                "Request_qualname": "Request",
                "JSONResponse_identity": True,
                "JSONResponse_module": "starlette.responses",
                "JSONResponse_qualname": "JSONResponse",
            },
            "installed_distributions": [{"name": n, "version": v} for n, v in versions.items()],
            "wheels": [{"name": n, "version": v, "sha256": "0" * 64} for n, v in versions.items()],
            "synthetic_control_only": True,
        }
        self.raw = {
            "schema": "manual-component-observations/v1",
            "contract_sha256": sha(contract_raw),
            "source_identity": {
                "api_sha256": sha(api_raw),
                "models_sha256": sha((ROOT / "data/consumer/models.py").read_bytes()),
                "api_slices": slices,
                "projection_imports_sha256": self.profile["imports_ast_sha256"],
                "projection_id": self.profile["id"],
                "original_timeout_seconds": 15.0,
                "original_byte_limit": 524288,
                "whole_api_imported": False,
                "create_app_called": False,
                "journal_created": False,
                "credentials_created": False,
            },
            "versions": versions,
            "observations": rows,
            "wall_seconds": 15.2,
            "cpu_seconds": 0.1,
            "runtime_model_calls": 0,
            "runtime_network_requests": 0,
            "money_usd": None,
            "synthetic_control_only": True,
        }

    def row(self, case_id):
        return next(row for row in self.raw["observations"] if row["id"] == case_id)

    def verify(self):
        observation_path, environment_path = self.outdir / "observations.json", self.outdir / "environment.json"
        observation_path.write_text(json.dumps(self.raw, allow_nan=False))
        environment_path.write_text(json.dumps(self.environment, allow_nan=False))
        return verifier.verify(
            self.contract_path, observation_path, ROOT / "data/consumer", environment_path, self.profile["id"]
        )

    def assert_refused(self):
        self.assertNotEqual(self.verify()["status"], "PRESERVED_WITHIN_COMPONENT_CONTRACT")

    def test_synthetic_complete_record_matches(self):
        result = self.verify()
        self.assertEqual(result["status"], "PRESERVED_WITHIN_COMPONENT_CONTRACT")
        self.assertEqual(result["counts"]["PASS"], 61)

    def test_missing_case_refused(self):
        self.raw["observations"].pop()
        self.assert_refused()

    def test_duplicate_case_refused(self):
        self.raw["observations"].append(copy.deepcopy(self.raw["observations"][0]))
        self.assert_refused()

    def test_extra_case_refused(self):
        row = copy.deepcopy(self.raw["observations"][0])
        row["id"] = "uncontracted"
        self.raw["observations"].append(row)
        self.assert_refused()

    def test_contract_identity_refused(self):
        self.raw["contract_sha256"] = "0" * 64
        self.assert_refused()

    def test_source_identity_refused(self):
        self.raw["source_identity"]["api_sha256"] = "0" * 64
        self.assert_refused()

    def test_projection_import_route_refused(self):
        self.raw["source_identity"]["projection_imports_sha256"] = "0" * 64
        self.assert_refused()

    def test_source_slice_identity_refused(self):
        self.raw["source_identity"]["api_slices"][0]["sha256"] = "0" * 64
        self.assert_refused()

    def test_environment_mismatch_refused(self):
        self.raw["versions"]["starlette"] = "different"
        self.assert_refused()

    def test_native_preparation_not_boolean_complete_refused(self):
        self.environment["complete"] = 1
        self.assert_refused()

    def test_native_preparation_wrong_schema_refused(self):
        self.environment["schema"] = "component-development-environment/v1"
        self.environment["status"] = "COMPLETE"
        self.assert_refused()

    def test_native_preparation_error_refused(self):
        self.environment["error"] = "Synthetic preparation failure"
        self.assert_refused()

    def test_native_bridge_identity_refused(self):
        self.environment["fastapi_import_bridge"]["Request_identity"] = False
        self.assert_refused()

    def test_native_installed_version_refused(self):
        self.environment["installed_distributions"][0]["version"] = "different"
        self.assert_refused()

    def test_environment_package_missing_refused(self):
        del self.raw["versions"]["fastapi"]
        self.environment["wheels"] = [w for w in self.environment["wheels"] if w["name"] != "fastapi"]
        self.assert_refused()

    def test_status_mismatch_refused(self):
        self.row("asgi.missing-length")["observation"]["status"] = 200
        self.assert_refused()

    def test_duplicate_security_header_refused(self):
        self.row("asgi.patch-valid")["observation"]["headers"].append(["Cache-Control", "no-store"])
        self.assert_refused()

    def test_body_corruption_refused(self):
        self.row("asgi.valid-fragmented-utf8")["observation"]["downstream_body_sha256"] = "0" * 64
        self.assert_refused()

    def test_disconnect_response_refused(self):
        self.row("asgi.disconnect")["observation"]["response_body_utf8"] = "{}"
        self.assert_refused()

    def test_boolean_integer_output_alias_refused(self):
        self.row("model.mission-allocation")["observation"]["output"]["work"]["budget"] = True
        self.assert_refused()

    def test_missing_output_field_refused(self):
        del self.row("model.mission-allocation")["observation"]["output"]["work"]["unit"]
        self.assert_refused()

    def test_nonfinite_string_materialization_refused(self):
        self.row("model.forecast-nan")["observation"]["materialized_nonfinite"][0]["actual_type"] = "str"
        self.assert_refused()

    def test_fast_timeout_refused(self):
        self.row("asgi.actual-timeout")["wall_seconds"] = 0.01
        self.assert_refused()

    def test_monkeypatched_timeout_refused(self):
        self.raw["source_identity"]["original_timeout_seconds"] = 0.01
        self.assert_refused()

    def test_exception_not_validation_refused(self):
        self.row("model.forecast-nan")["observation"]["error_type"] = "RuntimeError"
        self.assert_refused()

    def test_execution_failure_refused(self):
        self.row("model.mission-code")["execution_error"] = "Synthetic failure"
        self.assert_refused()

    def test_unknown_money_not_zeroed(self):
        self.raw["money_usd"] = 0
        self.assert_refused()

    def test_unknown_runtime_activity_refused(self):
        self.raw["runtime_network_requests"] = 1
        self.assert_refused()


if __name__ == "__main__":
    unittest.main(verbosity=2)
