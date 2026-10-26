# SPDX-License-Identifier: Apache-2.0
"""Reusable ordinary unittest execution of the shared component contract.

Only the pinned pure definitions and their declared dependency imports execute.
This worker does not import the proposed producer or the independent verifier.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import base64
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import sys
import time
import traceback
import types
import unittest


NAMES = {
    "MAX_REQUEST_BYTES", "BODY_TIMEOUT_SECONDS", "SECURITY_HEADERS",
    "RequestBoundary", "Review", "Control",
}
PROFILE = "native-fastapi-bridge-v2"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def wire(value):
    """Lossless JSON representation of the small recorded ASGI messages."""
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (tuple, list)):
        return [wire(x) for x in value]
    if isinstance(value, dict):
        return {k: wire(v) for k, v in value.items()}
    return value


def load_source(consumer, contract, profile):
    """Independent source projection; preserve the original selected AST nodes."""
    captured = {}
    for filename in ("api.py", "models.py"):
        path = consumer / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError("SOURCE_NOT_REGULAR:" + filename)
        raw = path.read_bytes()
        wanted = [s for s in contract["sources"] if s["path"] == "data/consumer/" + filename]
        if len(wanted) != 1 or digest(raw) != wanted[0]["sha256"] or len(raw) != wanted[0]["bytes"]:
            raise ValueError("SOURCE_IDENTITY:" + filename)
        captured[filename] = raw
    models = types.ModuleType("conventional_alpha_models")
    models.__file__ = str(consumer / "models.py")
    sys.modules[models.__name__] = models
    exec(compile(captured["models.py"], models.__file__, "exec"), models.__dict__)

    source = captured["api.py"].decode("utf-8")
    nodes, slices, found = [], [], []
    for node in ast.parse(source).body:
        assigned = ({node.name} if isinstance(node, ast.ClassDef) else
                    {x.id for x in node.targets if isinstance(x, ast.Name)}
                    if isinstance(node, ast.Assign) else set())
        selected = assigned & NAMES
        if selected:
            if assigned != selected:
                raise ValueError("PROJECTION_EXTRA_ASSIGNMENT")
            found.extend(selected)
            nodes.append(node)
            slices.append({"names": sorted(selected), "start_line": node.lineno,
                           "end_line": node.end_lineno,
                           "sha256": digest(ast.get_source_segment(source, node).encode())})
    if set(found) != NAMES or len(found) != len(NAMES):
        raise ValueError("PROJECTION_MISSING_OR_DUPLICATE")
    imports = ast.parse(profile["imports_source"])
    imports_hash = digest(ast.dump(imports).encode())
    if imports_hash != profile["imports_ast_sha256"] or profile["id"] != PROFILE:
        raise ValueError("PROJECTION_IMPORT_IDENTITY")
    boundary = types.ModuleType("conventional_alpha_boundary")
    boundary.__file__ = str(consumer / "api.py")
    boundary.StrictModel = models.StrictModel
    sys.modules[boundary.__name__] = boundary
    module = ast.Module(body=imports.body + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), boundary.__file__, "exec"), boundary.__dict__)
    identity = {
        "projection_id": PROFILE, "api_sha256": digest(captured["api.py"]),
        "models_sha256": digest(captured["models.py"]), "api_slices": slices,
        "projection_imports_sha256": imports_hash,
        "original_timeout_seconds": boundary.BODY_TIMEOUT_SECONDS,
        "original_byte_limit": boundary.MAX_REQUEST_BYTES,
        "whole_api_imported": False, "create_app_called": False,
        "journal_created": False, "credentials_created": False,
    }
    return boundary, models, identity


def fixture_chunks(case, contract):
    result = []
    for part in case["input"].get("chunks", []):
        if set(part) == {"text"} and type(part["text"]) is str:
            result.append(part["text"].encode(contract["asgi_defaults"]["text_chunk_encoding"]))
        elif (set(part) == {"byte", "count"} and type(part["byte"]) is int
              and type(part["count"]) is int and 0 <= part["byte"] <= 255
              and 0 <= part["count"] <= contract["asgi_defaults"]["chunk_byte_count_max"]):
            result.append(bytes([part["byte"]]) * part["count"])
        else:
            raise ValueError("INVALID_CHUNK_FIXTURE")
    return result


async def asgi_observation(case, boundary, contract):
    definition, defaults = case["input"], contract["asgi_defaults"]
    parts = fixture_chunks(case, contract)
    headers = [(k.lower().encode("latin1"), v.encode("latin1")) for k, v in definition.get("headers", [])]
    if not any(k == b"host" for k, _ in headers):
        headers.append(tuple(x.encode("latin1") for x in defaults["default_host_header"]))
    scope = {k: copy.deepcopy(defaults[k]) for k in
             ("type", "asgi", "http_version", "scheme", "root_path", "path")}
    scope.update(method=definition.get("method", "POST"), headers=headers,
                 raw_path=defaults["raw_path"].encode(), query_string=defaults["query_string"].encode(),
                 server=tuple(defaults["server"]), client=tuple(defaults["client"]))
    cursor, calls = 0, 0
    forwarded = bytearray()
    sent, incoming, downstream_events = [], [], []

    async def receive():
        nonlocal cursor
        await asyncio.sleep(definition.get("receive_delay_seconds", 0))
        if cursor == len(parts):
            event = {"type": "http.disconnect"}
        else:
            body = parts[cursor]
            cursor += 1
            event = {"type": "http.request", "body": body,
                     "more_body": cursor < len(parts) or definition.get("disconnect", False)}
        incoming.append(copy.deepcopy(event))
        return event

    async def send(event):
        sent.append(copy.deepcopy(event))

    async def downstream(_scope, read, write):
        nonlocal calls
        calls += 1
        while True:
            event = await read()
            downstream_events.append(copy.deepcopy(event))
            if event["type"] == "http.disconnect":
                return
            forwarded.extend(event.get("body", b""))
            if not event.get("more_body", False):
                break
        await write({"type": "http.response.start", "status": contract["downstream_contract"]["response_status"],
                     "headers": [(b"content-type", b"application/json"),
                                 *[(k.encode("latin1"), v.encode("latin1"))
                                   for k, v in contract["downstream_contract"]["response_headers"]]]})
        await write({"type": "http.response.body", "body": b'{"component":"accepted"}', "more_body": False})

    await boundary.RequestBoundary(downstream)(scope, receive, send)
    starts = [e for e in sent if e["type"] == "http.response.start"]
    response = b"".join(e.get("body", b"") for e in sent if e["type"] == "http.response.body")
    parsed = json.loads(response) if response else None
    supplied = b"".join(parts)
    return {
        "response_present": bool(starts), "status": starts[0]["status"] if starts else None,
        "response_starts": len(starts),
        "headers": [[k.decode("latin1"), v.decode("latin1")] for k, v in starts[0].get("headers", [])] if starts else [],
        "response_body_utf8": response.decode("utf-8"),
        "error": parsed.get("error") if isinstance(parsed, dict) else None,
        "downstream_invocations": calls, "input_bytes": len(supplied),
        "input_body_sha256": digest(supplied), "downstream_body_bytes": len(forwarded) if calls else None,
        "downstream_body_sha256": digest(forwarded) if calls else None,
        "body_preserved": bytes(forwarded) == supplied if calls == 1 else None,
        "receive_calls": cursor, "raw_asgi": {"incoming": wire(incoming), "outgoing": wire(sent),
                                                "downstream_received": wire(downstream_events)},
    }


def model_observation(case, boundary, models):
    from pydantic import ValidationError

    item = case["input"]
    value = copy.deepcopy(item["value"])
    materialized = []
    for change in item.get("nonfinite_overrides", []):
        owner = value
        for element in change["path"][:-1]:
            owner = owner[element]
        number = {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": -float("inf")}[change["token"]]
        owner[change["path"][-1]] = number
        materialized.append({**change, "actual_type": "float", "actual_repr": repr(number)})
    model = getattr(boundary if item["model"] in {"Review", "Control"} else models, item["model"])
    if item["model"] not in {"Mission", "Review", "Control"}:
        raise ValueError("UNSUPPORTED_MODEL")
    try:
        if item["method"] == "model_validate":
            accepted = model.model_validate(value)
        elif item["method"] == "model_validate_json":
            accepted = model.model_validate_json(json.dumps(value, allow_nan=False))
        else:
            raise ValueError("UNSUPPORTED_VALIDATION_METHOD")
    except ValidationError as exc:
        return {"accepted": False, "error_type": "ValidationError",
                "errors": [{"type": e["type"], "loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
                "materialized_nonfinite": materialized}
    return {"accepted": True, "output": accepted.model_dump(mode="json"),
            "materialized_nonfinite": materialized}


class ContractCase(unittest.TestCase):
    def __init__(self, case, boundary, models, contract, observations):
        super().__init__("runTest")
        self.definition, self.boundary, self.models = case, boundary, models
        self.contract, self.observations = contract, observations
        self.record = None

    def id(self):
        return self.definition["id"]

    def shortDescription(self):
        return self.id()

    def runTest(self):
        case = self.definition
        started, cpu = time.perf_counter(), time.process_time()
        row = {"id": case["id"], "kind": case["kind"], "observation": None, "execution_error": None}
        self.record = row
        try:
            try:
                if case["kind"] == "asgi":
                    row["observation"] = asyncio.run(asgi_observation(case, self.boundary, self.contract))
                elif case["kind"] == "model":
                    row["observation"] = model_observation(case, self.boundary, self.models)
                else:
                    raise ValueError("UNSUPPORTED_CASE_KIND")
            except Exception as exc:
                row["execution_error"] = f"{type(exc).__name__}: {exc}"
                row["traceback"] = traceback.format_exc()
                raise
            obs = row["observation"]
            for key, expected in case["expected"].items():
                if key not in {"security_headers_required", "materialized_nonfinite_tokens"}:
                    self.assertTrue(key in obs and exact(obs[key], expected), "expected field: " + key)
            if case["kind"] == "asgi":
                self.assertEqual(obs["response_starts"], int(case["expected"]["response_present"]))
                if case["expected"]["security_headers_required"]:
                    for name, expected in self.contract["security_headers"].items():
                        self.assertEqual([v for k, v in obs["headers"] if k.lower() == name], [expected])
                if case["id"] == "asgi.actual-timeout":
                    self.assertGreaterEqual(time.perf_counter() - started, 14.999)
            else:
                wanted = [{**v, "actual_type": "float", "actual_repr":
                           {"NaN": "nan", "Infinity": "inf", "-Infinity": "-inf"}[v["token"]]}
                          for v in case["input"].get("nonfinite_overrides", [])]
                self.assertTrue(exact(obs["materialized_nonfinite"], wanted))
                if not case["expected"]["accepted"]:
                    self.assertEqual(obs["error_type"], "ValidationError")
                    self.assertTrue(obs["errors"])
        finally:
            row["wall_seconds"] = time.perf_counter() - started
            row["cpu_seconds"] = time.process_time() - cpu
            self.observations.append(row)


class RecordedResult(unittest.TextTestResult):
    def addSuccess(self, test):
        test.record["unittest_outcome"] = "PASS"
        super().addSuccess(test)

    def addFailure(self, test, error):
        test.record["unittest_outcome"] = "FAIL"
        test.record["assertion_failure"] = self._exc_info_to_string(error, test)
        super().addFailure(test, error)

    def addError(self, test, error):
        if test.record is not None:
            test.record["unittest_outcome"] = "ERROR"
        super().addError(test, error)


def run(consumer, contract_path, lock_path=None):
    started, cpu = time.perf_counter(), time.process_time()
    worker_hash = digest(Path(__file__).read_bytes())
    contract_raw = contract_path.read_bytes()
    contract = json.loads(contract_raw)
    ids = [case["id"] for case in contract["cases"]]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("CASE_INVENTORY")
    profiles_path = contract_path.resolve().parents[1] / "protocol/component-projections.json"
    profiles = json.loads(profiles_path.read_text())["profiles"]
    selected = [p for p in profiles if p["id"] == PROFILE]
    if len(selected) != 1:
        raise ValueError("PROJECTION_PROFILE")
    profile = selected[0]
    versions = {name: importlib.metadata.version(name) for name in profile["required_packages"]}
    lock_hash = None
    if lock_path is not None:
        lock_raw = lock_path.read_bytes()
        lock_hash = digest(lock_raw)
        pins = dict(re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^\s]+)", lock_raw.decode()))
        if pins != versions:
            raise ValueError("ENVIRONMENT_LOCK_VERSION_MISMATCH")
    boundary, models, identity = load_source(consumer, contract, profile)
    rows = []
    suite = unittest.TestSuite(ContractCase(c, boundary, models, contract, rows) for c in contract["cases"])
    results = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=RecordedResult).run(suite)
    record = {
        "schema": "manual-component-observations/v1", "producer": "independent-stdlib-unittest",
        "source_identity": identity, "contract_sha256": digest(contract_raw), "versions": versions,
        "observations": rows, "wall_seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu, "runtime_model_calls": 0,
        "runtime_network_requests": 0, "money_usd": None,
        "scope": "Original pure component definitions and FastAPI import bridge; no whole-application or release qualification",
        "execution_identity": {"worker_sha256_before": worker_hash, "worker_sha256_after": digest(Path(__file__).read_bytes()),
                               "lock_sha256": lock_hash, "python": platform.python_version(),
                               "implementation": platform.python_implementation(), "executable": sys.executable,
                               "platform": platform.platform(), "projection_profiles_sha256": digest(profiles_path.read_bytes())},
        "unittest": {"tests_run": results.testsRun, "failures": len(results.failures),
                     "errors": len(results.errors), "skipped": len(results.skipped), "successful": results.wasSuccessful()},
        "cache": {"reusable_suite": True, "environment_reuse": "Controlled and charged by the shared launcher",
                  "observation_cache_used": False},
    }
    return record, results.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("OUTPUT_EXISTS")
    try:
        record, passed = run(args.consumer, args.contract, args.lock)
    except Exception as exc:
        record = {"schema": "conventional-worker-refusal/v1", "error": f"{type(exc).__name__}: {exc}",
                  "traceback": traceback.format_exc(), "money_usd": None}
        passed = False
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"out": str(args.out), "successful": passed,
                      "cases": len(record.get("observations", [])), "producer": record.get("producer")}))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
