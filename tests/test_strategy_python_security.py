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
import time
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
    assert observed["scanned_files"] == len(security.TARGETS) == 48
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
    assert len(security.TARGETS) == len(set(security.TARGETS)) == 48
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


@pytest.mark.parametrize("names", [(), ("--config",), ("../escape.py",), ("/tmp/escape.py",), ("unknown.py",)])
def test_official_role_refuses_unknown_empty_and_option_targets(names: tuple[str, ...]) -> None:
    with pytest.raises((security.CheckFailure, OSError)):
        security.official_targets(ROOT, names)


def test_official_report_cannot_substitute_another_or_empty_selection() -> None:
    value = report()
    value["paths"]["scanned"] = ["selected.py"]
    assert security.validate_report(json.dumps(value).encode(), 0, ("selected.py",))["scanned_files"] == 1
    for supplied in [(), ("different.py",), ("selected.py", "missing.py")]:
        with pytest.raises(security.CheckFailure):
            security.validate_report(json.dumps(value).encode(), 0, supplied)


def test_official_role_passes_exact_captured_body_and_retains_protocol_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Protocol-only fixture; actual official download/engine coverage is tested below."""
    root = tmp_path.resolve()
    (root / "selected.py").write_text("x = 1\n")
    shutil.copyfile(ROOT / "semgrep.yml", root / "semgrep.yml")
    monkeypatch.setattr(security.metadata, "version", lambda _name: "1.99.0")
    monkeypatch.setattr(security, "official_targets", lambda _root, names: names)
    monkeypatch.setattr(security.subprocess, "check_output", lambda *_a, **_k: "a" * 40)
    raw = b"rules:\n- id: captured-rule\n  languages: [python]\n  pattern: eval(...)\n  message: captured\n  severity: ERROR\n"

    def captured(path: Path) -> dict[str, Any]:
        path.write_bytes(raw)
        return {
            "source_url": security.OFFICIAL_URL,
            "sha256": security.hashlib.sha256(raw).hexdigest(),
            "rule_ids": ["captured-rule"],
        }

    monkeypatch.setattr(security, "fetch_official_policy", captured)
    requested = []

    class Process:
        def __init__(self, command: list[str], **kwargs: Any) -> None:
            requested.append(command)
            assert command[:4] == [sys.executable, "-I", "-m", "semgrep.console_scripts.entrypoint"]
            assert Path(command[5]).read_bytes() == raw
            assert "p/python" not in command  # No second, unbound registry fetch.
            assert command[-2:] == ["--", "selected.py"]
            value = report()
            value["paths"]["scanned"] = ["selected.py"]
            kwargs["stdout"].write(json.dumps(value).encode())
            self.pid = 0

        def wait(self, timeout: int) -> int:
            assert timeout == 600
            return 0

    monkeypatch.setattr(security.subprocess, "Popen", Process)
    first = security.check_official(root, ("selected.py",))
    second = security.check_official(root, ("selected.py",))
    assert first["passed"] is True and second["passed"] is True and len(requested) == 2
    assert first["official_policy"]["source_url"] == "https://semgrep.dev/c/p/python"
    assert first["artifact_directory"] != second["artifact_directory"]
    for result in (first, second):
        directory = root / result["artifact_directory"]
        assert (directory / "official-p-python.yml").read_bytes() == raw
        assert {"scanner.json", "scanner.stderr", "source-before.json", "source-after.json", "summary.json"} <= {
            path.name for path in directory.iterdir()
        }


def test_actual_official_role_downloads_and_scans_an_actual_component(scanner_python: str) -> None:
    """A small real component scan is partial evidence, never a repository pass."""
    result = subprocess.run(
        [
            scanner_python,
            "-I",
            str(ROOT / "scripts/check_strategy_python_security.py"),
            "--official-repository",
            "--",
            "contrib/strategy_succession/transport/strategy_executor.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    assert observed["selected_files"] == observed["scanned_files"] == 1
    assert observed["official_policy"]["source_url"] == security.OFFICIAL_URL
    assert len(observed["official_policy"]["rule_ids"]) > 2
    directory = ROOT / observed["artifact_directory"]
    assert (
        security.hashlib.sha256((directory / "official-p-python.yml").read_bytes()).hexdigest()
        == observed["official_policy"]["sha256"]
    )
    command = json.loads((directory / "command.json").read_text())
    assert command[command.index("--config") + 1] == str(directory / "official-p-python.yml")
    policy_raw = (directory / "official-p-python.yml").read_bytes()
    for definition in observed["official_policy"]["rule_definitions"]:
        span = policy_raw[definition["start_byte"] : definition["end_byte"]]
        assert security.hashlib.sha256(span).hexdigest() == definition["sha256"]


def test_actual_official_ids_are_stable_across_evidence_directories(scanner_python: str, tmp_path: Path) -> None:
    """The real engine reports official IDs, without a temporary path prefix."""
    root = tmp_path / "official-source"
    root.mkdir()
    (root / "inert.py").write_text("import hashlib\nhashlib.sha1(b'inert')\n")
    shutil.copyfile(ROOT / "semgrep.yml", root / "semgrep.yml")
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "inert.py", "semgrep.yml"],
        ["git", "-c", "user.name=Static fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "inert"],
    ):
        subprocess.run(command, cwd=root, check=True, capture_output=True)
    driver = (
        "import json,runpy,sys;from pathlib import Path;"
        "s=runpy.run_path(sys.argv[1],run_name='official_fixture');"
        "r=s['check_official'](Path(sys.argv[2]),('inert.py',));print(json.dumps(r))"
    )
    attempts = []
    for _ in range(2):
        result = subprocess.run(
            [scanner_python, "-I", "-c", driver, str(ROOT / "scripts/check_strategy_python_security.py"), str(root)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        observed = json.loads(result.stdout)
        assert observed["passed"] is False and observed["exit_code"] == 1
        assert observed["selected_files"] == 1 and observed["source_drift"] == []
        report_raw = json.loads((root / observed["artifact_directory"] / "scanner.json").read_text())
        assert report_raw["paths"]["scanned"] == ["inert.py"] and report_raw["errors"] == []
        assert report_raw["skipped_rules"] == []
        attempts.append((observed, {finding["check_id"] for finding in report_raw["results"]}))
    expected = "python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1"
    assert expected in attempts[0][1] == attempts[1][1]
    assert attempts[0][0]["artifact_directory"] != attempts[1][0]["artifact_directory"]


def test_fixed_official_fetch_keeps_unmodified_unicode_rule_spans(scanner_python: str, tmp_path: Path) -> None:
    driver = r"""
