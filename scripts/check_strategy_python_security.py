# SPDX-License-Identifier: Apache-2.0
"""Primary official repository Python scan and an additional bounded Strategy check.

The no-argument role checks two pinned patterns over a fixed source set, excluding
scientific/held files. The official role only parses pre-commit's selected source;
neither role executes that source or grants runtime authority.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.machinery
import importlib.util
from importlib import metadata
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from types import CodeType
from typing import Any, BinaryIO, cast
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
RULE_CONFIG = "scripts/strategy_python_security.yml"
RULE_SHA256 = "41b6fcf8b68115407c4671670da9926e91f9402a1be9a733b08ba7d11c68cdd0"
SEMGREP_VERSION = "1.99.0"
OFFICIAL_URL = "https://semgrep.dev/c/p/python"
OFFICIAL_OUTPUT = "evidence/semgrep-official"
LEGACY_CONFIG_SHA256 = "8cfac716549d157d4f994670a80abecb65c2f94c64fe976a1f2e52d9d707a918"
RULE_IDS = (
    "strategy-python-no-dynamic-evaluation",
    "strategy-python-no-subprocess-shell",
)
# Deliberate finite selection. Changes require separate source/policy review;
# neither a candidate nor a command-line argument may expand or reduce it.
TARGETS = (
    "alpha_factory_v1/__init__.py",
    "alpha_factory_v1/demos/self_healing_repo/agent_core/sandbox.py",
    "contrib/strategy_succession/__init__.py",
    "contrib/strategy_succession/qa/collect_qualification.py",
    "contrib/strategy_succession/qa/proc_namespace.py",
    "contrib/strategy_succession/qa/restore_component_fixture.py",
    "contrib/strategy_succession/qa/test_browser.py",
    "contrib/strategy_succession/qa/test_crash.py",
    "contrib/strategy_succession/qa/test_environment.py",
    "contrib/strategy_succession/qa/test_integration.py",
    "contrib/strategy_succession/review/transport_probes.py",
    "contrib/strategy_succession/serve.py",
    "contrib/strategy_succession/setup.py",
    "contrib/strategy_succession/transport/strategy_executor.py",
    "contrib/strategy_succession/transport/test_strategy_executor.py",
    "contrib/strategy_succession/worker/fixed_worker.py",
    "contrib/strategy_succession/worker/native_repair.py",
    "contrib/strategy_succession/worker/python_bridge.py",
    "contrib/strategy_succession/worker/test_fixed_worker.py",
    "contrib/strategy_succession/worker/test_native_repair.py",
    "contrib/strategy_succession/worker/test_supervisor_crash.py",
    "contrib/strategy_succession/worker/test_worker_engineering.py",
    "scripts/accept_public_strategy.py",
    "scripts/check_no_binary_diff.py",
    "scripts/check_strategy_python_security.py",
    "scripts/check_strategy_research_source.py",
    "scripts/dp_scrubber.py",
    "scripts/package_agent_release.py",
    "scripts/refresh_capability_checkout.py",
    "scripts/reuse_writer4_http.py",
    "scripts/ruff_targets.py",
    "scripts/semgrep_inapplicability.py",
    "scripts/strategy_engineering_release.py",
    "scripts/validate_homepage.py",
    "tests/test_capability_checkout_release_versions.py",
    "tests/test_ci_ruff_scope_contract.py",
    "tests/test_dp_scrubber.py",
    "tests/test_paper_workflow_policy.py",
    "tests/test_public_strategy_acceptance.py",
    "tests/test_sandbox_docker.py",
    "tests/test_ruff_targets.py",
    "tests/test_semgrep_inapplicability.py",
    "tests/test_strategy_engineering_release.py",
    "tests/test_strategy_python_security.py",
    "tests/test_strategy_qualification_xml.py",
    "tests/test_strategy_release_documents.py",
    "tests/test_strategy_research_source.py",
    "tests/test_strategy_succession_binary_admission.py",
    "tests/test_autonomous_enterprise_binary_admission.py",
    "tests/test_writer4_http_reuse.py",
)
MAX_SOURCE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
FETCH_WALL_SECONDS = 30
MATCHER_PATH = "scripts/semgrep_inapplicability.py"
# The independently reviewed module, with only its approved-map literal set to
# None. A map-pin edit never changes this code pin; other source edits do.
MATCHER_CODE_SHA256 = "3a7d74fcd8bbb4db06ec018dbae81d16dcff9813b35d0dce922f4ce4aef18443"


class CheckFailure(ValueError):
    """A failed/unknown scan has no security-admission status."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class _NoOfficialRedirect(HTTPRedirectHandler):
    """A response cannot expand the fixed official-registry network destination."""

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise CheckFailure("Official registry redirects are not admitted")


def _open_official(request: Request, timeout: int) -> Any:
    return build_opener(_NoOfficialRedirect()).open(request, timeout=timeout)


def _stop_group(pid: int, force: bool = False) -> None:
    require(pid > 0, "Invalid owned scanner process identity")
    try:
        os.killpg(pid, signal.SIGKILL if force else signal.SIGTERM)
    except ProcessLookupError:
        pass


