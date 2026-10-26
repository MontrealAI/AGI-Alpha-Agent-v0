# SPDX-License-Identifier: Apache-2.0
"""Tests for dp_scrubber hook."""
import json
from pathlib import Path
import subprocess

import pytest

from scripts import dp_scrubber


def test_blocks_paywalled_excerpt(tmp_path: Path) -> None:
    text = ("paywalled " * 65).strip()
    f = tmp_path / "secret.txt"
    f.write_text(text)

    assert dp_scrubber.scan_file(Path(f)) is True


def _git(root: Path, *arguments: str) -> str:
    """Run fixture-only Git commands without configuring a global identity."""
    result = subprocess.run(
        ["git", "-c", "user.name=DP fixture", "-c", "user.email=fixture@example.invalid", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Create an isolated accepted baseline for release-delta checks."""
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "--quiet")
    (root / "notes.txt").write_text("Public baseline notes.\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    _git(root, "commit", "--quiet", "-m", "Accepted fixture baseline")
    base = _git(root, "rev-parse", "HEAD")
    monkeypatch.chdir(root)
    monkeypatch.delenv("ALLOW_PRIVATE_TEXT", raising=False)
    return root, base


def _report(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    value = json.loads(capsys.readouterr().out)
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize(("text", "exit_code"), [("paywalled excerpt\n", 1), ("Public release notes.\n", 0)])
def test_clean_checkout_release_delta_is_scanned(
    repository: tuple[Path, str], capsys: pytest.CaptureFixture[str], text: str, exit_code: int
) -> None:
    """A clean CI index must not hide already committed release additions."""
    root, base = repository
    (root / "notes.txt").write_text(text, encoding="utf-8")
    _git(root, "add", "notes.txt")
    _git(root, "commit", "--quiet", "-m", "Release fixture")
    assert _git(root, "status", "--porcelain") == ""
    assert dp_scrubber.main([]) == 0
    capsys.readouterr()

    assert dp_scrubber.main(["--base", base]) == exit_code
    report = _report(capsys)
    assert report["head"] == _git(root, "rev-parse", "HEAD")
    assert report["worktree_and_index_match_head"] is True
    assert report["scanned_text_files"] == 1
    assert report["flagged_files"] == exit_code
    assert report["flagged_paths"] == (["notes.txt"] if exit_code else [])


def test_base_refuses_tracked_unstaged_text(repository: tuple[Path, str], capsys: pytest.CaptureFixture[str]) -> None:
    root, base = repository
    (root / "notes.txt").write_text("paywalled fixture\n", encoding="utf-8")
    (root / "untracked.txt").write_text("paywalled untracked fixture\n", encoding="utf-8")
    assert dp_scrubber.main([]) == 0
    assert dp_scrubber.main(["--base", base]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "must match committed HEAD" in output.err


def test_staged_default_still_classifies_current_staged_paths(
    repository: tuple[Path, str], capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = repository
    (root / "notes.txt").write_text("paywalled fixture\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    assert dp_scrubber.main([]) == 1
    assert "notes.txt" in capsys.readouterr().err
    (root / "notes.txt").write_text("Public fixture notes.\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    assert dp_scrubber.main([]) == 0


def test_only_additions_are_classified_and_deletions_binaries_are_counted(
    repository: tuple[Path, str], capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = repository
    (root / "old.txt").write_text("paywalled existing fixture\n", encoding="utf-8")
    (root / "remove.txt").write_text("paywalled removed fixture\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "Expanded accepted fixture")
    base = _git(root, "rev-parse", "HEAD")
    (root / "old.txt").write_text("paywalled existing fixture\nPublic new paragraph.\n", encoding="utf-8")
    (root / "remove.txt").unlink()
    (root / "binary.dat").write_bytes(b"\x00paywalled fixture\xff")
    (root / "empty.txt").write_bytes(b"")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "Release additions, deletion and binary fixture")
    assert dp_scrubber.main(["--base", base]) == 0
    report = _report(capsys)
    assert report["changed_paths"] == 4
    assert report["scanned_text_files"] == 1
    assert report["flagged_files"] == 0
    assert report["binary_files_not_scanned"] == 1
    assert report["deleted_files_not_scanned"] == 1
    assert report["text_files_without_additions"] == 1


def test_literal_names_and_subdirectory_invocation(
    repository: tuple[Path, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, base = repository
    name = "notes [literal]\twith\nlines.txt"
    (root / name).write_text("paywalled fixture\n", encoding="utf-8")
    _git(root, "add", "--", name)
    _git(root, "commit", "--quiet", "-m", "Literal path fixture")
    subdirectory = root / "subdirectory"
    subdirectory.mkdir()
    monkeypatch.chdir(subdirectory)
    assert dp_scrubber.main(["--base", base]) == 1
    assert _report(capsys)["flagged_paths"] == [name]


@pytest.mark.parametrize("base", ["HEAD", "a" * 39, "g" * 40, "0" * 40])
def test_bad_or_missing_exact_base_fails_closed(
    repository: tuple[Path, str], capsys: pytest.CaptureFixture[str], base: str
) -> None:
    assert dp_scrubber.main(["--base", base]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "scan failed" in output.err


def test_git_error_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ALLOW_PRIVATE_TEXT", raising=False)
    assert dp_scrubber.main(["--base", "a" * 40]) == 2


def test_nonancestor_base_fails_closed(repository: tuple[Path, str]) -> None:
    root, original = repository
    _git(root, "checkout", "--quiet", "--orphan", "other-history")
    _git(root, "commit", "--quiet", "-m", "Unrelated fixture")
    unrelated = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--quiet", original)
    assert dp_scrubber.main(["--base", unrelated]) == 2


def test_symlink_delta_is_refused_without_classification(repository: tuple[Path, str]) -> None:
    root, base = repository
    (root / "outside.txt").write_text("paywalled fixture\n", encoding="utf-8")
    (root / "notes.txt").unlink()
    (root / "notes.txt").symlink_to(root / "outside.txt")
    _git(root, "add", "notes.txt")
    _git(root, "commit", "--quiet", "-m", "Symlink fixture")
    assert dp_scrubber.main(["--base", base]) == 2


@pytest.mark.parametrize("name", [b"../outside", b"/absolute", b"C:/outside", b"parent\\outside"])
def test_escaping_inventory_paths_are_refused(tmp_path: Path, name: bytes) -> None:
    with pytest.raises(RuntimeError, match="Unsafe tracked path"):
        dp_scrubber._safe_path(tmp_path, name, deleted=True)


def test_non_utf8_text_fails_closed(repository: tuple[Path, str]) -> None:
    root, base = repository
    (root / "notes.txt").write_bytes(b"paywalled fixture\xff\n")
    _git(root, "add", "notes.txt")
    _git(root, "commit", "--quiet", "-m", "Non-UTF-8 fixture")
    assert dp_scrubber.main(["--base", base]) == 2


def test_override_cannot_bypass_explicit_delta(
    repository: tuple[Path, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, base = repository
    monkeypatch.setenv("ALLOW_PRIVATE_TEXT", "1")
    assert dp_scrubber.main(["--base", base]) == 2
    assert "cannot override" in capsys.readouterr().err


def test_external_diff_and_text_conversion_are_not_executed(repository: tuple[Path, str]) -> None:
    root, base = repository
    marker = root / "helper-was-run"
    helper = root / "external-helper.sh"
    helper.write_text(f"#!/bin/sh\nprintf ran > '{marker}'\n", encoding="utf-8")
    helper.chmod(0o755)
    _git(root, "config", "diff.external", str(helper))
    _git(root, "config", "diff.fixture.textconv", str(helper))
    (root / ".gitattributes").write_text("notes.txt diff=fixture\n", encoding="utf-8")
    _git(root, "add", ".gitattributes")
    (root / "notes.txt").write_text("paywalled fixture\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    _git(root, "commit", "--quiet", "-m", "External helper refusal fixture")
    assert dp_scrubber.main(["--base", base]) == 1
    assert not marker.exists()


@pytest.mark.parametrize("stage_overlay", [False, True])
def test_bad_committed_head_cannot_be_masked_by_safe_overlay(
    repository: tuple[Path, str], capsys: pytest.CaptureFixture[str], stage_overlay: bool
) -> None:
    root, base = repository
    (root / "notes.txt").write_text("paywalled committed fixture\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    _git(root, "commit", "--quiet", "-m", "Positive committed fixture")
    (root / "notes.txt").write_text("Public overlay notes.\n", encoding="utf-8")
    if stage_overlay:
        _git(root, "add", "notes.txt")
    assert dp_scrubber.main(["--base", base]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "must match committed HEAD" in output.err


def test_index_mismatch_cannot_be_hidden_by_head_matching_worktree(repository: tuple[Path, str]) -> None:
    root, base = repository
    (root / "notes.txt").write_text("paywalled index fixture\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    (root / "notes.txt").write_text("Public baseline notes.\n", encoding="utf-8")
    assert _git(root, "diff", "HEAD", "--", "notes.txt") == ""
    assert dp_scrubber.main(["--base", base]) == 2


def test_assume_unchanged_cannot_hide_tracked_overlay(repository: tuple[Path, str]) -> None:
    root, base = repository
    _git(root, "update-index", "--assume-unchanged", "notes.txt")
    (root / "notes.txt").write_text("paywalled overlay fixture\n", encoding="utf-8")
    assert dp_scrubber.main(["--base", base]) == 2


@pytest.mark.parametrize("variant", ["exact", "changed", "copy", "executable"])
def test_reviewed_fixture_admission_is_bound_to_exact_body_path_and_mode(
    repository: tuple[Path, str], capsys: pytest.CaptureFixture[str], variant: str
) -> None:
    root, base = repository
    path = "other-fixture.py" if variant == "copy" else "tests/test_dp_scrubber.py"
    fixture = root / path
    fixture.parent.mkdir(parents=True, exist_ok=True)
    body = Path(__file__).read_bytes()
    fixture.write_bytes(body + (b"\n# Changed synthetic fixture.\n" if variant == "changed" else b""))
    if variant == "executable":
        fixture.chmod(0o755)
    _git(root, "add", "--", path)
    _git(root, "commit", "--quiet", "-m", "Synthetic classifier fixture admission case")
    assert dp_scrubber.main(["--base", base]) == (0 if variant == "exact" else 1)
    report = _report(capsys)
    assert report["flagged_files"] == 1
    assert report["flagged_paths"] == [path]
    assert report["reviewed_synthetic_fixture_files"] == (1 if variant == "exact" else 0)
    assert report["unadmitted_positive_files"] == (0 if variant == "exact" else 1)


def test_reviewed_release_fixture_remains_positive_in_staged_default(repository: tuple[Path, str]) -> None:
    root, _ = repository
    fixture = root / "tests/test_dp_scrubber.py"
    fixture.parent.mkdir()
    fixture.write_bytes(Path(__file__).read_bytes())
    _git(root, "add", "tests/test_dp_scrubber.py")
    assert dp_scrubber.main([]) == 1
