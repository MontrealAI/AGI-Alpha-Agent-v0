# SPDX-License-Identifier: Apache-2.0
"""Transfer actual retained code and execute a separately authorized fresh audit."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from binding import (
    DOMAIN,
    MODE,
    SCOPE,
    STUDY,
    bind_request,
    canonical,
    check_grant,
    dependency_inventory,
    digest,
    file_sha,
    grant_payload,
    inherited,
    load_json,
    native_trust,
    pack_bundle,
    safe_member,
    save,
    scan_payload,
    unpack_bundle,
    upstream_runner,
    verify_installed_bundle,
)

HERE = Path(__file__).resolve().parent
GENERIC_BANK = {
    "schema": "inspection-runtime-conformance-bank/v1",
    "cases": [
        "frozen-application-source-identity",
        "received-bundle-exact-closure",
        "installed-dependency-identity",
        "registered-protected-string-rejection",
        "credential-pattern-rejection",
        "unsafe-source-member-rejection",
    ],
    "claim": "finite packaging/runtime checks only; no scientific mission acceptance or economic admission",
}


def refused(action: Callable[[], Any]) -> dict[str, Any]:
    """Record a negative control without converting unexpected success to acceptance."""
    try:
        action()
    except (ValueError, KeyError, OSError) as error:
        return {"passed": True, "reason": str(error)}
    return {"passed": False, "reason": "unexpectedly permitted"}


def complete_identity(manifest: dict[str, Any], bundle_sha: str, evaluator: dict[str, Any]) -> dict[str, Any]:
    """Use the exact complete-identity interface already supported by the v3 cache."""
    return {
        "source": manifest["closure"]["files"],
        "artifact": {"bundle_sha256": bundle_sha, "manifest_sha256": digest(manifest)},
        "schema": manifest["closure"]["schema_identity"],
        "dependencies": manifest["dependency_identity"],
        "evaluator": {
            "generic": {name: file_sha(HERE / name) for name in ("binding.py", "recipient.py", "run_integration.py")},
            "fresh_semantics": evaluator,
        },
        "scope": SCOPE,
        "policy": {
            "instrument_policy": manifest["closure"]["policy_identity"],
            "allow_exact_generic_reuse": True,
            "reuse_limit": "only the exact six declared runtime/packaging cases; no mission results or permission",
        },
        "bank": digest(GENERIC_BANK),
    }


def generic_checks(
    source: Path, manifest: dict[str, Any], unpacked: dict[str, Any], inventory: dict[str, Any]
) -> dict[str, Any]:
    """Perform actual finite conformance checks, explicitly outside semantic qualification."""
    source_ok = all(file_sha(source / name) == expected for name, expected in manifest["closure"]["files"].items())
    protected = b"FIXTURE_ONLY_REGISTERED_PROTECTED_ANSWER"
    secret = b"sk-" + b"X" * 30
    checks = [
        {"name": GENERIC_BANK["cases"][0], "passed": source_ok},
        {"name": GENERIC_BANK["cases"][1], "passed": unpacked == manifest},
        {"name": GENERIC_BANK["cases"][2], "passed": inventory["identity"] == manifest["dependency_identity"]},
        {"name": GENERIC_BANK["cases"][3], **refused(lambda: scan_payload(protected, (protected,)))},
        {"name": GENERIC_BANK["cases"][4], **refused(lambda: scan_payload(secret))},
        {"name": GENERIC_BANK["cases"][5], "passed": not safe_member("instrument/../../protected/answers.json")},
    ]
    return {
        "accepted": all(row["passed"] for row in checks),
        "cases": len(checks),
        "checks": checks,
        "scope": GENERIC_BANK["claim"],
        "scientific_acceptance": None,
        "production_authority": None,
    }


def authority_controls(
    identity: dict[str, Any], binding: dict[str, Any], context: dict[str, Any], native: Any, key: Any
) -> list[dict[str, Any]]:
    """Use actual signatures/roles for mission, permission, time and revocation checks."""
    now = int(time.time())
    payload = grant_payload(identity, binding, "authority-negative-controls", now)

    def signed(value: dict[str, Any]) -> dict[str, Any]:
        return native.sign_record(key, "local-controller", DOMAIN, value).model_dump()

    envelope = signed(payload)
    checks = [
        {
            "name": "correct-current-local-research-signature",
            "passed": check_grant(envelope, context, identity, binding, now) == payload,
        }
    ]
    changed_binding = copy.deepcopy(binding)
    changed_binding["mission"]["statement"] = "A changed mission cannot inherit the former authorization."
    checks.append(
        {
            "name": "changed-mission-refused",
            **refused(lambda: check_grant(envelope, context, identity, changed_binding, now)),
        }
    )
    missing_binding = copy.deepcopy(binding)
    missing_binding["request_sha256"] = digest({"missing_semantics": True})
    checks.append(
        {
            "name": "removed-request-metadata-refused",
            **refused(lambda: check_grant(envelope, context, identity, missing_binding, now)),
        }
    )
    changed_identity = copy.deepcopy(identity)
    changed_identity["dependencies"]["python"]["version"] = "CHANGED_RUNTIME"
    checks.append(
        {
            "name": "changed-dependency-authority-refused",
            **refused(lambda: check_grant(envelope, context, changed_identity, binding, now)),
        }
    )
    changed_source = copy.deepcopy(binding)
    first = next(iter(changed_source["assets"]))
    changed_source["assets"][first]["sha256"] = "0" * 64
    checks.append(
        {
            "name": "changed-source-authority-refused",
            **refused(lambda: check_grant(envelope, context, identity, changed_source, now)),
        }
    )
    expired = signed({**payload, "expires": now})
    checks.append(
        {"name": "expired-authority-refused", **refused(lambda: check_grant(expired, context, identity, binding, now))}
    )
    future = signed({**payload, "not_before": now + 1})
    checks.append(
        {"name": "future-authority-refused", **refused(lambda: check_grant(future, context, identity, binding, now))}
    )
    revoked = {**context, "revoked": ["local-controller"]}
    checks.append(
        {"name": "revoked-authority-refused", **refused(lambda: check_grant(envelope, revoked, identity, binding, now))}
    )
    corrupted = copy.deepcopy(envelope)
    corrupted["signature"] = ("A" if corrupted["signature"][0] != "A" else "B") + corrupted["signature"][1:]
    checks.append(
        {
            "name": "invalid-signature-refused",
            **refused(lambda: check_grant(corrupted, context, identity, binding, now)),
        }
    )
    manufacturing = signed({**payload, "right": "manufacture-or-release-part"})
    checks.append(
        {
            "name": "physical-operation-right-not-conferred",
            **refused(lambda: check_grant(manufacturing, context, identity, binding, now)),
        }
    )
    return checks


def native_scope_control() -> dict[str, Any]:
    """Preserve the production capsule schema's refusal of manufacturing scope."""
    native_trust()
    from alpha_factory_v1.core.runtime.successor.flywheel_capsules import CapsuleManifest
    from pydantic import ValidationError

    manifest = {
        "skill_id": "inspection-evidence-research",
        "version": 1,
        "origin_mission": "public-source-research",
        "origin_record_digest": "1" * 64,
        "origin_agent": "atlas.agent.agi.eth",
        "origin_wallet": "0x" + "11" * 20,
        "content_digest": "2" * 64,
        "supported_scope": "bounded-public-source-selection/v1",
        "prerequisites": [],
        "limitations": "Research conformance only; no customer, ENS or production claim.",
        "rights": "cleared-for-authenticated-network",
        "rights_evidence": "3" * 64,
        "dependency_digests": [],
    }
    CapsuleManifest.model_validate(manifest)
    try:
        CapsuleManifest.model_validate({**manifest, "supported_scope": "manufacturing-inspection-evidence/v1"})
    except ValidationError as error:
        passed = any(row["loc"] == ("supported_scope",) and row["type"] == "literal_error" for row in error.errors())
        return {
            "name": "native-manufacturing-scope-refused",
            "passed": passed,
            "reason": "unchanged native supported_scope literal excludes this manufacturing capability",
        }
    return {"name": "native-manufacturing-scope-refused", "passed": False, "reason": "unexpectedly permitted"}


