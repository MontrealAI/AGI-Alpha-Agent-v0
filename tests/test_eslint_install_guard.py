# SPDX-License-Identifier: Apache-2.0
"""Keep the ESLint dependency stamp safe across concurrent pre-commit batches."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_eslint.sh"
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.skipif(os.name == "nt" or not shutil.which("bash"), reason="POSIX shell hook"),
]


@pytest.fixture
def hook(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """Use an isolated repository and a recording linter, without npm or network."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    script = tmp_path / "run_eslint.sh"
    shutil.copyfile(SCRIPT, script)
    (tmp_path / ".nvmrc").write_text("22.17.1\n")
    browser = tmp_path / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
    binaries = browser / "node_modules/.bin"
    binaries.mkdir(parents=True)
    (browser / "package-lock.json").write_text('{"lockfileVersion":3}\n')
    (browser / "example.js").write_text("export const answer = 42;\n")
    node = binaries / "node"
    node.write_text("#!/bin/bash\nprintf 'v22.17.1\\n'\n")
    linter = binaries / "eslint"
    linter.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$ESLINT_LOG"\n')
    node.chmod(0o755)
    linter.chmod(0o755)
    env = os.environ.copy()
    env.pop("BASH_ENV", None)
    env["PATH"] = str(binaries) + os.pathsep + env["PATH"]
    env["ESLINT_LOG"] = str(tmp_path / "eslint.log")
    return script, browser, env


def invoke(hook: tuple[Path, Path, dict[str, str]]) -> subprocess.CompletedProcess[str]:
    script, browser, env = hook
    return subprocess.run(
        ["bash", str(script), str((browser / "example.js").relative_to(script.parent))],
        cwd=script.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_existing_stale_installation_remains_blocked(hook: tuple[Path, Path, dict[str, str]]) -> None:
    script, browser, env = hook
    stamp = browser / "node_modules/.package_lock_checksum"
    stamp.write_text("outdated\n")
    result = invoke(hook)
    assert result.returncode != 0 and "out of date" in result.stderr
    assert stamp.read_text() == "outdated\n"
    assert not Path(env["ESLINT_LOG"]).exists()


def test_parallel_first_use_never_exposes_partial_stamp(hook: tuple[Path, Path, dict[str, str]]) -> None:
    script, browser, env = hook
    opened = script.parent / "writer-opened"
    release = script.parent / "release-writer"
    startup = script.parent / "pause-echo.sh"
    # Redirection happens before this function runs. Pause the first write after
    # opening its destination so another lint batch deterministically overlaps.
    startup.write_text(
        "echo() {\n"
        "  if [[ ${STAMP_RACE_WRITER-} == 1 && ${1-} =~ ^[0-9a-f]{64}$ ]]; then\n"
        '    builtin printf ready > "$STAMP_OPENED"\n'
        '    while [[ ! -f "$STAMP_RELEASE" ]]; do sleep 0.01; done\n'
        "  fi\n"
        '  builtin echo "$@"\n'
        "}\n"
    )
    env["BASH_ENV"] = str(startup)
    writer_env = {**env, "STAMP_RACE_WRITER": "1", "STAMP_OPENED": str(opened), "STAMP_RELEASE": str(release)}
    writer = subprocess.Popen(
        ["bash", str(script), str((browser / "example.js").relative_to(script.parent))],
        cwd=script.parent,
        env=writer_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 5
        while not opened.exists():
            assert writer.poll() is None, "Writer exited before the overlap"
            assert time.monotonic() < deadline, "Writer did not reach the overlap"
            time.sleep(0.01)
        follower = invoke(hook)
        assert follower.returncode == 0, follower.stderr
    finally:
        release.touch()
        try:
            stdout, stderr = writer.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            writer.kill()
            writer.communicate()
            raise
    assert writer.returncode == 0, stdout + stderr
    expected = hashlib.sha256((browser / "package-lock.json").read_bytes()).hexdigest() + "\n"
    assert (browser / "node_modules/.package_lock_checksum").read_text() == expected
    assert len(Path(env["ESLINT_LOG"]).read_text().splitlines()) == 2
    assert not list((browser / "node_modules").glob(".package_lock_checksum.*"))
