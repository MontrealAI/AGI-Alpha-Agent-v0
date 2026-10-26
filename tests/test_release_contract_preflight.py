# SPDX-License-Identifier: Apache-2.0
"""Cheap release contracts fail early without replacing full acceptance."""
import hashlib
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = "Release contract preflight before full regression"
FULL = "Offline regression including notebooks (four held native tests excluded)"
ORIGINAL_FULL_RUN_SHA256 = "6ba1fa02fcd483b1ae934ed2e398da8986c0111fcf21308ce7be12061102ab02"
CONTRACTS = {
    "tests/test_ci_install_bounds.py",
    "tests/test_chromium_provision_lifecycle.py",
    "tests/test_capability_checkout_release_versions.py",
    "tests/test_capability_publication_edition.py",
    "tests/test_release_contract_preflight.py",
}


def steps():
    job = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())["jobs"]["regression"]
    return job["steps"]


def test_preflight_is_bounded_blocking_and_full_regression_is_unchanged():
    sequence = steps()
    early = next(step for step in sequence if step.get("name") == PREFLIGHT)
    full = next(step for step in sequence if step.get("name") == FULL)
    assert sequence.index(early) + 1 == sequence.index(full)
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
    assert set(early["run"].split()[7:]) == CONTRACTS
    assert hashlib.sha256(full["run"].encode()).hexdigest() == ORIGINAL_FULL_RUN_SHA256


@pytest.mark.parametrize("exit_code", [0, 1, 124, 137])
def test_failed_preflight_never_runs_full_suite_or_returns_success(tmp_path, exit_code):
    sequence = steps()
    early = next(step["run"] for step in sequence if step.get("name") == PREFLIGHT)
    full = next(step["run"] for step in sequence if step.get("name") == FULL)
    binary = tmp_path / "bin"
    binary.mkdir()
    python = binary / "python"
    python.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALLS"\n'
        'if [[ "$1" == "-m" && "$2" == "pytest" ]]; then exit "$PREFLIGHT_EXIT"; fi\n'
        'if [[ "$1" == "-m" && "$2" == "scripts.run_local_tests" ]]; then touch .coverage; fi\n'
        "exit 0\n"
    )
    python.chmod(0o755)
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", early + "\n" + full],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{binary}:{os.environ['PATH']}",
            "CALLS": str(calls),
            "PREFLIGHT_EXIT": str(exit_code),
        },
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == exit_code, result.stderr
    observed = calls.read_text().splitlines()
    if exit_code:
        assert len(observed) == 1
        assert not (tmp_path / "evidence").exists()
    else:
        assert len(observed) == 3
        assert observed[1] == "-"
        assert observed[2].startswith("-m scripts.run_local_tests -q --cov ")
        assert "--cov-fail-under=80" in observed[2]
        assert observed[2].count("--deselect=") == 4
        assert (tmp_path / "evidence/coverage.data").exists()
