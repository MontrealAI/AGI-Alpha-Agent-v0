# SPDX-License-Identifier: Apache-2.0
"""Verify preservation enforcement against an actual immutable Git baseline."""

import subprocess
from pathlib import Path

import pytest

from scripts.check_successor_preservation import check


@pytest.fixture
def baseline(tmp_path: Path) -> tuple[Path, str]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "guide.md").write_text("Original\n```mermaid\ngraph TD\nA-->B\n```\n")
    (tmp_path / "figure.png").write_bytes(b"original media")
    (tmp_path / "implementation.py").write_text("version = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "Baseline"],
        cwd=tmp_path,
        check=True,
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    return tmp_path, commit


def test_inventory_records_implementation_changes_without_erasing_history(baseline) -> None:
    root, commit = baseline
    (root / "implementation.py").write_text("version = 2\n")
    report = check(root, commit)
    assert report["files_preserved"] == 3
    assert report["changed_files"] == 1
    assert report["media_bytes_preserved"] == report["mermaid_blocks_preserved"] == 1
    assert len(report["inventory"]) == 3


@pytest.mark.parametrize("damage", ["missing", "media", "diagram", "link"])
def test_preservation_rejects_deleted_paths_media_or_diagrams(baseline, damage: str) -> None:
    root, commit = baseline
    if damage == "missing":
        (root / "implementation.py").unlink()
    elif damage == "media":
        (root / "figure.png").write_bytes(b"different")
    elif damage == "diagram":
        (root / "guide.md").write_text("Original text without diagram")
    else:
        (root / "implementation.py").unlink()
        (root / "implementation.py").symlink_to("guide.md")
    with pytest.raises(ValueError):
        check(root, commit)