def _download_body(destination: str, connection: Any) -> None:
    """A separately terminable worker prevents a dripping response escaping the deadline."""
    try:
        os.setsid()
        with _open_official(Request(OFFICIAL_URL, headers={"Accept": "application/json"}), timeout=30) as response:
            require(
                response.status == 200 and response.geturl() == OFFICIAL_URL, "Official registry changed origin/status"
            )
            count = 0
            read = getattr(response, "read1", response.read)
            with Path(destination).open("xb") as stream:
                while block := read(65536):
                    count += len(block)
                    require(count <= 2_000_000, "Official registry rules exceed their bound")
                    stream.write(block)
                    stream.flush()
            require(count > 0, "Official registry rules are empty")
        connection.send({"ok": True})
    except Exception as error:
        connection.send({"ok": False, "error_type": type(error).__name__})
    finally:
        connection.close()


def _fetch_body(destination: Path) -> bytes:
    context = multiprocessing.get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_download_body, args=(str(destination), sender), daemon=True)
    process.start()
    sender.close()
    try:
        process.join(timeout=FETCH_WALL_SECONDS)
        require(not process.is_alive(), "Official registry fetch exceeded its absolute wall deadline")
        require(process.exitcode == 0 and receiver.poll(), "Official registry fetch produced no verified result")
        status = receiver.recv()
        require(status == {"ok": True}, "Official registry fetch failed: " + str(status.get("error_type", "unknown")))
    finally:
        if process.is_alive():
            _stop_group(process.pid or 0)
            # The deadline can arrive before the worker has established its
            # session. Its owned Process remains a safe fallback identity.
            process.terminate()
            process.join(timeout=3)
            if process.is_alive():
                _stop_group(process.pid or 0, force=True)
                process.kill()
                process.join(timeout=3)
        receiver.close()
        process.close()
    with destination.open("rb") as stream:
        raw = stream.read(2_000_001)
    require(0 < len(raw) <= 2_000_000, "Official registry rules exceed their bound")
    return raw


def _limit_output_files() -> None:
    resources = importlib.import_module("resource")
    resources.setrlimit(resources.RLIMIT_FSIZE, (MAX_REPORT_BYTES + 1, MAX_REPORT_BYTES + 1))


def _execute(
    command: list[str], root: Path, env: dict[str, str], output: BinaryIO, errors: BinaryIO, seconds: int
) -> tuple[int, bool]:
    """Bound output in producers and stop every owned worker before returning."""
    process = subprocess.Popen(
        command,
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=output,
        stderr=errors,
        start_new_session=True,
        preexec_fn=_limit_output_files,
    )
    expired = False
    code = None
    try:
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            expired = True
            _stop_group(process.pid)
            try:
                code = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _stop_group(process.pid, force=True)
                code = process.wait(timeout=3)
    finally:
        # Even a successful leader can leave writers/workers behind. Never
        # inspect its report while an owned descendant can still modify it.
        _stop_group(process.pid, force=True)
    assert code is not None
    return code, expired


def require(condition: bool, message: str) -> None:
    """Fail closed instead of interpreting incomplete evidence as a pass."""
    if not condition:
        raise CheckFailure(message)


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _capture(root: Path, name: str, maximum: int = MAX_SOURCE_BYTES) -> tuple[str, tuple[int, ...], int]:
    path = root / name
    require(path.resolve(strict=True) == path, "Scan source or ancestor is a symlink")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "Unbounded or nonregular scan source")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    require(
        len(data) <= maximum
        and _fingerprint(before) == _fingerprint(opened) == _fingerprint(after) == _fingerprint(current)
        and path.resolve(strict=True) == path,
        "Scan source changed during capture",
    )
    return hashlib.sha256(data).hexdigest(), _fingerprint(current), len(data)


def capture_sources(root: Path) -> dict[str, tuple[str, tuple[int, ...], int]]:
    """Capture exact direct sources and the reviewed rule body before running tools."""
    require(root.is_absolute() and root.resolve(strict=True) == root, "Use a direct absolute source root")
    app = root / "contrib/strategy_succession"
    observed = {
        path.relative_to(root).as_posix()
        for path in app.rglob("*.py")
        if not path.relative_to(root).as_posix().startswith("contrib/strategy_succession/worker/scientific/")
    }
    require(
        observed == {name for name in TARGETS if name.startswith("contrib/strategy_succession/")},
        "Unreviewed or missing Strategy Python target scope",
    )
    sources = {name: _capture(root, name) for name in (RULE_CONFIG, *TARGETS)}
    require(sources[RULE_CONFIG][0] == RULE_SHA256, "Local security rules differ from the reviewed pin")
    require(sum(row[2] for row in sources.values()) <= MAX_TOTAL_BYTES, "Security scan source budget exceeded")
    return sources


def _json(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for name, child in items:
            require(name not in value, "Duplicate scanner JSON key")
            value[name] = child
        return value

    def nonfinite(_value: str) -> Any:
        raise CheckFailure("Nonfinite scanner JSON value")

    def finite_float(value: str) -> float:
        parsed = float(value)
        require(math.isfinite(parsed), "Nonfinite scanner JSON value")
        return parsed

    require(len(raw) <= MAX_REPORT_BYTES, "Scanner report exceeds its bound")
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite, parse_float=finite_float)
    require(isinstance(value, dict), "Scanner report must be an object")
    return cast(dict[str, Any], value)