import hashlib,json,runpy,sys
from pathlib import Path
s=runpy.run_path(sys.argv[1],run_name='fetch_fixture')
raw='rules:\n- id: exact-id\n  languages: [python]\n  pattern: eval(...)\n  message: café\n  severity: ERROR\n'.encode()
calls=Path(sys.argv[2]+'.calls')
class Response:
 status=200
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def geturl(self):return s['OFFICIAL_URL']
 def read(self,maximum):
  assert maximum==65536
  if getattr(self,'read_done',False):return b''
  self.read_done=True;return raw
def opened(request,timeout):
 assert request.full_url=='https://semgrep.dev/c/p/python' and timeout==30
 assert 'Authorization' not in request.headers
 with calls.open('a') as stream:stream.write(request.full_url+'\n')
 return Response()
s['fetch_official_policy'].__globals__['_open_official']=opened
destination=Path(sys.argv[2])
identity=s['fetch_official_policy'](destination)
assert destination.read_bytes()==raw and calls.read_text().splitlines()==[s['OFFICIAL_URL']]
assert identity['sha256']==hashlib.sha256(raw).hexdigest()
for row in identity['rule_definitions']:
 assert row['id']=='exact-id'
 assert row['sha256']==hashlib.sha256(raw[row['start_byte']:row['end_byte']]).hexdigest()