def concrete_drift_controls(bundle: Path, manifest: dict[str, Any], request: Path) -> list[dict[str, Any]]:
    """Alter temporary copies only; preserved sources and protected jobs stay unchanged."""
    checks = []
    with tempfile.TemporaryDirectory(prefix="v4-identity-drift-") as temporary:
        root = Path(temporary)
        altered = root / "altered.zip"
        altered.write_bytes(bundle.read_bytes() + b"FIXTURE_ARTIFACT_MUTATION")
        checks.append(
            {
                "name": "altered-transferred-archive-refused",
                **refused(lambda: unpack_bundle(altered, root / "bad-archive", file_sha(bundle))),
            }
        )
        destination = root / "changed-code"
        unpack_bundle(bundle, destination, file_sha(bundle))
        code = destination / manifest["closure"]["entrypoint"]
        with code.open("ab") as stream:
            stream.write(b"\n# TEMPORARY SOURCE-INTEGRITY NEGATIVE CONTROL\n")
        checks.append(
            {
                "name": "changed-received-source-refused",
                **refused(lambda: verify_installed_bundle(destination, manifest)),
            }
        )
        dependency = next(iter(manifest["closure"]["dependencies"]))
        checks.append(
            {
                "name": "incompatible-current-dependency-refused",
                **refused(lambda: dependency_inventory({dependency: "0.0.0-incompatible-fixture"})),
            }
        )
        changed_request = copy.deepcopy(load_json(request))
        for asset in changed_request["assets"].values():
            asset["path"] = str((request.parent / asset["path"]).resolve())
        first_asset = next(iter(changed_request["assets"].values()))
        changed_source = root / "altered-public-source"
        changed_source.write_bytes(Path(first_asset["path"]).read_bytes() + b"\nFIXTURE_SOURCE_HASH_MUTATION\n")
        first_asset["path"] = str(changed_source)
        negative_request = root / "negative-source-request.json"
        save(negative_request, changed_request)
        checks.append(
            {"name": "changed-public-source-bytes-refused", **refused(lambda: bind_request(negative_request))}
        )
    return checks


