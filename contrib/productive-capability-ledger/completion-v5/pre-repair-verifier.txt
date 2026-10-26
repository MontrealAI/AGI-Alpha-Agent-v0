# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HASH = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
STAGES = ("recovery", "planning", "preparation", "execution", "verification", "correction", "packaging", "reporting")
FIXED_ARTIFACTS = {
    "plan.json",
    "final-acceptance.json",
    "report-context.json",
    "STOP",
    "prepared-inputs.json",
    "declared-inventory.csv",
    "observed-inventory.csv",
    "result.json",
    "acceptance.json",
    "correction.json",
    "differences.csv",
    "action-plan.csv",
    "workspace.json",
    "report.md",
    *("stage-" + stage + ".json" for stage in STAGES),
}
VARIABLE_ARTIFACT = re.compile(
    r"(?:(?:attempt|final-revalidation|interrupted-lock)-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|reservation-[0-9]{3})\.json\Z"
)
DEPENDENCIES = (
    "examples/ti-guide/guide.mjs",
    "examples/successor-alpha/engine.mjs",
    "examples/successor-alpha/research.mjs",
    "docs/assets/successor/engine.mjs",
)
RUNNER = "contrib/productive-capability-ledger/automation-v1/run-mission.mjs"
LEGACY_RUNNER_SHA256 = "b41247af80a42213398c82120ef481dc139c793cec457b52fb3e58df94ec7824"
LEGACY_METHOD_IDENTITY = "860c0f2af042fc61f5a16cd82408531d9e993abcf674ff54e134851dfe4800c9"
LEGACY_SOURCE_COMMIT = "d12e955909cb5b52a5225c39d4f7fab4a5f93d50"


def read_bytes(path: Path, maximum: int = 8_000_000) -> bytes:
    handle = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(handle)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise ValueError("Acceptance requires bounded regular files")
        chunks, used = [], 0
        while True:
            chunk = os.read(handle, min(65536, maximum + 1 - used))
            if not chunk:
                break
            chunks.append(chunk)
            used += len(chunk)
            if used > maximum:
                raise ValueError("Acceptance input grew beyond its byte bound")
        return b"".join(chunks)
    finally:
        os.close(handle)


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Acceptance input contains duplicate JSON keys")
        value[key] = item
    return value


