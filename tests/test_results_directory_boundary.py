# SPDX-License-Identifier: Apache-2.0
"""Check the actual results-directory initializer without optional server dependencies."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
from typing import Any, Callable
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/api_server.py"


def initializer() -> tuple[Callable[..., Path], dict[str, Any]]:
    tree = ast.parse(SOURCE.read_text())
    function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_prepare_results_directory"
    )
    namespace: dict[str, Any] = {"os": os, "Path": Path, "stat": stat}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["_prepare_results_directory"], namespace


@unittest.skipUnless(
    all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "fchmod", "geteuid"))
    and os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd,
    "POSIX directory-handle acceptance; unsupported platforms are separately refused",
)
class ResultsDirectoryBoundaryTests(unittest.TestCase):
    def test_new_and_existing_owned_directories_retain_owner_only_mode(self) -> None:
        prepare, _ = initializer()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "nested" / "results"
            self.assertEqual(prepare(directory), directory)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            directory.chmod(0o755)
            prepare(directory)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)

    def test_final_directory_symlink_refuses_without_changing_target(self) -> None:
        prepare, _ = initializer()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "unrelated"
            target.mkdir(mode=0o755)
            configured = Path(temporary) / "results"
            configured.symlink_to(target, target_is_directory=True)
            with self.assertRaises((OSError, ValueError)):
                prepare(configured)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)

    def test_configured_ancestor_link_refuses_before_creating_child(self) -> None:
        prepare, _ = initializer()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "unrelated"
            target.mkdir(mode=0o755)
            configured = Path(temporary) / "linked-parent"
            configured.symlink_to(target, target_is_directory=True)
            with self.assertRaises((OSError, ValueError)):
                prepare(configured / "results")
            self.assertFalse((target / "results").exists())
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)

    def test_directory_swap_before_open_cannot_redirect_chmod(self) -> None:
        prepare, _ = initializer()
        original_open = os.open
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            configured, retained, target = (parent / name for name in ("results", "retained", "unrelated"))
            configured.mkdir(mode=0o755)
            target.mkdir(mode=0o755)

            def swapped_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
                if path == "results":
                    configured.rename(retained)
                    configured.symlink_to(target, target_is_directory=True)
                return original_open(path, flags, *args, **kwargs)

            with (
                patch.object(os, "open", swapped_open),
                patch.object(os, "supports_dir_fd", os.supports_dir_fd | {swapped_open}),
            ):
                with self.assertRaises((OSError, ValueError)):
                    prepare(configured)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE(retained.stat().st_mode), 0o755)

    def test_directory_swap_after_open_keeps_chmod_bound_to_original_handle(self) -> None:
        prepare, _ = initializer()
        original_fchmod = os.fchmod
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            configured, retained, target = (parent / name for name in ("results", "retained", "unrelated"))
            configured.mkdir(mode=0o755)
            target.mkdir(mode=0o755)

            def swapped_chmod(descriptor: int, mode: int) -> None:
                configured.rename(retained)
                configured.symlink_to(target, target_is_directory=True)
                original_fchmod(descriptor, mode)

            with patch.object(os, "fchmod", swapped_chmod):
                with self.assertRaisesRegex(ValueError, "changed during preparation"):
                    prepare(configured)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE(retained.stat().st_mode), 0o700)

    def test_world_writable_unprotected_ancestor_refuses(self) -> None:
        prepare, _ = initializer()
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "shared"
            parent.mkdir(mode=0o777)
            parent.chmod(0o777)
            with self.assertRaisesRegex(ValueError, "trusted ownership"):
                prepare(parent / "results")
            self.assertFalse((parent / "results").exists())

    def test_default_system_alias_is_resolved_before_appending_owned_directories(self) -> None:
        prepare, namespace = initializer()
        with tempfile.TemporaryDirectory() as temporary:
            actual = Path(temporary) / "system-temp"
            actual.mkdir()
            alias = Path(temporary) / "system-alias"
            alias.symlink_to(actual, target_is_directory=True)

            def paths(value: Any) -> Any:
                if value == "/tmp":
                    return SimpleNamespace(lstat=lambda: SimpleNamespace(st_uid=0), resolve=alias.resolve)
                return Path(value)

            namespace["Path"] = paths
            with patch.dict(os.environ, {}, clear=True):
                result = prepare()
            self.assertEqual(result, actual / "alphafactory" / "simulations")
            self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o700)

    def test_regular_file_root_and_parent_traversal_refuse(self) -> None:
        prepare, _ = initializer()
        with tempfile.TemporaryDirectory() as temporary:
            ordinary = Path(temporary) / "ordinary"
            ordinary.write_bytes(b"untouched")
            before = ordinary.stat().st_mode
            for path in (ordinary, Path(ordinary.anchor), Path(temporary) / ".." / "results"):
                with self.subTest(path=path), self.assertRaises((OSError, ValueError)):
                    prepare(path)
            self.assertEqual(ordinary.stat().st_mode, before)
            self.assertEqual(ordinary.read_bytes(), b"untouched")


class UnsupportedResultsDirectoryTests(unittest.TestCase):
    def test_missing_handle_capability_refuses_before_filesystem_mutation(self) -> None:
        prepare, _ = initializer()
        with tempfile.TemporaryDirectory() as temporary, patch.object(os, "supports_dir_fd", set()):
            path = Path(temporary) / "must-not-exist"
            with self.assertRaisesRegex(RuntimeError, "platform is unqualified"):
                prepare(path)
            self.assertFalse(path.exists())

    def test_server_initialization_uses_the_checked_helper(self) -> None:
        tree = ast.parse(SOURCE.read_text())
        assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "_results_dir" for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        self.assertIsInstance(assignments[0].value, ast.Call)
        self.assertEqual(ast.unparse(assignments[0].value), "_prepare_results_directory()")


if __name__ == "__main__":
    unittest.main()