def validate_report(
    raw: bytes, returncode: int, targets: tuple[str, ...] = TARGETS, rules: tuple[str, ...] = RULE_IDS
) -> dict[str, Any]:
    """Require actual complete target coverage, never a green empty scan."""
    require(bool(targets), "No security target selection was supplied")
    report = _json(raw)
    require(report.get("version") == SEMGREP_VERSION, "Scanner report has an unqualified version")
    require(type(report.get("results")) is list, "Scanner omitted its findings")
    require(
        report.get("errors") == [] and type(report.get("errors")) is list, "Scanner reported errors or omitted errors"
    )
    require(
        report.get("skipped_rules") == [] and type(report.get("skipped_rules")) is list,
        "Scanner skipped or omitted rules",
    )
    paths = report.get("paths")
    require(isinstance(paths, dict), "Scanner omitted target coverage")
    assert isinstance(paths, dict)
    scanned = paths.get("scanned")
    require(
        type(scanned) is list
        and all(type(name) is str for name in scanned)
        and len(scanned) == len(set(scanned)) == len(targets)
        and set(scanned) == set(targets),
        "Scanner target coverage is empty, incomplete, duplicated or unexpected",
    )
    require(paths.get("skipped", []) == [], "Scanner skipped a target")
    findings = report["results"]
    if findings:
        details = []
        for finding in findings:
            require(isinstance(finding, dict), "Malformed scanner finding")
            require(finding.get("check_id") in rules and finding.get("path") in targets, "Unexpected scanner finding")
            start = finding.get("start", {})
            line = start.get("line") if isinstance(start, dict) else None
            require(type(line) is int and line > 0, "Scanner finding omitted its location")
            details.append({"rule_id": finding["check_id"], "path": finding["path"], "line": line})
        raise CheckFailure("Pinned Python security rules found prohibited operations", {"findings": details})
    require(returncode == 0, "Scanner did not finish successfully")
    return {"scanned_files": len(cast(list[str], scanned)), "findings": 0, "errors": 0, "skipped_rules": 0}


def fetch_official_policy(destination: Path) -> dict[str, Any]:
    """Capture once and run the exact unmodified official registry response."""
    raw = _fetch_body(destination)
    parser = importlib.import_module("ruamel.yaml").YAML(typ="safe")
    try:
        text = raw.decode("utf-8")
        value = parser.load(text)
        document = parser.compose(text)
    except Exception as error:
        raise CheckFailure("Official registry YAML is invalid", {"error_type": type(error).__name__}) from error
    require(isinstance(value, dict) and type(value.get("rules")) is list, "Official registry omitted its rules")
    rules = value["rules"]
    require(bool(rules) and all(isinstance(rule, dict) for rule in rules), "Official registry has no valid rules")
    ids = [rule.get("id") for rule in rules]
    require(
        all(type(name) is str and name for name in ids) and len(ids) == len(set(ids)),
        "Official registry has duplicate or missing rule identities",
    )
    require(any("python" in rule.get("languages", []) for rule in rules), "Official registry has no Python rules")
    sequences = [node for key, node in document.value if key.value == "rules"]
    require(len(sequences) == 1 and sequences[0].tag.endswith(":seq"), "Official rule spans are not a direct sequence")
    rule_nodes = sequences[0].value
    require(len(rule_nodes) == len(rules), "Official rule definition spans are incomplete")
    definitions = []
    for rule, node in zip(rules, rule_nodes):
        first, last = node.start_mark.index, node.end_mark.index
        span = text[first:last].encode("utf-8")
        definitions.append(
            {
                "id": rule["id"],
                "sha256": hashlib.sha256(span).hexdigest(),
                "start_byte": len(text[:first].encode("utf-8")),
                "end_byte": len(text[:last].encode("utf-8")),
            }
        )
    return {
        "source_url": OFFICIAL_URL,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rule_ids": ids,
        "rule_definitions": definitions,
        "definition_digest_scope": "Exact unmodified YAML mapping-node byte spans, excluding sequence indicators",
    }


def official_targets(root: Path, names: tuple[str, ...]) -> tuple[str, ...]:
    """Validate the actual nonempty pre-commit selection rather than infer its scope."""
    require(bool(names) and len(names) == len(set(names)), "Official scan requires unique actual filename targets")
    tracked = set(_repository_git(root, "ls-files", "-z").decode("utf-8").split("\0"))
    for name in names:
        path = Path(name)
        require(
            not name.startswith("-")
            and not path.is_absolute()
            and path.as_posix() == name
            and not {"", ".", ".."}.intersection(name.split("/"))
            and name in tracked,
            "Unknown, escaping or option-like official target",
        )
        require(path.suffix in {".py", ".pyw", ".pyi"}, "Official role requires Python source filenames")
        _capture(root, name, 1_000_000)
    return names


