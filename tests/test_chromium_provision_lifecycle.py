# SPDX-License-Identifier: Apache-2.0
"""Exercise actual installer shell control flow without provisioning software."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def installer_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    return [(name, step) for name, job in workflow["jobs"].items()
            for step in job.get("steps", [])
            if step.get("name") == "Install Chromium with bounded official retries"]


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("statuses,expected,calls", [
    ("0", 0, 1), ("124,0", 124, 1), ("137,0", 137, 1),
    ("1,0", 0, 2), ("1,1", 1, 2), ("1,124", 124, 2), ("1,137", 137, 2),
])
def test_actual_provision_steps_never_retry_after_timeout(tmp_path, index, statuses, expected, calls):
    steps = installer_steps()
    assert len(steps) == 2
    _, step = steps[index]
    assert step["timeout-minutes"] == 12
    script = step["run"]
    assert "timeout --kill-after=30s 5m python -m playwright install --with-deps chromium" in script
    binary = tmp_path / "bin"
    binary.mkdir()
    timeout = binary / "timeout"
    timeout.write_text('''#!/bin/bash
set -eu
[[ "$1" == "--kill-after=30s" && "$2" == "5m" ]]
count=0
if [[ -f "$CALLS" ]]; then count=$(cat "$CALLS"); fi
IFS=, read -ra statuses <<< "$STATUSES"
echo "$((count + 1))" > "$CALLS"
exit "${statuses[$count]}"
''')
    timeout.chmod(0o755)
    sleep = binary / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    callfile = tmp_path / "calls"
    result = subprocess.run(["bash", "-eu", "-o", "pipefail", "-c", script],
                            env={**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                                 "CALLS": str(callfile), "STATUSES": statuses},
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == expected, result.stdout + result.stderr
    assert int(callfile.read_text()) == calls
    if expected in {124, 137}:
        assert "refusing a same-host retry" in result.stdout