def parse(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def public_path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", value)
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("Unsafe public source path")
    return value


def git_blob(commit: str, path: str) -> bytes:
    if not COMMIT.fullmatch(commit):
        raise ValueError("Invalid source commit")
    operand = commit + ":" + public_path(path)
    environment = {key: value for key, value in os.environ.items() if not key.lower().startswith("git_")}
    environment.update(GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    command = ["git", "--no-lazy-fetch", "--no-replace-objects", "--no-pager"]
    listing = subprocess.check_output(
        [*command, "ls-tree", "-z", commit, "--", path], cwd=ROOT, timeout=5, env=environment
    )
    entries = listing.decode().split("\0")
    if len(entries) != 2 or not entries[0].endswith("\t" + path):
        raise ValueError("An exact ordinary Git source entry is required")
    mode, kind, _ = entries[0].split("\t")[0].split(" ")
    if mode not in {"100644", "100755"} or kind != "blob":
        raise ValueError("Only ordinary Git source modes 100644 and 100755 are admitted")
    size = int(subprocess.check_output([*command, "cat-file", "-s", operand], cwd=ROOT, timeout=5, env=environment))
    if size > 4_000_000:
        raise ValueError("Public source blob exceeds its byte bound")
    raw = subprocess.check_output([*command, "show", operand], cwd=ROOT, timeout=5, env=environment)
    if len(raw) != size:
        raise ValueError("Git source changed during inspection")
    return raw


def csv_records(raw: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    if reader.fieldnames != ["path", "sha256"]:
        raise ValueError("Inventory CSV must retain exact source columns")
    rows = list(reader)
    if len(rows) > 128 or len({row["path"] for row in rows}) != len(rows):
        raise ValueError("Inventory CSV exceeds its bound or repeats a source path")
    for row in rows:
        public_path(row["path"])
        if set(row) != {"path", "sha256"} or not HASH.fullmatch(row["sha256"]):
            raise ValueError("Inventory CSV contains invalid source identities")
    return rows


def verify(directory: Path) -> dict[str, Any]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("A regular run directory is required")
    checks = 0

    def require(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            raise ValueError(message)

    def canonical(value: Any) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

    def artifact_name(value: Any) -> str:
        require(
            isinstance(value, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]+", value) is not None
            and value not in {".", "..", "COMPLETE.json", "writer.lock"},
            "An artifact reference attempts to leave the approved run scope",
        )
        assert isinstance(value, str)
        return value

    complete = parse(read_bytes(directory / "COMPLETE.json"))
    require(complete["schema"] == "alpha-automated-source-delivery/v2", "Unexpected complete-delivery schema")
    require(
        complete["accepted"] is True and complete["authority"] == "none", "Local acceptance cannot import authority"
    )
    require(complete["commercialAcceptance"] == "unknown", "Commercial acceptance was not measured")
    require(
        complete["connectedExecution"].startswith("NOT RUN"), "Local source work cannot qualify a connected executor"
    )
    require(
        complete["fullAgentCost"]["value"] is None and complete["fullAgentCost"]["basis"] == "unknown",
        "Unmeasured whole Agent cost cannot become zero",
    )
    artifacts = complete["artifacts"]
    require(
        isinstance(artifacts, dict) and 1 <= len(artifacts) <= len(FIXED_ARTIFACTS) + 4 * 128,
        "Artifact inventory is missing or exceeds the supported lifetime envelope",
    )
    raw_files: dict[str, bytes] = {}
    for name, digest in artifacts.items():
        artifact_name(name)
        require(name in FIXED_ARTIFACTS or VARIABLE_ARTIFACT.fullmatch(name) is not None, "Unknown delivery artifact")
        require(isinstance(digest, str) and HASH.fullmatch(digest) is not None, "Invalid artifact identity")
        raw_files[name] = read_bytes(directory / name, 8_000_000 if name in FIXED_ARTIFACTS else 32_768)
        require(sha(raw_files[name]) == digest, "Complete-delivery artifact bytes differ: " + name)
    required = {
        "plan.json",
        "final-acceptance.json",
        "prepared-inputs.json",
        "result.json",
        "acceptance.json",
        "correction.json",
        "workspace.json",
        "declared-inventory.csv",
        "observed-inventory.csv",
        "differences.csv",
        "action-plan.csv",
        "report.md",
        *("stage-" + stage + ".json" for stage in STAGES),
    }
    require(required <= artifacts.keys(), "A finished-delivery payload is missing")
    plan = parse(raw_files["plan.json"])
    require(
        plan["schema"] in {"alpha-source-assurance-plan/v2", "alpha-source-assurance-plan/v3"},
        "Unexpected bounded-plan schema",
    )
    require(plan["authority"] == "none", "A plan cannot grant execution authority")
    require(complete["approvalDigest"] == sha(canonical(plan)), "Approved plan digest differs")
    require(complete["sourceRef"] == plan["sourceRef"], "Complete delivery changed its approved source")
    require(complete["runId"] == plan["runId"], "Run identity changed")
    if plan["schema"] == "alpha-source-assurance-plan/v3":
        require(type(plan["maxAttempts"]) is int and 1 <= plan["maxAttempts"] <= 128, "Invalid attempt envelope")
        require(
            len(artifacts) <= len(FIXED_ARTIFACTS) + 4 * plan["maxAttempts"],
            "Artifact inventory exceeds this plan's approved attempt envelope",
        )
        require(type(plan["maxSeconds"]) is int and 1 <= plan["maxSeconds"] <= 60, "Invalid per-attempt bound")
        require(
            type(plan["maxTotalSeconds"]) is int and plan["maxSeconds"] <= plan["maxTotalSeconds"] <= 3600,
            "Invalid total reservation bound",
        )
        created = datetime.fromisoformat(plan["createdAt"].replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(plan["expiresAt"].replace("Z", "+00:00"))
        require(0 < (expiry - created).total_seconds() <= 86400, "Invalid expiry envelope")
        names = sorted(path.name for path in directory.iterdir() if path.name.startswith("reservation-"))
        require(1 <= len(names) <= plan["maxAttempts"], "Reservations exceed attempt envelope")
        require(len(names) * plan["maxSeconds"] <= plan["maxTotalSeconds"], "Reservations exceed total execution")
        reserved_attempts: set[str] = set()
        for ordinal, name in enumerate(names, 1):
            require(name == f"reservation-{ordinal:03}.json", "Reservation history has a gap")
            reservation = parse(read_bytes(directory / name))
            require(reservation["schema"] == "alpha-source-reservation/v1", "Unknown reservation schema")
            require(reservation["approvalDigest"] == complete["approvalDigest"], "Reservation changes approval")
            require(
                reservation["ordinal"] == ordinal and reservation["reservedSeconds"] == plan["maxSeconds"],
                "Interrupted work must retain its complete reservation",
            )
            started = datetime.fromisoformat(reservation["startedAt"].replace("Z", "+00:00"))
            require(created <= started < expiry, "Reservation falls outside approval validity")
            attempt = reservation["attempt"]
            require(
                isinstance(attempt, str)
                and re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", attempt)
                is not None,
                "Invalid reserved attempt identity",
            )
            require(attempt not in reserved_attempts, "Reservation attempts must be unique")
            reserved_attempts.add(attempt)
        execution_names = sorted(
            path.name
            for path in directory.iterdir()
            if path.name.startswith("attempt-") and path.name.endswith(".json")
        )
        require(
            set(execution_names)
            == {name for name in raw_files if name.startswith("attempt-") and name.endswith(".json")},
            "Retained execution attempts cannot be omitted from the completion inventory",
        )
        execution_attempts: set[str] = set()
        for name in execution_names:
            execution = parse(raw_files[name])
            require(
                name == f"attempt-{execution['attempt']}.json"
                and execution["approvalDigest"] == complete["approvalDigest"],
                "Execution attempt lost its identity or approved scope",
            )
            require(execution["attempt"] in reserved_attempts, "Execution attempt has no retained reservation")
            execution_attempts.add(execution["attempt"])
        for stage in STAGES:
            receipt = parse(raw_files[f"stage-{stage}.json"])
            require(receipt["attempt"] in execution_attempts, "Stage lacks its reserved execution attempt")
        final_reservation = complete["authorization"]
        require(1 <= final_reservation["ordinal"] <= len(names), "Completion reservation is missing")
        require(
            final_reservation == parse(read_bytes(directory / f"reservation-{final_reservation['ordinal']:03}.json")),
            "Completion changed its execution reservation",
        )
        require(final_reservation["attempt"] in execution_attempts, "Completion is not bound to an execution attempt")
        for ordinal in range(1, final_reservation["ordinal"] + 1):
            require(f"reservation-{ordinal:03}.json" in raw_files, "Completion omits a reserved allowance")
        final_verification = f"final-revalidation-{final_reservation['attempt']}.json"
        require(
            final_verification in raw_files and parse(raw_files[final_verification]) == complete["finalRevalidation"],
            "Completion lacks its reserved final verification",
        )
        require(not (directory / "CANCELLED.json").exists(), "A cancelled mission is not an accepted completion")
    source_ref = plan["sourceRef"]
    require(
        isinstance(source_ref, str) and COMMIT.fullmatch(source_ref) is not None,
        "Source ref must be an exact Git commit",
    )
    source_manifest = git_blob(source_ref, plan["manifestPath"])
    require(sha(source_manifest) == plan["manifestSha256"], "Approved manifest bytes differ")
    sources = parse(source_manifest)["sources"]
    require(isinstance(sources, dict) and 1 <= len(sources) <= 128, "Source inventory exceeds its approved bound")
    require(len(sources) == plan["sourceCount"], "Approved source count differs")
    dependencies = plan["dependencySha256"]
    require(set(dependencies) == {*DEPENDENCIES, RUNNER}, "Executable dependency closure changed")
    require(plan["methodIdentity"] == sha(canonical(dependencies)), "Retained executable identity differs")
    require(complete["methodIdentity"] == plan["methodIdentity"], "Result changed the approved method")
    legacy = dependencies[RUNNER] == LEGACY_RUNNER_SHA256 and plan["methodIdentity"] == LEGACY_METHOD_IDENTITY
    reporting_predecessor = (
        dependencies[RUNNER] == "2158e34cab75f11242f6d130c696ba276abb53e017f862ecc7ee8e40e1f8779b"
        and plan["methodIdentity"] == "17e09fd0d79d823e176d7a4f2eb547adc91ff71162766c6d0995fe2d3778fab9"
    )
    envelope_predecessor = (
        dependencies[RUNNER] == "9aa3a9009fac35f03b4a96f2de545ee0403cafaa5a163243185f8c5af77ca216"
        and plan["methodIdentity"] == "fa12a246aafcb5cb52f972e3cfb190a92c302eaafe27436bacdcf4fb9a46912c"
    )
    historical_commit = (
        LEGACY_SOURCE_COMMIT
        if legacy
        else "2b442458847ca4655d0ed92afc6b1b62e8672e8d" if reporting_predecessor else None
    )
    if envelope_predecessor:
        historical_commit = "1d46b4d553ac84b5da174a427961d7b34ae8e1fb"
    if (
        dependencies[RUNNER] == "9ac945d9ce62580e6c4b15418bf6c99d0e1aab9833b6b51d7e0469ef00fdcd46"
        and plan["methodIdentity"] == "5b3559ee139bf27f9c29f91a57ddf8b2b6e91ff0f53ed2353833eb55c81ebc1f"
    ):
        historical_commit = "2c5c393c1e5431c00d59d077c403739e789abd43"
    if (
        dependencies[RUNNER] == "571032112384201eb27383ef7313115f1c0737b214d022c8dbd033b48050bac4"
        and plan["methodIdentity"] == "3e2a9cab0dd0dfe89729b3c5dda3cb2013cc7b8a7d72066f713444323e5629bd"
    ):
        historical_commit = "443246db37b30b83f4b9c8a854ceb226601e0155"
    for path, digest in dependencies.items():
        public_path(path)
        installed = git_blob(historical_commit, path) if historical_commit else read_bytes(ROOT / path, 4_000_000)
        require(
            sha(installed) == digest,
            (
                "Preserved historical executable differs: "
                if historical_commit
                else "Current installed executable differs: "
            )
            + path,
        )
        if path in DEPENDENCIES:
            require(
                sha(git_blob(source_ref, path)) == digest, "Comparison dependency differs from the committed source"
            )
    prepared = parse(raw_files["prepared-inputs.json"])
    require(prepared["schema"] == "alpha-source-assurance-inputs/v1", "Unexpected prepared-input schema")
    require(
        prepared["sourceRef"] == source_ref and prepared["manifestPath"] == plan["manifestPath"],
        "Prepared scope differs",
    )
    inputs = prepared["input"]
    require(set(inputs) == {"leftCsv", "rightCsv", "leftKey", "rightKey"}, "Prepared inputs changed shape")
    require(inputs["leftKey"] == inputs["rightKey"] == "path", "Inventory identifiers changed")
    require(
        inputs["leftCsv"].encode() == raw_files["declared-inventory.csv"],
        "Declared CSV differs from the prepared input",
    )
    require(
        inputs["rightCsv"].encode() == raw_files["observed-inventory.csv"],
        "Observed CSV differs from the prepared input",
    )
    left_rows, right_rows = (
        csv_records(raw_files["declared-inventory.csv"]),
        csv_records(raw_files["observed-inventory.csv"]),
    )
    declared, observed = ({row["path"]: row["sha256"] for row in rows} for rows in (left_rows, right_rows))
    require(declared == sources and declared.keys() == observed.keys(), "CSV scope differs from the original manifest")
    for path, digest in observed.items():
        require(sha(git_blob(source_ref, path)) == digest, "Observed hash differs from the exact committed public blob")
    changed = [row["path"] for row in right_rows if declared[row["path"]] != row["sha256"]]
    result = parse(raw_files["result.json"])
    require(result["schema"] == "ti-catalogue-result/v1", "Unexpected existing catalogue-result format")
    for side, filename in (("left", "declared-inventory.csv"), ("right", "observed-inventory.csv")):
        identity = result[side + "Identity"]
        require(
            identity == {"sha256": sha(raw_files[filename]), "bytes": len(raw_files[filename])},
            "CSV byte identity differs",
        )
    differences = result["differences"]
    require(
        [[row["key"], row["leftValue"], row["rightValue"]] for row in differences]
        == [[path, declared[path], observed[path]] for path in changed],
        "Independent exact-key/hash differences disagree",
    )
    require(
        all(row["kind"] == "conflict" and row["field"] == "sha256" for row in differences),
        "Changed source kind differs",
    )
    metrics = result["metrics"]
    for key, expected in {
        "leftRows": len(sources),
        "rightRows": len(sources),
        "matchedPairs": len(sources),
        "unmatchedRows": 0,
        "fieldDifferences": len(changed),
        "conflictingPairs": len(changed),
        "actionGroups": len(changed),
        "evidenceReferences": len(changed),
    }.items():
        require(metrics[key] == expected, "Independent source metric disagrees: " + key)
    resolution = result["resolution"]
    require(resolution["automaticallyResolved"] is False, "No source was automatically repaired or approved")
    require(resolution["coverage"]["originalOccurrences"] == len(changed), "Original disagreement coverage differs")
    require([action["key"] for action in resolution["actions"]] == changed, "Action group lost an affected source")
    for filename, key in (("differences.csv", "key"), ("action-plan.csv", "exact_key")):
        reader = csv.DictReader(io.StringIO(raw_files[filename].decode(), newline=""))
        headers = (
            ["id", "occurrence", "action", "key", "kind", "leftRow", "rightRow", "field", "leftValue", "rightValue"]
            if filename == "differences.csv"
            else [
                "action",
                "exact_key",
                "type",
                "left_data_rows",
                "right_data_rows",
                "original_review_occurrences",
                "next_step",
            ]
        )
        require(reader.fieldnames == headers, "Download replaced its exact result schema: " + filename)
        rows = list(reader)
        require([row[key] for row in rows] == changed, "Download lost or invented an affected source: " + filename)
    workspace = parse(raw_files["workspace.json"])
    require(
        workspace["schema"] == "ti-catalogue-workspace/v1" and workspace["authority"] == "none",
        "Workspace changed scope",
    )
    require(workspace["input"] == inputs and workspace["result"] == result, "Portable workspace lost exact work")
    require(
        workspace["sourceHash"] == plan["methodIdentity"] and workspace["runId"] == plan["runId"],
        "Workspace source differs",
    )
    acceptance = parse(raw_files["acceptance.json"])
    require(
        acceptance["accepted"] is True and acceptance["changedPaths"] == changed,
        "Runtime checker did not accept exact work",
    )
    require(
        acceptance["commercialAcceptance"] == "unknown" and acceptance["authority"] == "none",
        "Checker exceeded local scope",
    )
    correction = parse(raw_files["correction.json"])
    require(correction["decision"] == "report-discrepancies-without-source-mutation", "Correction scope changed")
    require(
        correction["changedPaths"] == changed and correction["needsRoutineCorrection"] is False,
        "Correction decision differs",
    )
    final_acceptance = parse(raw_files["final-acceptance.json"])
    require(
        final_acceptance["schema"] == "alpha-source-final-acceptance/v1"
        and final_acceptance["accepted"] is True
        and final_acceptance["approvalDigest"] == complete["approvalDigest"]
        and final_acceptance["sourceRef"] == source_ref
        and final_acceptance["methodIdentity"] == plan["methodIdentity"]
        and final_acceptance["authority"] == "none",
        "Full revalidation did not bind the final acceptance",
    )
    revalidation = complete["finalRevalidation"]
    require(
        revalidation["accepted"] is True and revalidation["schema"] == "alpha-source-final-revalidation/v1",
        "Complete result lacks its full recomputation",
    )
    require(
        any(name.startswith("final-revalidation-") and parse(raw_files[name]) == revalidation for name in artifacts),
        "Final revalidation timing has no exact retained receipt",
    )
    traces = complete["stages"]
    require([trace["stage"] for trace in traces] == list(STAGES), "Every automated workflow stage needs one receipt")
    stage_payloads = {
        "recovery": set(),
        "planning": set(),
        "preparation": {"prepared-inputs.json", "declared-inventory.csv", "observed-inventory.csv"},
        "execution": {"result.json"},
        "verification": {"acceptance.json"},
        "correction": {"correction.json"},
        "packaging": {"differences.csv", "action-plan.csv", "workspace.json"},
        "reporting": {"report.md"},
    }
    for trace in traces:
        stage = trace["stage"]
        require(
            trace == parse(raw_files["stage-" + stage + ".json"]), "A stage receipt differs from the complete trace"
        )
        require(trace["approvalDigest"] == complete["approvalDigest"], "A stage changed approved scope")
        require(set(trace["artifacts"]) == stage_payloads[stage], "A stage changed its allowed artifact writes")
        for filename, digest in trace["artifacts"].items():
            artifact_name(filename)
            require(artifacts[filename] == digest, "A stage's exact payload differs")
        for field in ("wallMicroseconds", "cpuMicroseconds", "toolInvocations", "modelCalls", "routineHumanMinutes"):
            value = trace[field]
            require(
                set(value) == {"value", "basis", "reference"}
                and isinstance(value["value"], int)
                and not isinstance(value["value"], bool)
                and value["value"] >= 0
                and value["basis"] == "measured"
                and bool(value["reference"]),
                "A measured stage fact is missing or invalid: " + field,
            )
        require(trace["modelCalls"]["value"] == 0, "This deterministic offering used no live model adapter")
        require(trace["routineHumanMinutes"]["value"] == 0, "Routine human handling was not automated")
        require(
            trace["monetaryCost"]["value"] is None and trace["monetaryCost"]["basis"] == "unknown",
            "Unpriced process observations must not become zero monetary cost",
        )
    report = raw_files["report.md"].decode()
    reporting = traces[-1]
    context = reporting.get("reportContext")
    require(
        isinstance(context, dict)
        and set(context) == {"priorStageReceipts", "unknownAttempts"}
        and context["priorStageReceipts"] == 7
        and isinstance(context["unknownAttempts"], int)
        and not isinstance(context["unknownAttempts"], bool)
        and 0 <= context["unknownAttempts"] < 128,
        "Historical report context is missing or invalid",
    )
    if not legacy:
        require("report-context.json" in raw_files, "Current runner requires durable report context")
        attempt_names = sorted(name for name in raw_files if name.startswith("attempt-") and name.endswith(".json"))
        require(1 <= len(attempt_names) <= 128, "Complete retry history exceeded its lifetime attempt bound")
        for name in attempt_names:
            attempt = parse(raw_files[name])
            require(
                re.fullmatch(
                    r"attempt-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.json",
                    name,
                )
                is not None
                and isinstance(attempt, dict)
                and attempt.get("attempt") == name.removeprefix("attempt-").removesuffix(".json")
                and attempt.get("approvalDigest") == complete["approvalDigest"]
                and attempt.get("state") == "started",
                "Complete attempt history lost its approved scope",
            )
        interrupted = complete["interruptedOrUncommittedAttempts"]
        require(
            interrupted["value"] == len(attempt_names) - 1
            and not isinstance(interrupted["value"], bool)
            and interrupted["basis"] == "measured",
            "Complete retry history lost interrupted-work accounting",
        )
        snapshot = parse(raw_files["report-context.json"])
        require(
            isinstance(snapshot, dict)
            and set(snapshot) == {"schema", "approvalDigest", "attempt", "priorStageReceipts", "attempts"}
            and snapshot["schema"] == "alpha-source-report-context/v1"
            and snapshot["approvalDigest"] == complete["approvalDigest"]
            and snapshot["priorStageReceipts"] == 7,
            "Durable report context changed its approved scope",
        )
        rows = snapshot["attempts"]
        require(isinstance(rows, list) and 1 <= len(rows) <= 128, "Report attempt snapshot is missing or unbounded")
        names = []
        for row in rows:
            require(
                isinstance(row, dict)
                and set(row) == {"name", "sha256"}
                and isinstance(row["name"], str)
                and re.fullmatch(
                    r"attempt-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.json",
                    row["name"],
                )
                is not None
                and isinstance(row["sha256"], str)
                and HASH.fullmatch(row["sha256"]) is not None,
                "Invalid report attempt snapshot row",
            )
            name = artifact_name(row["name"])
            require(name in raw_files and sha(raw_files[name]) == row["sha256"], "Report attempt bytes differ")
            attempt = parse(raw_files[name])
            require(
                isinstance(attempt, dict)
                and attempt.get("attempt") == name.removeprefix("attempt-").removesuffix(".json")
                and attempt.get("approvalDigest") == complete["approvalDigest"]
                and attempt.get("state") == "started",
                "Report attempt lost its approved scope",
            )
            names.append(name)
        require(names == sorted(set(names)), "Report attempts must be sorted and unique")
        require(
            isinstance(snapshot["attempt"], str) and "attempt-" + snapshot["attempt"] + ".json" in names,
            "Original reporting attempt is missing from its snapshot",
        )
        require(context["unknownAttempts"] == len(rows) - 1, "Report context disagrees with its durable snapshot")
    expected_report = (
        f"# Finished public-source assurance\n\n{plan['sourceCount']} committed source identities checked; "
        f"{len(changed)} paths need attention.\n\nSource: {source_ref}; manifest: {plan['manifestPath']}.\n\n"
        "The action plan and full differences identify every mismatch. Nothing modifies or approves the inspected "
        "source.\n\n## Automated work\n\nPreparation, bounded planning, comparison, exact checking, "
        "refusal/correction decision, packaging, reporting and checkpoint recovery run in software after approval.\n\n"
        f"## Cost and attention\n\n7 prior stage receipts; {context['unknownAttempts']} interrupted/uncommitted "
        "attempt(s) at this reporting checkpoint. Completion and reconnect receipts account for later restart cost. "
        "No service model calls were used. These are process observations, not complete Agent monetary cost. Hardware, "
        "allocated engineering/maintenance, wages, human comparison time and commercial acceptance remain "
        "unmeasured.\n\n"
        "User decisions remain: approve the exact input scope, inspect the finished report and decide whether proposed "
        "source corrections should be commissioned. Those decisions do not become routine operator labor in this "
        "offering.\n\n## Scope\n\nForeground local Node execution only. No authenticated executor, network, wallet, "
        "payment, scheduler or arbitrary source-code execution.\n"
    )
    require(report == expected_report, "Finished report differs from its exact independently reconstructed context")
    require(source_ref in report and plan["manifestPath"] in report, "Finished report lost source provenance")
    require(
        "Foreground local Node execution only" in report and "No service model calls" in report,
        "Report overstates execution",
    )
    return {
        "schema": "alpha-independent-automated-source-acceptance/v1",
        "accepted": True,
        "checks": checks,
        "runId": plan["runId"],
        "sourceRef": source_ref,
        "methodIdentity": plan["methodIdentity"],
        "runnerSourceMode": "preserved-historical-source" if historical_commit else "current-installed-source",
        "verifierSha256": sha(read_bytes(Path(__file__))),
        "sourceRows": len(sources),
        "changedPaths": changed,
        "completeSha256": sha(read_bytes(directory / "COMPLETE.json")),
        "authority": "none",
        "commercialAcceptance": "unknown",
        "connectedExecution": "NOT RUN; local Node only",
        "implementation": (
            "Separately implemented Python CSV/Git/hash acceptance; no JavaScript " "comparison code imported."
        ),
        "scope": (
            "Accepted deterministic source-assurance deliverable; not authenticated "
            "executor or monetary-cost qualification."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.run_directory), indent=2))
