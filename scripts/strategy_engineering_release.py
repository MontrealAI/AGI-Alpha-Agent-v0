# SPDX-License-Identifier: Apache-2.0
"""Verify and add the fixed Strategy companion to the existing Alpha publisher.

This helper does no dispatch, upload, tagging or publication. Required hosted
workflow gates retain their own authority; these checks bind their concrete
package, browser, installed-runtime and recovery evidence to committed bytes.
"""
from __future__ import annotations

import ast
import base64
import csv
from configparser import ConfigParser
from copy import deepcopy
from email.parser import BytesParser
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tomllib
from typing import Any, cast
from urllib.parse import urlsplit
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packaging.specifiers import SpecifierSet

CONTRIB = "contrib/strategy_succession/"
PACKAGE = "strategy_succession_engineering/"
DIST = "agi_alpha_strategy_succession_engineering"
SCIENTIFIC = "7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7"
PUBLIC_RUNTIME = "fff8c6c8a8dbeeebf1f91cc8e9a3fae17113baac93b6ed0d6096ecb59d072554"
PUBLIC_PREPARER_SCOPE = "exact generated source HTML opened locally; public Pages is separately qualified"
COUNTERS = ("service_work", "improvement_work", "native_calls", "native_solve_seconds")
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
    "fresh_distinct_graph",
    "bilingual_scope_and_recovery",
    "readable_report_download",
    "input_preflight_no_authority",
    "public_preparer_input_identity",
}
PLAN_FIELDS = (
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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read(path: Path, maximum: int = 5_000_000) -> bytes:
    try:
        info = path.lstat()
    except OSError as error:
        raise ValueError("Required Strategy acceptance artifact is missing") from error
    _require(
        stat.S_ISREG(info.st_mode) and info.st_size <= maximum, "Acceptance artifacts must be bounded regular files"
    )
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        _require(
            stat.S_ISREG(opened.st_mode) and (opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino),
            "Acceptance artifact changed during inspection",
        )
        data = stream.read(maximum + 1)
    _require(len(data) <= maximum, "Acceptance artifact grew beyond its limit")
    return data


def _json(data: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in items:
            _require(key not in value, "Duplicate acceptance JSON key")
            value[key] = child
        return value

    def constant(_value: str) -> Any:
        raise ValueError("Nonfinite acceptance quantity")

    def finite_float(value: str) -> float:
        result = float(value)
        _require(math.isfinite(result), "Nonfinite acceptance quantity")
        return result

    value = json.loads(data, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)
    _require(isinstance(value, dict), "Acceptance artifact must be a JSON object")
    return cast(dict[str, Any], value)


def _read_json(path: Path) -> dict[str, Any]:
    return _json(_read(path))


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _source_hash(profile_raw: bytes) -> str:
    profile = _json(profile_raw)
    sources = {"installation-profile": hashlib.sha256(profile_raw).hexdigest(), **profile["files"]}
    sources.update(
        {"runtime/" + name: profile["runtime_python_files"][name] for name in profile["runtime_enforcement_files"]}
    )
    return _digest(sources)


def _committed_files(root: Path, commit: str) -> dict[str, bytes]:
    _require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "An exact Git commit is required")
    listing = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-rz", commit, "--", CONTRIB], check=True, capture_output=True
    ).stdout
    modes: dict[str, str] = {}
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        modes[name.decode()] = metadata.decode().split()[0]

    def body(name: str) -> bytes:
        _require(modes.get(name) in {"100644", "100755"}, "Companion source must be a committed regular file")
        value = subprocess.run(
            ["git", "-C", str(root), "show", "--no-textconv", commit + ":" + name], check=True, capture_output=True
        ).stdout
        _require(len(value) <= 8_000_000, "Committed companion source exceeds its bound")
        return value

    config = tomllib.loads(body(CONTRIB + "pyproject.toml").decode())
    payload = config["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"]
    names = {*payload, "serve.py", "__init__.py", "pyproject.toml", "setup.py"}
    _require(1 <= len(names) <= 256, "Invalid companion source inventory")
    result: dict[str, bytes] = {}
    for name in sorted(names):
        path = PurePosixPath(name)
        _require(
            isinstance(name, str)
            and path.as_posix() == name
            and not path.is_absolute()
            and not any(p in {"", ".", ".."} for p in name.split("/"))
            and "\\" not in name,
            "Companion source path escapes its fixed scope",
        )
        result[CONTRIB + name] = body(CONTRIB + name)
    return result


