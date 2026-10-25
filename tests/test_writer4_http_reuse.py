# SPDX-License-Identifier: Apache-2.0
"""Benign temporary Git/file controls; no product, network, browser or native execution."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.reuse_writer4_http import (
    MAX_COMPONENT_FILE_BYTES,
    MAX_COMPONENT_TOTAL_BYTES,
    committed,
    git,
    physical,
    same_component,
)


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
        git(self.root, "init", "--quiet")
        git(self.root, "add", "--", self.name)
        git(
            self.root,
            "-c",
            "user.name=Public fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--quiet",
            "-m",
            "Benign component fixture",
        )
        self.expected = committed(self.root, "HEAD", ("component",))

    def test_exact_nonempty_component_is_eligible(self) -> None:
        self.assertTrue(same_component(self.expected, physical(self.root, {self.name}, self.expected)))
        self.assertFalse(same_component({}, {}))

    def test_committed_identity_retains_oid_mode_and_independent_sha256(self) -> None:
        mode, oid, size, content_sha256 = self.expected[self.name]
        raw = git(self.root, "cat-file", "blob", oid)
        self.assertEqual(raw, b"documentary-fixture-a\n")
        self.assertEqual(mode, "100644")
        self.assertEqual(size, len(raw))
        self.assertEqual(oid, git(self.root, "rev-parse", "HEAD:" + self.name).decode().strip())
        self.assertEqual(content_sha256, hashlib.sha256(raw).hexdigest())

    def test_one_changed_body_is_ineligible(self) -> None:
        self.path.write_bytes(b"documentary-fixture-b\n")
        self.assertEqual(self.path.stat().st_size, self.expected[self.name][2])
        with self.assertRaisesRegex(ValueError, "Physical component bytes differ"):
            physical(self.root, {self.name}, self.expected)

    def test_one_changed_mode_is_ineligible(self) -> None:
        self.path.chmod(0o755)
        actual = physical(self.root, {self.name}, self.expected)
        self.assertFalse(same_component(self.expected, actual))

    def test_replaced_path_is_ineligible(self) -> None:
        renamed = "component/renamed-fixture.txt"
        self.path.rename(self.root / renamed)
        with self.assertRaisesRegex(ValueError, "not in the committed source"):
            physical(self.root, {renamed}, self.expected)

    def test_uncommitted_additional_path_is_ineligible(self) -> None:
        extra = "component/untracked-fixture.txt"
        (self.root / extra).write_bytes(b"additional public fixture\n")
        with self.assertRaisesRegex(ValueError, "not in the committed source"):
            physical(self.root, {self.name, extra}, self.expected)

    def test_committed_content_digest_cannot_be_ignored(self) -> None:
        mode, oid, size, _ = self.expected[self.name]
        forged = {self.name: (mode, oid, size, "0" * 64)}
        with self.assertRaisesRegex(ValueError, "Committed component content identity differs"):
            physical(self.root, {self.name}, forged)

    def test_symlink_to_identical_bytes_is_ineligible(self) -> None:
        other = self.root / "other-public-fixture.txt"
        other.write_bytes(self.path.read_bytes())
        self.path.unlink()
        self.path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "not a direct regular file"):
            physical(self.root, {self.name}, self.expected)

    def test_all_committed_metadata_is_bounded_before_any_blob_read(self) -> None:
        _, oid, size, _ = self.expected[self.name]
        metadata = (
            f"100644 blob {oid} {size}\t{self.name}\0"
            f"100644 blob {oid} {MAX_COMPONENT_FILE_BYTES + 1}\tcomponent/oversized.txt\0"
        ).encode()

        def metadata_only(root: Path, *arguments: str) -> bytes:
            self.assertEqual(arguments[0], "ls-tree", "Blob body read preceded complete metadata validation")
            return metadata

        with patch("scripts.reuse_writer4_http.git", side_effect=metadata_only):
            with self.assertRaisesRegex(ValueError, "source byte bounds"):
                committed(self.root, "HEAD", ("component",))

    def test_total_committed_size_is_bounded_before_any_blob_read(self) -> None:
        _, oid, _, _ = self.expected[self.name]
        count = MAX_COMPONENT_TOTAL_BYTES // MAX_COMPONENT_FILE_BYTES + 1
        metadata = "".join(
            f"100644 blob {oid} {MAX_COMPONENT_FILE_BYTES}\tcomponent/fixture-{index}.txt\0" for index in range(count)
        ).encode()

        def metadata_only(root: Path, *arguments: str) -> bytes:
            self.assertEqual(arguments[0], "ls-tree", "Oversized total reached a blob read")
            return metadata

        with patch("scripts.reuse_writer4_http.git", side_effect=metadata_only):
            with self.assertRaisesRegex(ValueError, "source byte bounds"):
                committed(self.root, "HEAD", ("component",))

    def test_changed_head_metadata_is_refused_before_any_blob_read(self) -> None:
        mode, oid, size, _ = self.expected[self.name]
        variants = [
            ("100755", oid, size, self.name),
            (mode, "0" * 40, size, self.name),
            (mode, oid, size + 1, self.name),
            (mode, oid, size, "component/replaced.txt"),
        ]
        for changed_mode, changed_oid, changed_size, changed_name in variants:
            with self.subTest(mode=changed_mode, oid=changed_oid, size=changed_size, name=changed_name):
                metadata = f"{changed_mode} blob {changed_oid} {changed_size}\t{changed_name}\0".encode()

                def metadata_only(root: Path, *arguments: str) -> bytes:
                    self.assertEqual(arguments[0], "ls-tree", "Changed HEAD metadata reached a blob read")
                    return metadata

                with patch("scripts.reuse_writer4_http.git", side_effect=metadata_only):
                    with self.assertRaisesRegex(ValueError, "metadata differs"):
                        committed(self.root, "HEAD", ("component",), expected=self.expected)

    def test_oversized_physical_stat_is_refused_before_any_body_read(self) -> None:
        with self.path.open("r+b") as stream:
            stream.truncate(MAX_COMPONENT_FILE_BYTES + 1)
        with patch("scripts.reuse_writer4_http.git", side_effect=AssertionError("Unexpected Git body read")):
            with patch("pathlib.Path.open", side_effect=AssertionError("Unexpected physical body read")):
                with self.assertRaisesRegex(ValueError, "size differs"):
                    physical(self.root, {self.name}, self.expected)

    def test_oversized_physical_inventory_is_refused_before_any_body_read(self) -> None:
        mode, oid, _, digest = self.expected[self.name]
        oversized = {self.name: (mode, oid, MAX_COMPONENT_FILE_BYTES + 1, digest)}
        with patch("scripts.reuse_writer4_http.git", side_effect=AssertionError("Unexpected Git body read")):
            with patch("pathlib.Path.open", side_effect=AssertionError("Unexpected physical body read")):
                with self.assertRaisesRegex(ValueError, "source byte bounds"):
                    physical(self.root, {self.name}, oversized)

    def test_total_physical_inventory_is_bounded_before_any_body_read(self) -> None:
        mode, oid, _, digest = self.expected[self.name]
        count = MAX_COMPONENT_TOTAL_BYTES // MAX_COMPONENT_FILE_BYTES + 1
        oversized = {
            f"component/fixture-{index}.txt": (mode, oid, MAX_COMPONENT_FILE_BYTES, digest) for index in range(count)
        }
        with patch("scripts.reuse_writer4_http.git", side_effect=AssertionError("Unexpected Git body read")):
            with patch("pathlib.Path.open", side_effect=AssertionError("Unexpected physical body read")):
                with self.assertRaisesRegex(ValueError, "source byte bounds"):
                    physical(self.root, set(oversized), oversized)


if __name__ == "__main__":
    unittest.main()