def invoke_recipient(
    label: str, root: Path, request: Path, grant: dict[str, Any], out: Path, journal: Path
) -> dict[str, Any]:
    """Launch a new recipient process; it then launches the received actual CLI."""
    directory = out / label
    directory.mkdir()
    save(directory / "grant.json", grant)
    command = [
        sys.executable,
        "-B",
        str(HERE / "recipient.py"),
        "--bundle-root",
        str(root),
        "--manifest",
        str(out / "bundle-manifest.json"),
        "--identity",
        str(out / "complete-identity.json"),
        "--request",
        str(request),
        "--grant",
        str(directory / "grant.json"),
        "--context",
        str(out / "local-authority-context.json"),
        "--journal",
        str(journal),
        "--report",
        str(directory / "report.json"),
        "--receipt",
        str(directory / "process.json"),
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, timeout=240, check=False)
    record = {
        "command": command,
        "seconds": time.perf_counter() - started,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    save(directory / "launcher.json", record)
    if not (directory / "process.json").exists():
        return {"refused": True, "reason": "recipient process failed before receipt", "launcher": record}
    return cast_dict(load_json(directory / "process.json"))


def cast_dict(value: Any) -> dict[str, Any]:
    """Reject malformed evidence records rather than assuming success."""
    if not isinstance(value, dict):
        raise ValueError("expected evidence object")
    return value


def verify_evaluator_closure(manifest_path: Path, manifest: dict[str, Any], request: Path, oracle: Path) -> int:
    """Check opaque frozen evaluator/task hashes without ingesting protected answers."""
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("independent evaluator requires a complete frozen file inventory")
    root = manifest_path.parent
    for name, expected in files.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or file_sha(root / path) != expected:
            raise ValueError("independent evaluator source or protected input changed: " + name)
    for path in (request, oracle):
        relative = str(path.relative_to(root))
        if files.get(relative) != file_sha(path):
            raise ValueError("selected fresh request/oracle absent from frozen evaluator inventory")
    return len(files)


def verify_report(checker: Path, request: Path, report: Path, oracle: Path, output: Path) -> dict[str, Any]:
    """Run the independent checker without reading its protected answer content."""
    command = [
        sys.executable,
        "-B",
        str(checker),
        "--request",
        str(request),
        "--report",
        str(report),
        "--oracle",
        str(oracle),
        "--output",
        str(output),
    ]
    started = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    receipt = {
        "command": command,
        "seconds": time.perf_counter() - started,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "checker_sha256": file_sha(checker),
        "oracle_sha256": file_sha(oracle),
    }
    save(output.with_name(output.stem + "-process.json"), receipt)
    if not output.is_file():
        return {"accepted": False, "checker_failure": receipt}
    verdict = cast_dict(load_json(output))
    return {
        "accepted": result.returncode == 0 and verdict.get("accepted") is True,
        "checker_verdict": verdict,
        "checker_returncode": result.returncode,
        "verification_seconds": receipt["seconds"],
    }


def stable_report(value: Any) -> Any:
    """Remove only declared runtime telemetry from identical-content parity comparison."""
    excluded = {"execution", "elapsed_seconds", "wall_seconds", "runtime_seconds", "import_seconds", "duration_seconds"}
    if isinstance(value, dict):
        return {key: stable_report(item) for key, item in value.items() if key not in excluded}
    if isinstance(value, list):
        return [stable_report(item) for item in value]
    return value


def run(
    closure: Path,
    request: Path,
    checker: Path,
    oracle: Path,
    evaluator_identity: Path,
    output: Path,
    source: Path = STUDY,
    *,
    expected_closure_sha256: str,
    expected_evaluator_sha256: str,
) -> dict[str, Any]:
    """Execute once after core and independent evaluator freezes; preserve any failure."""
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    if file_sha(closure) != expected_closure_sha256 or file_sha(evaluator_identity) != expected_evaluator_sha256:
        raise ValueError("source/evaluator freeze identity changed before transfer")
    save(
        output / "freeze-bindings.json",
        {
            "instrument_freeze_sha256": expected_closure_sha256,
            "evaluator_identity_sha256": expected_evaluator_sha256,
            "request_file_sha256": file_sha(request),
            "oracle_sha256": file_sha(oracle),
            "integration_sources": {
                name: file_sha(HERE / name) for name in ("binding.py", "recipient.py", "run_integration.py")
            },
            "stage": "before first recipient execution",
        },
    )
    specification = load_json(closure)
    evaluator = load_json(evaluator_identity)
    if evaluator.get("checker_sha256") != file_sha(checker):
        raise ValueError("independent checker changed after evaluator freeze")
    evaluator_file_count = verify_evaluator_closure(evaluator_identity, evaluator, request, oracle)
    helper = inherited()
    source_manifest = helper.upstream().verify_sources()
    save(
        output / "upstream-source-binding.json",
        {
            "source_manifest": source_manifest,
            "preserved_v3_helper_sha256": file_sha(Path(helper.__file__)),
            "no_upstream_source_changed": True,
        },
    )
    inventory = dependency_inventory(specification["dependencies"])
    save(output / "dependency-inventory.json", inventory)
    bundle = output / "retained-capability.zip"
    manifest = pack_bundle(source, specification, inventory["identity"], bundle)
    bundle_sha = file_sha(bundle)
    save(output / "bundle-manifest.json", manifest)
    transport_started = time.perf_counter()
    transport = upstream_runner().run(bundle, output / "transport")
    transport_seconds = time.perf_counter() - transport_started
    received = output / "transport" / "received-v2.zip"
    if not received.is_file():
        raise ValueError("existing lifecycle did not deliver artifact bytes")
    recipient_root, library_root = output / "recipient-code", output / "ordinary-library-code"
    recipient_manifest = unpack_bundle(received, recipient_root, bundle_sha)
    library_manifest = unpack_bundle(bundle, library_root, bundle_sha)
    identity = complete_identity(manifest, bundle_sha, evaluator)
    save(output / "complete-identity.json", identity)
    cache = helper.QualificationCache()
    first = cache.qualify(identity, lambda: generic_checks(source, manifest, recipient_manifest, inventory))
    second = cache.qualify(identity, lambda: (_ for _ in ()).throw(ValueError("exact cache failed to reuse")))
    cache_controls = []
    for field in ("source", "artifact", "schema", "dependencies", "evaluator", "scope", "policy", "bank"):
        changed = copy.deepcopy(identity)
        if field == "policy":
            changed[field]["instrument_policy"] = "different-policy"
        else:
            changed[field] = {"changed": field}
        called = []

        def requalification_required() -> dict[str, Any]:
            called.append(True)
            raise ValueError("changed complete identity requires new qualification; no passing receipt supplied")

        control = refused(lambda: cache.qualify(changed, requalification_required))
        cache_controls.append(
            {
                "name": "cache-invalidated-by-" + field,
                "passed": control["passed"] and bool(called),
                "reason": control["reason"],
            }
        )
    save(
        output / "generic-qualification.json",
        {"bank": GENERIC_BANK, "first": first, "exact_reuse": second, "changed_identity_controls": cache_controls},
    )
    binding = bind_request(request)
    save(output / "current-source-bindings.json", binding)
    native = native_trust()
    registry, keys = native.local_principals()
    context = {
        "mode": MODE,
        "recipient": "lyra.agent.agi.eth",
        "revoked": [],
        "public_controller_key": registry.anchor("local-controller", "controller").public_key,
        "provenance": "operator-configured ephemeral fixture, not obtained from incoming capsule or ENS",
    }
    save(output / "local-authority-context.json", context)
    controls = authority_controls(identity, binding, context, native, keys["local-controller"])
    controls += concrete_drift_controls(bundle, manifest, request)
    controls += cache_controls
    controls += [native_scope_control()]
    controls += [
        {
            "name": "existing-lifecycle-controls",
            "passed": transport["passed"] == transport["total"],
            "count": transport["total"],
        },
        {"name": "same-content-library-manifest", "passed": library_manifest == recipient_manifest},
        {
            "name": "exact-generic-reuse-cases-only",
            "passed": second["qualification_cases_executed"] == 0
            and second["mission_acceptance"] is None
            and second["authority"] is None,
        },
    ]
    from alpha_factory_v1.core.runtime.store import Journal

    with tempfile.TemporaryDirectory(prefix="opportunity-v4-authority-") as temporary:
        journal_path = Path(temporary) / "native"
        journal = Journal.initialize(journal_path)
        grant = native.sign_record(
            keys["local-controller"],
            "local-controller",
            DOMAIN,
            grant_payload(identity, binding, "fresh-received-computation", int(time.time())),
        )
        recipient = invoke_recipient(
            "fresh-recipient", recipient_root, request, grant.model_dump(), output, journal_path
        )
        ordinary_grant = native.sign_record(
            keys["local-controller"],
            "local-controller",
            DOMAIN,
            grant_payload(identity, binding, "same-content-library", int(time.time())),
        )
        ordinary = invoke_recipient(
            "ordinary-library", library_root, request, ordinary_grant.model_dump(), output, journal_path
        )
        replay = invoke_recipient(
            "consumed-authority-control", recipient_root, request, grant.model_dump(), output, journal_path
        )
        controls.append(
            {
                "name": "consumed-current-authority-refused",
                "passed": replay.get("refused") is True and "already consumed" in replay.get("reason", ""),
            }
        )
        verification = journal.verify()
        with journal.transaction() as connection:
            chain = [
                {"sequence": seq, "mission": mission, "body": json.loads(body), "hash": hashed, "signature": signature}
                for seq, mission, body, hashed, signature in connection.execute("SELECT * FROM events ORDER BY seq")
            ]
        save(
            output / "native-authority-journal.json",
            {"verification": verification, "events": chain, "private_keys_exported": False},
        )
    fresh_report = output / "fresh-recipient" / "report.json"
    ordinary_report = output / "ordinary-library" / "report.json"
    fresh_check = (
        verify_report(
            checker, request, fresh_report, oracle, output / "fresh-recipient" / "independent-verification.json"
        )
        if fresh_report.exists()
        else {"accepted": False, "reason": "recipient produced no report"}
    )
    ordinary_check = (
        verify_report(
            checker, request, ordinary_report, oracle, output / "ordinary-library" / "independent-verification.json"
        )
        if ordinary_report.exists()
        else {"accepted": False, "reason": "ordinary library produced no report"}
    )
    parity = (
        fresh_report.exists()
        and ordinary_report.exists()
        and stable_report(load_json(fresh_report)) == stable_report(load_json(ordinary_report))
    )
    controls += [
        {
            "name": "fresh-cli-executed",
            "passed": recipient.get("returncode") == 0 and recipient.get("separate_cli_process") is True,
        },
        {
            "name": "same-content-library-cli-executed",
            "passed": ordinary.get("returncode") == 0 and ordinary.get("separate_cli_process") is True,
        },
        {"name": "fresh-current-mission-preserved", "passed": recipient.get("request") == binding},
        {"name": "fresh-independent-audit-acceptance", "passed": fresh_check.get("accepted") is True},
        {"name": "same-content-library-independent-acceptance", "passed": ordinary_check.get("accepted") is True},
        {"name": "same-content-library-semantic-parity", "passed": bool(parity)},
        {
            "name": "original-source-manifest-still-valid",
            "passed": helper.upstream().verify_sources() == source_manifest,
        },
        {
            "name": "independent-evaluator-and-task-freeze-still-valid",
            "passed": verify_evaluator_closure(evaluator_identity, evaluator, request, oracle) == evaluator_file_count,
        },
    ]
    save(output / "checks.json", controls)
    summary = {
        "schema": "inspection-evidence-fresh-transfer/v1",
        "checks": controls,
        "passed": sum(row["passed"] for row in controls),
        "total": len(controls),
        "artifact_sha256": bundle_sha,
        "artifact_bytes": bundle.stat().st_size,
        "uncompressed_application_bytes": sum((source / name).stat().st_size for name in specification["files"]),
        "mounted_source_bytes": sum(row["bytes"] for row in binding["assets"].values()),
        "current_request_sha256": binding["request_sha256"],
        "recipient_mission": binding["mission"],
        "fresh_recipient": {"execution": recipient, "independent_verification": fresh_check},
        "ordinary_library": {
            "execution": ordinary,
            "independent_verification": ordinary_check,
            "same_content_semantic_parity": bool(parity),
        },
        "generic_cases_first": first["qualification_cases_executed"],
        "generic_cases_exact_reuse": second["qualification_cases_executed"],
        "generic_reuse_scope": GENERIC_BANK["claim"],
        "fresh_mission_rechecked": True,
        "transport_seconds": transport_seconds,
        "total_seconds": time.perf_counter() - started,
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
        "actual_model_tokens": None,
        "production_admission": "NOT_QUALIFIED_UNSUPPORTED_MANUFACTURING_SCOPE",
        "empirical_alpha_admission": False,
        "transport_basis": "unchanged lifecycle artificial monetary conformance fixture; not economic evidence",
        "dependency_boundary": "complete custom application transferred; declared installed dependencies rehashed separately",
        "authority": "native local Ed25519 roles plus existing Journal; modeled agent names, no live ENS authentication",
        "graph_specific_value": "not established; identical-content ordinary library is the parity control",
        "scope_changes": False,
        "jobs_validator_governance_settlement_changes": False,
    }
    save(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for option in ("closure", "request", "checker", "oracle", "evaluator-identity", "out"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--source", type=Path, default=STUDY)
    parser.add_argument("--expected-closure-sha256", required=True)
    parser.add_argument("--expected-evaluator-sha256", required=True)
    arguments = parser.parse_args()
    result = run(
        arguments.closure.resolve(),
        arguments.request.resolve(),
        arguments.checker.resolve(),
        arguments.oracle.resolve(),
        arguments.evaluator_identity.resolve(),
        arguments.out.resolve(),
        arguments.source.resolve(),
        expected_closure_sha256=arguments.expected_closure_sha256,
        expected_evaluator_sha256=arguments.expected_evaluator_sha256,
    )
    print(json.dumps({key: result[key] for key in ("passed", "total", "artifact_bytes", "production_admission")}))
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
