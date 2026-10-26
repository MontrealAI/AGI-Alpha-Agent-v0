# SPDX-License-Identifier: Apache-2.0
"""Independent finite-contract verifier; never imports or executes the consumer.

This checks recorded observations, not the trustworthiness of a hostile recorder.
Run separately from the observer. A mismatch needs baseline evidence before it can
be attributed to a dependency regression. A pass grants no release authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import time
from pathlib import Path

FROZEN_CONTRACT_SHA256 = "89d9c776a7c9f32444b1e14479b9403e8beaaef81c0832f0237af027ddf41735"
FROZEN_PROFILES_SHA256 = "44fb41d04a7b67e867c95a5299a231564a411685e121db19d59c19de6c25a5a8"
PROJECTED_NAMES = {
    "MAX_REQUEST_BYTES",
    "BODY_TIMEOUT_SECONDS",
    "SECURITY_HEADERS",
    "RequestBoundary",
    "Review",
    "Control",
}
PROJECTION_IMPORTS = (
    "from __future__ import annotations\nimport asyncio\nfrom typing import Literal\n"
    "from pydantic import Field\nfrom starlette.requests import Request\n"
    "from starlette.responses import JSONResponse\n"
    "from starlette.types import ASGIApp, Message, Receive, Scope, Send\n"
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_equal(left, right):
    """JSON structural equality, preserving bool/int/float distinctions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(strict_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(strict_equal(a, b) for a, b in zip(left, right))
    return left == right


def finite_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def input_bytes(case):
    parts = []
    for entry in case["input"].get("chunks", []):
        if set(entry) == {"text"} and type(entry["text"]) is str:
            parts.append(entry["text"].encode("utf-8"))
        elif (
            set(entry) == {"byte", "count"}
            and type(entry["byte"]) is int
            and type(entry["count"]) is int
            and 0 <= entry["byte"] <= 255
            and 0 <= entry["count"] <= 524289
        ):
            parts.append(bytes([entry["byte"]]) * entry["count"])
        else:
            raise ValueError("Unsupported contract chunk")
    return b"".join(parts)


def verify_case(case, row, security_headers):
    errors, incomplete = [], []
    if row.get("kind") != case["kind"]:
        incomplete.append("case_kind_mismatch")
    if "execution_error" not in row or row["execution_error"] is not None:
        incomplete.append("execution_error_or_missing_execution_status")
    for field in ("wall_seconds", "cpu_seconds"):
        if not finite_nonnegative(row.get(field)):
            incomplete.append("invalid_" + field)
    observed = row.get("observation")
    if type(observed) is not dict:
        return {
            "id": case["id"],
            "status": "INCOMPLETE",
            "errors": errors,
            "incomplete": incomplete + ["missing_observation"],
        }
    expected = case["expected"]
    for key, value in expected.items():
        if key in {"security_headers_required", "materialized_nonfinite_tokens"}:
            continue
        if key not in observed:
            incomplete.append("missing_" + key)
        elif not strict_equal(observed[key], value):
            errors.append("expected_field_mismatch:" + key)
    if case["kind"] == "asgi":
        body = input_bytes(case)
        for key, value in {
            "input_bytes": len(body),
            "input_body_sha256": sha(body),
            "response_starts": 1 if expected["response_present"] else 0,
        }.items():
            if key not in observed:
                incomplete.append("missing_" + key)
            elif not strict_equal(observed[key], value):
                errors.append("evidence_mismatch:" + key)
        headers = observed.get("headers")
        if type(headers) is not list or any(
            type(h) is not list or len(h) != 2 or any(type(v) is not str for v in h) for h in headers
        ):
            incomplete.append("invalid_header_capture")
        elif expected["security_headers_required"]:
            for name, value in security_headers.items():
                values = [v for k, v in headers if k.lower() == name]
                if values != [value]:
                    errors.append("security_header_mismatch:" + name)
        elif headers:
            errors.append("headers_without_response")
        response = observed.get("response_body_utf8")
        if type(response) is not str:
            incomplete.append("missing_response_body_capture")
        elif not expected["response_present"] and response != "":
            errors.append("body_without_response")
        elif expected["error"] is not None:
            try:
                parsed = json.loads(response)
            except (ValueError, TypeError):
                parsed = None
            if not isinstance(parsed, dict) or parsed.get("error") != expected["error"]:
                errors.append("error_body_mismatch")
        if case["id"] == "asgi.actual-timeout":
            elapsed = row.get("wall_seconds")
            if not finite_nonnegative(elapsed) or elapsed < 14.999:
                errors.append("original_timeout_not_observed_1ms_clock_tolerance")
    else:
        materialized = observed.get("materialized_nonfinite")
        wanted = []
        for override in case["input"].get("nonfinite_overrides", []):
            wanted.append(
                {
                    **override,
                    "actual_type": "float",
                    "actual_repr": {"NaN": "nan", "Infinity": "inf", "-Infinity": "-inf"}[override["token"]],
                }
            )
        if materialized is None:
            incomplete.append("missing_nonfinite_materialization_capture")
        elif not strict_equal(materialized, wanted):
            errors.append("nonfinite_materialization_mismatch")
        if not expected["accepted"]:
            if observed.get("error_type") != "ValidationError":
                errors.append("rejection_is_not_validation_error")
            details = observed.get("errors")
            if type(details) is not list or not details or any(type(v) is not dict for v in details):
                incomplete.append("missing_validation_error_capture")
    status = "INCOMPLETE" if incomplete else "BEHAVIOR_MISMATCH" if errors else "PASS"
    return {"id": case["id"], "status": status, "errors": errors, "incomplete": incomplete}


def verify(contract_path, observation_path, consumer_dir, environment_path, projection_id):
    start, cpu = time.perf_counter(), time.process_time()
    contract_raw, observed_raw = contract_path.read_bytes(), observation_path.read_bytes()
    contract, raw = json.loads(contract_raw), json.loads(observed_raw)
    environment_raw = environment_path.read_bytes()
    environment = json.loads(environment_raw)
    incomplete = []
    if sha(contract_raw) != FROZEN_CONTRACT_SHA256:
        incomplete.append("contract_not_frozen_identity")
    if raw.get("contract_sha256") != sha(contract_raw):
        incomplete.append("recorded_contract_identity_mismatch")
    if raw.get("schema") != "manual-component-observations/v1":
        incomplete.append("unsupported_observation_schema")
    if contract.get("schema") != "useful-work-component-contract/v1":
        incomplete.append("unsupported_contract_schema")
    source = raw.get("source_identity", {})
    project_root = contract_path.resolve().parent.parent
    profiles_path = project_root / "protocol/component-projections.json"
    profiles_raw = profiles_path.read_bytes()
    if sha(profiles_raw) != FROZEN_PROFILES_SHA256:
        incomplete.append("projection_profiles_not_frozen_identity")
    profiles = json.loads(profiles_raw)["profiles"]
    selected = [item for item in profiles if item["id"] == projection_id]
    if len(selected) != 1:
        raise ValueError("Unknown or duplicate projection identity")
    profile = selected[0]
    for entry in contract["sources"]:
        path = (
            consumer_dir / Path(entry["path"]).name
            if entry["path"].startswith("data/consumer/")
            else project_root / entry["path"]
        )
        if not path.is_file() or len(path.read_bytes()) != entry["bytes"] or sha(path.read_bytes()) != entry["sha256"]:
            incomplete.append("local_source_identity_mismatch:" + entry["path"])
        if entry["path"].startswith("data/consumer/"):
            field = Path(entry["path"]).stem + "_sha256"
            if source.get(field) != entry["sha256"]:
                incomplete.append("recorded_source_identity_mismatch:" + field)
    api = (consumer_dir / "api.py").read_text()
    slices = []
    for node in ast.parse(api).body:
        names = (
            {node.name}
            if isinstance(node, ast.ClassDef)
            else {n.id for n in node.targets if isinstance(n, ast.Name)} if isinstance(node, ast.Assign) else set()
        )
        if names & PROJECTED_NAMES:
            slices.append(
                {
                    "names": sorted(names & PROJECTED_NAMES),
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "sha256": sha(ast.get_source_segment(api, node).encode()),
                }
            )
    if (
        not strict_equal(source.get("api_slices"), slices)
        or {n for row in slices for n in row["names"]} != PROJECTED_NAMES
    ):
        incomplete.append("projected_source_slice_mismatch")
    expected_imports = sha(ast.dump(ast.parse(profile["imports_source"])).encode())
    if expected_imports != profile["imports_ast_sha256"]:
        incomplete.append("projection_profile_internal_identity_mismatch")
    if source.get("projection_imports_sha256") != expected_imports:
        incomplete.append("projection_imports_mismatch")
    if profile["native_import_route"] and source.get("projection_id") != projection_id:
        incomplete.append("native_projection_identity_missing_or_mismatched")
    for field, expected in {
        "original_timeout_seconds": 15.0,
        "original_byte_limit": 524288,
        "whole_api_imported": False,
        "create_app_called": False,
        "journal_created": False,
        "credentials_created": False,
    }.items():
        if field not in source or not strict_equal(source[field], expected):
            incomplete.append("source_execution_scope_mismatch:" + field)
    if profile["native_import_route"]:
        if environment.get("schema") != "component-environment-preparation/v1":
            incomplete.append("native_environment_preparation_schema_required")
        if environment.get("complete") is not True or environment.get("error", "missing") is not None:
            incomplete.append("native_environment_preparation_incomplete")
        if environment.get("application_qualified") is not False or environment.get("consumer_executed") is not False:
            incomplete.append("native_environment_preparation_scope_mismatch")
        bridge = environment.get("fastapi_import_bridge", {})
        expected_bridge = {
            "Request_identity": True,
            "Request_module": "starlette.requests",
            "Request_qualname": "Request",
            "JSONResponse_identity": True,
            "JSONResponse_module": "starlette.responses",
            "JSONResponse_qualname": "JSONResponse",
        }
        if not strict_equal(bridge, expected_bridge):
            incomplete.append("native_environment_import_bridge_unverified")
    elif environment.get("schema") != "component-development-environment/v1" or environment.get("status") != "COMPLETE":
        incomplete.append("provisional_environment_acquisition_not_complete")
    wheels = environment.get("wheels", [])
    expected_versions = {w["name"]: w["version"] for w in wheels}
    if set(expected_versions) != set(profile["required_packages"]):
        incomplete.append("projection_environment_package_set_mismatch")
    if (
        not wheels
        or len(wheels) != len(expected_versions)
        or not all(type(w.get("sha256")) is str and len(w["sha256"]) == 64 for w in wheels)
    ):
        incomplete.append("environment_manifest_incomplete")
    if not strict_equal(raw.get("versions"), expected_versions):
        incomplete.append("package_version_identity_mismatch")
    if profile["native_import_route"]:
        installed_rows = environment.get("installed_distributions")
        if type(installed_rows) is not list or any(
            type(row) is not dict or type(row.get("name")) is not str or type(row.get("version")) is not str
            for row in installed_rows
        ):
            incomplete.append("native_installed_distribution_capture_missing")
        else:
            installed = {re.sub(r"[-_.]+", "-", row["name"]).lower(): row["version"] for row in installed_rows}
            selected_installed = {name: version for name, version in installed.items() if name != "pip"}
            if len(installed) != len(installed_rows) or not strict_equal(selected_installed, expected_versions):
                incomplete.append("native_installed_distribution_identity_mismatch")
    for field in ("wall_seconds", "cpu_seconds"):
        if not finite_nonnegative(raw.get(field)):
            incomplete.append("invalid_total_" + field)
    for field in ("runtime_model_calls", "runtime_network_requests"):
        if not strict_equal(raw.get(field), 0):
            incomplete.append("unaccounted_runtime_activity:" + field)
    if "money_usd" not in raw or raw["money_usd"] is not None:
        incomplete.append("unsupported_monetary_measurement")
    cases = contract["cases"]
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        incomplete.append("duplicate_contract_case")
    rows = raw.get("observations")
    if type(rows) is not list:
        rows = []
        incomplete.append("missing_observations")
    by_id = {}
    for row in rows:
        if type(row) is not dict or type(row.get("id")) is not str:
            incomplete.append("invalid_observation_row")
            continue
        if row["id"] in by_id:
            incomplete.append("duplicate_observation_case:" + row["id"])
        by_id[row["id"]] = row
    for extra in set(by_id) - set(ids):
        incomplete.append("unexpected_observation_case:" + extra)
    results = []
    for case in cases:
        if case["id"] not in by_id:
            results.append({"id": case["id"], "status": "INCOMPLETE", "errors": [], "incomplete": ["missing_case"]})
        else:
            results.append(verify_case(case, by_id[case["id"]], contract["security_headers"]))
    counts = {
        state: sum(row["status"] == state for row in results) for state in ("PASS", "BEHAVIOR_MISMATCH", "INCOMPLETE")
    }
    success = (
        "PRESERVED_WITHIN_COMPONENT_CONTRACT" if profile["native_import_route"] else "PROVISIONAL_PROJECTION_MATCH"
    )
    status = (
        "INCOMPLETE"
        if incomplete or counts["INCOMPLETE"]
        else "BEHAVIOR_MISMATCH" if counts["BEHAVIOR_MISMATCH"] else success
    )
    return {
        "schema": "independent-component-verification/v1",
        "status": status,
        "contract_sha256": sha(contract_raw),
        "observations_sha256": sha(observed_raw),
        "environment_manifest_sha256": sha(environment_raw),
        "environment_versions": expected_versions,
        "environment_manifest_schema": environment.get("schema"),
        "projection_id": projection_id,
        "projection_profiles_sha256": sha(profiles_raw),
        "native_import_route": profile["native_import_route"],
        "projection_scope": profile["scope"],
        "global_incomplete": incomplete,
        "counts": counts,
        "cases": results,
        "source_execution": False,
        "verifier_wall_seconds": time.perf_counter() - start,
        "verifier_cpu_seconds": time.process_time() - cpu,
        "money_usd": None,
        "authority": "Finite component evidence only; no full release, lock, authentication or operator approval.",
        "attribution": "A behavior mismatch requires baseline and reproduction before dependency-regression attribution.",
        "evidence_limit": "Checks recorded source/package identities and observations; does not independently attest installed binary bytes or a hostile recorder.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contract", "observations", "consumer", "environment", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument(
        "--projection", required=True, choices=["provisional-starlette-direct-v1", "native-fastapi-bridge-v2"]
    )
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("OUTPUT_EXISTS")
    result = verify(args.contract, args.observations, args.consumer, args.environment, args.projection)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "counts", "global_incomplete")}))
    raise SystemExit(
        0 if result["status"] in {"PRESERVED_WITHIN_COMPONENT_CONTRACT", "PROVISIONAL_PROJECTION_MATCH"} else 2
    )


if __name__ == "__main__":
    main()