def _load_matcher(root: Path) -> Any:
    before = _capture(root, MATCHER_PATH, 1_000_000)
    with (root / MATCHER_PATH).open("rb") as stream:
        body = stream.read(1_000_001)
    require(len(body) <= 1_000_000, "Matcher grew beyond its source bound")
    matches = list(re.finditer(rb'^APPROVED_MAP_SHA256: str \| None = (None|"[0-9a-f]{64}")$', body, re.MULTILINE))
    require(len(matches) == 1, "Matcher must have one exact reviewed map-pin declaration")
    first, last = matches[0].span(1)
    normalized = body[:first] + b"None" + body[last:]
    require(hashlib.sha256(normalized).hexdigest() == MATCHER_CODE_SHA256, "Matcher differs from the reviewed code pin")
    require(_capture(root, MATCHER_PATH, 1_000_000) == before, "Matcher changed before loading")
    name = "_agialpha_reviewed_semgrep_matcher"

    class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
        def get_code(self, _fullname: str) -> CodeType:
            # Compile only captured/pinned bytes; ignore repo bytecode caches
            # and never reopen a changed source file for execution.
            return compile(body, str(root / MATCHER_PATH), "exec", dont_inherit=True)

    specification = importlib.util.spec_from_file_location(
        name, root / MATCHER_PATH, loader=PinnedSourceLoader(name, str(root / MATCHER_PATH))
    )
    require(specification is not None and specification.loader is not None, "Reviewed matcher cannot be loaded")
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module  # Dataclass registration only; no repo sys.path entry.
    specification.loader.exec_module(module)
    require(_capture(root, MATCHER_PATH, 1_000_000) == before, "Matcher changed while loading")
    return module


def _matcher_evidence(value: Any) -> dict[str, Any]:
    return {
        "targets": list(value.targets),
        "repository_inventory_sha256": value.repository.sha256,
        "repository_records": list(value.repository.records),
        "raw_source_sha256": dict(value.repository.raw_sha256),
        "head_source_sha256": dict(value.repository.head_sha256),
        "within_run_fingerprints": dict(value.repository.fingerprints),
    }


def _repository_git(root: Path, *args: str) -> bytes:
    # Reuse the pinned module's bounded, selector-free Git transport for source
    # metadata as well as its whole-content inventory.
    return cast(bytes, _load_matcher(root)._git(*args))


def _sha256(value: Any) -> bool:
    return type(value) is str and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _public_source_path(value: Any) -> bool:
    if type(value) is not str or not value or len(value) > 4096 or any(ord(char) < 32 for char in value):
        return False
    path = Path(value)
    return (
        not value.startswith("-")
        and not path.is_absolute()
        and path.as_posix() == value
        and not {"", ".", ".."}.intersection(value.split("/"))
    )


def _public_policy(value: Any) -> dict[str, Any] | None:
    """Only identifiers/digests/positions; never licensed rule bodies/metadata."""
    if not isinstance(value, dict):
        return None
    valid = True
    raw_ids = value.get("rule_ids", [])
    if type(raw_ids) is not list:
        raw_ids, valid = [], False
    ids = [name for name in raw_ids if type(name) is str and re.fullmatch(r"[A-Za-z0-9_.-]{1,512}", name)]
    valid = valid and len(ids) == len(raw_ids) == len(set(ids)) and _sha256(value.get("sha256"))
    definitions = []
    rows = value.get("rule_definitions", [])
    if type(rows) is not list:
        rows, valid = [], False
    for row in rows:
        if (
            isinstance(row, dict)
            and row.get("id") in ids
            and _sha256(row.get("sha256"))
            and all(type(row.get(key)) is int for key in ("start_byte", "end_byte"))
            and 0 <= row["start_byte"] < row["end_byte"] <= 2_000_000
        ):
            definitions.append({key: row[key] for key in ("id", "sha256", "start_byte", "end_byte")})
        else:
            valid = False
    result = {
        "source_url": OFFICIAL_URL,
        "sha256": value.get("sha256") if _sha256(value.get("sha256")) else None,
        "rule_ids": ids,
        "rule_definitions": definitions,
        "definition_digest_scope": "Unmodified local YAML mapping spans; rule bodies are not published",
        "declared_license": "Semgrep Rules License v1.0",
    }
    size = value.get("bytes")
    if size is None or (type(size) is int and 0 <= size <= 2_000_000):
        result["bytes"] = size
    else:
        valid = False
    timestamp = value.get("observed_at")
    if timestamp is None:
        result["observed_at"] = None
    elif type(timestamp) is str and len(timestamp) <= 40:
        try:
            datetime.fromisoformat(timestamp)
            result["observed_at"] = timestamp
        except ValueError:
            valid = False
    else:
        valid = False
    result["projection_valid"] = valid
    return result


