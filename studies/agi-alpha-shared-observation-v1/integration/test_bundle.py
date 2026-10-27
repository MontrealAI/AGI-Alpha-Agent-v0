# SPDX-License-Identifier: Apache-2.0
"""Target corrupt, stale and path-injecting transfer payloads before execution."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from bundle import make_bundle, read_bundle, unpack_bundle


class BundleBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.compiler = self.root / "compiler.py"
        self.profile = self.root / "sensor_profile.json"
        self.compiler.write_text("print('fixture only')\n")
        self.profile.write_text('{"scope": "fixture only"}\n')
        self.bundle = self.root / "bundle.zip"
        self.receipt = make_bundle(self.compiler, self.profile, self.bundle)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_deterministic_transfer_preserves_exact_bytes(self) -> None:
        other = self.root / "other.zip"
        second = make_bundle(self.compiler, self.profile, other)
        self.assertEqual(self.receipt["sha256"], second["sha256"])
        destination = self.root / "recipient"
        unpack_bundle(other, second["sha256"], destination)
        self.assertEqual((destination / "compiler.py").read_bytes(), self.compiler.read_bytes())
        self.assertEqual((destination / "sensor_profile.json").read_bytes(), self.profile.read_bytes())

    def test_changed_expected_identity_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "differs"):
            read_bundle(self.bundle, "0" * 64)

    def test_altered_payload_cannot_keep_old_manifest(self) -> None:
        corrupt = self.root / "corrupt.zip"
        with zipfile.ZipFile(self.bundle) as source, zipfile.ZipFile(corrupt, "w") as destination:
            for name in source.namelist():
                destination.writestr(name, b"raise RuntimeError('unexpected')\n" if name == "compiler.py" else source.read(name))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            read_bundle(corrupt, hashlib.sha256(corrupt.read_bytes()).hexdigest())

    def test_extra_path_is_refused_before_unpack(self) -> None:
        corrupt = self.root / "path.zip"
        with zipfile.ZipFile(self.bundle) as source, zipfile.ZipFile(corrupt, "w") as destination:
            for name in source.namelist():
                destination.writestr(name, source.read(name))
            destination.writestr("../escape.py", b"pass\n")
        target = self.root / "recipient"
        with self.assertRaisesRegex(ValueError, "exactly"):
            unpack_bundle(corrupt, hashlib.sha256(corrupt.read_bytes()).hexdigest(), target)
        self.assertFalse(target.exists())
        self.assertFalse((self.root / "escape.py").exists())

    def test_duplicate_manifest_inventory_is_refused(self) -> None:
        corrupt = self.root / "inventory.zip"
        with zipfile.ZipFile(self.bundle) as source, zipfile.ZipFile(corrupt, "w") as destination:
            manifest = json.loads(source.read("manifest.json"))
            manifest["files"][1] = manifest["files"][0]
            for name in source.namelist():
                destination.writestr(name, json.dumps(manifest).encode() if name == "manifest.json" else source.read(name))
        with self.assertRaisesRegex(ValueError, "inventory"):
            read_bundle(corrupt, hashlib.sha256(corrupt.read_bytes()).hexdigest())

    def test_symlink_source_is_refused(self) -> None:
        link = self.root / "linked.py"
        link.symlink_to(self.compiler)
        with self.assertRaisesRegex(ValueError, "ordinary"):
            make_bundle(link, self.profile, self.root / "linked.zip")

    def test_existing_recipient_directory_is_never_overwritten(self) -> None:
        destination = self.root / "recipient"
        destination.mkdir()
        old = destination / "compiler.py"
        old.write_text("preserve recipient work\n")
        with self.assertRaises(FileExistsError):
            unpack_bundle(self.bundle, self.receipt["sha256"], destination)
        self.assertEqual(old.read_text(), "preserve recipient work\n")


if __name__ == "__main__":
    unittest.main()
