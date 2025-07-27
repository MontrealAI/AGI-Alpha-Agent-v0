# SPDX-License-Identifier: Apache-2.0
"""CLI integration test for patcher_core."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.skip(
    "patcher_core CLI test disabled in constrained environment",
    allow_module_level=True,
)


pytestmark = [
    pytest.mark.skipif(shutil.which("patch") is None, reason="patch not installed"),
]

pytest.importorskip("openai_agents", minversion="0.0.17")


def test_patcher_core_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    tests_dir = repo / "tests"
    tests_dir.mkdir(parents=True)

    # buggy source file
    (repo / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    # failing test
    (tests_dir / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )

    # patch to fix the bug
    patch_file = tmp_path / "fix.diff"
    patch_file.write_text(
        r"""--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
def add(a, b):
-    return a - b
+    return a + b
\ No newline at end of file
""",
        encoding="utf-8",
    )

    openai_agents = pytest.importorskip("openai_agents")

    class StubAgent:
        def __init__(self, *a: object, **k: object) -> None:
            self.patch_file = os.environ.get("PATCH_FILE")

        def __call__(self, _prompt: str) -> str:
            return Path(self.patch_file).read_text() if self.patch_file else ""

    monkeypatch.setattr(openai_agents, "OpenAIAgent", StubAgent)

    env = os.environ.copy()
    env["PATCH_FILE"] = str(patch_file)
    root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = os.pathsep.join([str(root), str(root / "stubs"), env.get("PYTHONPATH", "")])
    env.setdefault("OPENAI_API_KEY", "dummy")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.self_healing_repo.patcher_core",
            "--repo",
            str(repo),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert "Patch fixed the tests" in combined
