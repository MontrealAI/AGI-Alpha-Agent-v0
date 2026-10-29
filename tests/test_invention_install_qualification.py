# SPDX-License-Identifier: Apache-2.0
"""Input alignment tests; no installed/Docker execution is simulated as success."""
import argparse
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_installed_invention import selected_inputs


class InstalledInputTests(unittest.TestCase):
    def test_explicit_inputs_never_silently_use_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chosen = {name: root / ("custom-" + name + ".json") for name in ("request", "program", "context", "freeze")}
            for path in chosen.values():
                path.write_text("{}")
            self.assertEqual(selected_inputs(root, argparse.Namespace(**chosen)), chosen)

    def test_defaults_are_explicit_and_relative_to_selected_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ("request", "program", "context", "freeze")
            args = argparse.Namespace(**dict.fromkeys(names))
            expected = {name: root / "evidence/invention-qualification-20261029" / (name + ".json") for name in names}
            for path in expected.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}")
            self.assertEqual(selected_inputs(root, args), expected)

    def test_outside_checkout_input_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            root.mkdir()
            args = argparse.Namespace(request=root.parent / "elsewhere.json")
            with self.assertRaisesRegex(ValueError, "inside the source checkout"):
                selected_inputs(root, args)

    def test_symlink_input_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "original.json"
            target.write_text("{}")
            link = root / "link.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "regular file"):
                selected_inputs(root, argparse.Namespace(request=link))


if __name__ == "__main__":
    unittest.main()
