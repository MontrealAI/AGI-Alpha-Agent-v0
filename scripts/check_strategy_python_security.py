# SPDX-License-Identifier: Apache-2.0
"""Enforce two pinned local Python patterns over one fixed Strategy source set.

This is bounded static admission, not general Python security qualification or
permission to execute a candidate. Scientific and held source is never selected.
"""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
RULE_CONFIG = "scripts/strategy_python_security.yml"
RULE_SHA256 = "41b6fcf8b68115407c4671670da9926e91f9402a1be9a733b08ba7d11c68cdd0"
SEMGREP_VERSION = "1.99.0"
RULE_IDS = (
    "strategy-python-no-dynamic-evaluation",
    "strategy-python-no-subprocess-shell",
)
# Deliberate finite selection. Changes require separate source/policy review;
# neither a candidate nor a command-line argument may expand or reduce it.
TARGETS = (
    "alpha_factory_v1/__init__.py",
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
    "scripts/ruff_targets.py",
    "scripts/strategy_engineering_release.py",
    "scripts/validate_homepage.py",
    "tests/test_capability_checkout_release_versions.py",
    "tests/test_ci_ruff_scope_contract.py",
    "tests/test_dp_scrubber.py",
    "tests/test_paper_workflow_policy.py",
    "tests/test_public_strategy_acceptance.py",
    "tests/test_ruff_targets.py",
    "tests/test_strategy_engineering_release.py",
    "tests/test_strategy_python_security.py",
    "tests/test_strategy_release_documents.py",
    "tests/test_strategy_research_source.py",
    "tests/test_strategy_succession_binary_admission.py",
)
MAX_SOURCE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024


class CheckFailure(ValueError):
    """A failed/unknown scan has no security-admission status."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def require(condition: bool, message: str) -> None:
    """Fail closed instead of interpreting incomplete evidence as a pass."""
    if not condition:
        raise CheckFailure(message)


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _capture(root: Path, name: str) -> tuple[str, tuple[int, ...], int]:
    path = root / name
    require(path.resolve(strict=True) == path, "Scan source or ancestor is a symlink")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_SOURCE_BYTES, "Unbounded or nonregular scan source")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(MAX_SOURCE_BYTES + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    require(
        len(data) <= MAX_SOURCE_BYTES
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


def validate_report(raw: bytes, returncode: int) -> dict[str, Any]:
    """Require actual complete target coverage, never a green empty scan."""
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
        and len(scanned) == len(set(scanned)) == len(TARGETS)
        and set(scanned) == set(TARGETS),
        "Scanner target coverage is empty, incomplete, duplicated or unexpected",
    )
    require(paths.get("skipped", []) == [], "Scanner skipped a target")
    findings = report["results"]
    if findings:
        details = []
        for finding in findings:
            require(isinstance(finding, dict), "Malformed scanner finding")
            require(
                finding.get("check_id") in RULE_IDS and finding.get("path") in TARGETS, "Unexpected scanner finding"
            )
            start = finding.get("start", {})
            line = start.get("line") if isinstance(start, dict) else None
            require(type(line) is int and line > 0, "Scanner finding omitted its location")
            details.append({"rule_id": finding["check_id"], "path": finding["path"], "line": line})
        raise CheckFailure("Pinned Python security rules found prohibited operations", {"findings": details})
    require(returncode == 0, "Scanner did not finish successfully")
    return {"scanned_files": len(cast(list[str], scanned)), "findings": 0, "errors": 0, "skipped_rules": 0}


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
        result = subprocess.run(
            command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=errors, timeout=60
        )
        output.seek(0)
        raw = output.read(MAX_REPORT_BYTES + 1)
    require(capture_sources(root) == sources, "Sources or policy changed while scanning")
    coverage = validate_report(raw, result.returncode)
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
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
