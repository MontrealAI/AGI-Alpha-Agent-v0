# SPDX-License-Identifier: Apache-2.0
"""Independent clone recovery preserves work and avoids shared local attributes."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pytest

from scripts.research_papers import verify_files

pytestmark = pytest.mark.smoke

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
    def test_documented_subshell_isolates_routing_and_preserves_caller_environment(self) -> None:
        bash = shutil.which("bash")
        if os.name == "nt":
            git_path = shutil.which("git")
            if git_path:
                bundled = Path(git_path).resolve().parent.parent / "bin/bash.exe"
                if bundled.is_file():
                    bash = str(bundled)
        if bash is None:
            self.fail("Bash/Git Bash is required to exercise the documented smoke regression")
        document = (ROOT / "docs/agent/PAPER_UPLOADS.md").read_text(encoding="utf-8")
        recipe = next(
            block for block in re.findall(r"```sh\n(.*?)```", document, re.S) if "compgen -A variable" in block
        )
        with tempfile.TemporaryDirectory(prefix="paper-routing-") as directory:
            parent = Path(directory).resolve()
            origin = parent / "origin"
            _, new = history(origin)
            external = parent / "external-objects"
            shutil.copytree(origin / ".git/objects", external)
            home = parent / "home"
            home.mkdir()
            env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
            env.pop("BASH_ENV", None)
            env.pop("ENV", None)
            env.update(
                HOME=str(home),
                XDG_CONFIG_HOME=str(home / "config"),
                GIT_CONFIG_GLOBAL=os.devnull,
                GIT_CONFIG_NOSYSTEM="1",
                GIT_ATTR_NOSYSTEM="1",
                GIT_OBJECT_DIRECTORY=str(external),
            )
            (origin / "notes.txt").write_bytes(b"Staged\n")
            git(origin, "add", "notes.txt")
            (origin / "notes.txt").write_bytes(b"Staged\nUnstaged\n")
            (origin / "untracked.txt").write_bytes(b"Keep\n")
            (origin / PAPERS[0]).write_bytes(ORIGINAL + b"% Author revision\n")
            protected = [origin / name for name in (*PAPERS, ".gitattributes", "notes.txt", "untracked.txt")]
            protected += [path for path in (origin / ".git").rglob("*") if path.is_file()]
            original = {path: path.read_bytes() for path in protected}
            objects_before = {path: path.read_bytes() for path in external.rglob("*") if path.is_file()}
            unsafe = parent / "unsafe"
            for cwd, args in (
                (origin, ["clone", "--template=", "--no-local", "--no-checkout", ".", str(unsafe)]),
                (unsafe, ["checkout", "--detach", new]),
            ):
                subprocess.check_output(
                    ["git", "-C", str(cwd), "-c", "core.attributesFile=", "-c", f"core.hooksPath={os.devnull}", *args],
                    env=env,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
            objects_after = {path: path.read_bytes() for path in external.rglob("*") if path.is_file()}
            self.assertNotEqual(objects_after, objects_before)
            with self.assertRaises(subprocess.CalledProcessError):
                git(unsafe, "cat-file", "-e", new + "^{commit}")
            # A synchronous fixture fsmonitor proves the external execution channel
            # without spawning background workers, using sockets, or racing checkout.
            monitor = parent / "monitor.py"
            monitor_log = parent / "monitor.log"
            monitor.write_text(
                "from pathlib import Path\nimport sys\n"
                f"with Path({str(monitor_log)!r}).open('ab') as log:\n"
                "    log.write(b'fsmonitor invoked\\n')\n"
                "Path('fsmonitor-marker.tex').write_bytes(b'% External configuration ran\\n')\n"
                "sys.stdout.buffer.write(b'fixture-token\\0/\\0')\n",
                encoding="utf-8",
            )
            global_config = home / ".gitconfig"
            git(
                origin,
                "config",
                "--file",
                str(global_config),
                "core.fsmonitor",
                f'"{Path(sys.executable).as_posix()}" "{monitor.as_posix()}"',
            )
            protected += [monitor, global_config]
            original.update({path: path.read_bytes() for path in (monitor, global_config)})
            isolate_config = "  export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 || exit 1\n"
            self.assertEqual(recipe.count(isolate_config), 1)
            unsafe_monitor = parent / "unsafe-monitor"
            old_recipe = recipe.replace(isolate_config, "").replace("FULL_VERIFIED_COMMIT_SHA", new)
            old_recipe = old_recipe.replace("../AGI-Alpha-Agent-byte-clean", shlex.quote(unsafe_monitor.as_posix()))
            result = subprocess.run(
                [bash, "--noprofile", "--norc", "-c", old_recipe],
                cwd=origin,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.decode().strip(), new)
            self.assertTrue((unsafe_monitor / "fsmonitor-marker.tex").is_file())
            self.assertIn(b"fsmonitor invoked", monitor_log.read_bytes())
            protected.append(monitor_log)
            original[monitor_log] = monitor_log.read_bytes()
            mixed_index = parent / "mixed.index"
            mixed_index.write_bytes(b"Preserve external mixed-case index\n")
            protected.append(mixed_index)
            original[mixed_index] = mixed_index.read_bytes()
            for case in ("success", "readonly", "readonly-mixed", "enumeration-error", "missing-commit", "occupied"):
                with self.subTest(case=case):
                    fresh = parent / case
                    if case == "occupied":
                        fresh.mkdir()
                        (fresh / "keep.txt").write_bytes(b"Do not replace\n")
                    chosen = "0" * 40 if case == "missing-commit" else new
                    script = recipe.replace("FULL_VERIFIED_COMMIT_SHA", chosen).replace(
                        "../AGI-Alpha-Agent-byte-clean", shlex.quote(fresh.as_posix())
                    )
                    # Bash can retain these spellings even on case-sensitive hosts.
                    # Native Windows routing remains a separate hosted qualification.
                    prefix = (
                        f"export git_object_directory={shlex.quote(external.as_posix())}\n"
                        f"export Git_Dir={shlex.quote((parent / 'unrelated.git').as_posix())}\n"
                        f"export gIt_InDeX_fIlE={shlex.quote(mixed_index.as_posix())}\n"
                    )
                    if case == "readonly":
                        prefix += "readonly GIT_OBJECT_DIRECTORY\n"
                    elif case == "readonly-mixed":
                        prefix += "readonly Git_Dir\n"
                    elif case == "enumeration-error":
                        prefix += "compgen() { return 1; }\n"
                    script = script.replace(
                        "  source_sha=",
                        '  [ -z "${git_object_directory+x}${Git_Dir+x}${gIt_InDeX_fIlE+x}" ] || exit 98\n  source_sha=',
                    )
                    snapshot = 'declare -p "${!GIT_@}" git_object_directory Git_Dir gIt_InDeX_fIlE'
                    script = (
                        prefix
                        + f"caller_before=$({snapshot})\n"
                        + script
                        + f"\nresult=$?\ncaller_after=$({snapshot})\n"
                        + '[ "$caller_before" = "$caller_after" ] || exit 99\nexit "$result"\n'
                    )
                    result = subprocess.run(
                        [bash, "--noprofile", "--norc", "-c", script],
                        cwd=origin,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=30,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 99, result.stderr)
                    self.assertNotEqual(result.returncode, 98, result.stderr)
                    if case == "success":
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.decode().strip(), new)
                        self.assertEqual(git(fresh, "rev-parse", "HEAD").decode().strip(), new)
                        self.assertFalse((fresh / ".git/objects/info/alternates").exists())
                        self.assertFalse((fresh / "fsmonitor-marker.tex").exists())
                        for name in PAPERS:
                            self.assertEqual((fresh / name).read_bytes(), ORIGINAL)
                            self.assertEqual(git(fresh, "show", ":" + name), ORIGINAL)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        if case == "occupied":
                            self.assertEqual(list(fresh.iterdir()), [fresh / "keep.txt"])
                            self.assertEqual((fresh / "keep.txt").read_bytes(), b"Do not replace\n")
                        else:
                            self.assertFalse(fresh.exists())
                    self.assertEqual({path: path.read_bytes() for path in protected}, original)
                    self.assertEqual(
                        {path: path.read_bytes() for path in external.rglob("*") if path.is_file()}, objects_after
                    )

    def test_recovery_commands_disable_global_filters_templates_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-filter-template-") as directory:
            parent = Path(directory).resolve()
            origin = parent / "origin"
            _, new = history(origin)
            template = parent / "template"
            (template / "info").mkdir(parents=True)
            template_attributes = template / "info/attributes"
            template_attributes.write_bytes(b"*.tex filter=mutate\n")
            attributes = parent / "attributes"
            attributes.write_bytes(b"*.tex filter=mutate\n")
            smudge = parent / "smudge.py"
            smudge.write_text(
                "import sys\nsys.stdout.buffer.write(sys.stdin.buffer.read().replace(b'Immutable', b'Mutated'))\n",
                encoding="utf-8",
            )
            hooks = parent / "hooks"
            hooks.mkdir()
            hook_script = parent / "post_checkout.py"
            hook_script.write_text(
                "from pathlib import Path\n"
                f"for name in {PAPERS!r}:\n"
                "    path = Path(name)\n"
                "    path.write_bytes(path.read_bytes().replace(b'Immutable', b'Hooked'))\n"
                "Path('hook-ran').write_bytes(b'Benign fixture hook ran\\n')\n",
                encoding="utf-8",
            )
            hook = hooks / "post-checkout"
            hook.write_bytes(
                f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "{hook_script.as_posix()}"\n'.encode()
            )
            hook.chmod(0o755)
            config = parent / "global.config"
            for key, value in (
                ("core.attributesFile", attributes.as_posix()),
                ("init.templateDir", template.as_posix()),
                ("core.hooksPath", hooks.as_posix()),
                ("filter.mutate.smudge", f'"{Path(sys.executable).as_posix()}" "{smudge.as_posix()}"'),
            ):
                git(origin, "config", "--file", str(config), key, value)
            # These commands intentionally retain the hostile fixture configuration.
            # The normal git() helper would mask the defect being tested.
            env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
            env.update(
                GIT_CONFIG_GLOBAL=str(config),
                GIT_CONFIG_NOSYSTEM="1",
                GIT_ATTR_NOSYSTEM="1",
                GIT_TEMPLATE_DIR=str(template),
            )
            (origin / "notes.txt").write_bytes(b"Staged\n")
            git(origin, "add", "notes.txt")
            (origin / "notes.txt").write_bytes(b"Staged\nUnstaged\n")
            (origin / "untracked.txt").write_bytes(b"Keep\n")
            (origin / PAPERS[0]).write_bytes(ORIGINAL + b"% Author revision\n")
            protected = [config, attributes, template_attributes, smudge, origin / ".git/index", origin / ".git/config"]
            protected += [hook, hook_script]
            protected += [origin / name for name in (*PAPERS, "notes.txt", "untracked.txt")]
            before = {path: path.read_bytes() for path in protected}
            no_hooks = ["-c", f"core.hooksPath={os.devnull}"]
            cases = (
                ("global-filter", no_hooks, ["--template="], False),
                ("template-filter", [*no_hooks, "-c", "core.attributesFile="], [], False),
                ("checkout-hook", ["-c", "core.attributesFile="], ["--template="], False),
                ("isolated-empty", [*no_hooks, "-c", "core.attributesFile="], ["--template="], True),
                ("isolated-null", [*no_hooks, "-c", f"core.attributesFile={os.devnull}"], ["--template="], True),
            )
            for label, settings, templates, isolated in cases:
                with self.subTest(case=label):
                    fresh = parent / label
                    for cwd, args in (
                        (origin, ["clone", *templates, "--no-local", "--no-checkout", ".", str(fresh)]),
                        (fresh, ["checkout", "--detach", new]),
                    ):
                        subprocess.check_output(
                            ["git", "-C", str(cwd), *settings, *args],
                            env=env,
                            stderr=subprocess.PIPE,
                            timeout=30,
                        )
                    marker = b"Hooked" if label == "checkout-hook" else b"Mutated"
                    expected = ORIGINAL if isolated else ORIGINAL.replace(b"Immutable", marker)
                    self.assertEqual((fresh / "hook-ran").exists(), label == "checkout-hook")
                    for name in PAPERS:
                        self.assertEqual((fresh / name).read_bytes(), expected)
                        self.assertEqual(git(fresh, "show", ":" + name), ORIGINAL)
                    self.assertEqual(git(fresh, "rev-parse", "HEAD").decode().strip(), new)
                    if isolated:
                        self.assertFalse((fresh / ".git/info/attributes").exists())
                    self.assertEqual({path: path.read_bytes() for path in protected}, before)
                    self.assertFalse((origin / "hook-ran").exists())

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
                git(existing, "clone", "--template=", "--no-local", "--no-checkout", str(existing), str(fresh))
                git(fresh, "checkout", "--detach", new)
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

    def test_independent_clone_avoids_shared_attributes_and_preserves_original_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="paper-upgrade-") as directory:
            parent = Path(directory).resolve()
            origin, existing, fresh = (parent / name for name in ("origin", "existing", "fresh"))
            donor = parent / "donor"
            old, new = history(donor)
            # Only this disposable source fixture deliberately borrows objects.
            git(donor, "clone", "--shared", "--no-checkout", str(donor), str(origin))
            git(origin, "checkout", "--detach", new)
            alternates = origin / ".git/objects/info/alternates"
            self.assertTrue(alternates.is_file())
            alternates_bytes = alternates.read_bytes()
            info_attributes = origin / ".git/info/attributes"
            info_attributes.write_bytes(b"*.tex text\n")
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
            linked = parent / "linked-counterexample"
            git(existing, "worktree", "add", "--detach", str(linked), new)
            for name in PAPERS:
                self.assertEqual((linked / name).read_bytes(), ORIGINAL.replace(b"\n", b"\r\n"))
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
            config = origin / ".git/config"
            config_bytes = config.read_bytes()
            attributes_bytes = info_attributes.read_bytes()
            registered = git(existing, "worktree", "list", "--porcelain")
            occupied = parent / "occupied"
            occupied.mkdir()
            (occupied / "keep.txt").write_bytes(b"Existing destination contents\n")
            with self.assertRaises(subprocess.CalledProcessError):
                git(existing, "clone", "--template=", "--no-local", "--no-checkout", str(existing), str(occupied))
            self.assertEqual(list(occupied.iterdir()), [occupied / "keep.txt"])
            self.assertEqual((occupied / "keep.txt").read_bytes(), b"Existing destination contents\n")
            self.assertEqual(git(existing, "worktree", "list", "--porcelain"), registered)
            self.assertEqual(index.read_bytes(), index_bytes)
            self.assertEqual(config.read_bytes(), config_bytes)
            self.assertEqual(info_attributes.read_bytes(), attributes_bytes)
            self.assertEqual(alternates.read_bytes(), alternates_bytes)
            self.assertEqual({name: (existing / name).read_bytes() for name in files}, files)
            git(existing, "clone", "--template=", "--no-local", "--no-checkout", str(existing), str(fresh))
            self.assertTrue((fresh / ".git").is_dir())
            self.assertFalse((fresh / ".git/info/attributes").exists())
            self.assertFalse((fresh / ".git/objects/info/alternates").exists())
            git(fresh, "checkout", "--detach", new)
            self.assertEqual(git(fresh, "rev-parse", "HEAD").decode().strip(), new)
            for name in PAPERS:
                self.assertEqual((fresh / name).read_bytes(), ORIGINAL)
                self.assertEqual(git(fresh, "show", ":" + name), ORIGINAL)
            self.assertEqual(index.read_bytes(), index_bytes)
            self.assertEqual(config.read_bytes(), config_bytes)
            self.assertEqual(info_attributes.read_bytes(), attributes_bytes)
            self.assertEqual(alternates.read_bytes(), alternates_bytes)
            self.assertEqual(git(existing, "worktree", "list", "--porcelain"), registered)
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
            git(existing, "clone", "--template=", "--no-local", "--no-checkout", str(existing), str(fresh))
            git(fresh, "checkout", "--detach", new)
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