def _verify_wheel(raw: bytes, files: dict[str, bytes]) -> dict[str, Any]:
    project = tomllib.loads(files[CONTRIB + "pyproject.toml"].decode())
    version = project["project"]["version"]
    module = ast.parse(files[CONTRIB + "__init__.py"].decode("utf-8"))
    assignments = [
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
    ]
    _require(
        len(module.body) == 2
        and isinstance(module.body[0], ast.Expr)
        and isinstance(module.body[0].value, ast.Constant)
        and type(module.body[0].value.value) is str
        and len(assignments) == 1
        and module.body[1] is assignments[0]
        and len(assignments[0].targets) == 1
        and isinstance(assignments[0].value, ast.Constant)
        and type(assignments[0].value.value) is str
        and assignments[0].value.value == version,
        "Literal package __version__ differs from distribution metadata",
    )
    _require(project["project"]["name"] == "agi-alpha-strategy-succession-engineering", "Wrong companion project")
    payload = {
        *project["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"],
        "serve.py",
        "__init__.py",
    }
    profile_raw = files[CONTRIB + "ENGINEERING_MANIFEST.json"]
    profile = _json(profile_raw)
    _require(
        profile.get("schema") == "strategy-engineering-installation/v1"
        and profile.get("qualified_runtime_versions") == ["1.42.0"]
        and profile.get("public_runtime_wheel_sha256") == PUBLIC_RUNTIME
        and profile.get("scientific_source_hash") == SCIENTIFIC,
        "Companion runtime/scientific profile is unqualified",
    )
    _require(set(profile["files"]) == payload - {"ENGINEERING_MANIFEST.json"}, "Incomplete installed source guard")
    for name, expected in profile["files"].items():
        _require(hashlib.sha256(files[CONTRIB + name]).hexdigest() == expected, "Guarded source differs from Git")
    metadata_prefix = DIST + "-" + version + ".dist-info/"
    metadata_names = {
        metadata_prefix + n
        for n in (
            "METADATA",
            "WHEEL",
            "entry_points.txt",
            "top_level.txt",
            "RECORD",
            "licenses/LICENSE",
            "licenses/notices/AGIJobs-MIT-LICENSE.txt",
            "licenses/worker/LICENSE",
        )
    }
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [i.filename for i in entries]
        _require(len(names) == len(set(names)), "Duplicate wheel member")
        _require(set(names) == {PACKAGE + n for n in payload} | metadata_names, "Unexpected or missing wheel payload")
        _require(
            sum(i.file_size for i in entries) <= 50_000_000
            and all(i.file_size <= 8_000_000 and not stat.S_ISLNK(i.external_attr >> 16) for i in entries),
            "Unbounded or linked wheel payload",
        )
        _require(archive.testzip() is None, "Wheel CRC verification failed")
        for name in payload:
            _require(archive.read(PACKAGE + name) == files[CONTRIB + name], "Wheel source differs from committed bytes")
        metadata = BytesParser().parsebytes(archive.read(metadata_prefix + "METADATA"))
        _require(
            metadata["Name"] == project["project"]["name"]
            and metadata["Version"] == version
            and metadata["Metadata-Version"] == "2.4",
            "Companion wheel metadata identity mismatch",
        )
        _require(
            SpecifierSet(metadata["Requires-Python"] or "") == SpecifierSet(project["project"]["requires-python"])
            and metadata["License-Expression"] == "Apache-2.0",
            "Companion interpreter/license metadata mismatch",
        )
        _require(
            set(metadata.get_all("Requires-Dist", [])) == set(project["project"]["dependencies"]),
            "Companion dependency inventory mismatch",
        )
        entrypoints = ConfigParser()
        entrypoints.read_string(archive.read(metadata_prefix + "entry_points.txt").decode())
        _require(
            entrypoints.sections() == ["console_scripts"]
            and dict(entrypoints["console_scripts"])
            == {"strategy-succession-engineering": "strategy_succession_engineering.serve:main"},
            "Unexpected companion entry point",
        )
        wheel_metadata = BytesParser().parsebytes(archive.read(metadata_prefix + "WHEEL"))
        _require(
            wheel_metadata.get_all("Tag") == ["py3-none-any"]
            and wheel_metadata["Root-Is-Purelib"] == "true"
            and wheel_metadata["Wheel-Version"] == "1.0",
            "Companion wheel platform/interpreter tag mismatch",
        )
        _require(
            archive.read(metadata_prefix + "top_level.txt") == b"strategy_succession_engineering\n",
            "Companion top-level import inventory mismatch",
        )
        for name in ("LICENSE", "notices/AGIJobs-MIT-LICENSE.txt", "worker/LICENSE"):
            _require(
                archive.read(metadata_prefix + "licenses/" + name) == files[CONTRIB + name],
                "Companion license copy differs from committed bytes",
            )
        record = list(csv.reader(io.StringIO(archive.read(metadata_prefix + "RECORD").decode())))
        _require(len(record) == len(names) and {r[0] for r in record} == set(names), "Wheel RECORD is incomplete")
        for name, expected_hash, expected_size in record:
            if name == metadata_prefix + "RECORD":
                _require(expected_hash == expected_size == "", "Wheel RECORD self-entry is invalid")
                continue
            data = archive.read(name)
            actual = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
            _require(expected_hash == actual and expected_size == str(len(data)), "Wheel RECORD hash mismatch")
    return {
        "version": version,
        "profile": profile,
        "profile_raw": profile_raw,
        "source_hash": _source_hash(profile_raw),
    }


