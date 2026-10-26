# SPDX-License-Identifier: Apache-2.0
"""Import the writer's sealed component decision and recheck inert observations."""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def fixed_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("fixed component verifier unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = fixed_module("upgrade_component_core", HERE / "core.py")
verifier = fixed_module("upgrade_component_verifier", HERE / "vendor/verify_component.py")
VERIFIER_ORIGINAL_SHA256 = "fc002f8b13429585e97bc2c1216a4c666ca162dfeb9b509d10da34298b9950be"
SCHEMA = "alpha-component-delivery-input/v1"


def read_json(files: dict[str, Any], name: str) -> dict[str, Any]:
    return core.load(files[name]["text"].encode())  # type: ignore[no-any-return]


def verifier_ast(raw: bytes) -> str:
    tree = ast.parse(raw)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    other = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    tree.body = sorted(imports, key=ast.dump) + other
    return ast.dump(tree)


def validate(pack: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    core.exact(pack, {"schema", "id", "title", "files"})
    if pack["schema"] != SCHEMA or not isinstance(pack["id"], str) or not core.IDENT.fullmatch(pack["id"]):
        raise ValueError("unsupported component packet")
    if (
        not isinstance(pack["title"], str)
        or not 1 <= len(pack["title"]) <= 200
        or any(ord(c) < 32 for c in pack["title"])
    ):
        raise ValueError("invalid component packet title")
    files = pack["files"]
    if not isinstance(files, dict) or not 8 <= len(files) <= 64:
        raise ValueError("component packet requires its complete bounded text evidence")
    total = 0
    for name, item in files.items():
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)
            or any(s in {"", ".", ".."} for s in name.split("/"))
        ):
            raise ValueError("unsupported component evidence path")
        core.exact(item, {"sha256", "text"})
        if not isinstance(item["text"], str):
            raise TypeError("component evidence must be inert UTF8 text")
        raw = item["text"].encode()
        total += len(raw)
        if len(raw) > 100_000 or total > 650_000 or core.sha(raw) != item["sha256"]:
            raise ValueError("component evidence size or identity changed")
    manifest = read_json(files, "artifact-manifest.json")
    core.exact(manifest, {"files"})
    members = manifest["files"]
    if not isinstance(members, list) or len(members) > 62:
        raise ValueError("unsupported sealed component manifest")
    seen = set()
    for entry in members:
        core.exact(entry, {"path", "bytes", "sha256"})
        name = entry["path"]
        if not isinstance(name, str) or name in seen or name not in files or type(entry["bytes"]) is not int:
            raise ValueError("missing or duplicate sealed component evidence")
        seen.add(name)
        raw = files[name]["text"].encode()
        if len(raw) != entry["bytes"] or core.sha(raw) != entry["sha256"]:
            raise ValueError("sealed component evidence does not match manifest")
    extras = set(files) - seen
    if extras not in (
        {"artifact-manifest.json", "assembly-receipt.json"},
        {"artifact-manifest.json", "correction-receipt.json"},
    ):
        raise ValueError("unmanifested component evidence is not admitted")
    decision = read_json(files, "decision.json")
    if decision.get("schema") != "alpha-component-decision/v1" or decision.get("mission_id") != pack["id"]:
        raise ValueError("component decision identity changed")
    for evidence in decision["evidence"]:
        name = evidence["package_path"]
        if (
            name not in files
            or evidence["sha256"] != files[name]["sha256"]
            or evidence["bytes"] != len(files[name]["text"].encode())
        ):
            raise ValueError("decision claim lacks its exact referenced evidence")
    original = files["evidence/verify_component.py"]["text"].encode()
    if core.sha(original) != VERIFIER_ORIGINAL_SHA256:
        raise ValueError("writer's original verifier identity changed; explicit revalidation required")
    if verifier_ast(original) != verifier_ast((HERE / "vendor/verify_component.py").read_bytes()):
        raise ValueError("installed verifier differs substantively from writer's original")
    urls = decision.get("source_urls")
    if (
        not isinstance(urls, list)
        or not 1 <= len(urls) <= 8
        or any(
            not isinstance(url, str)
            or not re.fullmatch(
                r"https://github\.com/MontrealAI/AGI-Alpha-Agent-v0/blob/[0-9a-f]{40}/[A-Za-z0-9_./-]+\.py", url
            )
            for url in urls
        )
    ):
        raise ValueError("component decision source links are not exact public Python source")
    return files, decision


