# SPDX-License-Identifier: Apache-2.0
"""Dependency provisioning is bounded; genuine release acceptance stays blocking."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def named(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)


@pytest.mark.parametrize("job_name", ["regression", "gallery"])
def test_official_browser_install_has_independent_attempt_and_step_budgets(job_name):
    job = workflow("agent-release.yml")["jobs"][job_name]
    step = named(job, "Install Chromium with bounded official retries")
    assert step["timeout-minutes"] == 12
    assert step["env"]["PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT"] == "60000"
    script = step["run"]
    assert "for attempt in 1 2" in script
    assert "timeout --kill-after=30s 5m python -m playwright install --with-deps chromium" in script
    assert 'exit "$status"' in script
    assert "continue-on-error" not in step
    assert "|| true" not in script
    assert "pytest" not in script and "validate_" not in script


@pytest.mark.parametrize(
    "codes,expected,count",
    [
        ("0", 0, 1),
        ("124,0", 0, 2),
        ("1,0", 0, 2),
        ("1,1", 1, 2),
        ("124,124", 124, 2),
        ("137,137", 137, 2),
        ("42,43", 43, 2),
    ],
)
def test_actual_retry_shell_stops_at_two_and_preserves_final_failure(tmp_path, codes, expected, count):
    script = named(
        workflow("agent-release.yml")["jobs"]["regression"], "Install Chromium with bounded official retries"
    )["run"]
    binary = tmp_path / "bin"
    binary.mkdir()
    timeout = binary / "timeout"
    timeout.write_text(
        """#!/bin/bash
[[ "$*" == '--kill-after=30s 5m python -m playwright install --with-deps chromium' ]] || exit 99
n=0; [[ ! -f "$COUNTER" ]] || read -r n < "$COUNTER"
echo "$((n+1))" > "$COUNTER"
IFS=, read -ra codes <<< "$CODES"
exit "${codes[$n]:-98}"
"""
    )
    timeout.chmod(0o755)
    sleep = binary / "sleep"
    sleep.write_text("#!/bin/bash\nexit 0\n")
    sleep.chmod(0o755)
    counter = tmp_path / "count"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", script],
        capture_output=True,
        env={**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "COUNTER": str(counter), "CODES": codes},
    )
    assert result.returncode == expected, result.stderr
    assert int(counter.read_text()) == count


def test_real_timeout_terminates_each_hung_attempt_and_fails(tmp_path):
    if not shutil.which("timeout"):
        pytest.skip("GNU timeout is an Ubuntu runner utility")
    script = named(workflow("agent-release.yml")["jobs"]["gallery"], "Install Chromium with bounded official retries")[
        "run"
    ]
    script = script.replace("--kill-after=30s 5m", "--kill-after=0.05s 0.05s").replace("sleep 5", "true")
    binary = tmp_path / "bin"
    binary.mkdir()
    python = binary / "python"
    python.write_text('#!/bin/bash\necho attempt >> "$COUNTER"\nsleep 5\n')
    python.chmod(0o755)
    counter = tmp_path / "count"
    result = subprocess.run(
        ["bash", "-eu", "-o", "pipefail", "-c", script],
        timeout=5,
        capture_output=True,
        env={**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "COUNTER": str(counter)},
    )
    assert result.returncode == 124
    assert counter.read_text().splitlines() == ["attempt", "attempt"]


@pytest.mark.parametrize("job_name", ["regression", "gallery"])
def test_dependency_caches_bind_runtime_workflow_and_locks_not_results(job_name):
    job = workflow("agent-release.yml")["jobs"][job_name]
    steps = job["steps"]
    for action, manager in [("actions/setup-python@", "pip"), ("actions/setup-node@", "npm")]:
        step = next(s for s in steps if s.get("uses", "").startswith(action))
        assert steps.index(step) < steps.index(named(job, "Install Chromium with bounded official retries"))
        config = step["with"]
        assert config["cache"] == manager
        paths = config["cache-dependency-path"].splitlines()
        # Official actions key by runner OS; workflow bytes additionally bind the
        # selected runtime and installer pins without caching environments/results.
        assert ".github/workflows/agent-release.yml" in paths
        if manager == "pip":
            assert {"requirements.lock", "requirements-dev.lock"} <= set(paths)
            assert config["python-version"] == "3.12"
            if job_name == "gallery":
                assert "requirements-docs.lock" in paths
        else:
            assert "tests/browser/package-lock.json" in paths
            assert config["node-version"] == "22.17.1"
        assert not any("node_modules" in p or "evidence" in p for p in paths)


@pytest.mark.parametrize("job_name", ["tests", "docs-check", "docs-build"])
def test_disk_cleanup_precedes_restore_without_removing_later_disk_relief(job_name):
    job = workflow("ci.yml")["jobs"][job_name]
    steps = job["steps"]
    cleanup = steps.index(named(job, "Free disk space"))
    ensure = steps.index(named(job, "Ensure pip cache directory"))
    restore = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/setup-python@"))
    assert cleanup < ensure < restore
    assert named(job, "Free disk space")["run"] == "bash scripts/ci_free_disk.sh"
    if job_name == "tests":
        purge = named(job, "Clean caches before pytest")
        assert "python -m pip cache purge" in purge["run"]
        assert steps.index(purge) > steps.index(named(job, "Install dependencies"))


def test_acceptance_commands_remain_separate_required_and_unchanged():
    jobs = workflow("agent-release.yml")["jobs"]
    regression = jobs["regression"]
    gallery = jobs["gallery"]
    assert regression["timeout-minutes"] == 90
    assert gallery["timeout-minutes"] == 35
    assert gallery["strategy"]["matrix"]["assets"] == ["minimal", "full"]
    for job, name in [
        (regression, "Original locked development environment"),
        (gallery, "Install the historical documentation environment"),
    ]:
        install = named(job, name)
        assert install["timeout-minutes"] == 15
        assert install["env"] == {"PIP_DEFAULT_TIMEOUT": "60", "PIP_RETRIES": "2"}
        assert "python -m pip check" in install["run"]
        assert "playwright install" not in install["run"]
    install = named(regression, "Original locked development environment")
    assert "python -m pip install --require-hashes -r requirements.lock -r requirements-dev.lock" in install["run"]
    for job, name in [
        (regression, "Full offline regression including notebooks"),
        (regression, "Strict types and repository checks"),
        (gallery, "Verify independent browser algorithm contracts"),
    ]:
        step = named(job, name)
        assert not step.get("continue-on-error", False)
        assert "if" not in step
        assert "npm ci" not in step["run"] and "pip install" not in step["run"]
    full = named(regression, "Full offline regression including notebooks")["run"]
    assert "--cov-fail-under=80" in full and "--junitxml=evidence/regression.xml" in full
    assert (
        "node --test tests/browser/portal_engine.test.mjs"
        in named(gallery, "Verify independent browser algorithm contracts")["run"]
    )
