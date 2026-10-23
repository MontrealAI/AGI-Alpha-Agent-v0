# SPDX-License-Identifier: Apache-2.0
"""The reviewed evidence exception admits exact inert media and fails closed."""

from __future__ import annotations

import copy
from contextlib import AbstractContextManager
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
from typing import Any
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import check_no_binary_diff as gate
from scripts import research_papers as papers

ROOT = Path(__file__).resolve().parents[1]


class EnterpriseAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        target = self.root / gate.ENTERPRISE_MANIFEST
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / gate.ENTERPRISE_MANIFEST).read_bytes())
        self.rows = gate._load_enterprise_manifest(ROOT)
        self.png = next(name for name in self.rows if name.endswith("/desktop.png"))
        self.zip = next(name for name in self.rows if name.endswith(".zip"))
        for name in (self.png, self.zip):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def rewrite_manifest(self, data: object) -> AbstractContextManager[Any]:
        raw = json.dumps(data).encode()
        (self.root / gate.ENTERPRISE_MANIFEST).write_bytes(raw)
        return patch.object(gate, "ENTERPRISE_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest())

    def test_all_sixteen_originals_pass_actual_byte_and_media_validation(self) -> None:
        self.assertEqual(len(self.rows), 16)
        self.assertEqual(sum(row["size"] for row in self.rows.values()), 13_510_902)
        self.assertEqual(gate._enterprise_admissions(ROOT, list(self.rows)), set(self.rows))

    def test_exact_original_subset_passes(self) -> None:
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png, self.zip]), {self.png, self.zip})

    def test_changed_byte_is_rejected(self) -> None:
        path = self.root / self.png
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png]), set())

    def test_changed_length_and_deleted_file_are_rejected(self) -> None:
        path = self.root / self.png
        path.write_bytes(path.read_bytes() + b"x")
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png]), set())
        path.unlink()
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png]), set())

    def test_unknown_extra_and_renamed_original_are_rejected(self) -> None:
        renamed = self.png.replace("desktop.png", "unreviewed.png")
        shutil.copyfile(self.root / self.png, self.root / renamed)
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png, renamed]), {self.png})
        self.assertEqual(gate._enterprise_admissions(self.root, [renamed]), set())

    def test_file_symlink_is_rejected(self) -> None:
        path = self.root / self.png
        path.unlink()
        path.symlink_to(ROOT / self.png)
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png]), set())

    def test_parent_symlink_is_rejected(self) -> None:
        path = self.root / self.png
        parent = path.parent
        moved = parent.with_name(parent.name + "-moved")
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png]), set())

    def test_directory_in_place_of_evidence_is_rejected(self) -> None:
        path = self.root / self.png
        path.unlink()
        path.mkdir()
        self.assertEqual(gate._enterprise_admissions(self.root, [self.png]), set())

    def test_manifest_tampering_is_rejected(self) -> None:
        path = self.root / gate.ENTERPRISE_MANIFEST
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "reviewed bytes"):
            gate._enterprise_admissions(self.root, [self.png])

    def test_missing_and_symlink_manifest_are_rejected(self) -> None:
        path = self.root / gate.ENTERPRISE_MANIFEST
        path.unlink()
        with self.assertRaises(OSError):
            gate._enterprise_admissions(self.root, [self.png])
        path.symlink_to(ROOT / gate.ENTERPRISE_MANIFEST)
        with self.assertRaisesRegex(ValueError, "symlink"):
            gate._enterprise_admissions(self.root, [self.png])

    def test_missing_manifest_does_not_admit_unrelated_binaries(self) -> None:
        (self.root / gate.ENTERPRISE_MANIFEST).unlink()
        self.assertEqual(gate._enterprise_admissions(self.root, ["extra.zip", "unrelated.png"]), set())

    def test_main_admits_originals_and_keeps_unknown_binary_failure(self) -> None:
        for paths, expected in [([self.png, self.zip], 0), ([self.png, "extra.zip"], 1)]:
            output = io.StringIO()
            with (
                self.subTest(paths=paths),
                patch.object(gate, "_git_root", return_value=self.root),
                patch.object(gate, "_base_ref", return_value="base"),
                patch.object(gate, "_iter_changed_paths", return_value=paths),
                patch.object(gate, "_has_binary_diff", return_value=[]),
                patch.object(gate, "_run", return_value=subprocess.CompletedProcess([], 1)),
                patch.object(papers, "load_catalog", return_value={}),
                patch.object(papers, "verify_files"),
                patch.object(papers, "asset_hashes", return_value={}),
                patch("sys.stdout", output),
            ):
                self.assertEqual(gate.main(), expected)
            if expected:
                self.assertIn("  - extra.zip", output.getvalue())
            else:
                self.assertEqual(output.getvalue(), "No binary changes detected.\n")

    def test_malformed_manifest_json_is_rejected(self) -> None:
        raw = b"{"
        (self.root / gate.ENTERPRISE_MANIFEST).write_bytes(raw)
        with patch.object(gate, "ENTERPRISE_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest()):
            with self.assertRaises(ValueError):
                gate._load_enterprise_manifest(self.root)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        raw = b'{"schema":1,"schema":2}'
        (self.root / gate.ENTERPRISE_MANIFEST).write_bytes(raw)
        with patch.object(gate, "ENTERPRISE_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                gate._load_enterprise_manifest(self.root)

    def test_manifest_schema_source_inventory_and_records_are_closed(self) -> None:
        original = json.loads((ROOT / gate.ENTERPRISE_MANIFEST).read_bytes())
        changes = [
            ("schema", "unknown"),
            ("source_commit", "0" * 40),
            ("source_tree", "0" * 40),
            ("files", original["files"][:-1]),
            ("files", original["files"] + [original["files"][0]]),
            ("unknown", "field"),
        ]
        for key, value in changes:
            with self.subTest(key=key, value=str(value)[:40]):
                data = copy.deepcopy(original)
                data[key] = value
                with self.rewrite_manifest(data), self.assertRaises(ValueError):
                    gate._load_enterprise_manifest(self.root)
        for key, value in [
            ("path", "../outside.png"),
            ("path", self.png.replace("desktop.png", "../desktop.png")),
            ("path", self.png.replace("desktop.png", "./desktop.png")),
            ("path", self.png.replace("/", "\\")),
            ("size", True),
            ("size", -1),
            ("sha256", "x" * 64),
            ("git_blob", "x" * 40),
            ("media_type", "image/png"),
            ("media_type", {}),
            ("unknown", "field"),
        ]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(original)
                data["files"][0][key] = value
                with self.rewrite_manifest(data), self.assertRaises(ValueError):
                    gate._load_enterprise_manifest(self.root)

    def test_duplicate_record_and_wrong_total_size_are_rejected(self) -> None:
        data = json.loads((ROOT / gate.ENTERPRISE_MANIFEST).read_bytes())
        data["files"][1] = data["files"][0]
        with self.rewrite_manifest(data), self.assertRaises(ValueError):
            gate._load_enterprise_manifest(self.root)
        data = json.loads((ROOT / gate.ENTERPRISE_MANIFEST).read_bytes())
        data["files"][0]["size"] += 1
        with self.rewrite_manifest(data), self.assertRaises(ValueError):
            gate._load_enterprise_manifest(self.root)

    def test_media_refusal_is_independent_of_hash_and_size(self) -> None:
        for name in (self.png, self.zip):
            with self.subTest(name=name):
                raw = b"X" * self.rows[name]["size"]
                (self.root / name).write_bytes(raw)
                rows = copy.deepcopy(self.rows)
                rows[name]["sha256"] = hashlib.sha256(raw).hexdigest()
                rows[name]["git_blob"] = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
                with patch.object(gate, "_load_enterprise_manifest", return_value=rows):
                    self.assertEqual(gate._enterprise_admissions(self.root, [name]), set())

    def test_png_crc_truncation_and_trailing_data_are_rejected(self) -> None:
        raw = (ROOT / self.png).read_bytes()
        bad_crc = bytearray(raw)
        bad_crc[29] ^= 1
        for changed in (bytes(bad_crc), raw[:-1], raw + b"x", b"\x89PNG\r\n\x1a\n"):
            with self.subTest(size=len(changed)):
                self.assertFalse(gate._valid_png(changed))

    def test_zip_invalid_paths_duplicates_symlinks_and_malformed_bytes_are_rejected(self) -> None:
        path = self.root / "type-check.zip"
        for name in ("../outside", "/absolute", "a/../b", "a\\b", "a/./b"):
            with self.subTest(name=name):
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr(name, b"inert")
                path.write_bytes(buffer.getvalue())
                self.assertFalse(gate._valid_zip(path, path.read_bytes()))
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(info, b"target")
        path.write_bytes(buffer.getvalue())
        self.assertFalse(gate._valid_zip(path, path.read_bytes()))
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("duplicate", b"one")
                archive.writestr("duplicate", b"two")
        path.write_bytes(buffer.getvalue())
        self.assertFalse(gate._valid_zip(path, path.read_bytes()))
        path.write_bytes(b"PK\x03\x04not-an-archive")
        self.assertFalse(gate._valid_zip(path, path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
