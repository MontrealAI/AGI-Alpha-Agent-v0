# SPDX-License-Identifier: Apache-2.0
"""Real pinned-scanner challenges plus strict report/source admission checks.

The integration cases inspect Python as data; no fixture, mission, browser,
scientific program or held source is imported or executed by Semgrep.
"""

from __future__ import annotations

from copy import deepcopy
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest

from scripts import check_strategy_python_security as security

ROOT = Path(__file__).resolve().parents[1]


def report() -> dict[str, Any]:
    """Structural fixture only; a passing scan is proved separately by the real tool."""
    return {
        "version": security.SEMGREP_VERSION,
        "results": [],
        "errors": [],
        "skipped_rules": [],
        "paths": {"scanned": list(security.TARGETS)},
    }


@pytest.fixture(scope="module")
def scanner_python() -> str:
    """Reuse the existing pinned hook environment; never install or download a tool."""
    try:
        if metadata.version("semgrep") == security.SEMGREP_VERSION:
            return sys.executable
    except metadata.PackageNotFoundError:
        pass
    cache = Path(os.environ.get("PRE_COMMIT_HOME", str(Path.home() / ".cache/pre-commit")))
    for candidate in sorted(cache.glob("*/py_env-*/bin/python")):
        if not (candidate.parent / "semgrep").is_file():
            continue
        result = subprocess.run(
            [str(candidate), "-c", "from importlib.metadata import version; print(version('semgrep'))"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip() == security.SEMGREP_VERSION:
            return str(candidate)
    message = "Real Semgrep1.99.0 integration requires the existing blocking-hook environment; no auto-install"
    if os.environ.get("STRATEGY_REQUIRE_SEMGREP") == "1":
        pytest.fail(message)
    pytest.skip(message)


def source_copy(tmp_path: Path) -> Path:
    root = tmp_path / "fixed-source"
    for name in (security.RULE_CONFIG, *security.TARGETS):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return root


def execute_check(scanner_python: str, root: Path) -> subprocess.CompletedProcess[str]:
    """Use the same fixed checker on a temporary source copy, without target selectors."""
    driver = (
        "import json,sys;from pathlib import Path;from scripts import check_strategy_python_security as s;"
        "\ntry:r=s.check(Path(sys.argv[1]));code=0"
        "\nexcept s.CheckFailure as e:r={'passed':False,'reason':str(e),'details':e.details};code=1"
        "\nprint(json.dumps(r));raise SystemExit(code)"
    )
    env = {name: os.environ[name] for name in ("PATH", "LANG", "LC_ALL", "TMPDIR") if name in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    return subprocess.run(
        [scanner_python, "-c", driver, str(root)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90
    )


def test_actual_component_scan_has_all_fixed_files_and_rules(scanner_python: str) -> None:
    """A real process scans actual app/qualification bodies, not a mirrored safe puzzle."""
    result = subprocess.run(
        [scanner_python, "-I", str(ROOT / "scripts/check_strategy_python_security.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    assert observed["passed"] is True
    assert observed["scanned_files"] == len(security.TARGETS) == 42
    assert observed["rules"] == list(security.RULE_IDS)
    assert observed["rule_sha256"] == security.RULE_SHA256
    assert observed["production_authority"] is False and observed["runtime_qualified"] is False


@pytest.mark.parametrize(
    "source,expected_rule",
    [
        ("eval('1 + 1')\n", "strategy-python-no-dynamic-evaluation"),
        ("exec('x = 1')\n", "strategy-python-no-dynamic-evaluation"),
        ("import builtins\nbuiltins.eval('1')\n", "strategy-python-no-dynamic-evaluation"),
        ("eval('1')  # nosemgrep\n", "strategy-python-no-dynamic-evaluation"),
        (
            "import subprocess\nsubprocess.run('echo inert', shell=True)\n",
            "strategy-python-no-subprocess-shell",
        ),
        (
            "import subprocess as sp\nsp.Popen('echo inert', text=True, shell=True)\n",
            "strategy-python-no-subprocess-shell",
        ),
        (
            "from subprocess import check_output\ncheck_output('echo inert', shell=True)\n",
            "strategy-python-no-subprocess-shell",
        ),
    ],
)
def test_real_scanner_rejects_unsafe_source_without_executing_it(
    scanner_python: str, tmp_path: Path, source: str, expected_rule: str
) -> None:
    root = source_copy(tmp_path)
    target = "contrib/strategy_succession/serve.py"
    (root / target).write_text(source)
    result = execute_check(scanner_python, root)
    assert result.returncode == 1, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    assert observed["passed"] is False
    assert "prohibited operations" in observed["reason"]
    assert any(row["rule_id"] == expected_rule and row["path"] == target for row in observed["details"]["findings"])


def test_repository_package_cannot_impersonate_the_installed_scanner(scanner_python: str, tmp_path: Path) -> None:
    root = source_copy(tmp_path)
    (root / "contrib/strategy_succession/serve.py").write_text("eval('1')\n")
    fake = root / "semgrep/console_scripts"
    fake.mkdir(parents=True)
    (fake.parent / "__init__.py").write_text("")
    (fake / "__init__.py").write_text("")
    (fake / "entrypoint.py").write_text(
        "from pathlib import Path\nPath('scanner-impersonation-executed').write_text('bad')\n"
        + "print("
        + repr(json.dumps(report()))
        + ")\n"
    )
    result = execute_check(scanner_python, root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not (root / "scanner-impersonation-executed").exists()
    assert "prohibited operations" in json.loads(result.stdout)["reason"]


@pytest.mark.parametrize(
    "case",
    [
        "zero-files",
        "missing-file",
        "duplicate-file",
        "foreign-file",
        "missing-paths",
        "missing-findings",
        "errors",
        "missing-errors",
        "skipped-rule",
        "missing-rules",
        "skipped-target",
        "wrong-version",
        "nonzero-exit",
        "forged-finding",
    ],
)
def test_forged_empty_or_incomplete_reports_never_qualify(case: str) -> None:
    value = deepcopy(report())
    code = 0
    if case == "zero-files":
        value["paths"]["scanned"] = []
    elif case == "missing-file":
        value["paths"]["scanned"].pop()
    elif case == "duplicate-file":
        value["paths"]["scanned"][-1] = value["paths"]["scanned"][0]
    elif case == "foreign-file":
        value["paths"]["scanned"][-1] = "foreign.py"
    elif case == "missing-paths":
        del value["paths"]
    elif case == "missing-findings":
        del value["results"]
    elif case == "errors":
        value["errors"] = [{"type": "ParseError"}]
    elif case == "missing-errors":
        del value["errors"]
    elif case == "skipped-rule":
        value["skipped_rules"] = [{"rule_id": security.RULE_IDS[0]}]
    elif case == "missing-rules":
        del value["skipped_rules"]
    elif case == "skipped-target":
        value["paths"]["skipped"] = [{"path": security.TARGETS[0]}]
    elif case == "wrong-version":
        value["version"] = "0.0.0"
    elif case == "nonzero-exit":
        code = 2
    else:
        value["results"] = [{"check_id": "unreviewed-rule", "path": "foreign.py"}]
    with pytest.raises(security.CheckFailure):
        security.validate_report(json.dumps(value).encode(), code)


@pytest.mark.parametrize(
    "raw", [b"[]", b"{}", b'{"version":"1.99.0","version":"1.99.0"}', b'{"x":NaN}', b'{"x":1e309}']
)
def test_malformed_or_duplicate_json_is_refused(raw: bytes) -> None:
    with pytest.raises(ValueError):
        security.validate_report(raw, 0)


@pytest.mark.parametrize("change", ["rule-drift", "missing-target", "target-symlink", "new-app-file"])
def test_rule_or_source_scope_drift_fails_before_scanner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    root = source_copy(tmp_path)
    if change == "rule-drift":
        (root / security.RULE_CONFIG).write_text("rules: []\n")
    elif change == "missing-target":
        (root / security.TARGETS[0]).unlink()
    elif change == "target-symlink":
        path = root / security.TARGETS[0]
        path.unlink()
        path.symlink_to(root / security.TARGETS[1])
    else:
        (root / "contrib/strategy_succession/worker/unreviewed.py").write_text("x = 1\n")
    monkeypatch.setattr(
        security.metadata, "version", lambda _name: pytest.fail("Scanner entered before source admission")
    )
    with pytest.raises((security.CheckFailure, OSError)):
        security.check(root)


def test_fixed_targets_exclude_scientific_and_held_sources() -> None:
    assert len(security.TARGETS) == len(set(security.TARGETS)) == 42
    assert not any(name.startswith("studies/") or "/scientific/" in name for name in security.TARGETS)
    assert not any(
        name.endswith(
            (
                "test_successor_capability_delivery.py",
                "test_discovery_lab_continuation.py",
                "fleet_receipt_native.mjs",
                "fleet_git_metadata.mjs",
                "fleet_module_boundary.mjs",
            )
        )
        for name in security.TARGETS
    )


def test_command_line_cannot_change_policy_root_rules_or_targets() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_strategy_python_security", "--targets", "foreign.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "no command-line selectors" in json.loads(result.stdout)["reason"]
