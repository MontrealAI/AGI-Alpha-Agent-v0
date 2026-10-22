# SPDX-License-Identifier: Apache-2.0
"""Fresh sibling recovery preserves work when old checkout conversions survive."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.research_papers import verify_files

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = b"% Immutable original\n\\section{Original}\n"
PAPERS = ("docs/Out_Learn.tex", "docs/Autonomous_Enterprises.tex", "docs/papers/versioned-original.tex")


def git(root: Path, *args: str) -> bytes:
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_ATTR_NOSYSTEM="1")
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "core.autocrlf=true",
            "-c",
            "core.safecrlf=false",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-c",
            f"core.excludesFile={os.devnull}",
            "-c",
            "user.name=Checkout Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            *args,
        ],
        stderr=subprocess.PIPE,
        timeout=30,
        env=env,
    )


def history(root: Path) -> tuple[str, str]:
    root.mkdir()
    git(root, "init", "--quiet")
    (root / ".gitattributes").write_bytes(b"# Before opaque manuscript attributes\n")
    (root / "notes.txt").write_bytes(b"Initial notes\n")
    for name in PAPERS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ORIGINAL)
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "Original source")
    old = git(root, "rev-parse", "HEAD").decode().strip()
    (root / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    git(root, "add", ".gitattributes")
    git(root, "commit", "--quiet", "-m", "Preserve opaque bytes")
    new = git(root, "rev-parse", "HEAD").decode().strip()
    for name in PAPERS:
        assert git(root, "show", f"{old}:{name}") == git(root, "show", f"{new}:{name}") == ORIGINAL
    return old, new


class PaperCheckoutTransitionTests(unittest.TestCase):
    def test_fixture_ignores_hostile_global_attributes_and_ignore(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-git-attributes-") as directory:
            parent = Path(directory).resolve()
            attributes = parent / "xdg/git/attributes"
            attributes.parent.mkdir(parents=True)
            attributes.write_bytes(b"*.tex -text\n")
            ignored = attributes.with_name("ignore")
            ignored.write_bytes(b"*.tex\n")
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(parent / "xdg")}):
                origin, existing, fresh = (parent / name for name in ("origin", "existing", "fresh"))
                old, new = history(origin)
                git(origin, "worktree", "add", "--detach", str(existing), old)
                for name in PAPERS:
                    self.assertEqual((existing / name).read_bytes(), ORIGINAL.replace(b"\n", b"\r\n"))
                git(existing, "checkout", "--detach", new)
                git(existing, "worktree", "add", "--detach", str(fresh), new)
                for name in PAPERS:
                    self.assertEqual((fresh / name).read_bytes(), ORIGINAL)
                    self.assertEqual(git(fresh, "show", ":" + name), ORIGINAL)
            self.assertEqual(attributes.read_bytes(), b"*.tex -text\n")
            self.assertEqual(ignored.read_bytes(), b"*.tex\n")

    def test_fixture_ignores_inherited_git_routing_and_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-git-env-") as directory:
            parent = Path(directory).resolve()
            unrelated_index = parent / "unrelated.index"
            unrelated_index.write_bytes(b"Do not modify this external index\n")
            inherited = {
                "GIT_DIR": str(parent / "unrelated.git"),
                "GIT_WORK_TREE": str(parent / "unrelated-worktree"),
                "GIT_INDEX_FILE": str(unrelated_index),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.bare",
                "GIT_CONFIG_VALUE_0": "true",
            }
            with patch.dict(os.environ, inherited):
                history(parent / "fixture")
            self.assertTrue((parent / "fixture/.git/index").is_file())
            self.assertEqual(unrelated_index.read_bytes(), b"Do not modify this external index\n")
            self.assertFalse((parent / "unrelated.git").exists())
            self.assertFalse((parent / "unrelated-worktree").exists())

    def test_upgrade_recovery_preserves_staged_unstaged_and_untracked_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-upgrade-") as directory:
            parent = Path(directory).resolve()
            origin, existing, fresh = (parent / name for name in ("origin", "existing", "fresh"))
            old, new = history(origin)
            git(origin, "worktree", "add", "--detach", str(existing), old)
            for name in PAPERS:
                self.assertEqual((existing / name).read_bytes(), ORIGINAL.replace(b"\n", b"\r\n"))
            self.assertEqual(git(existing, "status", "--porcelain"), b"")
            (existing / "notes.txt").write_bytes(b"Staged notes\n")
            git(existing, "add", "notes.txt")
            staged = git(existing, "show", ":notes.txt")
            (existing / "notes.txt").write_bytes(b"Staged notes\nUnstaged notes\n")
            (existing / "untracked.txt").write_bytes(b"Keep this too\n")
            git(existing, "checkout", "--detach", new)
            self.assertEqual(git(existing, "show", ":notes.txt"), staged)
            self.assertEqual((existing / "notes.txt").read_bytes(), b"Staged notes\nUnstaged notes\n")
            # Current Git can retain CRLF here; versions that refresh it are also safe.
            for name in PAPERS:
                self.assertIn((existing / name).read_bytes(), (ORIGINAL, ORIGINAL.replace(b"\n", b"\r\n")))
            # Recovery must also preserve a genuine manuscript edit, not only conversion.
            edited = existing / PAPERS[0]
            edited.write_bytes(edited.read_bytes() + b"% Uncommitted author revision\n")
            files = {
                name: (existing / name).read_bytes()
                for name in (*PAPERS, ".gitattributes", "notes.txt", "untracked.txt")
            }
            index = Path(git(existing, "rev-parse", "--git-path", "index").decode().strip())
            if not index.is_absolute():
                index = existing / index
            index_bytes = index.read_bytes()
            registered = git(existing, "worktree", "list", "--porcelain")
            occupied = parent / "occupied"
            occupied.mkdir()
            (occupied / "keep.txt").write_bytes(b"Existing destination contents\n")
            with self.assertRaises(subprocess.CalledProcessError):
                git(existing, "worktree", "add", "--detach", str(occupied), new)
            self.assertEqual(list(occupied.iterdir()), [occupied / "keep.txt"])
            self.assertEqual((occupied / "keep.txt").read_bytes(), b"Existing destination contents\n")
            self.assertEqual(git(existing, "worktree", "list", "--porcelain"), registered)
            self.assertEqual(index.read_bytes(), index_bytes)
            git(existing, "worktree", "add", "--detach", str(fresh), new)
            self.assertEqual(git(fresh, "rev-parse", "HEAD").decode().strip(), new)
            for name in PAPERS:
                self.assertEqual((fresh / name).read_bytes(), ORIGINAL)
                self.assertEqual(git(fresh, "show", ":" + name), ORIGINAL)
            self.assertEqual(index.read_bytes(), index_bytes)
            self.assertEqual({name: (existing / name).read_bytes() for name in files}, files)
            self.assertEqual(git(existing, "show", ":notes.txt"), staged)

    def test_first_forced_upgrade_is_not_a_required_recovery_step(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-first-checkout-") as directory:
            parent = Path(directory).resolve()
            origin, existing, fresh = (parent / name for name in ("origin", "existing", "fresh"))
            old, new = history(origin)
            git(origin, "worktree", "add", "--detach", str(existing), old)
            # Only in this disposable clean fixture, never the user-edit recovery flow.
            git(existing, "checkout", "--force", "--detach", new)
            for name in PAPERS:
                self.assertIn((existing / name).read_bytes(), (ORIGINAL, ORIGINAL.replace(b"\n", b"\r\n")))
            git(existing, "worktree", "add", "--detach", str(fresh), new)
            for name in PAPERS:
                self.assertEqual((fresh / name).read_bytes(), ORIGINAL)

    def test_digest_error_guides_without_rewriting_or_accepting_different_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-digest-") as directory:
            root = Path(directory).resolve()
            target = root / "original.tex"
            expected = hashlib.sha256(ORIGINAL).hexdigest()
            catalog = {"papers": [{"pdf": None, "tex": {"path": "original.tex", "sha256": expected}}]}
            for raw in (ORIGINAL.replace(b"\n", b"\r\n"), ORIGINAL + b"% Real edit\n"):
                with self.subTest(raw=raw):
                    target.write_bytes(raw)
                    with self.assertRaisesRegex(ValueError, "Paper digest mismatch.*local edits, corruption") as caught:
                        verify_files(root, catalog, pdf_checks=False)
                    self.assertIn("PAPER_UPLOADS.md#recovering-a-byte-mismatched-checkout", str(caught.exception))
                    self.assertEqual(target.read_bytes(), raw)
                    self.assertEqual(catalog["papers"][0]["tex"]["sha256"], expected)


if __name__ == "__main__":
    unittest.main()
