# SPDX-License-Identifier: Apache-2.0
"""Import the writer's sealed component decision and recheck inert observations."""

from __future__ import annotations

import ast
import difflib
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
REQUIRED_FILES = frozenset(
    {
        "READ-ME.md",
        "artifact-manifest.json",
        "assembly-receipt.json",
        "correction-receipt.json",
        "decision.json",
        "proposed-component-lock.patch",
        "reproduce.txt",
        "evidence/api.py",
        "evidence/models.py",
        "evidence/test_api_boundary.py",
        "evidence/manual_probe.py",
        "evidence/measured_run.py",
        "evidence/verify_component.py",
        "evidence/component-contract.json",
        "evidence/component-projections.json",
        "evidence/intent-charter.json",
    }
    | {
        f"evidence/{prefix}{suffix}"
        for prefix in ("baseline-bridge", "target")
        for suffix in (
            "-environment.json",
            "-execution.json",
            "-observations.json",
            "-verification-execution.json",
            "-verification.json",
            ".lock",
        )
    }
)


def check_correction_custody(files: dict[str, Any]) -> None:
    """Reconcile the original assembly and every declared reporting correction."""
    assembly = read_json(files, "assembly-receipt.json")
    correction = read_json(files, "correction-receipt.json")
    original = correction.get("original_files")
    if (
        assembly.get("schema") != "first-manual-delivery-assembly/v1"
        or assembly.get("files_verified") != len(REQUIRED_FILES) - 3
        or correction.get("schema") != "first-delivery-report-correction/v1"
        or not isinstance(original, dict)
        or set(original) != REQUIRED_FILES - {"correction-receipt.json"}
        or any(not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h) for h in original.values())
        or correction.get("corrected_artifact_manifest_sha256") != files["artifact-manifest.json"]["sha256"]
        or correction.get("original_assembly_receipt_preserved") is not True
        or original["assembly-receipt.json"] != files["assembly-receipt.json"]["sha256"]
        or correction.get("mission_count_increment") != 0
    ):
        raise ValueError("original assembly/correction custody is incomplete or inconsistent")
    changed = correction.get("changed_content_files")
    if not isinstance(changed, list):
        raise TypeError("missing correction relationships")
    seen = set()
    for row in changed:
        core.exact(row, {"path", "before_sha256", "after_sha256"})
        name = row["path"]
        if (
            name not in original
            or name in seen
            or name in {"artifact-manifest.json", "assembly-receipt.json"}
            or row["before_sha256"] != original[name]
            or row["after_sha256"] != files[name]["sha256"]
            or row["before_sha256"] == row["after_sha256"]
        ):
            raise ValueError("invalid correction relationship")
        seen.add(name)
    if any(
        original[name] != files[name]["sha256"] for name in original if name not in seen | {"artifact-manifest.json"}
    ):
        raise ValueError("undeclared writer packet correction")
    method_files = {
        "evidence/manual_probe.py",
        "evidence/measured_run.py",
        "evidence/verify_component.py",
        "evidence/component-contract.json",
        "evidence/component-projections.json",
    }
    behavioral = any(name.startswith("evidence/") for name in seen)
    if (
        correction.get("behavioral_evidence_changed") is not behavioral
        or correction.get("decision_changed") is not ("decision.json" in seen)
        or correction.get("method_or_evaluator_changed") is not bool(seen & method_files)
    ):
        raise ValueError("correction receipt misstates its actual scope")


def check_profile(files: dict[str, Any], prefix: str, versions: dict[str, Any]) -> None:
    """Bind exact delivered lock rows to recorded installed wheels and versions."""
    pins: dict[str, tuple[str, str]] = {}
    for line in files[f"evidence/{prefix}.lock"]["text"].splitlines():
        match = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)==([A-Za-z0-9.+_-]+) --hash=sha256:([0-9a-f]{64})", line)
        if match is None or match[1] in pins:
            raise ValueError("component lock requires unique exact version and wheel identities")
        pins[match[1]] = (match[2], match[3])
    env = read_json(files, f"evidence/{prefix}-environment.json")
    wheels = env.get("wheels")
    if not isinstance(wheels, list) or len(wheels) != len(pins):
        raise ValueError("component lock differs from recorded wheel inventory")
    wheel_pins = {row["name"]: (row["version"], row["sha256"]) for row in wheels}
    installed = env.get("installed_distributions")
    if not isinstance(installed, list):
        raise TypeError("missing installed component profile")
    distributions = {re.sub(r"[-_.]+", "-", row["name"].lower()): row["version"] for row in installed}
    if (
        wheel_pins != pins
        or len(wheel_pins) != len(wheels)
        or {name: value[0] for name, value in pins.items()} != versions
        or len(distributions) != len(installed)
        or set(distributions) != set(pins) | {"pip"}
        or any(distributions.get(name) != pin[0] for name, pin in pins.items())
    ):
        raise ValueError("component lock, wheel hashes or installed dependency profile disagree")


