# SPDX-License-Identifier: Apache-2.0
"""Exact-object paper lane proofs reject mixed work and hidden unsafe history."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Any

import pytest

from scripts import paper_changes as changes
from scripts import research_papers as papers
from tests.test_research_papers import paper_row, pdf_bytes, refresh_fixture, write_paper_fixture


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "-c", "core.hooksPath=/dev/null", *args], text=True, stderr=subprocess.PIPE
    ).strip()


def save(root: Path, message: str = "Fixture commit") -> str:
    git(root, "add", "--all")
    git(root, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "core.filemode", "true")
    write_paper_fixture(root)
    for name in ("scripts/research_papers.py", "scripts/build_service_worker.py", "scripts/paper_changes.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# trusted software baseline\n")
    (root / "app.py").write_text("VALUE = 'trusted'\n")
    return root, save(root, "Trusted software base")


def append_paper(root: Path, slug: str = "new-paper") -> None:
    data = papers.load_catalog(root)
    raw = pdf_bytes()
    row = paper_row(slug, featured=False, raw=raw)
    (root / row["pdf"]["path"]).write_bytes(raw)
    tex = b"\\documentclass{article}\n% exact opaque source\n"
    tex_path = f"docs/papers/{slug}.tex"
    (root / tex_path).write_bytes(tex)
    row["tex"] = {"path": tex_path, "sha256": hashlib.sha256(tex).hexdigest()}
    data["papers"].append(row)
    refresh_fixture(root, data)


def assert_full(root: Path, base: str | None, head: str) -> dict[str, Any]:
    result = changes.classify(root, base, head)
    assert result["mode"] == "full", result
    assert result["software_commit"] == head
    assert result["paper_commit"] == head
    assert result["reason"]
    assert result["release_plan"]["tier"] == "full"
    assert result["release_plan"]["software_checks"] == "run"
    return result


def editorial_base(history: tuple[Path, str]) -> tuple[Path, str]:
    root, _ = history
    (root / "docs/CHANGELOG.md").write_text("## Existing record\n\nPreserved text.\n")
    return root, save(root, "Existing changelog baseline")


def prepend_editorial(root: Path, text: str = "## Clarification\n\n- Plain prose only.\n\n") -> None:
    path = root / "docs/CHANGELOG.md"
    path.write_bytes(text.encode() + path.read_bytes())


def test_passive_editorial_skips_software_without_publishing_a_new_identity(history: tuple[Path, str]) -> None:
    root, base = editorial_base(history)
    prepend_editorial(root)
    head = save(root)
    result = changes.classify(root, base, head)
    assert result["mode"] == "paper"
    plan = result["release_plan"]
    assert plan["tier"] == "passive-editorial"
    assert plan["source_commit"] == head and plan["base_commit"] == base
    assert plan["paper_publication"] == plan["software_publication"] == "not-applicable"
    assert plan["component_reuse"] is False


def test_papers_plus_editorial_retain_existing_paper_publication(history: tuple[Path, str]) -> None:
    root, base = editorial_base(history)
    prepend_editorial(root)
    append_paper(root)
    result = changes.classify(root, base, save(root))
    assert result["mode"] == "paper"
    assert result["release_plan"]["tier"] == "paper"
    assert result["release_plan"]["paper_publication"] == "run"


@pytest.mark.parametrize("text", ["Correction to existing wording.\n", "## Notes\n\n[Link](https://example.org/)\n"])
def test_editorial_corrections_and_markdown_are_not_arbitrarily_restricted(
    history: tuple[Path, str], text: str
) -> None:
    root, base = editorial_base(history)
    (root / "docs/CHANGELOG.md").write_text(text)
    result = changes.classify(root, base, save(root))
    assert result["mode"] == "paper"
    assert result["release_plan"]["tier"] == "passive-editorial"


@pytest.mark.parametrize("path", ["app.py", "requirements.lock", "scripts/release_plan.py", ".github/workflows/x.yml"])
def test_editorial_cannot_hide_shared_code_policy_or_dependencies(history: tuple[Path, str], path: str) -> None:
    root, base = editorial_base(history)
    prepend_editorial(root)
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n")
    assert_full(root, base, save(root))


def test_editorial_cannot_hide_reverted_unsafe_history(history: tuple[Path, str]) -> None:
    root, base = editorial_base(history)
    old = (root / "app.py").read_bytes()
    (root / "app.py").write_text("unsafe\n")
    save(root)
    (root / "app.py").write_bytes(old)
    prepend_editorial(root)
    assert_full(root, base, save(root))


@pytest.mark.parametrize("kind", ["binary", "delete", "executable", "symlink"])
def test_nonpassive_changelog_changes_require_full(history: tuple[Path, str], kind: str) -> None:
    root, base = editorial_base(history)
    path = root / "docs/CHANGELOG.md"
    if kind == "binary":
        path.write_bytes(b"\xff")
    elif kind == "delete":
        path.unlink()
    elif kind == "executable":
        prepend_editorial(root)
        path.chmod(0o755)
    else:
        path.unlink()
        path.symlink_to("../app.py")
    assert_full(root, base, save(root))


def test_only_catalog_new_paper_bytes_and_exact_generated_outputs_pass(history: tuple[Path, str]) -> None:
    root, base = history
    append_paper(root)
    head = save(root, "Add one immutable paper")
    result = changes.classify(root, base, head)
    assert result["mode"] == "paper", result
    assert result["software_commit"] == base
    assert result["paper_commit"] == head
    assert len(result["transitions"]) == 1
    assert set(result["transitions"][0]["paths"]) == {
        papers.CATALOG,
        "docs/papers/new-paper.pdf",
        "docs/papers/new-paper.tex",
        *changes.GENERATED,
    }
    assert result["catalog_sha256"] == hashlib.sha256((root / papers.CATALOG).read_bytes()).hexdigest()


@pytest.mark.parametrize("base_kind", ["missing", "zero", "abbreviated", "symbolic", "unknown", "same", "blob"])
def test_unknown_or_inexact_trusted_base_fails_closed(history: tuple[Path, str], base_kind: str) -> None:
    root, base = history
    append_paper(root)
    head = save(root)
    candidate = {
        "missing": None,
        "zero": "0" * 40,
        "abbreviated": base[:12],
        "symbolic": "main",
        "unknown": "f" * 40,
        "same": head,
        "blob": git(root, "rev-parse", f"{base}:README.md"),
    }[base_kind]
    assert_full(root, candidate, head)


@pytest.mark.parametrize("head", ["HEAD", "main", "f" * 40, "x" * 40])
def test_head_must_also_be_an_existing_exact_commit(history: tuple[Path, str], head: str) -> None:
    root, base = history
    assert_full(root, base, head)


@pytest.mark.parametrize(
    "target",
    [
        "app.py",
        "unknown.txt",
        "docs/unknown.html",
        "docs/papers/unlisted.pdf",
        "docs/assets/payload.js",
        "scripts/research_papers.py",
        "scripts/build_service_worker.py",
        "scripts/paper_changes.py",
        "alpha_factory_v1/demos/catalog.json",
        ".github/workflows/release.yml",
    ],
)
def test_mixed_source_unknown_and_validator_tampering_require_full_release(
    history: tuple[Path, str], target: str
) -> None:
    root, base = history
    append_paper(root)
    path = root / target
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("untrusted change\n")
    assert_full(root, base, save(root))


@pytest.mark.parametrize("target", sorted(changes.GENERATED))
def test_generated_files_must_match_exact_trusted_rendering(history: tuple[Path, str], target: str) -> None:
    root, base = history
    append_paper(root)
    path = root / target
    path.write_bytes(path.read_bytes() + b"\nUntrusted payload outside generated content\n")
    assert_full(root, base, save(root))


@pytest.mark.parametrize("target", ["README.md", "docs/index.html", "docs/papers/new-paper.pdf", papers.CATALOG])
@pytest.mark.parametrize("kind", ["executable", "symlink"])
def test_mode_and_symlink_changes_never_qualify(history: tuple[Path, str], target: str, kind: str) -> None:
    root, base = history
    append_paper(root)
    path = root / target
    if kind == "executable":
        path.chmod(0o755)
    else:
        path.unlink()
        path.symlink_to("app.py")
    assert_full(root, base, save(root))


@pytest.mark.parametrize("target", ["README.md", "docs/index.html", "docs/papers/paper-0.pdf", "app.py"])
def test_deletions_require_full_release(history: tuple[Path, str], target: str) -> None:
    root, base = history
    append_paper(root)
    (root / target).unlink()
    assert_full(root, base, save(root))


@pytest.mark.parametrize(
    "kind", ["old-bytes", "old-hash-and-bytes", "old-id", "new-hash", "invalid-json", "new-not-pdf"]
)
def test_catalog_or_original_integrity_failures_require_full_release(history: tuple[Path, str], kind: str) -> None:
    root, base = history
    append_paper(root)
    data = papers.load_catalog(root)
    if kind in {"old-bytes", "old-hash-and-bytes"}:
        row = data["papers"][0]
        changed = (root / row["pdf"]["path"]).read_bytes() + b"\ntampered"
        (root / row["pdf"]["path"]).write_bytes(changed)
        if kind == "old-hash-and-bytes":
            row["pdf"]["sha256"] = hashlib.sha256(changed).hexdigest()
    elif kind == "old-id":
        data["papers"][0]["id"] = "retargeted"
    elif kind == "new-hash":
        data["papers"][-1]["pdf"]["sha256"] = "0" * 64
    elif kind == "new-not-pdf":
        row = data["papers"][-1]
        raw = b"<script>not a PDF</script>"
        (root / row["pdf"]["path"]).write_bytes(raw)
        row["pdf"]["sha256"] = hashlib.sha256(raw).hexdigest()
    refresh_fixture(root, data)
    if kind == "invalid-json":
        (root / papers.CATALOG).write_text('{"schema":')
    assert_full(root, base, save(root))


def test_dirty_worktree_cannot_change_exact_git_classification(history: tuple[Path, str]) -> None:
    root, base = history
    append_paper(root)
    head = save(root)
    (root / "README.md").write_text("uncommitted garbage")
    (root / papers.CATALOG).write_text("uncommitted invalid JSON")
    (root / "app.py").write_text("uncommitted source change")
    result = changes.classify(root, base, head)
    assert result["mode"] == "paper", result


def test_code_change_then_revert_cannot_hide_inside_net_paper_diff(history: tuple[Path, str]) -> None:
    root, base = history
    (root / "app.py").write_text("VALUE = 'untrusted'\n")
    save(root, "Hidden source change")
    git(root, "checkout", base, "--", "app.py")
    save(root, "Revert hidden source change")
    append_paper(root)
    head = save(root, "Add legitimate paper")
    assert "app.py" not in git(root, "diff", "--name-only", base, head).splitlines()
    assert_full(root, base, head)


def test_merge_side_branch_change_and_revert_cannot_hide(history: tuple[Path, str]) -> None:
    root, base = history
    git(root, "switch", "-c", "side")
    (root / "app.py").write_text("VALUE = 'side-branch attack'\n")
    save(root, "Side branch changes source")
    git(root, "checkout", base, "--", "app.py")
    save(root, "Side branch restores source")
    git(root, "switch", "main")
    append_paper(root)
    save(root, "Main adds paper")
    git(root, "-c", "commit.gpgsign=false", "merge", "--no-ff", "side", "-m", "Merge apparently empty side branch")
    head = git(root, "rev-parse", "HEAD")
    assert "app.py" not in git(root, "diff", "--name-only", base, head).splitlines()
    assert_full(root, base, head)


def test_every_paper_transition_is_proved(history: tuple[Path, str]) -> None:
    root, base = history
    append_paper(root, "second")
    middle = save(root)
    append_paper(root, "third")
    head = save(root)
    result = changes.classify(root, base, head)
    assert result["mode"] == "paper", result
    assert [(row["before"], row["after"]) for row in result["transitions"]] == [(base, middle), (middle, head)]


def test_shallow_history_fails_closed(history: tuple[Path, str]) -> None:
    root, base = history
    append_paper(root)
    head = save(root)
    (root / ".git/shallow").write_text(head + "\n")
    assert_full(root, base, head)


def test_unrelated_history_fails_closed(history: tuple[Path, str]) -> None:
    root, base = history
    git(root, "switch", "--orphan", "unrelated")
    write_paper_fixture(root)
    head = save(root)
    assert_full(root, base, head)


def test_git_replace_objects_do_not_hide_source_changes(history: tuple[Path, str]) -> None:
    root, base = history
    append_paper(root)
    good = save(root)
    (root / "app.py").write_text("VALUE = 'attack'\n")
    bad = save(root)
    git(root, "replace", bad, good)
    assert_full(root, base, bad)


def test_history_limit_fails_closed(history: tuple[Path, str], monkeypatch: pytest.MonkeyPatch) -> None:
    root, base = history
    append_paper(root, "second")
    save(root)
    append_paper(root, "third")
    head = save(root)
    monkeypatch.setattr(changes, "MAX_HISTORY", 1)
    assert_full(root, base, head)


def test_noop_commit_is_not_a_substantive_paper_upload(history: tuple[Path, str]) -> None:
    root, base = history
    assert_full(root, base, save(root, "Empty commit"))


def test_inexact_baseline_generated_content_fails_closed(history: tuple[Path, str]) -> None:
    root, _ = history
    (root / "docs/service-worker.js").write_text("// forged baseline worker\n")
    base = save(root)
    append_paper(root)
    assert_full(root, base, save(root))


def test_git_process_failure_becomes_full_classification(
    history: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base = history
    append_paper(root)
    head = save(root)

    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("git", timeout=60)

    monkeypatch.setattr(changes.subprocess, "run", timeout)
    assert_full(root, base, head)


def test_safe_paper_side_branch_merge_is_proved_not_blanket_rejected(history: tuple[Path, str]) -> None:
    root, base = history
    git(root, "switch", "-c", "safe-side")
    append_paper(root)
    side = save(root, "Side branch adds only paper")
    git(root, "switch", "main")
    main = save(root, "Unchanged checkpoint")
    git(root, "-c", "commit.gpgsign=false", "merge", "--no-ff", "safe-side", "-m", "Merge only paper")
    head = git(root, "rev-parse", "HEAD")
    result = changes.classify(root, base, head)
    assert result["mode"] == "paper", result
    assert {row["after"] for row in result["transitions"]} == {side, main, head}


def test_baseline_without_catalog_requires_full_qualification(history: tuple[Path, str]) -> None:
    root, original = history
    (root / papers.CATALOG).unlink()
    base = save(root, "Pre-catalog software")
    git(root, "checkout", original, "--", papers.CATALOG)
    append_paper(root)
    assert_full(root, base, save(root))


def test_pathologically_nested_catalog_fails_closed(history: tuple[Path, str]) -> None:
    root, base = history
    append_paper(root)
    raw = '{"schema":"agialpha.research-papers.v1","papers":' + "[" * 2000 + "0" + "]" * 2000 + "}"
    (root / papers.CATALOG).write_text(raw)
    assert_full(root, base, save(root))


def test_latest_pr_paper_commit_retains_unmerged_software_qualification(history: tuple[Path, str]) -> None:
    root, base = history
    (root / "app.py").write_text("VALUE = 'new software'\n")
    software_head = save(root, "Software PR head")
    assert_full(root, base, software_head)
    append_paper(root)
    latest_head = save(root, "Paper-only latest commit on software PR")
    assert "app.py" not in git(root, "diff", "--name-only", software_head, latest_head).splitlines()
    # GitHub PR scope starts at the PR base, never the superseded head.
    assert_full(root, base, latest_head)
