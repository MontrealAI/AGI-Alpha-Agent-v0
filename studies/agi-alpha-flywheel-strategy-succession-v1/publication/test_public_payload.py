#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Small adversarial checks of publication extraction, never the scientific run."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from extract_evidence import SCHEMA, extract, load_index, validate_archives
from prepare_public_payload import ARCHIVE_TARGET_BYTES, chunks, scan_private


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(root, payloads, *, duplicate=False, zip_mode=0o100644):
    archive = root / "evidence/archives/test-01.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in payloads]
    manifest = "".join(f"{row['sha256']}  {row['path']}\n" for row in sorted(rows, key=lambda row: row["path"])).encode()
    with zipfile.ZipFile(archive, "x") as zipped:
        for name, data in payloads:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = zip_mode << 16
            zipped.writestr(info, data)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                zipped.writestr(payloads[0][0], payloads[0][1])
        zipped.writestr("SHA256SUMS.txt", manifest)
    index = {"schema": SCHEMA, "archives": [{"path": "evidence/archives/test-01.zip",
        "bytes": archive.stat().st_size, "sha256": sha(archive.read_bytes()),
        "manifest_sha256": sha(manifest), "members": rows}]}
    index_path = root / "evidence/ARCHIVE_INDEX.json"
    index_path.write_text(json.dumps(index))
    return load_index(root, index_path)


class ExtractionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_extraction_then_identical_retry(self):
        payloads = [("results/confirmation-v1/inputs/a.json", b'{"exact":true}\n'),
                    ("development/a.bin", bytes(range(256))),
                    ("operations/load-results/a.json", b'{"valid":true}')]
        index = fixture(self.root, payloads)
        self.assertEqual(len(validate_archives(self.root, index)), 1)
        self.assertFalse((self.root / "results").exists())
        self.assertEqual(extract(self.root, index)["written"], 3)
        for name, data in payloads:
            self.assertEqual((self.root / name).read_bytes(), data)
        retry = extract(self.root, index)
        self.assertEqual((retry["written"], retry["identical_existing_retained"]), (0, 3))

    def test_changed_existing_bytes_block_all_writes(self):
        first = "results/confirmation-v1/inputs/a.json"
        last = "review/results/z.json"
        index = fixture(self.root, [(first, b"new"), (last, b"expected")])
        target = self.root / last
        target.parent.mkdir(parents=True)
        target.write_bytes(b"my work")
        with self.assertRaisesRegex(ValueError, "different existing bytes"):
            extract(self.root, index)
        self.assertFalse((self.root / first).exists())
        self.assertEqual(target.read_bytes(), b"my work")

    def test_separate_evidence_handoff_restores_original_paths(self):
        evidence = self.root / "handoff"
        evidence.mkdir()
        source = self.root / "source"
        source.mkdir()
        name = "results/confirmation-v1/inputs/a.json"
        index = fixture(evidence, [(name, b"exact external evidence")])
        validate_archives(source, index, archive_root=evidence)
        self.assertEqual(list(source.iterdir()), [])
        report = extract(source, index, archive_root=evidence)
        self.assertEqual(report["written"], 1)
        self.assertEqual((source / name).read_bytes(), b"exact external evidence")
        self.assertFalse((evidence / "results").exists())

    def test_traversal_refused(self):
        index = fixture(self.root, [("results/confirmation-v1/../../outside", b"no")])
        with self.assertRaisesRegex(ValueError, "bounded relative"):
            extract(self.root, index)
        self.assertFalse((self.root / "outside").exists())

    def test_symlink_destination_refused(self):
        outside = self.root / "unrelated"
        outside.mkdir()
        (self.root / "development").symlink_to(outside, target_is_directory=True)
        index = fixture(self.root, [("development/should-not-appear.json", b"no")])
        with self.assertRaisesRegex(ValueError, "Symbolic-link"):
            extract(self.root, index)
        self.assertEqual(list(outside.iterdir()), [])

    def test_duplicate_zip_entry_refused(self):
        index = fixture(self.root, [("development/a.json", b"first")], duplicate=True)
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            extract(self.root, index)
        self.assertFalse((self.root / "development").exists())

    def test_symbolic_zip_entry_refused(self):
        index = fixture(self.root, [("development/a.json", b"target")], zip_mode=0o120777)
        with self.assertRaisesRegex(ValueError, "special"):
            extract(self.root, index)

    def test_corrupt_archive_identity_refused(self):
        index = fixture(self.root, [("development/a.json", b"data")])
        index["archives"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "size/hash"):
            extract(self.root, index)
        self.assertFalse((self.root / "development").exists())

    def test_four_mib_shards_keep_members_whole(self):
        paths = []
        for name, count in [("a", ARCHIVE_TARGET_BYTES - 1), ("b", 2), ("c", 3)]:
            path = self.root / name
            with path.open("wb") as stream:
                stream.truncate(count)
            paths.append(path)
        batches = chunks(paths)
        self.assertEqual([[p.name for p in batch] for batch in batches], [["a"], ["b", "c"]])
        with paths[0].open("wb") as stream:
            stream.truncate(ARCHIVE_TARGET_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "4 MiB"):
            chunks(paths)

    def test_private_locator_refusal_does_not_rewrite(self):
        path = self.root / "private.txt"
        original = ("https://chatgpt.com/" + "library?file_id=" + "lib" + "file_1234567890123456").encode()
        path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "locator refused"):
            scan_private(path)
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