def _empty_authority(value: Any, depth: int = 0) -> None:
    _require(depth <= 64, "Evidence nesting exceeds its bound")
    if isinstance(value, dict):
        for name, child in value.items():
            if name in {"proof", "authority"}:
                _require(child == [], "Local evidence cannot inherit proof or authority")
            if name == "production_authority":
                _require(child is False, "Local evidence cannot grant production authority")
            if name == "grants":
                _require(child in ([], {}), "Exported active grants are prohibited")
            _empty_authority(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _empty_authority(child, depth + 1)


def _verify_plan(
    plan: dict[str, Any],
    source_hash: str,
    profile: dict[str, Any],
    *,
    complete: bool = True,
    require_improvement: bool = True,
) -> dict[str, Any]:
    _require(type(require_improvement) is bool, "Improvement admission mode must be explicit boolean")
    _empty_authority(plan)
    _require(
        plan.get("source_hash") == source_hash
        and plan.get("production_authority") is False
        and plan.get("executor_id") == profile["executor_id"],
        "Mission source or authority mismatch",
    )
    _require(plan.get("method") == "run-journey", "Acceptance must execute the real three-phase journey")
    _require(
        plan["request_hash"]
        == _digest({"method": plan["method"], "input": plan["input"], "request_id": plan["request_id"]}),
        "Mission input commitment mismatch",
    )
    _require(
        plan["plan_id"] == _digest({"request_id": plan["request_id"]})[:32], "Mission idempotency identity mismatch"
    )
    prepared = {k: plan[k] for k in PLAN_FIELDS}
    prepared.update(state="prepared", observed={k: 0 for k in COUNTERS}, partial_receipts=[])
    _require(_digest(prepared) == plan["plan_digest"], "Prepared approval envelope mismatch")
    time_fields = ("prepared_at", "expires_at", "approved_at", "started_at", "lease_expires_at")
    _require(all(_number(plan.get(k)) for k in time_fields), "Approval/start/lease timestamps are missing or invalid")
    _require(
        type(plan["request_seconds"]) is int
        and plan["request_seconds"] == profile["request_seconds"]
        and math.isclose(plan["expires_at"] - plan["prepared_at"], profile["grant_seconds"], rel_tol=0, abs_tol=0.001),
        "Approval lifetime differs from the installed profile",
    )
    _require(
        plan["prepared_at"] <= plan["approved_at"] <= plan["started_at"] < plan["expires_at"]
        and plan["started_at"]
        <= plan["lease_expires_at"]
        <= min(plan["expires_at"], plan["started_at"] + plan["request_seconds"] + 0.001),
        "Approval/start/lease ordering is invalid",
    )
    if complete:
        _require(
            _number(plan.get("completed_at"))
            and plan["started_at"] <= plan["completed_at"] < min(plan["expires_at"], plan["lease_expires_at"]),
            "Completion occurred outside the approved lease",
        )
    caps = plan["caps"]
    _require(
        set(caps) == set(COUNTERS)
        and all(_number(caps[k]) for k in COUNTERS)
        and all(type(caps[k]) is int for k in COUNTERS[:3]),
        "Invalid mission caps",
    )
    expected = profile["per_plan_caps"]
    _require(
        all(caps[k] == expected[k] for k in ("service_work", "improvement_work"))
        and (caps["native_calls"], caps["native_solve_seconds"])
        in {(0, 0), (expected["native_calls"], expected["native_solve_seconds"])},
        "Unqualified mission budget",
    )
    partials_raw = plan.get("partial_receipts")
    _require(
        isinstance(plan.get("observed"), dict)
        and set(plan["observed"]) == set(COUNTERS)
        and all(_number(plan["observed"][k]) and plan["observed"][k] <= caps[k] for k in COUNTERS)
        and all(type(plan["observed"][k]) is int for k in COUNTERS[:3]),
        "Observed request accounting is invalid",
    )
    _require(
        isinstance(partials_raw, list) and (len(partials_raw) == 3 if complete else 1 <= len(partials_raw) <= 3),
        "Checked partial deliveries are missing",
    )
    partials = cast(list[dict[str, Any]], partials_raw)
    seen_hashes: set[str] = set()
    seen_tasks: set[str] = set()
    for index, partial in enumerate(partials):
        _require(
            partial.get("schema") == "strategy-executor-partial/v1"
            and partial.get("phase_index") == index
            and partial.get("source_hash") == source_hash
            and partial.get("scientific_source_hash") == SCIENTIFIC
            and partial.get("request_hash") == plan["request_hash"]
            and partial.get("policy_binding") == plan["policy_binding"]
            and partial.get("proof") == partial.get("authority") == [],
            "Partial delivery source/order/authority mismatch",
        )
        body = {k: v for k, v in partial.items() if k != "transport_digest"}
        _require(_digest(body) == partial["transport_digest"], "Partial transport digest mismatch")
        receipt = {
            "source_hash": source_hash,
            "scientific_source_hash": SCIENTIFIC,
            "task": partial["task"],
            "result": partial["result"],
            "checker": partial["checker"],
            "method": partial["selectedmethod"],
            "proof": [],
            "authority": [],
        }
        task_id = partial["task"].get("id")
        _require(
            isinstance(task_id, str)
            and bool(task_id)
            and partial["result"].get("task_id") == task_id
            and partial["checker"].get("valid") is True,
            "Partial delivery has no matching checked result",
        )
        _require(
            _digest(receipt) == partial["receipt_hash"]
            and partial["receipt_hash"] not in seen_hashes
            and task_id not in seen_tasks,
            "Partial receipt substitution or relabelled generation",
        )
        seen_hashes.add(partial["receipt_hash"])
        seen_tasks.add(task_id)
    if not complete:
        _require(
            plan.get("state") in {"running", "unknown", "reconciled"}, "Crash evidence hides its uncertain outcome"
        )
        return plan
    _require(plan.get("state") == "completed", "Journey did not complete")
    outcome = plan["outcome"]
    _require(
        set(outcome) == {"result", "costs", "source_hash", "verified"}
        and outcome["verified"] is True
        and outcome["source_hash"] == source_hash
        and _digest(outcome) == plan["outcome_hash"],
        "Completed outcome hash/source mismatch",
    )
    costs = outcome["costs"]
    _require(
        set(costs) == {*COUNTERS, "unknown_costs"}
        and isinstance(costs["unknown_costs"], list)
        and all(_number(costs[k]) and costs[k] <= caps[k] for k in COUNTERS)
        and all(type(costs[k]) is int for k in COUNTERS[:3]),
        "Actual mission cost inventory is invalid",
    )
    _require(
        costs["service_work"] > 0
        and (costs["improvement_work"] > 0 if require_improvement else costs["improvement_work"] == 0)
        and costs["native_solve_seconds"] == 2 * costs["native_calls"],
        "Separate productive work or charged native allowance is absent",
    )
    _require(plan["observed"] == {k: costs[k] for k in COUNTERS}, "Observed work differs from final accounting")
    phases = outcome["result"]["phases"]
    _require(len(phases) == 3, "Three distinct actual deliveries are required")
    for phase, partial in zip(phases, partials):
        _require(
            phase.get("verified") is True
            and phase.get("qualified") is True
            and phase.get("receipt_hash") == partial["receipt_hash"]
            and phase.get("task") == partial["task"]
            and phase.get("result") == partial["result"]
            and phase.get("selected_method") == partial["selectedmethod"],
            "Final deliveries do not match committed checked partials",
        )
        _require(
            _digest(phase["receipt"]) == phase["receipt_hash"]
            and phase["receipt"].get("proof") == phase["receipt"].get("authority") == [],
            "Final receipt integrity/authority mismatch",
        )
    semantic_fields = {
        "kind",
        "jobs",
        "capacity",
        "release",
        "deadline",
        "locked",
        "baseline",
        "movement_limit",
        "horizon",
        "disruption",
    }
    initial_task = {k: v for k, v in phases[0]["task"].items() if k in semantic_fields and v != {}}
    changed_task = {k: v for k, v in phases[1]["task"].items() if k in semantic_fields and v != {}}
    _require(
        initial_task != changed_task
        and phases[2]["baseline_source"]["receipt_hash"] == phases[1]["receipt_hash"]
        and phases[2]["baseline_source"].get("verified") is True,
        "Changed work or actual predecessor-based repair is absent",
    )
    _verify_task_derivation(plan["input"], phases)
    return plan


def _verify_task_derivation(supplied: dict[str, Any], phases: list[dict[str, Any]]) -> None:
    _require(
        isinstance(supplied, dict)
        and isinstance(supplied.get("initial"), dict)
        and isinstance(supplied.get("changes"), dict)
        and isinstance(supplied.get("repair"), dict),
        "Approved journey input is incomplete",
    )
    initial = supplied["initial"]
    _require(phases[0]["task"] == initial and initial.get("kind") == "plan", "First delivery ignores the approved task")
    changed = deepcopy(initial)
    changed["id"] = initial["id"][:110] + "-changed"
    changes = supplied["changes"]
    _require(
        set(changes) <= {"durations", "crew", "capacity", "release", "deadline"},
        "Unsupported approved requirement change",
    )
    for field, target in (("durations", "duration"), ("crew", "crew")):
        for job_id, value in changes.get(field, {}).items():
            matches = [j for j in changed["jobs"] if j["id"] == job_id]
            _require(len(matches) == 1, "Changed requirements name an unknown/duplicate job")
            matches[0][target] = value
    for field in ("capacity", "release", "deadline"):
        if field in changes:
            changed[field] = deepcopy(changes[field])
    _require(phases[1]["task"] == changed, "Second delivery does not implement the approved changed requirements")
    repair = supplied["repair"]
    _require(
        set(repair) <= {"observed_at", "capacity", "deadline", "movement_limit"}
        and type(repair.get("observed_at")) is int
        and 0 <= repair["observed_at"] < len(changed["capacity"]),
        "Repair observation is missing or out of scope",
    )
    observed = repair["observed_at"]
    schedule_raw = phases[1]["result"].get("schedule")
    _require(
        isinstance(schedule_raw, list)
        and len(schedule_raw) == len(changed["jobs"])
        and {r["id"] for r in schedule_raw} == {j["id"] for j in changed["jobs"]}
        and all(
            type(r.get("start")) is int and type(r.get("end")) is int and 0 <= r["start"] < r["end"]
            for r in schedule_raw
        ),
        "The preceding delivery has no complete checked schedule",
    )
    schedule = cast(list[dict[str, Any]], schedule_raw)
    repaired = deepcopy(changed)
    repaired.update(
        kind="repair",
        id=changed["id"][:110] + "-repair",
        baseline={r["id"]: r["start"] for r in schedule},
        locked={r["id"]: r["start"] for r in schedule if r["start"] < observed},
    )
    previous_release = changed.get("release", {})
    repaired["release"] = {
        j["id"]: (
            previous_release.get(j["id"], 0)
            if j["id"] in repaired["locked"]
            else max(previous_release.get(j["id"], 0), observed)
        )
        for j in changed["jobs"]
    }
    for field in ("capacity", "deadline", "movement_limit"):
        if field in repair:
            repaired[field] = deepcopy(repair[field])
    _require(
        len(repaired["capacity"]) == len(changed["capacity"])
        and repaired["capacity"][:observed] == changed["capacity"][:observed],
        "Repair changed the observed past or planning horizon",
    )
    disruption = {
        "observed_at": observed,
        "completed_jobs": [r["id"] for r in schedule if r["end"] <= observed],
        "in_progress_jobs": [r["id"] for r in schedule if r["start"] < observed < r["end"]],
    }
    repaired["disruption"] = disruption
    _require(
        phases[2]["task"] == repaired,
        "Repair baseline, locks, releases or disruption do not derive from the actual preceding result",
    )
    source = phases[2]["baseline_source"]
    _require(
        source.get("task_id") == changed["id"] and all(source.get(k) == v for k, v in disruption.items()),
        "Repair provenance substitutes a different observed planning prefix",
    )
    observations = _calendar_repair_observations(phases)
    _require(
        bool(observations["invalid_calendar_slots"]) and observations["committed_prefix_preserved"] is True,
        "Acceptance must repair an actual calendar conflict while preserving committed work",
    )


def _calendar_repair_observations(phases: list[dict[str, Any]]) -> dict[str, Any]:
    previous, repaired = phases[1], phases[2]
    capacity = repaired["task"]["capacity"]
    jobs = {j["id"]: j for j in previous["task"]["jobs"]}
    _require(
        1 <= len(jobs) <= 18
        and len(jobs) == len(previous["task"]["jobs"])
        and 1 <= len(capacity) <= 128
        and all(type(n) is int and 0 <= n <= 4 for n in capacity),
        "Calendar repair evidence exceeds its finite grammar",
    )
    load = [0] * len(capacity)
    original_schedule = previous["result"]["schedule"]
    for row in original_schedule:
        _require(
            row["id"] in jobs
            and type(row.get("start")) is int
            and type(row.get("end")) is int
            and 0 <= row["start"] < row["end"] <= len(capacity)
            and type(jobs[row["id"]].get("crew")) is int
            and 1 <= jobs[row["id"]]["crew"] <= 4,
            "Prior schedule cannot supply bounded calendar-load evidence",
        )
        for slot in range(row["start"], row["end"]):
            load[slot] += jobs[row["id"]]["crew"]
    original = {r["id"]: r for r in original_schedule}
    final_rows = repaired["result"].get("schedule")
    _require(isinstance(final_rows, list) and len(final_rows) == len(jobs), "Repaired schedule is incomplete")
    final = {r["id"]: r for r in final_rows}
    _require(set(final) == set(jobs), "Repaired schedule substitutes or duplicates project jobs")
    prefix = all(
        final[job]["start"] == start and final[job]["end"] == original[job]["end"]
        for job, start in repaired["task"]["locked"].items()
    )
    return {
        "invalid_calendar_slots": [slot for slot, value in enumerate(load) if value > capacity[slot]],
        "committed_prefix_preserved": prefix,
    }


def _verify_export(
    document: dict[str, Any],
    source_hash: str,
    profile: dict[str, Any],
    *,
    complete: bool = True,
    require_improvement: bool = True,
) -> dict[str, Any]:
    _require(set(document) == {"body", "sha256", "public_key", "signature"}, "Unsupported signed mission export")
    body = document["body"]
    _empty_authority(body)
    _require(
        body.get("schema") == "strategy-executor-evidence/v1"
        and body.get("production_authority") is False
        and body.get("source_hash") == source_hash
        and body.get("executor_id") == profile["executor_id"],
        "Exported source/authority mismatch",
    )
    _require(
        _digest(body) == document["sha256"]
        and body["journal_identity"] == "urn:agialpha:ed25519:" + document["public_key"],
        "Signed export body or local identity mismatch",
    )
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(document["public_key"])).verify(
            base64.b64decode(document["signature"], validate=True), bytes.fromhex(document["sha256"])
        )
    except Exception as error:
        raise ValueError("Mission export signature is invalid") from error
    return _verify_plan(body["plan"], source_hash, profile, complete=complete, require_improvement=require_improvement)


