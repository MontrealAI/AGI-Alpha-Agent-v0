# SPDX-License-Identifier: Apache-2.0
"""Cheap release contracts fail early without replacing full acceptance."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = "Release contract preflight before full regression"
GUARD = "Preserve held native source identities (no behavioral qualification)"
FULL = "Offline regression including notebooks (four held native tests excluded)"
ORIGINAL_FULL_RUN_SHA256 = "6ba1fa02fcd483b1ae934ed2e398da8986c0111fcf21308ce7be12061102ab02"
CONTRACTS = {
    "tests/test_ci_install_bounds.py",
    "tests/test_chromium_provision_lifecycle.py",
    "tests/test_capability_checkout_release_versions.py",
    "tests/test_capability_publication_edition.py",
    "tests/test_release_contract_preflight.py",
    "tests/test_held_native_source_guard.py",
    "tests/test_workbox_integrity_contract.py",
    "tests/test_release_artifact_handoffs.py",
}


def steps():
    job = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())["jobs"]["regression"]
    return job["steps"]


def test_preflight_is_bounded_blocking_and_full_regression_is_unchanged():
    sequence = steps()
    early = next(step for step in sequence if step.get("name") == PREFLIGHT)
    full = next(step for step in sequence if step.get("name") == FULL)
    guard = next(step for step in sequence if step.get("name") == GUARD)
    assert sequence.index(early) + 1 == sequence.index(guard)
    assert sequence.index(guard) + 1 == sequence.index(full)
    assert guard == {
        "name": GUARD,
        "run": "mkdir -p evidence\npython scripts/check_held_native_source.py > "
        "evidence/held-native-source-preservation.json\n",
    }
    assert early["timeout-minutes"] == 5
    assert set(early) == {"name", "timeout-minutes", "run"}
    assert not full.get("continue-on-error") and "if" not in full
    assert early["run"].split()[:8] == [
        "python",
        "-m",
        "pytest",
        "--noconftest",
        "-o",
        "addopts=",
        "-q",
        "tests/test_ci_install_bounds.py",
    ]
    assert set(early["run"].splitlines()[0].split()[7:]) == CONTRACTS
    assert (
        "ALPHA_PYTEST_OWNER_PID=$$ python -m scripts.run_local_tests -o addopts= "
        "tests/test_workbox_integrity.py -q --junitxml=evidence/workbox-preflight.xml"
    ) in early["run"]
    assert "ET.parse('evidence/workbox-preflight.xml')" in early["run"]
    assert hashlib.sha256(full["run"].encode()).hexdigest() == ORIGINAL_FULL_RUN_SHA256


@pytest.mark.parametrize(
    "exit_code,workbox_exit,report_exit,guard_exit",
    [
        (0, 0, 0, 0),
        (1, 0, 0, 0),
        (124, 0, 0, 0),
        (137, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 124, 0, 0),
        (0, 137, 0, 0),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
    ],
)
def test_failed_preflight_or_identity_guard_never_runs_full_suite(
    tmp_path, exit_code, workbox_exit, report_exit, guard_exit
):
    sequence = steps()
    early = next(step["run"] for step in sequence if step.get("name") == PREFLIGHT)
    full = next(step["run"] for step in sequence if step.get("name") == FULL)
    guard = next(step["run"] for step in sequence if step.get("name") == GUARD)
    binary = tmp_path / "bin"
    binary.mkdir()
    python = binary / "python"
    python.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALLS"\n'
        'if [[ "$1" == "-m" && "$2" == "pytest" ]]; then exit "$PREFLIGHT_EXIT"; fi\n'
        'if [[ "$1" == "scripts/check_held_native_source.py" ]]; then exit "$GUARD_EXIT"; fi\n'
        'if [[ "$1" == "-m" && "$2" == "scripts.run_local_tests" ]]; then\n'
        '  if [[ "$*" == *"tests/test_workbox_integrity.py"* ]]; then exit "$WORKBOX_EXIT"; fi\n'
        "  touch .coverage\n"
        "fi\n"
        'if [[ "$1" == "-" ]]; then\n'
        "  content=$(cat)\n"
        '  if [[ "$content" == *"workbox-preflight.xml"* ]]; then exit "$REPORT_EXIT"; fi\n'
        "fi\n"
        "exit 0\n"
    )
    python.chmod(0o755)
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", early + "\n" + guard + "\n" + full],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ['PATH']}",
            "CALLS": str(calls),
            "PREFLIGHT_EXIT": str(exit_code),
            "WORKBOX_EXIT": str(workbox_exit),
            "REPORT_EXIT": str(report_exit),
            "GUARD_EXIT": str(guard_exit),
        },
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == (exit_code or workbox_exit or report_exit or guard_exit), result.stderr
    observed = calls.read_text().splitlines()
    if exit_code:
        assert len(observed) == 1
        assert not (tmp_path / "evidence").exists()
    elif workbox_exit or report_exit:
        assert len(observed) == (2 if workbox_exit else 3)
        assert not (tmp_path / ".coverage").exists()
    elif guard_exit:
        assert len(observed) == 4
        assert observed[3] == "scripts/check_held_native_source.py"
        assert not (tmp_path / ".coverage").exists()
    else:
        assert len(observed) == 6
        assert observed[3] == "scripts/check_held_native_source.py"
        assert observed[4] == "-"
        assert observed[5].startswith("-m scripts.run_local_tests -q --cov ")
        assert "--cov-fail-under=80" in observed[5]
        assert observed[5].count("--deselect=") == 4
        assert (tmp_path / "evidence/coverage.data").exists()


@pytest.mark.parametrize(
    "case_xml,accepted",
    [
        ('<testcase classname="tests.test_workbox_integrity" name="test_workbox_hash_mismatch"/>', True),
        (
            '<testcase classname="tests.test_workbox_integrity" name="test_workbox_hash_mismatch"><skipped/></testcase>',
            False,
        ),
        (
            '<testcase classname="tests.test_workbox_integrity" name="test_workbox_hash_mismatch"><failure/></testcase>',
            False,
        ),
        (
            '<testcase classname="tests.test_workbox_integrity" name="test_workbox_hash_mismatch"><error/></testcase>',
            False,
        ),
        ('<testcase classname="other" name="test_workbox_hash_mismatch"/>', False),
        ('<testcase classname="tests.test_workbox_integrity" name="other"/>', False),
        ("", False),
        ('<testcase classname="tests.test_workbox_integrity" name="test_workbox_hash_mismatch"/>' * 2, False),
    ],
)
def test_workbox_preflight_requires_the_actual_complete_unskipped_case(tmp_path, case_xml, accepted):
    early = next(step["run"] for step in steps() if step.get("name") == PREFLIGHT)
    validation = early.split("python - <<'PY'\n", 1)[1].removesuffix("PY\n")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "workbox-preflight.xml").write_text(f"<testsuites><testsuite>{case_xml}</testsuite></testsuites>")
    result = subprocess.run(
        [sys.executable, "-c", validation], cwd=tmp_path, capture_output=True, check=False, timeout=5
    )
    assert (result.returncode == 0) is accepted, result.stderr