print(json.dumps(identity))
"""
    result = subprocess.run(
        [
            scanner_python,
            "-I",
            "-c",
            driver,
            str(ROOT / "scripts/check_strategy_python_security.py"),
            str(tmp_path / "official.yml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["rule_ids"] == ["exact-id"]


def test_official_redirect_cannot_expand_the_network_destination() -> None:
    with pytest.raises(security.CheckFailure, match="redirects"):
        security._NoOfficialRedirect().redirect_request(
            security.Request(security.OFFICIAL_URL), None, 302, "redirect", {}, "http://127.0.0.1/private"
        )


def test_fetch_absolute_deadline_stops_a_dripping_response_and_preserves_partial_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Response:
        status = 200

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *_args: Any) -> None:
            pass

        def geturl(self) -> str:
            return security.OFFICIAL_URL

        def read(self, _maximum: int) -> bytes:
            time.sleep(0.03)
            return b"partial-official-body\n"

    monkeypatch.setattr(security, "_open_official", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(security, "FETCH_WALL_SECONDS", 0.2)
    destination = tmp_path / "partial.yml"
    started = time.monotonic()
    with pytest.raises(security.CheckFailure, match="absolute wall deadline"):
        security._fetch_body(destination)
    assert time.monotonic() - started < 2
    assert destination.read_bytes().startswith(b"partial-official-body\n")


@pytest.mark.parametrize("stream_name", ["stdout", "stderr"])
def test_output_limit_bounds_actual_producers_before_report_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stream_name: str
) -> None:
    monkeypatch.setattr(security, "MAX_REPORT_BYTES", 1024)
    output_path, error_path = tmp_path / "scanner.json", tmp_path / "scanner.stderr"
    # An inert writer is executed only to exercise the OS producer limit; the
    # source inspected by Semgrep is never executed by this test.
    writer = "import sys\ns=sys." + stream_name + ".buffer\nwhile True:s.write(b'x'*65536);s.flush()\n"
    with output_path.open("wb") as output, error_path.open("wb") as errors:
        code, expired = security._execute([sys.executable, "-I", "-c", writer], tmp_path, {}, output, errors, 5)
    assert not expired and code != 0
    assert max(output_path.stat().st_size, error_path.stat().st_size) == 1025
    assert all(path.stat().st_size <= 1025 for path in (output_path, error_path))
    with pytest.raises(ValueError):
        security.validate_report(output_path.read_bytes(), code)


@pytest.mark.parametrize("changed", ["source", "captured-policy", "empty-coverage"])
def test_official_protocol_cannot_qualify_drift_or_zero_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    root = tmp_path.resolve()
    target = root / "selected.py"
    target.write_text("x = 1\n")
    shutil.copyfile(ROOT / "semgrep.yml", root / "semgrep.yml")
    monkeypatch.setattr(security.metadata, "version", lambda _name: "1.99.0")
    monkeypatch.setattr(security, "official_targets", lambda _root, names: names)
    monkeypatch.setattr(security.subprocess, "check_output", lambda *_a, **_k: "a" * 40)
    raw = b"rules: []\n"

    def captured(path: Path) -> dict[str, Any]:
        path.write_bytes(raw)
        return {"source_url": security.OFFICIAL_URL, "sha256": security.hashlib.sha256(raw).hexdigest(), "rule_ids": []}

    monkeypatch.setattr(security, "fetch_official_policy", captured)

    class Process:
        pid = 0

        def __init__(self, command: list[str], **kwargs: Any) -> None:
            value = report()
            value["paths"]["scanned"] = [] if changed == "empty-coverage" else ["selected.py"]
            kwargs["stdout"].write(json.dumps(value).encode())
            if changed == "source":
                target.write_text("x = 2\n")
            elif changed == "captured-policy":
                Path(command[5]).write_text("rules: changed\n")

        def wait(self, timeout: int) -> int:
            return 0

    monkeypatch.setattr(security.subprocess, "Popen", Process)
    result = security.check_official(root, ("selected.py",))
    assert result["passed"] is False
    directory = root / result["artifact_directory"]
    assert (directory / "scanner.json").is_file() and (directory / "summary.json").is_file()