def public_report(summary: dict[str, Any]) -> dict[str, Any]:
    """Public logs/artifacts expose results and identities, excluding raw errors."""
    keys = (
        "schema",
        "passed",
        "artifact_directory",
        "public_artifact_directory",
        "automatic_retry",
        "checker_sha256",
        "commit",
        "selected_targets",
        "selected_files",
        "scanned_files",
        "findings",
        "errors",
        "skipped_rules",
        "exit_code",
        "tool_version",
        "raw_report_sha256",
        "output_bytes",
        "elapsed_seconds",
        "child_cpu_user_seconds",
        "child_cpu_system_seconds",
        "source_drift",
        "wall_budget_expired",
        "local_config_sha256",
        "production_authority",
        "runtime_qualified",
        "raw_scan_passed",
        "raw_exit_code",
        "raw_finding_count",
        "policy_disposition",
        "policy_accepted",
        "inapplicable_finding_count",
        "matcher_code_sha256",
        "repository_inventory_sha256",
        "repository_files",
        "committed_context_qualified",
        "committed_context_required",
    )
    result: dict[str, Any] = {}
    invalid = []
    boolean = {
        "passed",
        "automatic_retry",
        "wall_budget_expired",
        "production_authority",
        "runtime_qualified",
        "raw_scan_passed",
        "policy_accepted",
        "committed_context_qualified",
        "committed_context_required",
    }
    hashes = {
        "checker_sha256",
        "raw_report_sha256",
        "local_config_sha256",
        "matcher_code_sha256",
        "repository_inventory_sha256",
    }
    counts = {
        "selected_files",
        "scanned_files",
        "findings",
        "errors",
        "skipped_rules",
        "raw_finding_count",
        "inapplicable_finding_count",
        "repository_files",
    }
    seconds = {"elapsed_seconds", "child_cpu_user_seconds", "child_cpu_system_seconds"}
    for key in keys:
        if key not in summary:
            continue
        value = summary[key]
        valid = False
        if key in boolean:
            valid = type(value) is bool
        elif key in hashes:
            valid = _sha256(value)
        elif key in counts:
            valid = value is None or (type(value) is int and value >= 0)
        elif key in seconds:
            valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
        elif key in ("exit_code", "raw_exit_code"):
            valid = type(value) is int
        elif key == "policy_disposition":
            valid = value in (
                "INACTIVE",
                "REFUSED",
                "EXACT_REVIEWED_INAPPLICABILITY",
                "NOT_NEEDED_RAW_PASS",
                "RAW_ONLY_UNQUALIFIED",
            )
        elif key == "commit":
            valid = type(value) is str and bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value))
        elif key == "schema":
            valid = value in ("agialpha.official-python-security/v1", "agialpha.strategy-python-security/v1")
        elif key == "tool_version":
            valid = value == SEMGREP_VERSION
        elif key in ("artifact_directory", "public_artifact_directory"):
            prefix = OFFICIAL_OUTPUT + ("/public" if key.startswith("public") else "")
            valid = type(value) is str and bool(re.fullmatch(re.escape(prefix) + r"/attempt-[a-z0-9_]{1,32}", value))
        elif key in ("selected_targets", "source_drift"):
            valid = type(value) is list and all(_public_source_path(name) for name in value)
        elif key == "output_bytes":
            valid = (
                type(value) is dict
                and set(value) == {"scanner.json", "scanner.stderr"}
                and all(type(size) is int and 0 <= size <= MAX_REPORT_BYTES + 1 for size in value.values())
            )
        if valid:
            result[key] = value
        else:
            invalid.append(key)
    observed = summary.get("observed", {})
    if isinstance(observed, dict):
        for source, target in (("errors", "observed_error_count"), ("skipped_rules", "observed_skipped_rule_count")):
            items = observed.get(source)
            result[target] = len(items) if type(items) is list else None
    if "reason" in summary:
        result["failure_details_sha256"] = hashlib.sha256(str(summary["reason"]).encode()).hexdigest()
        result["failure_details_location"] = "Retained local raw evidence; upstream configuration text is not published"
    result["official_policy"] = _public_policy(summary.get("official_policy"))
    if result["official_policy"] is not None and not result["official_policy"]["projection_valid"]:
        invalid.append("official_policy")
    result["projection_valid"] = not invalid
    result["invalid_public_fields"] = invalid
    if invalid:
        result["passed"] = False
    result["published_rule_bodies"] = False
    result["published_raw_report"] = False
    result["publication_scope"] = (
        "Counts, identifiers, source hashes and byte positions; local raw evidence remains unmodified"
    )
    return result


