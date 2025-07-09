# SPDX-License-Identifier: Apache-2.0
import unittest
from pathlib import Path
from alpha_factory_v1.demos import validate_demos


class TestDemos(unittest.TestCase):
    """Sanity checks for demo utilities."""

    def test_validate_demos(self) -> None:
        """``validate_demos`` succeeds for shipped demos."""
        # Require slightly longer READMEs to ensure usefulness
        exit_code = validate_demos.main(
            validate_demos.DEFAULT_DIR,
            min_lines=10,
            require_code_block=True,
        )
        self.assertEqual(exit_code, 0)

    def test_quickstart_wrapper(self) -> None:
        """The demo quick_start script delegates to the repo quickstart."""
        script = Path("alpha_factory_v1/demos/quick_start.sh")
        self.assertTrue(script.exists())
        content = script.read_text()
        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("../quickstart.sh", content)

    def test_demo_init_files(self) -> None:
        """Every demo directory is importable as a package."""
        base = Path(validate_demos.DEFAULT_DIR)
        for path in base.iterdir():
            if path.is_dir() and not path.name.startswith(".") and not path.name.startswith("__"):
                self.assertTrue(
                    (path / "__init__.py").exists(),
                    f"Missing __init__.py in {path.name}",
                )

    def test_demo_shell_scripts(self) -> None:
        """All demo shell scripts should be executable and have shebangs."""
        base = Path(validate_demos.DEFAULT_DIR)
        for script in base.rglob("*.sh"):
            with self.subTest(script=script.name):
                content = script.read_text(errors="ignore")
                self.assertTrue(content.startswith("#!/"), f"{script} missing shebang")
                self.assertTrue(script.stat().st_mode & 0o111, f"{script} not executable")

    def test_validate_demos_cli(self) -> None:
        """Running the module as a CLI should succeed."""
        import sys
        import subprocess

        # Ensure the module is executed fresh by ``python -m``.
        sys.modules.pop("alpha_factory_v1.demos.validate_demos", None)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.demos.validate_demos",
                "--min-lines",
                "10",
                "--require-code-block",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("validated", result.stdout.lower())
