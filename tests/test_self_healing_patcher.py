# SPDX-License-Identifier: Apache-2.0
import unittest
import os
import tempfile
import pathlib
import textwrap
from alpha_factory_v1.demos.self_healing_repo import patcher_core


class TestPatcherCore(unittest.TestCase):
    def test_sanity_check_patch_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            open(os.path.join(repo, "file.py"), "w").close()
            bad_patch = """--- a/missing.py
+++ b/missing.py
@@
-print('x')
+print('y')
"""
            with self.assertRaises(ValueError):
                patcher_core._sanity_check_patch(bad_patch, pathlib.Path(repo))

    def test_apply_patch_rejects_unknown_file(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            open(os.path.join(repo, "file.py"), "w").close()
            bad_patch = """--- a/missing.py
+++ b/missing.py
@@
-print('x')
+print('y')
"""
            with self.assertRaises(ValueError):
                patcher_core.apply_patch(bad_patch, repo_path=repo)

    def test_nested_prefix_handling(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "alpha"), exist_ok=True)
            file_path = os.path.join(repo, "alpha", "test.py")
            with open(file_path, "w") as fh:
                fh.write("x = 1\n")
            patch = textwrap.dedent(
                """\
                --- a/alpha/test.py
                +++ b/alpha/test.py
                @@ -1 +1 @@
                -x = 1
                +x = 2
                """
            )
            # Should not raise for valid nested path
            patcher_core._sanity_check_patch(patch, pathlib.Path(repo))
            patcher_core.apply_patch(patch, repo_path=repo)
            with open(file_path) as fh:
                data = fh.read()
            self.assertIn("x = 2", data)

    def test_apply_patch_success_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            file_path = os.path.join(repo, "hello.txt")
            with open(file_path, "w") as fh:
                fh.write("hello\n")
            patch = textwrap.dedent(
                """\
                --- a/hello.txt
                +++ b/hello.txt
                @@ -1 +1 @@
                -hello
                +hello world
                """
            )
            patcher_core.apply_patch(patch, repo_path=repo)
            with open(file_path) as fh:
                data = fh.read()
            self.assertIn("hello world", data)
            # ensure backup removed
            self.assertFalse(os.path.exists(file_path + ".bak"))

    def test_apply_patch_failure_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            file_path = os.path.join(repo, "hello.txt")
            with open(file_path, "w") as fh:
                fh.write("hello\n")
            bad_patch = "invalid diff"
            with self.assertRaises(RuntimeError) as cm:
                patcher_core.apply_patch(bad_patch, repo_path=repo)
            self.assertIn("patch command failed", str(cm.exception))
            with open(file_path) as fh:
                self.assertEqual(fh.read(), "hello\n")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