def assess(pack: dict[str, Any]) -> dict[str, Any]:
    meter = core.Meter()
    with meter.stage("preparation"):
        files, decision = validate(pack)
    with meter.stage("planning"):
        contract = read_json(files, "evidence/component-contract.json")
        if core.sha(files["evidence/component-contract.json"]["text"].encode()) != verifier.FROZEN_CONTRACT_SHA256:
            raise ValueError("writer's exact source contract changed")
        expected_cases = {row["id"] for row in contract["cases"]}
        if len(expected_cases) != len(contract["cases"]):
            raise ValueError("duplicate component requirement")
    with meter.stage("execution"):
        checks = []
        with tempfile.TemporaryDirectory(prefix="alpha-component-record-check-") as temporary:
            root = Path(temporary)
            mapping = {
                "evidence/component-contract.json": "protocol/component-contract.json",
                "evidence/component-projections.json": "protocol/component-projections.json",
                "evidence/api.py": "data/consumer/api.py",
                "evidence/models.py": "data/consumer/models.py",
                "evidence/test_api_boundary.py": "discovery/test_api_boundary.py",
            }
            for old, new in mapping.items():
                target = root / new
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(files[old]["text"])
            for side, prefix in (("before", "baseline-bridge"), ("after", "target")):
                observed_name = f"evidence/{prefix}-observations.json"
                environment_name = f"evidence/{prefix}-environment.json"
                saved_name = f"evidence/{prefix}-verification.json"
                observed = root / (side + "-observed.json")
                environment = root / (side + "-environment.json")
                observed.write_text(files[observed_name]["text"])
                environment.write_text(files[environment_name]["text"])
                result = verifier.verify(
                    root / "protocol/component-contract.json",
                    observed,
                    root / "data/consumer",
                    environment,
                    "native-fastapi-bridge-v2",
                )
                saved = read_json(files, saved_name)
                for key in (
                    "status",
                    "contract_sha256",
                    "observations_sha256",
                    "environment_manifest_sha256",
                    "environment_versions",
                    "projection_id",
                    "native_import_route",
                    "global_incomplete",
                    "counts",
                    "cases",
                ):
                    if not verifier.strict_equal(result[key], saved[key]):
                        raise ValueError("recomputed component verification differs from the saved decision")
                if result["environment_versions"] != decision[side + "_versions"]:
                    raise ValueError("component decision declares another dependency profile")
                if {row["id"] for row in result["cases"]} != expected_cases:
                    raise ValueError("component decision omits a required case")
                checks.append({"side": side, "result": result})
    with meter.stage("verification"):
        preserved = all(check["result"]["status"] == "PRESERVED_WITHIN_COMPONENT_CONTRACT" for check in checks)
        regression = (
            checks[0]["result"]["status"] == "PRESERVED_WITHIN_COMPONENT_CONTRACT"
            and checks[1]["result"]["status"] == "BEHAVIOR_MISMATCH"
            and checks[1]["result"]["counts"]["BEHAVIOR_MISMATCH"] > 0
            and checks[1]["result"]["counts"]["INCOMPLETE"] == 0
            and not checks[1]["result"]["global_incomplete"]
        )
        expected = "SCOPED_COMPONENT_PRESERVED" if preserved else "COMPONENT_REGRESSION" if regression else None
        if expected is None or decision["decision"] != expected:
            raise ValueError("component evidence is incomplete or its decision contradicts the verified behavior")
        if decision["coverage"]["requirements"] != len(expected_cases) or any(
            decision["coverage"][side + "_pass"] != check["result"]["counts"]["PASS"]
            for side, check in zip(("before", "after"), checks)
        ):
            raise ValueError("decision summary does not match complete component evidence")
    with meter.stage("correction"):
        corrections: list[Any] = []
    with meter.stage("reporting"):
        record = {
            "schema": "alpha-upgrade-decision/v1",
            "assessmentKind": "native-component-contract",
            "capability": "source-linked-component-decision/v1",
            "id": pack["id"],
            "title": pack["title"],
            "purpose": "Assess the writer's exact native dependency refresh component evidence and identify the remaining application qualification.",
            "inputSha256": core.sha(core.canonical(pack)),
            "missionKey": core.mission_key(pack),
            "nextAction": "ADVANCE_COMPONENT_KEEP_LOCK" if preserved else "HOLD_COMPONENT_AND_INVESTIGATE",
            "engineeringAcceptance": True,
            "customerAcceptance": "unknown",
            "productionApproved": False,
            "componentDecision": decision,
            "sourceFileCount": len(files),
            "componentChecks": checks,
            "calls": [],
            "recordedChecks": [],
            "historicalEvidence": [],
            "limits": decision["limits"]
            + [
                "This product rechecks saved observations with the writer's fixed verifier; it does not rerun the consumer or independently attest a hostile recorder."
            ],
            "review": {
                "creator": "Writer's source-pinned component outcome",
                "critic": "Reconcile all material decision claims with the sealed manifest, exact case/lock/profile identities and recomputed finite verifier outcomes.",
                "verifier": {
                    "accepted": True,
                    "method": "Rerun the original inert-observation verifier; same method is not an independent research replication.",
                    "defects": [],
                },
                "corrections": corrections,
            },
            "resources": {
                "stages": meter.rows,
                "runtimeModelCalls": {"value": 0, "basis": "measured"},
                "networkRequests": {"value": 0, "basis": "measured"},
                "inputBytes": {"value": len(core.canonical(pack)), "basis": "measured"},
                "python": sys.version,
                "unknown": [
                    "Complete research/authoring/inference cost",
                    "operator/customer minutes",
                    "delivery currency cost",
                    "integration/setup/upkeep",
                    "caller transport/journal and unobserved failed/recovery resources",
                ],
            },
        }
    return record


def main() -> None:
    raw = sys.stdin.buffer.read(core.MAX_PACK_BYTES + 1)
    try:
        result = assess(core.load(raw))
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        result = {
            "refused": True,
            "reason": str(exc),
            "inputSha256": core.sha(raw),
            "cost": "unknown; retain the charged parent attempt",
        }
    sys.stdout.buffer.write(core.canonical(result))


if __name__ == "__main__":
    main()
