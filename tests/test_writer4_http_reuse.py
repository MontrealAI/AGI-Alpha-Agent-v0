# SPDX-License-Identifier: Apache-2.0
"""Inert temporary-file controls; no product, Git, network, browser or native execution."""

from pathlib import Path
import tempfile
import unittest

from scripts.reuse_writer4_http import physical, same_component


class ExactHttpComponentControls(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.name = "component/documentary-fixture.txt"
        self.path = self.root / self.name
        self.path.parent.mkdir()
        self.path.write_bytes(b"documentary-fixture-a\n")
        self.path.chmod(0o644)
        self.expected = physical(self.root, {self.name})

    def test_exact_nonempty_component_is_eligible(self) -> None:
        self.assertTrue(same_component(self.expected, physical(self.root, {self.name})))
        self.assertFalse(same_component({}, {}))

    def test_one_changed_body_is_ineligible(self) -> None:
        self.path.write_bytes(b"documentary-fixture-b\n")
        actual = physical(self.root, {self.name})
        self.assertFalse(same_component(self.expected, actual))

    def test_one_changed_mode_is_ineligible(self) -> None:
        self.path.chmod(0o755)
        actual = physical(self.root, {self.name})
        self.assertFalse(same_component(self.expected, actual))

    def test_replaced_path_is_ineligible(self) -> None:
        renamed = "component/renamed-fixture.txt"
        self.path.rename(self.root / renamed)
        actual = physical(self.root, {renamed})
        self.assertFalse(same_component(self.expected, actual))


if __name__ == "__main__":
    unittest.main()
