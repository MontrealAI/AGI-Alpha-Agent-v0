# SPDX-License-Identifier: Apache-2.0
"""Synthetic path-boundary tests for the reviewed evidence packager."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import package_edition as package


class PackagePathSafetyTests(unittest.TestCase):
    """Exercise every selection branch without using any real private target."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agi-package-path-test-", dir="/dev/shm")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "study"
        self.root.mkdir()
        self.outside = self.base / "synthetic-outside"
        self.outside.mkdir()
        self.synthetic = self.outside / "fixture.txt"
        self.synthetic.write_bytes(b"SYNTHETIC TEST FIXTURE ONLY\n")
        self.frozen = self.root / "experiment/arms/fixture/input.txt"
        self.frozen.parent.mkdir(parents=True)
        self.frozen.write_bytes(b"approved fixture\n")
        self.manifest = self.root / "experiment/source_freeze.json"
        self.write_manifest({"arms/fixture/input.txt": package.digest(self.frozen.read_bytes())})

    def write_manifest(self, files: dict[str, str]) -> None:
        self.manifest.write_text(json.dumps({"files": files}) + "\n")

    def link(self, relative: str, target: Path | None = None) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target or self.synthetic)
        return path

    def test_regular_inside_file_is_selected_and_read(self) -> None:
        selected = package.include_files(self.root)
        self.assertIn("experiment/arms/fixture/input.txt", selected)
        self.assertEqual(package.verify_frozen(self.root), 1)
        self.assertEqual(package.safe_file(self.root, self.frozen)[0], b"approved fixture\n")

    def test_recursive_file_symlink_is_rejected(self) -> None:
        self.link("vendor/linked.txt")
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_recursive_parent_symlink_is_rejected(self) -> None:
        (self.root / "vendor").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_explicit_file_symlink_is_rejected(self) -> None:
        self.link("discovery/INITIAL_SCREEN.md")
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_explicit_parent_symlink_is_rejected(self) -> None:
        (self.outside / "INITIAL_SCREEN.md").write_text("synthetic screen")
        (self.root / "discovery").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_discovery_glob_file_symlink_is_rejected(self) -> None:
        self.link("discovery/beta_sources/linked.txt")
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_discovery_glob_parent_symlink_is_rejected(self) -> None:
        (self.root / "discovery").mkdir()
        (self.root / "discovery/beta_sources").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_frozen_override_cannot_reintroduce_skipped_link(self) -> None:
        path = self.link("experiment/__pycache__/linked.txt")
        self.write_manifest({"__pycache__/linked.txt": package.digest(self.synthetic.read_bytes())})
        with self.assertRaises(ValueError):
            package.include_files(self.root)
        with self.assertRaises(ValueError):
            package.verify_frozen(self.root)
        self.assertTrue(path.is_symlink())

    def test_frozen_manifest_file_symlink_is_rejected(self) -> None:
        target = self.outside / "manifest.json"
        target.write_bytes(self.manifest.read_bytes())
        self.manifest.unlink()
        self.manifest.symlink_to(target)
        with self.assertRaises(ValueError):
            package.verify_frozen(self.root)
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_frozen_parent_traversal_is_rejected(self) -> None:
        self.write_manifest({"../../synthetic-outside/fixture.txt": package.digest(self.synthetic.read_bytes())})
        with self.assertRaises(ValueError):
            package.verify_frozen(self.root)
        with self.assertRaises(ValueError):
            package.include_files(self.root)

    def test_virtual_license_and_readme_links_are_rejected(self) -> None:
        for relative in ["delivery/native_reuse/LICENSE", "delivery/README.md"]:
            with self.subTest(relative=relative):
                path = self.link(relative)
                with self.assertRaises(ValueError):
                    package.safe_file(self.root, path)

    def test_normalization_cannot_read_a_link(self) -> None:
        path = self.link("audit/example.py")
        with self.assertRaises(ValueError):
            package.normalized_sources({"audit/example.py": path}, root=self.root)

    def test_link_replacement_after_selection_is_rejected(self) -> None:
        selected = package.include_files(self.root)
        self.frozen.unlink()
        self.frozen.symlink_to(self.synthetic)
        with self.assertRaises(ValueError):
            package.read_member(
                self.root, "experiment/arms/fixture/input.txt", selected["experiment/arms/fixture/input.txt"]
            )

    def test_parent_replacement_after_selection_is_rejected(self) -> None:
        path = self.root / "audit/item.txt"
        path.parent.mkdir()
        path.write_text("approved synthetic text")
        selected = package.include_files(self.root)
        (self.outside / "item.txt").write_text("outside synthetic text")
        path.unlink()
        path.parent.rmdir()
        path.parent.symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            package.read_member(self.root, "audit/item.txt", selected["audit/item.txt"])

    def test_root_parent_link_is_rejected(self) -> None:
        alias = self.base / "study-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            package.safe_file(alias, alias / "experiment/arms/fixture/input.txt")

    def test_link_to_another_inside_file_is_also_rejected(self) -> None:
        path = self.link("audit/inside.txt", self.frozen)
        with self.assertRaises(ValueError):
            package.safe_file(self.root, path)

    def test_nonregular_inputs_are_rejected_without_blocking(self) -> None:
        directory = self.root / "audit/directory"
        directory.mkdir(parents=True)
        with self.assertRaises(ValueError):
            package.safe_file(self.root, directory)
        fifo = self.root / "audit/fifo"
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            package.safe_file(self.root, fifo)

    def test_outside_regular_file_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            package.safe_file(self.root, self.synthetic)

    def test_prior_gap_rejects_arbitrary_outside_file(self) -> None:
        with self.assertRaises(ValueError):
            package.select_prior(self.root, self.synthetic)

    def test_prior_gap_fixed_source_requires_pinned_hash(self) -> None:
        prior = self.base / "agi_alpha_gap_20261027/deliverables/AGI_ALPHA_Gap_Experiment.zip"
        prior.parent.mkdir(parents=True)
        prior.write_bytes(b"synthetic prior")
        with mock.patch.object(package, "GAP_SHA256", hashlib.sha256(b"synthetic prior").hexdigest()):
            self.assertEqual(package.select_prior(self.root, None), prior)
            prior.write_bytes(b"tampered synthetic prior")
            with self.assertRaises(ValueError):
                package.select_prior(self.root, prior)

    def test_prior_gap_fixed_file_symlink_is_rejected(self) -> None:
        prior = self.base / "agi_alpha_gap_20261027/deliverables/AGI_ALPHA_Gap_Experiment.zip"
        prior.parent.mkdir(parents=True)
        prior.symlink_to(self.synthetic)
        with self.assertRaises(ValueError):
            package.select_prior(self.root, None)

    def test_prior_gap_fixed_parent_symlink_is_rejected(self) -> None:
        old_root = self.base / "agi_alpha_gap_20261027"
        old_root.mkdir()
        (self.outside / "AGI_ALPHA_Gap_Experiment.zip").write_bytes(b"synthetic prior")
        (old_root / "deliverables").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            package.select_prior(self.root, None)

    def test_local_prior_gap_is_allowed_only_with_pinned_hash(self) -> None:
        prior = self.root / "AGI_ALPHA_Gap_Experiment.zip"
        prior.write_bytes(b"synthetic local prior")
        with mock.patch.object(package, "GAP_SHA256", hashlib.sha256(prior.read_bytes()).hexdigest()):
            self.assertEqual(package.select_prior(self.root, None), prior)
        with self.assertRaises(ValueError):
            package.select_prior(self.root, prior)

    def test_output_cannot_overwrite_inherited_prior_archive(self) -> None:
        prior = self.base / "agi_alpha_gap_20261027/deliverables/AGI_ALPHA_Gap_Experiment.zip"
        prior.parent.mkdir(parents=True)
        original = b"synthetic immutable prior"
        prior.write_bytes(original)
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(original).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(prior), "--replace"]),
            self.assertRaisesRegex(ValueError, "Cannot overwrite"),
        ):
            package.main()
        self.assertEqual(prior.read_bytes(), original)

    def test_output_hardlink_cannot_overwrite_prior_archive(self) -> None:
        prior = self.base / "agi_alpha_gap_20261027/deliverables/AGI_ALPHA_Gap_Experiment.zip"
        prior.parent.mkdir(parents=True)
        original = b"synthetic immutable prior"
        prior.write_bytes(original)
        output = self.root / "linked-output.zip"
        os.link(prior, output)
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(original).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(output), "--replace"]),
            self.assertRaisesRegex(ValueError, "Cannot overwrite"),
        ):
            package.main()
        self.assertEqual(prior.read_bytes(), original)

    def test_output_cannot_overwrite_selected_frozen_input(self) -> None:
        prior = self.root / "AGI_ALPHA_Gap_Experiment.zip"
        prior.write_bytes(b"synthetic prior")
        original = self.frozen.read_bytes()
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(prior.read_bytes()).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(self.frozen), "--replace"]),
            self.assertRaisesRegex(ValueError, "selected source or evidence"),
        ):
            package.main()
        self.assertEqual(self.frozen.read_bytes(), original)

    def test_output_cannot_overwrite_selected_current_source(self) -> None:
        prior = self.root / "AGI_ALPHA_Gap_Experiment.zip"
        prior.write_bytes(b"synthetic prior")
        source = self.root / "delivery/current_source.py"
        source.parent.mkdir()
        original = b"print('synthetic source')\n"
        source.write_bytes(original)
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(prior.read_bytes()).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(source), "--replace"]),
            self.assertRaisesRegex(ValueError, "selected source or evidence"),
        ):
            package.main()
        self.assertEqual(source.read_bytes(), original)

    def test_output_hardlink_cannot_overwrite_selected_input(self) -> None:
        prior = self.root / "AGI_ALPHA_Gap_Experiment.zip"
        prior.write_bytes(b"synthetic prior")
        output = self.root / "output-hardlink.zip"
        os.link(self.frozen, output)
        original = self.frozen.read_bytes()
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(prior.read_bytes()).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(output), "--replace"]),
            self.assertRaisesRegex(ValueError, "selected source or evidence"),
        ):
            package.main()
        self.assertEqual(self.frozen.read_bytes(), original)

    def assert_receipt_alias_refused_before_output(self, *, hardlink: bool) -> None:
        prior = self.root / "AGI_ALPHA_Gap_Experiment.zip"
        prior.write_bytes(b"synthetic prior")
        destination = self.root / "delivery/package_receipt.json"
        destination.parent.mkdir()
        original = self.frozen.read_bytes()
        if hardlink:
            os.link(self.frozen, destination)
        else:
            destination.symlink_to(self.frozen)
        output = self.root / "deliverables/output.zip"
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(prior.read_bytes()).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(output), "--replace"]),
            self.assertRaisesRegex(ValueError, "Receipt destination"),
        ):
            package.main()
        self.assertEqual(self.frozen.read_bytes(), original)
        self.assertEqual(package.verify_frozen(self.root), 1)
        self.assertFalse(output.exists())
        self.assertFalse(output.parent.exists())

    def test_receipt_symlink_refused_before_any_output_write(self) -> None:
        self.assert_receipt_alias_refused_before_output(hardlink=False)

    def test_receipt_hardlink_refused_before_any_output_write(self) -> None:
        self.assert_receipt_alias_refused_before_output(hardlink=True)

    def test_archive_output_cannot_equal_missing_receipt(self) -> None:
        prior = self.root / "AGI_ALPHA_Gap_Experiment.zip"
        prior.write_bytes(b"synthetic prior")
        destination = self.root / "delivery/package_receipt.json"
        destination.parent.mkdir()
        with (
            mock.patch.object(package, "ROOT", self.root),
            mock.patch.object(package, "GAP_SHA256", hashlib.sha256(prior.read_bytes()).hexdigest()),
            mock.patch("sys.argv", ["package_edition.py", "--output", str(destination), "--replace"]),
            self.assertRaisesRegex(ValueError, "receipt destination"),
        ):
            package.main()
        self.assertFalse(destination.exists())
        self.assertEqual(package.verify_frozen(self.root), 1)

    def test_archive_output_cannot_equal_existing_receipt(self) -> None:
        destination = self.root / "delivery/package_receipt.json"
        destination.parent.mkdir()
        destination.write_bytes(b"old receipt")
        with self.assertRaisesRegex(ValueError, "receipt destination"):
            package.receipt_parent(self.root, destination)
        self.assertEqual(destination.read_bytes(), b"old receipt")

    def test_receipt_parent_symlink_is_rejected(self) -> None:
        (self.root / "delivery").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(OSError):
            package.receipt_parent(self.root, self.root / "output.zip")
        self.assertFalse((self.outside / "package_receipt.json").exists())

    def test_atomic_receipt_write_updates_only_receipt(self) -> None:
        (self.root / "delivery").mkdir()
        original = self.frozen.read_bytes()
        fd = package.receipt_parent(self.root, self.root / "output.zip")
        try:
            package.write_receipt_atomic(fd, b'{"accepted": true}\n')
            package.write_receipt_atomic(fd, b'{"accepted": true, "updated": true}\n')
        finally:
            os.close(fd)
        self.assertEqual(self.frozen.read_bytes(), original)
        self.assertEqual(package.verify_frozen(self.root), 1)
        self.assertEqual(
            json.loads((self.root / "delivery/package_receipt.json").read_text()), {"accepted": True, "updated": True}
        )
        self.assertEqual(list((self.root / "delivery").glob(".package-receipt-*.tmp")), [])

    def test_late_receipt_hardlink_is_refused_without_truncating_target(self) -> None:
        (self.root / "delivery").mkdir()
        original = self.frozen.read_bytes()
        fd = package.receipt_parent(self.root, self.root / "output.zip")
        os.link(self.frozen, self.root / "delivery/package_receipt.json")
        try:
            with self.assertRaisesRegex(ValueError, "Receipt destination"):
                package.write_receipt_atomic(fd, b"new receipt")
        finally:
            os.close(fd)
        self.assertEqual(self.frozen.read_bytes(), original)
        self.assertEqual(package.verify_frozen(self.root), 1)

    def test_atomic_replace_does_not_follow_last_moment_alias(self) -> None:
        (self.root / "delivery").mkdir()
        original = self.frozen.read_bytes()
        fd = package.receipt_parent(self.root, self.root / "output.zip")
        real_replace = os.replace

        def replace_after_alias(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
            os.link(self.frozen, self.root / "delivery/package_receipt.json")
            real_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

        try:
            with mock.patch.object(os, "replace", side_effect=replace_after_alias):
                package.write_receipt_atomic(fd, b"new receipt")
        finally:
            os.close(fd)
        self.assertEqual(self.frozen.read_bytes(), original)
        self.assertEqual(package.verify_frozen(self.root), 1)
        self.assertEqual((self.root / "delivery/package_receipt.json").read_bytes(), b"new receipt")

    def test_explicit_review_receipt_symlink_is_rejected(self) -> None:
        self.link("publication/review_receipts/cfee251_review.json")
        with self.assertRaises(ValueError):
            package.include_files(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