def _write_public_receipt(root: Path, attempt: Path, summary: dict[str, Any]) -> None:
    destination = root / OFFICIAL_OUTPUT / "public" / attempt.name
    require(destination.resolve() == destination, "Public evidence directory must not be an alias")
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    summary["public_artifact_directory"] = destination.relative_to(root).as_posix()
    projected = public_report(summary)
    require(projected["projection_valid"], "Public evidence metadata failed type validation")
    findings = []
    report_path = attempt / "scanner.json"
    if report_path.is_file():
        try:
            with report_path.open("rb") as stream:
                report = _json(stream.read(MAX_REPORT_BYTES + 1))
            for finding in report.get("results", []):
                if not isinstance(finding, dict) or finding.get("path") not in summary.get("selected_targets", []):
                    continue
                name = finding.get("check_id")
                if type(name) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]{1,512}", name):
                    continue
                location = {key: finding.get(key) for key in ("start", "end")}
                if not all(
                    isinstance(row, dict)
                    and set(row) == {"line", "col", "offset"}
                    and all(type(number) is int for number in row.values())
                    for row in location.values()
                ):
                    continue
                findings.append({"rule_id": name, "path": finding["path"], **location})
        except (ValueError, OSError, TypeError):
            pass  # The failed raw report remains local and its hash is retained.
    sources = {}
    for phase in ("before", "after"):
        path = attempt / ("source-" + phase + ".json")
        if path.is_file():
            with path.open("rb") as stream:
                source = _json(stream.read(MAX_REPORT_BYTES + 1))
            allowed = set(summary.get("selected_targets", [])) | {"semgrep.yml"}
            require(
                all(
                    name in allowed
                    and _public_source_path(name)
                    and type(row) is list
                    and len(row) == 3
                    and _sha256(row[0])
                    and type(row[2]) is int
                    and row[2] >= 0
                    for name, row in source.items()
                ),
                "Public source identities failed type validation",
            )
            sources[phase] = {name: {"sha256": row[0], "bytes": row[2]} for name, row in source.items()}
    files = {
        "summary.json": projected,
        "policy-identity.json": projected["official_policy"],
        "finding-index.json": {
            "raw_report_sha256": summary.get("raw_report_sha256"),
            "raw_finding_count": summary.get("findings"),
            "projected_findings": findings,
            "raw_result_published": False,
        },
        "source-identities.json": sources,
    }
    for name, value in files.items():
        with (destination / name).open("x") as stream:
            stream.write(json.dumps(value, indent=2) + "\n")


