# SPDX-License-Identifier: Apache-2.0
"""Extra tests for the self-healing patcher utilities."""

from pathlib import Path
from unittest import mock
import pytest
import shutil

from alpha_factory_v1.demos.self_healing_repo import patcher_core


_DEF_DIFF = """--- a/hello.txt
+++ b/hello.txt
@@\n-hello\n+hi\n"""


def test_apply_patch_invalid_diff(tmp_path: Path, monkeypatch: mock.MagicMock) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("hello\n", encoding="utf-8")

    def fake_run(cmd, cwd):
        return 1, "patch failed"

    monkeypatch.setattr(patcher_core, "_run", fake_run)
    with pytest.raises(ValueError, match="unified diff"):
        patcher_core.apply_patch("bad diff", repo_path=str(tmp_path))
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_apply_patch_missing_patch_binary(tmp_path: Path, monkeypatch: mock.MagicMock) -> None:
    (tmp_path / "hello.txt").write_text("hello\n", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError) as exc:
        patcher_core.apply_patch(_DEF_DIFF, repo_path=str(tmp_path))
    assert "patch` command not found" in str(exc.value)


def test_apply_patch_rollback_on_failure(tmp_path: Path, monkeypatch: mock.MagicMock) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("hello\n", encoding="utf-8")

    def fake_run(cmd, cwd):
        return 1, "patch failed"

    monkeypatch.setattr(patcher_core, "_run", fake_run)
    with pytest.raises(RuntimeError):
        patcher_core.apply_patch(_DEF_DIFF, repo_path=str(tmp_path))

    assert target.read_text(encoding="utf-8") == "hello\n"
    assert not (tmp_path / "hello.txt.bak").exists()


@pytest.mark.parametrize("fail", [False, True])
def test_real_patch_preserves_user_backups_and_rolls_back_same_stem_files(tmp_path: Path, fail: bool) -> None:
    originals = {"hello.txt": "hello\n", "hello.py": "original\n"}
    artifacts = {"hello.bak": "user backup\n", "hello.py.orig": "user original\n", "hello.py.rej": "user rejects\n"}
    for name, content in {**originals, **artifacts}.items():
        (tmp_path / name).write_text(content)
    second_before = "missing" if fail else "original"
    diff = _DEF_DIFF + f"--- a/hello.py\n+++ b/hello.py\n@@ -1 +1 @@\n-{second_before}\n+updated\n"
    if fail:
        with pytest.raises(RuntimeError, match="patch command failed"):
            patcher_core.apply_patch(diff, str(tmp_path))
        expected = originals
    else:
        patcher_core.apply_patch(diff, str(tmp_path))
        expected = {"hello.txt": "hi\n", "hello.py": "updated\n"}
    assert {p.name: p.read_text() for p in tmp_path.iterdir()} == {**expected, **artifacts}