def check_execution_custody(files: dict[str, Any], prefix: str, *, verification: bool) -> None:
    """Check inert before/after input identities and the exact recorded output."""
    environment = f"data/development-{'baseline-bridge' if prefix == 'baseline-bridge' else 'target'}-environment"
    inputs = {
        "protocol/component-contract.json": "evidence/component-contract.json",
        "protocol/component-projections.json": "evidence/component-projections.json",
        "data/consumer/api.py": "evidence/api.py",
        "data/consumer/models.py": "evidence/models.py",
        environment + "/preparation.json": f"evidence/{prefix}-environment.json",
    }
    if verification:
        inputs |= {
            "src/verify_component.py": "evidence/verify_component.py",
            "discovery/test_api_boundary.py": "evidence/test_api_boundary.py",
            f"results/development/{prefix}-observations.json": f"evidence/{prefix}-observations.json",
        }
    else:
        inputs |= {
            "src/manual_probe.py": "evidence/manual_probe.py",
            "src/measured_run.py": "evidence/measured_run.py",
            environment + "/requirements.lock": f"evidence/{prefix}.lock",
        }
    suffix = "verification" if verification else "observations"
    receipt = read_json(files, f"evidence/{prefix}-{'verification-' if verification else ''}execution.json")
    # The fixed verifier writes a complete mismatch result and deliberately
    # exits 2. That is a useful hold outcome, not missing execution evidence.
    mismatch = (
        verification and read_json(files, f"evidence/{prefix}-verification.json").get("status") == "BEHAVIOR_MISMATCH"
    )
    expected_exit = 2 if mismatch else 0
    before, after = receipt.get("input_identities_before"), receipt.get("input_identities_after")
    if (
        receipt.get("schema") != "alpha-measured-command/v1"
        or receipt.get("complete_success") is not (expected_exit == 0)
        or receipt.get("command_started") is not True
        or receipt.get("timed_out") is not False
        or receipt.get("inputs_unchanged") is not True
        or type(receipt.get("exit_code")) is not int
        or receipt.get("exit_code") != expected_exit
        or receipt.get("timeout_seconds") != 45
        or receipt.get("missing_outputs") != []
        or not isinstance(before, list)
        or len(before) != len(inputs) + (0 if verification else 1)
        or not verifier.strict_equal(before, after)
    ):
        raise ValueError("recorded execution is incomplete or its inputs changed")
    paths = set()
    for row in before:
        core.exact(row, {"path", "bytes", "sha256"})
        if (
            not isinstance(row["path"], str)
            or not row["path"].startswith("/")
            or ".." in row["path"].split("/")
            or row["path"] in paths
            or type(row["bytes"]) is not int
            or row["bytes"] <= 0
            or not isinstance(row["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        ):
            raise ValueError("invalid execution input identity")
        paths.add(row["path"])
    roots = set()
    used = set()
    for relative, packaged in inputs.items():
        matches = [row for row in before if isinstance(row.get("path"), str) and row["path"].endswith("/" + relative)]
        if len(matches) != 1:
            raise ValueError("execution receipt omits a required input identity")
        row = matches[0]
        if row.get("sha256") != files[packaged]["sha256"] or row.get("bytes") != len(files[packaged]["text"].encode()):
            raise ValueError("execution input identity disagrees with delivered evidence")
        roots.add(row["path"][: -len(relative)])
        used.add(row["path"])
    if len(roots) != 1 or len(used) != len(inputs):
        raise ValueError("ambiguous execution source relationships")
    if not verification and not next(iter(paths - used)).endswith("/bin/python3.12"):
        raise ValueError("unsupported recorded interpreter identity")
    root = roots.pop()
    output = f"results/development/{prefix}-{suffix}.json"
    expected_output = {
        "path": root + output,
        "bytes": len(files[f"evidence/{prefix}-{suffix}.json"]["text"].encode()),
        "sha256": files[f"evidence/{prefix}-{suffix}.json"]["sha256"],
    }
    if receipt.get("output_identities") != [expected_output]:
        raise ValueError("execution output identity disagrees with delivered evidence")
    if verification:
        command = [
            "python",
            root + "src/verify_component.py",
            "--contract",
            root + "protocol/component-contract.json",
            "--consumer",
            root + "data/consumer",
            "--environment",
            root + environment + "/preparation.json",
            "--projection",
            "native-fastapi-bridge-v2",
            "--observations",
            root + f"results/development/{prefix}-observations.json",
            "--out",
            root + output,
        ]
    else:
        command = [
            root + environment + "/venv/bin/python",
            "-I",
            "-B",
            root + "src/manual_probe.py",
            "--consumer",
            root + "data/consumer",
            "--contract",
            root + "protocol/component-contract.json",
            "--out",
            root + output,
        ]
    if receipt.get("command") != command:
        raise ValueError("recorded execution does not use the bound native import method")


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
    if not isinstance(files, dict) or set(files) != REQUIRED_FILES:
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
    if extras != {"artifact-manifest.json", "correction-receipt.json"}:
        raise ValueError("unmanifested component evidence is not admitted")
    check_correction_custody(files)
    decision = read_json(files, "decision.json")
    if decision.get("schema") != "alpha-component-decision/v1" or decision.get("mission_id") != pack["id"]:
        raise ValueError("component decision identity changed")
    if (
        not isinstance(decision.get("evidence"), list)
        or len(decision["evidence"]) != len([name for name in REQUIRED_FILES if name.startswith("evidence/")])
        or {entry["package_path"] for entry in decision["evidence"]}
        != {name for name in REQUIRED_FILES if name.startswith("evidence/")}
    ):
        raise ValueError("component decision omits original material evidence")
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
    for side, prefix in (("before", "baseline-bridge"), ("after", "target")):
        check_profile(files, prefix, decision[side + "_versions"])
        check_execution_custody(files, prefix, verification=False)
        check_execution_custody(files, prefix, verification=True)
    patch = "".join(
        difflib.unified_diff(
            files["evidence/baseline-bridge.lock"]["text"].splitlines(keepends=True),
            files["evidence/target.lock"]["text"].splitlines(keepends=True),
            fromfile="baseline-component.lock",
            tofile="proposed-component.lock",
        )
    )
    if files["proposed-component-lock.patch"]["text"] != patch:
        raise ValueError("proposed patch does not exactly represent the verified component locks")
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