def _verify_service_schedule(task: dict[str, Any], result: dict[str, Any]) -> None:
    """Check this bounded planning control arithmetically, without a solver."""
    jobs = {job["id"]: job for job in task["jobs"]}
    rows = {row["id"]: row for row in result["schedule"]}
    capacity = task["capacity"]
    _require(
        1 <= len(jobs) <= 18
        and len(jobs) == len(task["jobs"])
        and len(rows) == len(result["schedule"]) == len(jobs)
        and set(rows) == set(jobs)
        and 1 <= len(capacity) <= 128
        and all(type(n) is int and 0 <= n <= 4 for n in capacity),
        "Service-only schedule inventory is invalid",
    )
    _require(
        all(
            type(job.get("duration")) is int
            and 1 <= job["duration"] <= 12
            and type(job.get("crew")) is int
            and 1 <= job["crew"] <= 4
            and isinstance(job.get("deps"), list)
            and all(dep in jobs for dep in job["deps"])
            for job in jobs.values()
        ),
        "Service-only job requirements exceed the fixed grammar",
    )
    for name, row in rows.items():
        job = jobs[name]
        _require(
            type(row.get("start")) is int
            and type(row.get("end")) is int
            and 0 <= row["start"] < row["end"] <= len(capacity)
            and row["end"] == row["start"] + job["duration"]
            and row["start"] >= task.get("release", {}).get(name, 0)
            and all(dep in rows and rows[dep]["end"] <= row["start"] for dep in job["deps"])
            and (name not in task.get("locked", {}) or row["start"] == task["locked"][name]),
            "Service-only schedule violates duration, precedence, release or committed work",
        )
    makespan = max(row["end"] for row in rows.values())
    movement = sum(abs(rows[name]["start"] - start) for name, start in task.get("baseline", {}).items())
    _require(
        result.get("schema") == "release-plan-result/v1"
        and result["task_id"] == task["id"]
        and type(result["makespan"]) is int
        and type(result["movement"]) is int
        and result["makespan"] == makespan <= task["deadline"]
        and result["movement"] == movement <= task.get("movement_limit", movement)
        and all(
            sum(jobs[name]["crew"] for name, row in rows.items() if row["start"] <= slot < row["end"]) <= limit
            for slot, limit in enumerate(capacity)
        ),
        "Service-only schedule exceeds its actual calendar or objective bounds",
    )


