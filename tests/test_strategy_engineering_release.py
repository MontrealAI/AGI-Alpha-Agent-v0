# SPDX-License-Identifier: Apache-2.0
"""Synthetic artifact-admission regressions; these do not execute a browser or scientific study."""

from __future__ import annotations

import base64
import csv
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tomllib
from typing import Any
import zipfile

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from scripts import strategy_engineering_release as release

ROOT = Path(__file__).resolve().parents[1]
SCIENCE = "7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7"
BROWSER_CHECKS = {
    "exact_browser_approval",
    "real_fixed_executor",
    "tab_closed_active",
    "reconnect_same_mission",
    "three_checked_partials",
    "keep_export_downloads",
    "no_token_storage_or_export",
    "cross_origin_refused",
    "pause_resume_stop",
    "no_duplicate_native_calls",
    "mobile_layout",
    "real_calendar_repair",
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@pytest.fixture
def profile() -> dict[str, Any]:
    return json.loads((ROOT / "contrib/strategy_succession/ENGINEERING_MANIFEST.json").read_text())


def source_identity(profile: dict[str, Any]) -> str:
    raw = (ROOT / "contrib/strategy_succession/ENGINEERING_MANIFEST.json").read_bytes()
    sources = {"installation-profile": hashlib.sha256(raw).hexdigest(), **profile["files"]}
    sources.update(
        {"runtime/" + name: profile["runtime_python_files"][name] for name in profile["runtime_enforcement_files"]}
    )
    return digest(sources)


def child_environment(profile: dict[str, Any]) -> dict[str, Any]:
    """Sanitized synthetic child report; no actual subprocess qualification is claimed."""
    expected = profile["qualified_environment"]
    observation = {
        "schema": "strategy-child-environment/v1",
        "invocation_context_matches": True,
        "prefix_context_matches": True,
        "python_implementation": expected["python_implementation"],
        "python_version": expected["python_version"],
        "dependencies": deepcopy(expected["dependencies"]),
        "native_imports": {name: expected["dependencies"][name] for name in ("numpy", "scipy")},
    }
    return {"observation": observation, "sha256": digest(observation)}


def phase(
    source: str, index: int, policy: str, request_hash: str, task: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check only authored toy schedules; no protected confirmation task is loaded."""
    schedules = [
        [{"id": "J1", "start": 0, "end": 1}, {"id": "J2", "start": 1, "end": 3}, {"id": "J3", "start": 3, "end": 4}],
        [{"id": "J1", "start": 0, "end": 1}, {"id": "J2", "start": 1, "end": 4}, {"id": "J3", "start": 4, "end": 5}],
        [{"id": "J1", "start": 0, "end": 1}, {"id": "J2", "start": 1, "end": 4}, {"id": "J3", "start": 5, "end": 6}],
    ]
    bounds = [
        {"value": 4, "critical": 4, "load": 4, "locked": 0},
        {"value": 5, "critical": 5, "load": 5, "locked": 0},
        {"value": 6, "critical": 5, "load": 6, "locked": 4},
    ]
    binding = index != 2 or task["capacity"][4] == 0
    if index == 2 and not binding:
        schedules[2][-1] = {"id": "J3", "start": 4, "end": 5}
        bounds[2] = {"value": 5, "critical": 5, "load": 5, "locked": 4}
    schedule = schedules[index]
    result = {
        "schema": "release-plan-result/v1",
        "task_id": task["id"],
        "schedule": schedule,
        "makespan": max(row["end"] for row in schedule),
        "movement": 1 if index == 2 and binding else 0,
        "lower_bound": bounds[index],
        "lookahead_steps": 0,
        "optimal_by_lower_bound": True,
        "dispatch_order": [row["id"] for row in schedule if row["id"] not in task.get("locked", {})],
        "proof": [],
        "authority": [],
    }
    spec = importlib.util.spec_from_file_location(
        "synthetic_fixture_checker", ROOT / "contrib/strategy_succession/worker/scientific/review/check.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checker = module.check({"task": task, "result": result})
    assert checker["valid"] is True and checker["qualified"] is True, checker
    raw = {
        "source_hash": source,
        "scientific_source_hash": SCIENCE,
        "task": task,
        "result": result,
        "checker": checker,
        "method": "ordinary-portfolio",
        "proof": [],
        "authority": [],
    }
    receipt_hash = digest(raw)
    final = {
        "label": "Synthetic fixture",
        "task_id": task["id"],
        "task": task,
        "result": result,
        "selected_method": "ordinary-portfolio",
        "verified": True,
        "qualified": True,
        "receipt_hash": receipt_hash,
        "receipt": raw,
        "costs": {},
        "attempts": [],
        "pack": None,
        "baseline_source": None,
    }
    partial = {
        "schema": "strategy-executor-partial/v1",
        "source_hash": source,
        "scientific_source_hash": SCIENCE,
        "policy_binding": policy,
        "request_hash": request_hash,
        "phase_index": index,
        "receipt_hash": receipt_hash,
        "task": task,
        "result": result,
        "checker": checker,
        "selectedmethod": "ordinary-portfolio",
        "proof": [],
        "authority": [],
    }
    partial["transport_digest"] = digest(partial)
    return final, partial


def completed_plan(profile: dict[str, Any], *, binding: bool = True) -> tuple[dict[str, Any], str]:
    source = source_identity(profile)
    method, request_id, policy = "run-journey", "synthetic-release-unit-fixture", "d" * 64
    initial = {
        "schema": "release-plan/v1",
        "id": "synthetic-fixture-project",
        "kind": "plan",
        "public_or_synthetic": "synthetic",
        "planning_only": True,
        "jobs": [
            {"id": "J1", "duration": 1, "crew": 1, "deps": []},
            {"id": "J2", "duration": 2, "crew": 1, "deps": ["J1"]},
            {"id": "J3", "duration": 1, "crew": 1, "deps": ["J2"]},
        ],
        "capacity": [1] * 20,
        "release": {"J1": 0, "J2": 0, "J3": 0},
        "deadline": 20,
    }
    repair_capacity = [0 if binding and slot == 4 else 1 for slot in range(20)]
    supplied = {
        "initial": initial,
        "changes": {"durations": {"J2": 3}},
        "repair": {"observed_at": 2, "capacity": repair_capacity, "deadline": 19, "movement_limit": 2},
        "construction": {"enabled": True},
    }
    request_hash = digest({"method": method, "input": supplied, "request_id": request_id})
    caps = deepcopy(profile["per_plan_caps"])
    base = {
        "plan_id": digest({"request_id": request_id})[:32],
        "request_id": request_id,
        "request_hash": request_hash,
        "method": method,
        "input": supplied,
        "executor_id": profile["executor_id"],
        "source_hash": source,
        "policy_binding": policy,
        "caps": caps,
        "prepared_at": 1000.0,
        "expires_at": 1000.0 + profile["grant_seconds"],
        "request_seconds": profile["request_seconds"],
        "state": "prepared",
        "production_authority": False,
        "observed": {"service_work": 0, "improvement_work": 0, "native_calls": 0, "native_solve_seconds": 0},
        "partial_receipts": [],
    }
    base["plan_digest"] = digest(base)
    changed = deepcopy(initial)
    changed["id"] = initial["id"] + "-changed"
    changed["jobs"][1]["duration"] = 3
    repaired = deepcopy(changed)
    repaired.update(
        kind="repair",
        id=changed["id"] + "-repair",
        capacity=repair_capacity,
        deadline=19,
        movement_limit=2,
        baseline={"J1": 0, "J2": 1, "J3": 4},
        locked={"J1": 0, "J2": 1},
        release={"J1": 0, "J2": 0, "J3": 2},
        disruption={"observed_at": 2, "completed_jobs": ["J1"], "in_progress_jobs": ["J2"]},
    )
    pairs = [phase(source, i, policy, request_hash, task) for i, task in enumerate((initial, changed, repaired))]
    phases, partials = [p[0] for p in pairs], [p[1] for p in pairs]
    phases[2]["baseline_source"] = {
        "receipt_hash": phases[1]["receipt_hash"],
        "task_id": phases[1]["task_id"],
        "verified": True,
        "observed_at": 2,
        "baseline_from": "actual preceding independently verified planning delivery",
        "prefix_basis": "Operator-supplied planning observation; prefix inferred from schedule, no physical completion observed.",
        "completed_jobs": ["J1"],
        "in_progress_jobs": ["J2"],
    }
    costs = {
        "service_work": 3,
        "improvement_work": 2,
        "native_calls": 6,
        "native_solve_seconds": 12,
        "unknown_costs": ["Human effort, opaque native work and monetary costs are unknown."],
    }
    outcome = {
        "result": {
            "phases": phases,
            "provenance": {
                "scientific_source_hash": SCIENCE,
                "frozen_research_changed": False,
                "proof": [],
                "authority": [],
            },
        },
        "costs": costs,
        "source_hash": source,
        "verified": True,
    }
    base.update(
        state="completed",
        approved_at=1001.0,
        started_at=1002.0,
        completed_at=1003.0,
        lease_id="b" * 32,
        lease_expires_at=1002.0 + profile["request_seconds"],
        partial_receipts=partials,
        observed={k: costs[k] for k in base["observed"]},
        outcome=outcome,
        outcome_hash=digest(outcome),
    )
    return json.loads(json.dumps(base)), source


def refresh_approval(plan: dict[str, Any]) -> None:
    plan["request_hash"] = digest({"method": plan["method"], "input": plan["input"], "request_id": plan["request_id"]})
    fields = (
        "plan_id",
        "request_id",
        "request_hash",
        "method",
        "input",
        "executor_id",
        "source_hash",
        "policy_binding",
        "caps",
        "prepared_at",
        "expires_at",
        "request_seconds",
        "production_authority",
    )
    prepared = {key: plan[key] for key in fields}
    prepared.update(state="prepared", observed={key: 0 for key in plan["observed"]}, partial_receipts=[])
    plan["plan_digest"] = digest(prepared)
    for partial in plan["partial_receipts"]:
        partial["request_hash"] = plan["request_hash"]
        partial["transport_digest"] = digest(
            {key: value for key, value in partial.items() if key != "transport_digest"}
        )


def refresh_delivery(plan: dict[str, Any], index: int) -> None:
    current = plan["outcome"]["result"]["phases"][index]
    current["receipt"]["task"] = deepcopy(current["task"])
    current["receipt"]["result"] = deepcopy(current["result"])
    current["receipt_hash"] = digest(current["receipt"])
    partial = plan["partial_receipts"][index]
    partial.update(
        task=deepcopy(current["task"]), result=deepcopy(current["result"]), receipt_hash=current["receipt_hash"]
    )
    partial["transport_digest"] = digest({key: value for key, value in partial.items() if key != "transport_digest"})
    plan["outcome_hash"] = digest(plan["outcome"])


def signed_export(plan: dict[str, Any], source: str) -> dict[str, Any]:
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    body = {
        "schema": "strategy-executor-evidence/v1",
        "journal_identity": "urn:agialpha:ed25519:" + public,
        "journal_record_digest": "e" * 64,
        "source_hash": source,
        "executor_id": plan["executor_id"],
        "plan": plan,
        "production_authority": False,
        "cost_units": {
            "service_work": "declared fixed-method units",
            "improvement_work": "declared construction units",
            "native_calls": "actual native call count",
            "native_solve_seconds": "charged solve allowance seconds; observed solver wall/CPU separate telemetry",
        },
        "limits": "Synthetic unit fixture; no actual browser or production authority.",
    }
    hashed = digest(body)
    return {
        "body": body,
        "sha256": hashed,
        "public_key": public,
        "signature": base64.b64encode(key.sign(bytes.fromhex(hashed))).decode(),
    }


def browser_fixture(export: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    raw = json.dumps(export, indent=2).encode()
    plan = export["body"]["plan"]
    return {
        "schema": "strategy-engineering-browser-acceptance/v1",
        "passed": True,
        "actual_browser": True,
        "browser_engine": "chromium",
        "served_origin": "http://127.0.0.1:8768",
        "source_hash": plan["source_hash"],
        "plan_id": plan["plan_id"],
        "outcome_hash": plan["outcome_hash"],
        "export_sha256": hashlib.sha256(raw).hexdigest(),
        "checks": {name: True for name in BROWSER_CHECKS},
        "tab_closed_during_active_request": True,
        "new_context_recovered_same_mission": True,
        "source_changes_or_mock_browser": False,
        "native_calls": plan["outcome"]["costs"]["native_calls"],
        "phase_receipts": [p["receipt_hash"] for p in plan["partial_receipts"]],
        "unchanged_baseline_invalid_calendar_slots": [4],
        "committed_prefix_preserved": True,
        "requests": [{"url": "http://127.0.0.1:8768/api/strategy-executor/status", "method": "GET"}],
    }, raw


def crash_fixture(profile: dict[str, Any]) -> tuple[dict[str, Any], str]:
    plan, source = completed_plan(profile)
    plan.update(
        state="running",
        partial_receipts=plan["partial_receipts"][:1],
        observed={"service_work": 1, "improvement_work": 0, "native_calls": 2, "native_solve_seconds": 4},
    )
    for name in ("outcome", "outcome_hash", "completed_at"):
        plan.pop(name)
    caps = deepcopy(profile["per_plan_caps"])
    return {
        "schema": "strategy-engineering-crash-recovery/v1",
        "passed": True,
        "actual_supervisor_signal": "SIGKILL",
        "source_hash": source,
        "descendants_observed": 1,
        "descendants_inactive": True,
        "descendant_stop_seconds": 0.01,
        "restarted_state": "running",
        "reserved_before": caps,
        "reserved_after": deepcopy(caps),
        "retained_partial_hashes": [plan["partial_receipts"][0]["receipt_hash"]],
        "duplicate_run_http": 409,
        "early_reconciliation_http": 409,
        "no_automatic_replay": True,
        "unknown_work_refunded": False,
        "operator_interventions": ["Synthetic unit fixture only"],
        "production_authority": False,
        "export": signed_export(plan, source),
    }, source


@pytest.mark.parametrize("version", ["1.42.0", "1.43.0", "1.43.99"])
def test_historical_releases_do_not_require_or_copy_companion(tmp_path: Path, version: str) -> None:
    output = tmp_path / "release"
    assert release.package(tmp_path / "absent-source", output, tmp_path / "absent-evidence", "a" * 40, version) is None
    assert not output.exists()


def test_new_release_without_qualification_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "release"
    with pytest.raises((ValueError, FileNotFoundError)):
        release.package(tmp_path, output, tmp_path / "missing", "a" * 40, "1.44.0")
    assert not output.exists()


def test_strict_json_refuses_duplicate_keys_and_nonfinite_values(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    for body in ('{"passed":true,"passed":false}', '{"cost":NaN}', '{"cost":Infinity}', '{"cost":1e309}'):
        path.write_text(body)
        with pytest.raises(ValueError):
            release._read_json(path)


def test_complete_synthetic_plan_and_signed_export_are_well_formed(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    release._verify_plan(plan, source, profile)
    release._verify_export(signed_export(plan, source), source, profile)


@pytest.mark.parametrize("field", ["source_hash", "plan_digest", "request_hash", "outcome_hash"])
def test_plan_source_and_exact_commitments_cannot_be_substituted(profile: dict[str, Any], field: str) -> None:
    plan, source = completed_plan(profile)
    plan[field] = "0" * 64
    with pytest.raises(ValueError):
        release._verify_plan(plan, source, profile)


@pytest.mark.parametrize(
    "case",
    [
        "missing-approval",
        "approval-before-prepare",
        "start-before-approval",
        "completion-before-start",
        "completion-at-lease-end",
        "completion-after-expiry",
        "overlong-lease",
        "overlong-request",
        "overlong-grant",
    ],
)
def test_exact_approval_profile_and_execution_timing_are_required(profile: dict[str, Any], case: str) -> None:
    plan, source = completed_plan(profile)
    if case == "missing-approval":
        plan.pop("approved_at")
    elif case == "approval-before-prepare":
        plan["approved_at"] = plan["prepared_at"] - 1
    elif case == "start-before-approval":
        plan["started_at"] = plan["approved_at"] - 0.5
    elif case == "completion-before-start":
        plan["completed_at"] = plan["started_at"] - 0.5
    elif case == "completion-at-lease-end":
        plan["completed_at"] = plan["lease_expires_at"]
    elif case == "completion-after-expiry":
        plan["completed_at"] = plan["expires_at"] + 1
    elif case == "overlong-lease":
        plan["lease_expires_at"] = plan["started_at"] + profile["request_seconds"] + 1
    elif case == "overlong-request":
        plan["request_seconds"] = profile["request_seconds"] + 1
        refresh_approval(plan)
    else:
        plan["expires_at"] = plan["prepared_at"] + profile["grant_seconds"] + 1
        refresh_approval(plan)
    with pytest.raises(ValueError):
        release._verify_plan(plan, source, profile)


@pytest.mark.parametrize(
    "case",
    [
        "unrelated-initial",
        "different-changes",
        "repair-baseline",
        "repair-locks",
        "repair-release",
        "repair-disruption",
        "header-only-repair",
        "wrong-observed-at",
    ],
)
def test_valid_hashes_do_not_replace_same_project_task_derivation(profile: dict[str, Any], case: str) -> None:
    plan, source = completed_plan(profile)
    if case in {"unrelated-initial", "different-changes"}:
        if case == "unrelated-initial":
            plan["input"]["initial"]["jobs"][0]["duration"] = 2
        else:
            plan["input"]["changes"]["durations"]["J2"] = 4
        refresh_approval(plan)
    else:
        repair = plan["outcome"]["result"]["phases"][2]
        if case == "repair-baseline":
            repair["task"]["baseline"]["J3"] = 0
        elif case == "repair-locks":
            repair["task"]["locked"].pop("J2")
        elif case == "repair-release":
            repair["task"]["release"]["J3"] = 0
        elif case == "repair-disruption":
            repair["task"]["disruption"]["completed_jobs"].append("J2")
        elif case == "header-only-repair":
            for field in ("baseline", "locked", "release", "disruption"):
                repair["task"].pop(field)
        else:
            repair["baseline_source"]["observed_at"] = 1
        refresh_delivery(plan, 2)
    with pytest.raises(ValueError):
        release._verify_plan(plan, source, profile)


def test_nonbinding_calendar_case_does_not_qualify_publication_repair(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile, binding=False)
    assert (
        plan["outcome"]["result"]["phases"][1]["result"]["schedule"]
        == plan["outcome"]["result"]["phases"][2]["result"]["schedule"]
    )
    assert all(p["receipt"]["checker"]["valid"] for p in plan["outcome"]["result"]["phases"])
    with pytest.raises(ValueError):
        release._verify_plan(plan, source, profile)


def test_checked_flags_and_valid_hashes_do_not_hide_moved_locked_work(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    repaired = plan["outcome"]["result"]["phases"][2]
    repaired["result"]["schedule"][1].update(start=2, end=5)
    refresh_delivery(plan, 2)
    with pytest.raises(ValueError):
        release._verify_plan(plan, source, profile)
    report, raw = browser_fixture(signed_export(plan, source))
    assert report["committed_prefix_preserved"] is True
    with pytest.raises(ValueError):
        release._verify_browser(report, raw, source, profile)


def test_signed_export_rejects_bad_signature_even_with_true_checks(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    document = signed_export(plan, source)
    document["signature"] = base64.b64encode(b"\0" * 64).decode()
    with pytest.raises(ValueError):
        release._verify_export(document, source, profile)


def test_partial_substitution_and_phase_relabelling_are_refused(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    substituted = deepcopy(plan)
    substituted["partial_receipts"][0]["task"]["id"] = "forged-task"
    with pytest.raises(ValueError):
        release._verify_plan(substituted, source, profile)
    repeated = deepcopy(plan)
    repeated["partial_receipts"][1] = deepcopy(repeated["partial_receipts"][0])
    repeated["partial_receipts"][1]["phase_index"] = 1
    repeated["partial_receipts"][1]["transport_digest"] = digest(
        {k: v for k, v in repeated["partial_receipts"][1].items() if k != "transport_digest"}
    )
    with pytest.raises(ValueError):
        release._verify_plan(repeated, source, profile)


def test_plan_cannot_exceed_separate_accounts_or_refund_native_attempts(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    expensive = deepcopy(plan)
    expensive["outcome"]["costs"]["improvement_work"] = plan["caps"]["improvement_work"] + 1
    expensive["observed"]["improvement_work"] = expensive["outcome"]["costs"]["improvement_work"]
    expensive["outcome_hash"] = digest(expensive["outcome"])
    with pytest.raises(ValueError):
        release._verify_plan(expensive, source, profile)
    refunded = deepcopy(plan)
    refunded["outcome"]["costs"]["native_solve_seconds"] = 0
    refunded["observed"]["native_solve_seconds"] = 0
    refunded["outcome_hash"] = digest(refunded["outcome"])
    with pytest.raises(ValueError):
        release._verify_plan(refunded, source, profile)


def test_local_records_never_create_production_authority(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    plan["production_authority"] = True
    with pytest.raises(ValueError):
        release._verify_export(signed_export(plan, source), source, profile)


def test_browser_report_requires_actual_artifact_and_matching_download(profile: dict[str, Any]) -> None:
    plan, source = completed_plan(profile)
    report, raw = browser_fixture(signed_export(plan, source))
    release._verify_browser(report, raw, source, profile)
    for field, value in (
        ("actual_browser", False),
        ("passed", False),
        ("source_hash", "0" * 64),
        ("outcome_hash", "0" * 64),
        ("export_sha256", "0" * 64),
        ("served_origin", "https://unrelated.example"),
        ("checks", {}),
        ("tab_closed_during_active_request", False),
        ("new_context_recovered_same_mission", False),
        ("source_changes_or_mock_browser", True),
        ("native_calls", 0),
        ("phase_receipts", []),
        ("requests", []),
        ("requests", [{"url": "https://unrelated.example/"}]),
        ("unchanged_baseline_invalid_calendar_slots", []),
        ("unchanged_baseline_invalid_calendar_slots", [9]),
        ("committed_prefix_preserved", False),
    ):
        changed = deepcopy(report)
        changed[field] = value
        with pytest.raises(ValueError):
            release._verify_browser(changed, raw, source, profile)


@pytest.mark.parametrize("missing", sorted(BROWSER_CHECKS))
def test_each_actual_browser_check_is_required(profile: dict[str, Any], missing: str) -> None:
    plan, source = completed_plan(profile)
    report, raw = browser_fixture(signed_export(plan, source))
    report["checks"].pop(missing)
    with pytest.raises(ValueError):
        release._verify_browser(report, raw, source, profile)


def test_crash_receipt_retains_unknown_reservations_and_disallows_replay(profile: dict[str, Any]) -> None:
    report, source = crash_fixture(profile)
    release._verify_crash(report, source, profile)
    for field, value in (
        ("reserved_after", {"service_work": 0, "improvement_work": 0, "native_calls": 0, "native_solve_seconds": 0}),
        ("unknown_work_refunded", True),
        ("no_automatic_replay", False),
        ("duplicate_run_http", 200),
        ("early_reconciliation_http", 200),
        ("restarted_state", "completed"),
        ("descendants_inactive", False),
        ("actual_supervisor_signal", "simulated"),
        ("retained_partial_hashes", []),
    ):
        changed = deepcopy(report)
        changed[field] = value
        with pytest.raises(ValueError):
            release._verify_crash(changed, source, profile)


def payload_files() -> dict[str, bytes]:
    root = ROOT / "contrib/strategy_succession"
    project = tomllib.loads((root / "pyproject.toml").read_text())
    names = set(project["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"])
    names.update({"serve.py", "__init__.py", "pyproject.toml", "setup.py"})
    return {release.CONTRIB + name: (root / name).read_bytes() for name in names}


def wheel_fixture(files: dict[str, bytes], changes: dict[str, bytes] | None = None) -> bytes:
    """Construct a synthetic wheel for integrity tests, without invoking a build or browser."""
    project = tomllib.loads(files[release.CONTRIB + "pyproject.toml"].decode())
    version = project["project"]["version"]
    prefix = release.DIST + "-" + version + ".dist-info/"
    names = set(project["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"])
    names.update({"serve.py", "__init__.py"})
    members = {release.PACKAGE + name: files[release.CONTRIB + name] for name in names}
    metadata = [
        "Metadata-Version: 2.4",
        "Name: " + project["project"]["name"],
        "Version: " + version,
        "License-Expression: Apache-2.0",
        "Requires-Python: " + ",".join(sorted(project["project"]["requires-python"].split(","))),
    ]
    metadata.extend("Requires-Dist: " + requirement for requirement in project["project"]["dependencies"])
    members.update(
        {
            prefix + "METADATA": ("\n".join(metadata) + "\n\nSynthetic unit fixture only.\n").encode(),
            prefix
            + "WHEEL": b"Wheel-Version: 1.0\nGenerator: synthetic-unit-fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            prefix
            + "entry_points.txt": b"[console_scripts]\nstrategy-succession-engineering = strategy_succession_engineering.serve:main\n",
            prefix + "top_level.txt": b"strategy_succession_engineering\n",
            prefix + "licenses/LICENSE": files[release.CONTRIB + "LICENSE"],
            prefix
            + "licenses/notices/AGIJobs-MIT-LICENSE.txt": files[release.CONTRIB + "notices/AGIJobs-MIT-LICENSE.txt"],
            prefix + "licenses/worker/LICENSE": files[release.CONTRIB + "worker/LICENSE"],
        }
    )
    members.update(changes or {})
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, data in sorted(members.items()):
        writer.writerow(
            [name, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("="), len(data)]
        )
    writer.writerow([prefix + "RECORD", "", ""])
    members[prefix + "RECORD"] = record.getvalue().encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(members.items()):
            archive.writestr(name, data)
    return stream.getvalue()


def test_exact_payload_wheel_is_required_and_extra_or_changed_members_are_refused() -> None:
    files = payload_files()
    accepted = release._verify_wheel(wheel_fixture(files), files)
    assert accepted["version"] == "0.1.0rc1"
    for changes in (
        {release.PACKAGE + "setup.py": b"unlisted module"},
        {release.PACKAGE + "transport/strategy_executor.py": b"changed code"},
    ):
        with pytest.raises(ValueError):
            release._verify_wheel(wheel_fixture(files, changes), files)


def test_wheel_metadata_cannot_expand_python_or_entrypoint_scope() -> None:
    files = payload_files()
    raw = wheel_fixture(files)
    prefix = release.DIST + "-0.1.0rc1.dist-info/"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        metadata = archive.read(prefix + "METADATA")
    modified = metadata.replace(b"Requires-Python: <3.13,>=3.12", b"Requires-Python: >=3.9")
    with pytest.raises(ValueError):
        release._verify_wheel(wheel_fixture(files, {prefix + "METADATA": modified}), files)
    entrypoints = b"[console_scripts]\nstrategy-succession-engineering = strategy_succession_engineering.serve:main\nextra-command = other_module:main\n"
    with pytest.raises(ValueError):
        release._verify_wheel(wheel_fixture(files, {prefix + "entry_points.txt": entrypoints}), files)


@pytest.mark.parametrize(
    "name,body",
    [
        ("WHEEL", b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py311-none-any\n"),
        ("top_level.txt", b"another_import\n"),
        ("licenses/LICENSE", b"substituted license"),
    ],
)
def test_wheel_tags_imports_and_license_copies_match_declared_source(name: str, body: bytes) -> None:
    files = payload_files()
    prefix = release.DIST + "-0.1.0rc1.dist-info/"
    with pytest.raises(ValueError):
        release._verify_wheel(wheel_fixture(files, {prefix + name: body}), files)


@pytest.mark.parametrize("kind", ["wheel", "metadata"])
def test_unknown_wheel_or_metadata_format_versions_are_refused(kind: str) -> None:
    files = payload_files()
    prefix = release.DIST + "-0.1.0rc1.dist-info/"
    raw = wheel_fixture(files)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = "WHEEL" if kind == "wheel" else "METADATA"
        before = b"Wheel-Version: 1.0" if kind == "wheel" else b"Metadata-Version: 2.4"
        after = b"Wheel-Version: 99.0" if kind == "wheel" else b"Metadata-Version: 99.0"
        changed = archive.read(prefix + name).replace(before, after)
    with pytest.raises(ValueError):
        release._verify_wheel(wheel_fixture(files, {prefix + name: changed}), files)


@pytest.fixture
def package_fixture(tmp_path: Path, profile: dict[str, Any]) -> tuple[Path, Path, Path, str, dict[str, bytes]]:
    root, evidence, output = tmp_path / "source", tmp_path / "evidence", tmp_path / "release"
    root.mkdir()
    files = payload_files()
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    subprocess.run(["git", "-c", "init.templateDir=", "init", "--quiet", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Unit Fixture",
            "-c",
            "user.email=unit@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--quiet",
            "-m",
            "Synthetic source fixture",
        ],
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    evidence.mkdir()
    name = release.DIST + "-0.1.0rc1-py3-none-any.whl"
    raw = wheel_fixture(files)
    (evidence / name).write_bytes(raw)
    (evidence / "reproduced-wheel").mkdir()
    (evidence / "reproduced-wheel" / name).write_bytes(raw)
    inventory = {
        "schema": "strategy-engineering-source-inventory/v1",
        "commit": commit,
        "version": "1.44.0",
        "files": {n: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in files.items()},
    }
    inventory_raw = json.dumps(inventory, indent=2).encode()
    (evidence / "source-inventory.json").write_bytes(inventory_raw)
    qualification = {
        "schema": "strategy-engineering-release-qualification/v1",
        "commit": commit,
        "version": "1.44.0",
        "companion_version": "0.1.0rc1",
        "wheel": {"name": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
        "source_inventory_sha256": hashlib.sha256(inventory_raw).hexdigest(),
        "installed_outside_checkout": True,
        "reproducible": True,
        "runtime_version": "1.42.0",
        "runtime_wheel_sha256": release.PUBLIC_RUNTIME,
        "child_environment": child_environment(profile),
        "checks": {
            name: True
            for name in (
                "transport",
                "worker",
                "environment",
                "integration",
                "browser",
                "crash_recovery",
                "dependency_audit",
            )
        },
    }
    (evidence / "qualification.json").write_text(json.dumps(qualification))
    audited = []
    for line in files[release.CONTRIB + "requirements-qualification.txt"].decode().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            dependency, version = line.strip().split("==")
            if dependency != "alpha-factory-v1":
                audited.append({"name": dependency, "version": version, "vulns": []})
    (evidence / "dependency-audit.json").write_text(
        json.dumps(
            {"schema": "strategy-engineering-dependency-audit/v1", "commit": commit, "passed": True, "packages": 25}
        )
    )
    (evidence / "pip-audit.json").write_text(json.dumps({"dependencies": audited, "fixes": []}))
    public = evidence / "acceptance-public"
    public.mkdir()
    plan, source = completed_plan(profile)
    browser, download = browser_fixture(signed_export(plan, source))
    (public / "browser-acceptance.json").write_text(json.dumps(browser))
    (public / "browser-mission-export.json").write_bytes(download)
    (public / "integrated-journey.json").write_text(json.dumps(plan))
    (public / "integrated-summary.json").write_text(
        json.dumps(
            {
                "source_hash": source,
                "outcome_hash": plan["outcome_hash"],
                "costs": plan["outcome"]["costs"],
                "child_environment": child_environment(profile),
            }
        )
    )
    crash, _ = crash_fixture(profile)
    (public / "crash-recovery.json").write_text(json.dumps(crash))
    return root, evidence, output, commit, files


def test_package_copies_only_three_assets_after_complete_integrity_admission(package_fixture) -> None:
    root, evidence, output, commit, _ = package_fixture
    result = release.package(root, output, evidence, commit, "1.44.0")
    assert result["production_authority"] is False and result["runtime_version"] == "1.42.0"
    assert len(list(output.iterdir())) == 3
    assert set(result["assets"]) == {p.name for p in output.iterdir()}
    assert release.package(root, output, evidence, commit, "1.44.0") == result


def test_existing_release_asset_is_never_overwritten(package_fixture) -> None:
    root, evidence, output, commit, _ = package_fixture
    output.mkdir()
    target = output / (release.DIST + "-0.1.0rc1-py3-none-any.whl")
    target.write_bytes(b"accepted existing bytes")
    with pytest.raises(ValueError):
        release.package(root, output, evidence, commit, "1.44.0")
    assert target.read_bytes() == b"accepted existing bytes" and len(list(output.iterdir())) == 1


@pytest.mark.parametrize("case", ["missing", "false"])
def test_qualification_environment_check_is_explicitly_required(package_fixture, case: str) -> None:
    root, evidence, output, commit, _ = package_fixture
    path = evidence / "qualification.json"
    qualification = json.loads(path.read_text())
    if case == "missing":
        qualification["checks"].pop("environment")
    else:
        qualification["checks"]["environment"] = False
    path.write_text(json.dumps(qualification))
    with pytest.raises(ValueError):
        release.package(root, output, evidence, commit, "1.44.0")
    assert not output.exists()


def test_exact_sanitized_child_environment_is_accepted(profile: dict[str, Any]) -> None:
    record = child_environment(profile)
    assert len(record["observation"]["dependencies"]) == 26
    release._verify_child_environment(record, profile)


@pytest.mark.parametrize(
    "case",
    [
        "wrong-dependency-version",
        "missing-dependency",
        "missing-native-import",
        "wrong-sha256",
        "false-invocation-context",
        "false-prefix-context",
        "raw-path-field",
        "wrong-python-version",
    ],
)
def test_child_environment_requires_exact_actual_context_dependencies_and_sanitization(
    profile: dict[str, Any], case: str
) -> None:
    record = child_environment(profile)
    observed = record["observation"]
    if case == "wrong-dependency-version":
        observed["dependencies"]["scipy"] = "0.0.0"
    elif case == "missing-dependency":
        observed["dependencies"].pop("alpha-factory-v1")
    elif case == "missing-native-import":
        observed["native_imports"].pop("numpy")
    elif case == "false-invocation-context":
        observed["invocation_context_matches"] = False
    elif case == "false-prefix-context":
        observed["prefix_context_matches"] = False
    elif case == "raw-path-field":
        observed["python_executable"] = "/synthetic/private/venv/bin/python"
    elif case == "wrong-python-version":
        observed["python_version"] = "0.0.0"
    record["sha256"] = "0" * 64 if case == "wrong-sha256" else digest(observed)
    with pytest.raises(ValueError):
        release._verify_child_environment(record, profile)


def test_qualification_requires_child_environment_not_only_parent_environment_check(package_fixture) -> None:
    root, evidence, output, commit, _ = package_fixture
    path = evidence / "qualification.json"
    qualification = json.loads(path.read_text())
    assert qualification["checks"]["environment"] is True
    qualification.pop("child_environment")
    path.write_text(json.dumps(qualification))
    with pytest.raises(ValueError):
        release.package(root, output, evidence, commit, "1.44.0")
    assert not output.exists()


@pytest.mark.parametrize("case", ["wrong-commit", "wheel-bytes", "reproduced-wheel"])
def test_qualification_booleans_do_not_replace_commit_wheel_or_rebuild_identity(package_fixture, case: str) -> None:
    root, evidence, output, commit, _ = package_fixture
    path = evidence / "qualification.json"
    qualification = json.loads(path.read_text())
    if case == "wrong-commit":
        qualification["commit"] = "0" * 40
        path.write_text(json.dumps(qualification))
    else:
        wheel = evidence / qualification["wheel"]["name"]
        if case == "reproduced-wheel":
            wheel = evidence / "reproduced-wheel" / wheel.name
        wheel.write_bytes(wheel.read_bytes() + b"unqualified bytes")
    with pytest.raises(ValueError):
        release.package(root, output, evidence, commit, "1.44.0")
    assert not output.exists()


@pytest.mark.parametrize(
    "artifact",
    [
        "qualification.json",
        "source-inventory.json",
        "acceptance-public/browser-acceptance.json",
        "acceptance-public/browser-mission-export.json",
        "acceptance-public/crash-recovery.json",
    ],
)
def test_missing_required_artifact_never_creates_release_outputs(package_fixture, artifact: str) -> None:
    root, evidence, output, commit, _ = package_fixture
    (evidence / artifact).unlink()
    with pytest.raises(ValueError):
        release.package(root, output, evidence, commit, "1.44.0")
    assert not output.exists()


def test_git_inventory_ignores_uncommitted_replacement_and_refuses_wrong_report(package_fixture) -> None:
    root, evidence, output, commit, files = package_fixture
    changed = root / (release.CONTRIB + "transport/strategy_executor.py")
    changed.write_text("uncommitted replacement")
    assert (
        release._committed_files(root, commit)[release.CONTRIB + "transport/strategy_executor.py"]
        == files[release.CONTRIB + "transport/strategy_executor.py"]
    )
    inventory_path = evidence / "source-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    inventory["files"][release.CONTRIB + "transport/strategy_executor.py"]["sha256"] = hashlib.sha256(
        changed.read_bytes()
    ).hexdigest()
    raw = json.dumps(inventory).encode()
    inventory_path.write_bytes(raw)
    qualification = json.loads((evidence / "qualification.json").read_text())
    qualification["source_inventory_sha256"] = hashlib.sha256(raw).hexdigest()
    (evidence / "qualification.json").write_text(json.dumps(qualification))
    with pytest.raises(ValueError):
        release.package(root, output, evidence, commit, "1.44.0")
    assert not output.exists()


@pytest.mark.parametrize("case", ["vulnerability", "skip", "missing-version", "wrong-version", "missing-package"])
def test_dependency_audit_cannot_hide_vulnerability_skip_or_incomplete_versions(package_fixture, case: str) -> None:
    root, evidence, output, commit, files = package_fixture
    report = json.loads((evidence / "dependency-audit.json").read_text())
    raw = json.loads((evidence / "pip-audit.json").read_text())
    if case == "vulnerability":
        raw["dependencies"][0]["vulns"] = [{"id": "SYNTHETIC-UNIT-CASE"}]
    elif case == "skip":
        raw["dependencies"][0]["skip_reason"] = "synthetic unavailable audit"
    elif case == "missing-version":
        raw["dependencies"][0].pop("version")
    elif case == "wrong-version":
        raw["dependencies"][0]["version"] = "0.0.0"
    else:
        raw["dependencies"].pop()
    with pytest.raises(ValueError):
        release._verify_dependency_audit(report, raw, files[release.CONTRIB + "requirements-qualification.txt"], commit)
    assert not output.exists()


@pytest.mark.parametrize("case", ["missing", "substituted"])
def test_installed_run_and_qualification_must_share_actual_child_witness(package_fixture, case: str) -> None:
    root, evidence, output, commit, _ = package_fixture
    path = evidence / "acceptance-public/integrated-summary.json"
    summary = json.loads(path.read_text())
    if case == "missing":
        summary.pop("child_environment")
    else:
        summary["child_environment"]["sha256"] = "0" * 64
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="summary substitutes"):
        release.package(root, output, evidence, commit, "1.44.0")
    assert not output.exists()
