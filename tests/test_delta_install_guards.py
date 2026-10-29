# SPDX-License-Identifier: Apache-2.0
"""Refusal guards only; these doubles do not claim installed execution."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.validate_installed_delta import qualify


class InstalledDeltaGuards(unittest.TestCase):
    def test_output_inside_source_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            with self.assertRaisesRegex(ValueError, "outside the source"):
                qualify(source, source / "proof")

    def test_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "new qualification directory"):
                qualify(root / "source", root)

    def test_nonisolated_python_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("scripts.validate_installed_delta.sys.prefix", "/same"),
                patch("scripts.validate_installed_delta.sys.base_prefix", "/same"),
                self.assertRaisesRegex(ValueError, "fresh wheel"),
            ):
                qualify(root / "source", root / "proof")


if __name__ == "__main__":
    unittest.main()
