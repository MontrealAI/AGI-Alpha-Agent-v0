# SPDX-License-Identifier: Apache-2.0
"""Exercise offline lock checks without running a package resolver or network request."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
from types import ModuleType
from typing import Any
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "verify_aiga_requirements_lock.py",
    "verify_alpha_colab_requirements_lock.py",
    "verify_alpha_requirements_lock.py",
    "verify_backend_requirements_lock.py",
    "verify_era_experience_requirements_lock.py",
    "verify_mats_requirements_lock.py",
    "verify_requirements_lock.py",
)


def load_checker(filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("lock_checker", ROOT / "scripts" / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OfflineLockCompilerTests(unittest.TestCase):
    def test_nonlocal_and_non_directory_wheelhouses_never_launch_resolver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            existing_file = Path(temporary) / "wheel.whl"
            existing_file.write_bytes(b"inert fixture")
            for filename in SCRIPTS:
                for value in (
                    "https://example.invalid/packages/",
                    "file:///tmp/packages",
                    str(Path(temporary) / "absent"),
                    str(existing_file),
                ):
                    with self.subTest(script=filename, value=value):
                        module = load_checker(filename)
                        with (
                            patch.dict(os.environ, {"WHEELHOUSE": value}),
                            patch.object(
                                module.subprocess, "run", return_value=subprocess.CompletedProcess([], 17, "", "")
                            ) as resolver,
                            contextlib.redirect_stderr(io.StringIO()) as errors,
                        ):
                            self.assertEqual(module.main(), 1)
                        resolver.assert_not_called()
                        self.assertIn("existing local directory", errors.getvalue())

    def test_local_directory_is_one_absolute_operand_and_failure_propagates(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            wheelhouse = Path(temporary) / "local wheels; literal value"
            wheelhouse.mkdir()
            relative = os.path.relpath(wheelhouse, Path.cwd())
            for filename in SCRIPTS:
                for compiler in (None, "/trusted/pip-compile"):
                    with self.subTest(script=filename, compiler=compiler):
                        module = load_checker(filename)
                        with (
                            patch.dict(os.environ, {"WHEELHOUSE": relative}),
                            patch.object(module.shutil, "which", return_value=compiler),
                            patch.object(
                                module.subprocess, "run", return_value=subprocess.CompletedProcess([], 17, "", "")
                            ) as resolver,
                        ):
                            self.assertEqual(module.main(), 17)
                        command = resolver.call_args.args[0]
                        self.assertEqual(command[command.index("--find-links") + 1], str(wheelhouse.resolve()))
                        self.assertIn("--no-index", command)
                        self.assertEqual(resolver.call_args.kwargs["timeout"], 600)
                        self.assertNotIn("shell", resolver.call_args.kwargs)

    def test_timeout_refuses_success_and_reports_finite_budget(self) -> None:
        for filename in SCRIPTS:
            with self.subTest(script=filename):
                module = load_checker(filename)
                with (
                    patch.dict(os.environ, {"WHEELHOUSE": ""}),
                    patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("pip-compile", 600)),
                    contextlib.redirect_stderr(io.StringIO()) as errors,
                ):
                    self.assertEqual(module.main(), 1)
                self.assertIn("600 seconds", errors.getvalue())

    def test_online_default_has_no_offline_options_and_propagates_failure(self) -> None:
        for filename in SCRIPTS:
            with self.subTest(script=filename):
                module = load_checker(filename)
                with (
                    patch.dict(os.environ, {"WHEELHOUSE": ""}),
                    patch.object(
                        module.subprocess, "run", return_value=subprocess.CompletedProcess([], 23, "", "")
                    ) as resolver,
                ):
                    self.assertEqual(module.main(), 23)
                self.assertNotIn("--no-index", resolver.call_args.args[0])
                self.assertNotIn("--find-links", resolver.call_args.args[0])

    def test_exact_and_changed_lock_outputs_keep_the_existing_equality_gate(self) -> None:
        for filename in SCRIPTS:
            for changed in (False, True):
                with self.subTest(script=filename, changed=changed):
                    module = load_checker(filename)

                    def compile_fixture(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
                        output_index = command.index("-o")
                        requirements = Path(command[output_index - 1])
                        lock = (
                            requirements.with_name("requirements-lock.txt")
                            if requirements.parent.name == "backend"
                            else requirements.with_suffix(".lock")
                        )
                        body = lock.read_bytes() + (b"\n# changed fixture\n" if changed else b"")
                        Path(command[output_index + 1]).write_bytes(body)
                        return subprocess.CompletedProcess(command, 0, "", "")

                    with (
                        patch.dict(os.environ, {"WHEELHOUSE": ""}),
                        patch.object(module.subprocess, "run", side_effect=compile_fixture),
                        contextlib.redirect_stderr(io.StringIO()) as errors,
                    ):
                        self.assertEqual(module.main(), 1 if changed else 0)
                    if changed:
                        self.assertIn("outdated", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