def check_official(root: Path, names: tuple[str, ...], *, require_committed_context: bool = False) -> dict[str, Any]:
    """Run primary official policy, preserving complete separate attempt artifacts."""
    output = root / OFFICIAL_OUTPUT
    require(root.is_absolute() and root.resolve(strict=True) == root, "Official root must be direct and absolute")
    require(output.resolve() == output, "Official evidence directory must not be an alias")
    output.mkdir(parents=True, exist_ok=True)
    require(output.resolve() == output, "Official evidence directory must not be an alias")
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=output))
    summary: dict[str, Any] = {
        "schema": "agialpha.official-python-security/v1",
        "passed": False,
        "scope": "Actual pre-commit filename selection; no finding, error or skipped work is waived",
        "production_authority": False,
        "runtime_qualified": False,
        "automatic_retry": False,
        "wall_budget_expired": False,
        "raw_scan_passed": False,
        "policy_accepted": False,
        "policy_disposition": "REFUSED",
        "committed_context_qualified": False,
        "committed_context_required": require_committed_context,
    }
    before: dict[str, tuple[str, tuple[int, ...], int]] = {}
    index_before = None
    checker_before = None
    started = time.perf_counter()
    try:
        require(type(require_committed_context) is bool, "Committed-context requirement must be boolean")
        checker_before = _capture(ROOT, "scripts/check_strategy_python_security.py", 1_000_000)
        summary["checker_sha256"] = checker_before[0]
        require(metadata.version("semgrep") == SEMGREP_VERSION, "Official policy requires pinned Semgrep 1.99.0")
        require(hasattr(os, "killpg"), "Official bounded process supervision requires the qualified POSIX environment")
        resources = importlib.import_module("resource")
        targets = official_targets(root, names)
        summary.update(selected_targets=list(targets), selected_files=len(targets))
        summary["commit"] = _repository_git(root, "rev-parse", "HEAD").decode("ascii").strip()
        index_before = _repository_git(root, "ls-files", "--stage", "-z")
        before = {name: _capture(root, name, 1_000_000) for name in (*targets, "semgrep.yml")}
        require(sum(row[2] for row in before.values()) <= 32_000_000, "Official source selection exceeds its bound")
        (attempt / "source-before.json").write_text(json.dumps(before, indent=2) + "\n")
        summary["local_config_sha256"] = before["semgrep.yml"][0]
        require(before["semgrep.yml"][0] == LEGACY_CONFIG_SHA256, "Legacy local security configuration changed")
        policy = fetch_official_policy(attempt / "official-p-python.yml")
        summary["official_policy"] = policy
        (attempt / "policy-identity.json").write_text(json.dumps(policy, indent=2) + "\n")
        matcher = _load_matcher(root)
        definitions = tuple(
            matcher.RuleDefinition(row["id"], row["start_byte"], row["end_byte"], row["sha256"])
            for row in policy.get("rule_definitions", [])
        )
        with (attempt / "official-p-python.yml").open("rb") as stream:
            pack_body = stream.read(2_000_001)
        require(
            len(pack_body) <= 2_000_000 and hashlib.sha256(pack_body).hexdigest() == policy["sha256"],
            "Official policy changed before qualification",
        )
        matcher_before = None
        try:
            matcher_before = matcher.capture_inputs(targets, pack_body, definitions)
        except ValueError as error:
            # A normal staged edit differs from HEAD. That prevents committed
            # source qualification, never the required raw official scan.
            summary["qualification_before_refusal"] = str(error)
        if matcher_before is not None:
            (attempt / "qualification-before.json").write_text(
                json.dumps(_matcher_evidence(matcher_before), indent=2) + "\n"
            )
            summary.update(
                matcher_code_sha256=MATCHER_CODE_SHA256,
                repository_inventory_sha256=matcher_before.repository.sha256,
                repository_files=len(matcher_before.repository.records),
            )
        command = [
            sys.executable,
            "-I",
            "-m",
            "semgrep.console_scripts.entrypoint",
            "--config",
            str(attempt / "official-p-python.yml"),
            "--config",
            "semgrep.yml",
            "--error",
            "--strict",
            "--json",
            "--metrics=off",
            "--disable-version-check",
            "--disable-nosem",
            "--no-rewrite-rule-ids",
            "--no-git-ignore",
            "--x-ignore-semgrepignore-files",
            "--jobs=2",
            "--",
            *targets,
        ]
        (attempt / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        env = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP")
            if key in os.environ
        }
        env.update(PYTHONNOUSERSITE="1", SEMGREP_ENABLE_VERSION_CHECK="0", SEMGREP_SEND_METRICS="off")
        usage = resources.getrusage(resources.RUSAGE_CHILDREN)
        with (attempt / "scanner.json").open("wb") as stdout, (attempt / "scanner.stderr").open("wb") as stderr:
            code, expired = _execute(command, root, env, stdout, stderr, 600)
            summary["wall_budget_expired"] = expired
        after_usage = resources.getrusage(resources.RUSAGE_CHILDREN)
        summary.update(
            exit_code=code,
            tool_version=SEMGREP_VERSION,
            child_cpu_user_seconds=after_usage.ru_utime - usage.ru_utime,
            child_cpu_system_seconds=after_usage.ru_stime - usage.ru_stime,
        )
        with (attempt / "scanner.json").open("rb") as stream:
            summary["raw_report_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
            stream.seek(0)
            raw = stream.read(MAX_REPORT_BYTES + 1)
        summary["output_bytes"] = {name: (attempt / name).stat().st_size for name in ("scanner.json", "scanner.stderr")}
        require(
            all(size <= MAX_REPORT_BYTES for size in summary["output_bytes"].values()),
            "Scanner output exceeded its producer bound",
        )
        matcher_after = None
        try:
            matcher_after = matcher.capture_inputs(targets, pack_body, definitions)
        except ValueError as error:
            summary["qualification_after_refusal"] = str(error)
        if matcher_after is not None:
            (attempt / "qualification-after.json").write_text(
                json.dumps(_matcher_evidence(matcher_after), indent=2) + "\n"
            )
        parsed = _json(raw)
        summary["observed"] = {key: parsed.get(key) for key in ("version", "paths", "errors", "skipped_rules")}
        summary["findings"] = len(parsed.get("results", [])) if type(parsed.get("results")) is list else None
        rules = tuple(policy["rule_ids"]) + ("solidity-tx-origin", "solidity-call-value")
        raw_clean = False
        try:
            summary.update(validate_report(raw, code, targets, rules))
            raw_clean = True
        except CheckFailure as error:
            # Only fully checked, nonempty exit1 findings reach applicability.
            # Errors, skipped work, coverage/version issues and exit2+ refuse.
            if code != 1 or not error.details.get("findings"):
                raise
            summary["details"] = error.details
        if matcher_before is not None and matcher_after is not None:
            decision = matcher.assess(raw, code, matcher_before, matcher_after)
            summary["committed_context_qualified"] = True
        else:
            # No committed context means no map lookup or exit1 exception,
            # even if an operator-approved map exists in another source epoch.
            decision = {
                "policy_disposition": "RAW_ONLY_UNQUALIFIED",
                "policy_accepted": False,
                "inapplicable_finding_count": 0,
            }
        summary.update(
            raw_scan_passed=raw_clean,
            raw_exit_code=code,
            raw_finding_count=summary.get("findings"),
            policy_disposition=decision["policy_disposition"],
            policy_accepted=decision["policy_accepted"],
            inapplicable_finding_count=decision["inapplicable_finding_count"],
        )
        summary["inapplicability_evidence"] = decision
        admitted = raw_clean and decision["policy_disposition"] == "RAW_ONLY_UNQUALIFIED"
        admitted = admitted or (
            decision["policy_accepted"] is True
            and (
                (raw_clean and decision["policy_disposition"] == "NOT_NEEDED_RAW_PASS")
                or (not raw_clean and code == 1 and decision["policy_disposition"] == "EXACT_REVIEWED_INAPPLICABILITY")
            )
        )
        require(admitted, "Official findings or qualification remain unadmitted")
        require(
            not require_committed_context or summary["committed_context_qualified"] is True,
            "This invocation requires committed-source qualification; raw-only evidence is insufficient",
        )
        require(summary.get("wall_budget_expired") is not True, "Official scanner exceeded its wall budget")
        require(
            hashlib.sha256((attempt / "official-p-python.yml").read_bytes()).hexdigest() == policy["sha256"],
            "Captured official rules changed during scanning",
        )
        summary["passed"] = True
    except (ValueError, OSError, ImportError, subprocess.SubprocessError) as error:
        summary.update(
            reason=str(error) if isinstance(error, CheckFailure) else type(error).__name__,
            details=error.details if isinstance(error, CheckFailure) else {},
        )
    finally:
        try:
            if (
                checker_before is not None
                and _capture(ROOT, "scripts/check_strategy_python_security.py", 1_000_000) != checker_before
            ):
                summary.update(passed=False, reason="Security checker changed during scanning")
            if "official_policy" in summary:
                if (
                    hashlib.sha256((attempt / "official-p-python.yml").read_bytes()).hexdigest()
                    != summary["official_policy"]["sha256"]
                ):
                    summary.update(passed=False, reason="Captured official rules changed during scanning")
            if (
                "commit" in summary
                and _repository_git(root, "rev-parse", "HEAD").decode("ascii").strip() != summary["commit"]
            ):
                summary.update(passed=False, reason="Committed source identity changed during qualification")
            if index_before is not None and _repository_git(root, "ls-files", "--stage", "-z") != index_before:
                summary.update(passed=False, reason="Git index changed during the raw official scan")
        except (ValueError, OSError) as error:
            summary.update(passed=False, reason=type(error).__name__)
        if before:
            try:
                after = {name: _capture(root, name, 1_000_000) for name in before}
                (attempt / "source-after.json").write_text(json.dumps(after, indent=2) + "\n")
                summary["source_drift"] = [name for name in before if before[name] != after[name]]
                if summary["source_drift"]:
                    summary.update(passed=False, reason="Official source changed during scanning")
            except (ValueError, OSError) as error:
                summary.update(passed=False, reason=type(error).__name__)
        summary["elapsed_seconds"] = time.perf_counter() - started
        summary["artifact_directory"] = attempt.relative_to(root).as_posix()
        try:
            _write_public_receipt(root, attempt, summary)
        except (ValueError, OSError, TypeError, KeyError):
            summary.update(passed=False, reason="Public evidence projection failed; local raw evidence is retained")
        (attempt / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def check(root: Path = ROOT) -> dict[str, Any]:
    """Execute the fixed local policy using the existing pinned hook interpreter."""
    sources = capture_sources(root)
    require(metadata.version("semgrep") == SEMGREP_VERSION, "Use the existing pinned Semgrep 1.99.0 hook environment")
    command = [
        sys.executable,
        "-I",
        "-m",
        # Semgrep1.99's top-level __main__ deliberately refuses execution. This
        # is its official installed console entry point in the same interpreter.
        "semgrep.console_scripts.entrypoint",
        "--config",
        RULE_CONFIG,
        "--error",
        "--strict",
        "--json",
        "--metrics=off",
        "--disable-version-check",
        "--disable-nosem",
        "--no-rewrite-rule-ids",
        "--no-git-ignore",
        "--x-ignore-semgrepignore-files",
        *TARGETS,
    ]
    env = {
        key: os.environ[key]
        for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP")
        if key in os.environ
    }
    env.update(PYTHONNOUSERSITE="1", SEMGREP_ENABLE_VERSION_CHECK="0", SEMGREP_SEND_METRICS="off")
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        code, expired = _execute(command, root, env, output, errors, 60)
        output.seek(0)
        raw = output.read(MAX_REPORT_BYTES + 1)
        require(
            os.fstat(output.fileno()).st_size <= MAX_REPORT_BYTES
            and os.fstat(errors.fileno()).st_size <= MAX_REPORT_BYTES,
            "Scanner output exceeded its producer bound",
        )
    require(not expired, "Bounded Strategy scanner exceeded its wall deadline")
    require(capture_sources(root) == sources, "Sources or policy changed while scanning")
    coverage = validate_report(raw, code)
    identities = {name: row[0] for name, row in sources.items()}
    digest = hashlib.sha256(json.dumps(identities, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": "agialpha.strategy-python-security/v1",
        "passed": True,
        "scope": "Fixed Strategy source set; direct eval/exec and literal subprocess shell=True only",
        "tool_version": SEMGREP_VERSION,
        "rule_sha256": RULE_SHA256,
        "rules": list(RULE_IDS),
        "source_inventory_sha256": digest,
        **coverage,
        "runtime_qualified": False,
        "production_authority": False,
    }


def main() -> int:
    """No target, rule, report or root selection is accepted from command-line data."""
    try:
        if sys.argv[1:2] == ["--official-repository"]:
            require(sys.argv[2:3] == ["--"], "Official role requires the filename delimiter")
            report = check_official(
                ROOT,
                tuple(sys.argv[3:]),
                require_committed_context=os.environ.get("STRATEGY_REQUIRE_COMMITTED_CONTEXT") == "1",
            )
        else:
            require(len(sys.argv) == 1, "This policy accepts no command-line selectors")
            report = check()
    except (ValueError, OSError, subprocess.SubprocessError, metadata.PackageNotFoundError) as error:
        report = {
            "schema": "agialpha.strategy-python-security/v1",
            "passed": False,
            "reason": str(error) if isinstance(error, CheckFailure) else type(error).__name__,
            "details": error.details if isinstance(error, CheckFailure) else {},
            "runtime_qualified": False,
            "production_authority": False,
        }
    display = public_report(report) if sys.argv[1:2] == ["--official-repository"] else report
    print(json.dumps(display, sort_keys=True))
    return 0 if report["passed"] is True and display.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