def _verify_service_only(
    plan: dict[str, Any],
    summary: dict[str, Any],
    export_raw: bytes,
    primary: dict[str, Any],
    source_hash: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Admit only the matched construction-off control; primary checks stay strict."""
    _verify_plan(primary, source_hash, profile)
    _require(
        _canonical(plan["input"].get("construction")) == _canonical({"enabled": False}),
        "Service-only control requires explicit construction false",
    )
    _verify_plan(plan, source_hash, profile, require_improvement=False)
    exported = _verify_export(_json(export_raw), source_hash, profile, require_improvement=False)
    _require(_canonical(exported) == _canonical(plan), "Service-only signed export substitutes another mission")
    expected = deepcopy(primary["input"])
    expected["construction"] = {"enabled": False}
    _require(
        plan["policy_binding"] == primary["policy_binding"],
        "Service-only control must use the same installed policy binding",
    )
    _require(
        _canonical(plan["input"]) == _canonical(expected)
        and plan["caps"] == primary["caps"]
        and plan["plan_id"] != primary["plan_id"]
        and plan["request_id"] != primary["request_id"],
        "Service-only control changed other input, budgets or mission identity",
    )
    result, costs = plan["outcome"]["result"], plan["outcome"]["costs"]
    _require(
        result.get("capabilities") == []
        and result["inheritance"].get("diagnostics") == []
        and result["inheritance"].get("lineage") == []
        and result["inheritance"].get("parent_benefit") == "NOT_ESTABLISHED"
        and all(
            result["repair_usefulness"].get(k) is None
            for k in ("candidate_trial", "candidate_frozen_digest", "training_qualification")
        )
        and result["repair_usefulness"].get("consequence") == "DEFER_NO_FROZEN_REPAIR"
        and result["repair_usefulness"].get("economic_decision") == "HOLD_FULL_COST_UNKNOWN"
        and result["repair_usefulness"].get("production_promotion") is False,
        "Service-only control constructed or promoted an asset",
    )
    _require(
        result["accounting"].get("improvement_total") == costs["improvement_work"] == 0
        and result["accounting"].get("improvement_ledger") == []
        and result["accounting"].get("service_total") == costs["service_work"]
        and all(event["costs"]["improvement_work"] == 0 for event in result["events"])
        and costs["native_calls"] == 6
        and costs["native_solve_seconds"] == 12
        and bool(costs["unknown_costs"])
        and all(isinstance(v, str) for v in costs["unknown_costs"]),
        "Service-only separate accounting or native allowance is invalid",
    )
    phases = result["phases"]
    for index, phase in enumerate(phases):
        _verify_service_schedule(phase["task"], phase["result"])
        methods = {"native-repair", "native-makespan"} if index == 2 else {"native-deadline", "native-makespan"}
        attempts = phase["attempts"]
        _require(
            len(attempts) == 3 and {a["method"] for a in attempts} == {"ordinary-portfolio", *methods},
            "Service-only strongest specialist comparison is missing",
        )
        qualified = []
        for attempt in attempts:
            if attempt["method"] in methods:
                _require(
                    attempt.get("valid") is True and attempt.get("qualified") is True,
                    "Service-only native attempt was not independently qualified",
                )
            if attempt.get("qualified") is True:
                _verify_service_schedule(phase["task"], attempt["result"])
                quality = (
                    (attempt["result"]["movement"], attempt["result"]["makespan"])
                    if index == 2
                    else (attempt["result"]["makespan"], attempt["result"]["movement"])
                )
                qualified.append(quality)
        chosen = phase["result"]
        quality = (chosen["movement"], chosen["makespan"]) if index == 2 else (chosen["makespan"], chosen["movement"])
        _require(quality == min(qualified), "Service-only delivery ignores a stronger qualified specialist")
    telemetry = result["native_telemetry"]
    native = [row for row in telemetry if row.get("role") == "specialist"]
    _require(
        len(native) == 6
        and all(
            row.get("ok") is True
            and row.get("status") == 0
            and row.get("error") is None
            and all(_number(row.get(k)) for k in ("process_wall_seconds", "call_wall_seconds", "call_cpu_seconds"))
            and all(_number(row.get("startup", {}).get(k)) for k in ("wall_seconds", "cpu_seconds"))
            for row in native
        ),
        "Service-only native measurements are missing or uncertain",
    )
    observations = _calendar_repair_observations(phases)
    _require(
        summary.get("schema") == "strategy-engineering-service-only-acceptance/v1"
        and summary.get("construction_enabled") is False
        and all(
            summary.get(k) is True
            for k in (
                "same_input_except_construction",
                "caps_unchanged",
                "committed_prefix_preserved",
                "no_constructed_assets",
                "deduplicated_without_new_charges",
                "journal_verified",
            )
        )
        and summary.get("comparison_outcome_hash") == primary["outcome_hash"]
        and summary.get("comparison_input_sha256") == _digest(primary["input"])
        and summary.get("input_sha256") == _digest(plan["input"])
        and all(summary.get(k) == plan[k] for k in ("source_hash", "plan_id", "outcome_hash"))
        and _canonical(summary.get("costs")) == _canonical(costs)
        and summary.get("charged_native_solve_allowance_seconds") == costs["native_solve_seconds"]
        and summary.get("phase_makespans") == [p["result"]["makespan"] for p in phases]
        and summary.get("phase_receipts") == [p["receipt_hash"] for p in phases]
        and summary.get("unchanged_baseline_invalid_calendar_slots") == observations["invalid_calendar_slots"]
        and summary.get("signed_export_sha256") == hashlib.sha256(export_raw).hexdigest(),
        "Service-only summary substitutes input, costs, receipts or checked effects",
    )
    projected = [
        {
            k: row[k]
            for k in (
                "role",
                "status",
                "signal",
                "error",
                "process_wall_seconds",
                "startup",
                "call_wall_seconds",
                "call_cpu_seconds",
            )
            if k in row
        }
        for row in telemetry
    ]
    _require(
        _canonical(summary.get("worker_runtime_telemetry")) == _canonical(result["runtime_telemetry"])
        and all(_number(result["runtime_telemetry"].get(k)) for k in ("node_cpu_seconds", "wall_seconds"))
        and _canonical(summary.get("python_call_observations")) == _canonical(projected)
        and all(
            _number(summary.get(k))
            for k in (
                "api_call_wall_seconds",
                "api_test_process_cpu_seconds",
                "independent_verification_wall_seconds",
                "independent_verification_test_process_cpu_seconds",
                "control_window_wall_seconds",
            )
        )
        and isinstance(summary.get("timing_scope"), str)
        and bool(summary["timing_scope"])
        and "human_minutes" in summary
        and summary["human_minutes"] is None
        and "monetary_cost" in summary
        and summary["monetary_cost"] is None,
        "Service-only timing boundaries or unknown human/money costs are missing",
    )
    return plan


def _verify_browser(
    report: dict[str, Any], export_raw: bytes, source_hash: str, profile: dict[str, Any]
) -> dict[str, Any]:
    _require(
        report.get("schema") == "strategy-engineering-browser-acceptance/v1"
        and report.get("passed") is True
        and report.get("actual_browser") is True
        and report.get("browser_engine") == "chromium"
        and report.get("source_hash") == source_hash,
        "Actual source-bound Chromium acceptance is missing",
    )
    origin = urlsplit(report["served_origin"])
    _require(
        origin.scheme == "http"
        and origin.hostname in {"127.0.0.1", "localhost", "::1"}
        and not origin.username
        and not origin.password,
        "Browser acceptance must use the explicit local executor",
    )
    _require(
        isinstance(report.get("checks"), dict)
        and set(report["checks"]) == BROWSER_CHECKS
        and all(v is True for v in report["checks"].values()),
        "A browser acceptance check failed",
    )
    _require(
        report.get("export_sha256") == hashlib.sha256(export_raw).hexdigest(), "Actual browser download bytes differ"
    )
    plan = _verify_export(_json(export_raw), source_hash, profile)
    _require(
        report.get("plan_id") == plan["plan_id"] and report.get("outcome_hash") == plan["outcome_hash"],
        "Browser report is bound to a different executed mission",
    )
    _require(
        report.get("tab_closed_during_active_request") is True
        and report.get("new_context_recovered_same_mission") is True
        and report.get("source_changes_or_mock_browser") is False
        and report.get("native_calls") == plan["outcome"]["costs"]["native_calls"]
        and report.get("phase_receipts") == [p["receipt_hash"] for p in plan["partial_receipts"]],
        "Browser continuity or actual receipt scope is incomplete",
    )
    repair = _calendar_repair_observations(plan["outcome"]["result"]["phases"])
    _require(
        report.get("unchanged_baseline_invalid_calendar_slots") == repair["invalid_calendar_slots"]
        and bool(repair["invalid_calendar_slots"])
        and report.get("committed_prefix_preserved") is True
        and repair["committed_prefix_preserved"] is True,
        "Browser repair claim does not match actual calendar/prefix evidence",
    )
    requests = report.get("requests")
    _require(
        isinstance(requests, list)
        and bool(requests)
        and all(
            isinstance(r, dict) and isinstance(r.get("url"), str) and r["url"].startswith(report["served_origin"] + "/")
            for r in requests
        ),
        "Browser network observations leave the admitted local origin",
    )
    return plan


def _verify_public_preparer(
    report: dict[str, Any], plan: dict[str, Any], default_raw: bytes, optin_raw: bytes, source_html: bytes
) -> None:
    """Bind real browser downloads to approved input and exact source HTML."""
    approved = plan["input"]
    default, opted_in = _json(default_raw), _json(optin_raw)
    _require(
        _canonical(opted_in) == _canonical(approved)
        and isinstance(approved.get("construction"), dict)
        and approved["construction"].get("enabled") is True,
        "Public-preparer download differs from the actual approved input",
    )
    expected_default = deepcopy(approved)
    expected_default["construction"]["enabled"] = False
    _require(
        _canonical(default) == _canonical(expected_default),
        "Public-preparer default or opt-in changes more than construction consent",
    )
    raw_hashes = {
        "browser-prepared-input-default.json": hashlib.sha256(default_raw).hexdigest(),
        "browser-prepared-input-optin.json": hashlib.sha256(optin_raw).hexdigest(),
    }
    downloads = report.get("downloads")
    _require(
        isinstance(downloads, dict)
        and all(downloads.get(name) == value for name, value in raw_hashes.items())
        and report.get("prepared_input_sha256") == raw_hashes["browser-prepared-input-optin.json"]
        and report.get("input_sha256") == _digest(approved),
        "Public-preparer artifact or canonical input identity differs",
    )
    _require(
        report.get("public_preparer_source_sha256") == hashlib.sha256(source_html).hexdigest()
        and report.get("public_preparer_scope") == PUBLIC_PREPARER_SCOPE,
        "Public-preparer local source identity or Pages distinction is missing",
    )
    _require(
        _canonical(report.get("construction_opt_in"))
        == _canonical(
            {
                "public_default": False,
                "explicit_browser_checkbox": True,
                "only_changed_setting": "construction.enabled",
                "approved_input_matches_actual_download": True,
            }
        ),
        "Explicit public construction opt-in evidence is incomplete",
    )


def _verify_crash(report: dict[str, Any], source_hash: str, profile: dict[str, Any]) -> dict[str, Any]:
    _require(
        report.get("schema") == "strategy-engineering-crash-recovery/v1"
        and report.get("passed") is True
        and report.get("source_hash") == source_hash
        and report.get("actual_supervisor_signal") == "SIGKILL"
        and type(report.get("descendants_observed")) is int
        and report["descendants_observed"] >= 1
        and report.get("descendants_inactive") is True
        and _number(report.get("descendant_stop_seconds")),
        "Actual bounded server/worker crash evidence is missing",
    )
    _require(
        report.get("reserved_before") == report.get("reserved_after") == profile["per_plan_caps"]
        and report.get("duplicate_run_http") == report.get("early_reconciliation_http") == 409
        and report.get("no_automatic_replay") is True
        and report.get("unknown_work_refunded") is False
        and report.get("production_authority") is False,
        "Crash recovery refunded uncertainty or replayed unobserved work",
    )
    plan = _verify_export(report["export"], source_hash, profile, complete=False)
    _require(
        report.get("restarted_state") == plan["state"]
        and report["reserved_after"] == plan["caps"]
        and report.get("retained_partial_hashes") == [p["receipt_hash"] for p in plan["partial_receipts"]],
        "Crash recovery lost or substituted its committed partial result",
    )
    return plan


def _verify_dependency_audit(report: dict[str, Any], raw: dict[str, Any], requirements: bytes, commit: str) -> None:
    expected: dict[str, str] = {}
    for line in requirements.decode().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, version = line.strip().split("==")
        name = re.sub(r"[-_.]+", "-", name).lower()
        if name != "alpha-factory-v1":
            _require(name not in expected, "Duplicate audited dependency pin")
            expected[name] = version
    _require(
        len(expected) == 25
        and report.get("schema") == "strategy-engineering-dependency-audit/v1"
        and report.get("commit") == commit
        and report.get("passed") is True
        and report.get("packages") == 25,
        "Exact third-party dependency audit is absent",
    )
    rows_raw = raw.get("dependencies")
    _require(isinstance(rows_raw, list) and len(rows_raw) == 25, "Dependency audit omitted or duplicated a package")
    rows = cast(list[dict[str, Any]], rows_raw)
    actual: dict[str, str] = {}
    for row in rows:
        _require(
            isinstance(row, dict)
            and isinstance(row.get("name"), str)
            and isinstance(row.get("version"), str)
            and row.get("vulns") == []
            and "skip_reason" not in row
            and "skipped" not in row,
            "Dependency audit contains a vulnerability, skip or unknown result",
        )
        name = re.sub(r"[-_.]+", "-", row["name"]).lower()
        _require(name not in actual, "Duplicate audited package")
        actual[name] = row["version"]
    _require(actual == expected, "Audited dependency names or versions differ from committed pins")
    _require(raw.get("fixes", []) == [], "Dependency audit reports unresolved remediation")


def _verify_child_environment(record: Any, profile: dict[str, Any]) -> None:
    _require(
        isinstance(record, dict) and set(record) == {"observation", "sha256"},
        "Actual child environment observation is missing",
    )
    observation = record["observation"]
    _require(
        isinstance(observation, dict)
        and set(observation)
        == {
            "schema",
            "invocation_context_matches",
            "prefix_context_matches",
            "python_implementation",
            "python_version",
            "dependencies",
            "native_imports",
        },
        "Child environment observation must have the exact sanitized fields",
    )
    _require(record["sha256"] == _digest(observation), "Actual child observation digest mismatch")
    _require(
        observation["schema"] == "strategy-child-environment/v1"
        and observation["invocation_context_matches"] is True
        and observation["prefix_context_matches"] is True,
        "Native child invocation does not match the approved parent context",
    )
    expected = profile["qualified_environment"]
    _require(
        observation["python_implementation"] == expected["python_implementation"]
        and observation["python_version"] == expected["python_version"]
        and isinstance(observation["dependencies"], dict)
        and len(observation["dependencies"]) == 26
        and observation["dependencies"] == expected["dependencies"],
        "Actual child Python/dependency environment is unqualified",
    )
    _require(
        observation["dependencies"].get("alpha-factory-v1") == "1.42.0"
        and observation["native_imports"] == {name: expected["dependencies"][name] for name in ("numpy", "scipy")},
        "Actual child native imports are absent or unqualified",
    )


def package(root: Path, output: Path, evidence: Path, commit: str, version: str) -> dict[str, Any] | None:
    """Copy three qualified additive assets into the existing release directory."""
    _require(re.fullmatch(r"\d+\.\d+\.\d+", version) is not None, "Invalid core release version")
    if tuple(map(int, version.split("."))) < (1, 44, 0):
        return None
    qualification = _read_json(evidence / "qualification.json")
    _require(
        qualification.get("schema") == "strategy-engineering-release-qualification/v1"
        and qualification.get("commit") == commit
        and qualification.get("version") == version,
        "Strategy qualification belongs to another exact core source",
    )
    _require(
        qualification.get("installed_outside_checkout") is True
        and qualification.get("reproducible") is True
        and qualification.get("runtime_version") == "1.42.0"
        and qualification.get("runtime_wheel_sha256") == PUBLIC_RUNTIME,
        "Standalone installed public-runtime qualification is absent",
    )
    checks = qualification.get("checks")
    _require(
        isinstance(checks, dict)
        and set(checks)
        == {"transport", "worker", "environment", "integration", "browser", "crash_recovery", "dependency_audit"}
        and all(v is True for v in checks.values()),
        "A required Strategy qualification failed or was skipped",
    )
    files = _committed_files(root, commit)
    _verify_dependency_audit(
        _read_json(evidence / "dependency-audit.json"),
        _read_json(evidence / "pip-audit.json"),
        files[CONTRIB + "requirements-qualification.txt"],
        commit,
    )
    inventory_raw = _read(evidence / "source-inventory.json")
    inventory = _json(inventory_raw)
    _require(
        qualification.get("source_inventory_sha256") == hashlib.sha256(inventory_raw).hexdigest()
        and inventory.get("schema") == "strategy-engineering-source-inventory/v1"
        and inventory.get("commit") == commit
        and inventory.get("version") == version,
        "Source inventory identity mismatch",
    )
    expected_inventory = {n: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in files.items()}
    _require(
        inventory.get("files") == expected_inventory,
        "Acceptance did not inspect the complete committed payload/build source",
    )
    wheel = qualification["wheel"]
    _require(
        isinstance(wheel.get("name"), str)
        and re.fullmatch(DIST + r"-[0-9A-Za-z.]+-py3-none-any\.whl", wheel["name"]) is not None,
        "Invalid fixed companion wheel name",
    )
    wheel_raw = _read(evidence / wheel["name"], 50_000_000)
    _require(
        wheel.get("sha256") == hashlib.sha256(wheel_raw).hexdigest() and wheel.get("bytes") == len(wheel_raw),
        "Actual companion wheel bytes differ from qualification",
    )
    _require(
        _read(evidence / "reproduced-wheel" / wheel["name"], 50_000_000) == wheel_raw,
        "Independent source rebuild did not reproduce the wheel bytes",
    )
    inspected = _verify_wheel(wheel_raw, files)
    _require(
        qualification.get("companion_version") == inspected["version"]
        and wheel["name"] == DIST + "-" + inspected["version"] + "-py3-none-any.whl",
        "Companion version mismatch",
    )
    profile, source_hash = inspected["profile"], inspected["source_hash"]
    _verify_child_environment(qualification.get("child_environment"), profile)
    browser = _read_json(evidence / "acceptance-public" / "browser-acceptance.json")
    browser_raw = _read(evidence / "acceptance-public" / "browser-mission-export.json")
    browser_plan = _verify_browser(browser, browser_raw, source_hash, profile)
    public_preparer_html = subprocess.check_output(
        ["git", "-C", str(root), "show", "--no-textconv", commit + ":docs/try/index.html"]
    )
    _verify_public_preparer(
        browser,
        browser_plan,
        _read(evidence / "acceptance-public" / "browser-prepared-input-default.json"),
        _read(evidence / "acceptance-public" / "browser-prepared-input-optin.json"),
        public_preparer_html,
    )
    installed = _read_json(evidence / "acceptance-public" / "integrated-journey.json")
    _verify_plan(installed, source_hash, profile)
    _verify_service_only(
        _read_json(evidence / "acceptance-public" / "service-only-journey.json"),
        _read_json(evidence / "acceptance-public" / "service-only-summary.json"),
        _read(evidence / "acceptance-public" / "service-only-export.json"),
        installed,
        source_hash,
        profile,
    )
    summary = _read_json(evidence / "acceptance-public" / "integrated-summary.json")
    _require(
        summary.get("source_hash") == source_hash
        and summary.get("outcome_hash") == installed["outcome_hash"]
        and summary.get("costs") == installed["outcome"]["costs"]
        and summary.get("child_environment") == qualification["child_environment"],
        "Installed acceptance summary substitutes a different run",
    )
    _verify_crash(_read_json(evidence / "acceptance-public" / "crash-recovery.json"), source_hash, profile)
    companion = inspected["version"]
    compatibility = {
        "schema": "strategy-engineering-release-compatibility/v1",
        "core_distribution_version": version,
        "core_source_commit": commit,
        "companion_version": companion,
        "source_hash": source_hash,
        "wheel": wheel,
        "runtime_version": "1.42.0",
        "runtime_public_wheel_sha256": PUBLIC_RUNTIME,
        "runtime_installation": "Separate virtual environment; core distribution version is not runtime compatibility",
        "qualified_environment": profile["qualified_environment"],
        "browser_plan_id": browser_plan["plan_id"],
        "browser_outcome_hash": browser_plan["outcome_hash"],
        "scope": profile["scope"],
        "production_authority": False,
        "four_product_installation": False,
        "native_cost_unit": "Charged solve allowance seconds; measured wall/CPU remain separate",
        "unknown_costs": ["human effort", "device/monetary cost", "opaque native work"],
        "held_harness_fleet_decisions": "unchanged",
    }
    assets = {
        wheel["name"]: wheel_raw,
        "strategy-succession-" + companion + "-operator.md": files[CONTRIB + "docs/operator.md"],
        "strategy-succession-"
        + companion
        + "-compatibility.json": (json.dumps(compatibility, indent=2) + "\n").encode(),
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, data in assets.items():
        target = output / name
        _require(
            not target.exists() or _read(target, 50_000_000) == data, "An existing release asset has different bytes"
        )
    for name, data in assets.items():
        target = output / name
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(data)
    return {
        "companion_version": companion,
        "source_hash": source_hash,
        "assets": {n: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in assets.items()},
        "production_authority": False,
        "runtime_version": "1.42.0",
    }
