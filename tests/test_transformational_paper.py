# SPDX-License-Identifier: Apache-2.0
"""Exercise actual paper reproduction and independently test ZIP input defenses."""

from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from typing import ClassVar
from unittest import mock
import warnings
import zipfile

from scripts import reproduce_transformational_paper as reproduction

REPO_ROOT = Path(__file__).resolve().parents[1]


class PaperReproductionTests(unittest.TestCase):
    """Reproduce the released artifact rather than a mocked numerical implementation."""

    def test_actual_published_artifact_reproduces_with_checksummed_evidence(self) -> None:
        before = {name: (REPO_ROOT / "docs" / name).read_bytes() for name in reproduction.ARTIFACT_SHA256}
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "evidence"
            completed = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts/reproduce_transformational_paper.py"), "--out", str(out)],
                cwd=Path(temporary),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report, json.loads((out / "report.json").read_text()))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(
                report["paper_url"],
                "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/Transformational_Intelligence.pdf",
            )
            self.assertEqual(report["manifest_checks_passed"], 15)
            self.assertEqual(report["companion_tests_passed"], 50)
            self.assertEqual(report["model_provider_calls"], 0)
            self.assertEqual(report["finite_model"]["active_accuracy"], "8191/8192")
            self.assertEqual(report["finite_model"]["passive_accuracy"], "1/2")
            self.assertEqual(report["finite_model"]["maximum_queries"], 12)
            self.assertIn("no autonomous discovery or general intelligence claim", report["scope"])
            commands = json.loads((out / "commands.json").read_text())
            self.assertEqual(len(commands), 2)
            self.assertTrue(all(command["returncode"] == 0 for command in commands))
            self.assertIn("Ran 50 tests", (out / "companion-tests.stderr.log").read_text())
            with zipfile.ZipFile(io.BytesIO(before["Transformational_Intelligence_LaTeX.zip"])) as bundle:
                for name in ("results.json", "accuracy.csv"):
                    actual = (out / "results" / name).read_bytes()
                    self.assertEqual(actual, bundle.read(f"Transformational_Intelligence/results/{name}"))
                    self.assertEqual(report["results"][name]["sha256"], hashlib.sha256(actual).hexdigest())
            checksum_names = set()
            for line in (out / "SHA256SUMS").read_text().splitlines():
                expected, name = line.split("  ", 1)
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), expected)
                checksum_names.add(name)
            self.assertEqual(
                checksum_names,
                {path.relative_to(out).as_posix() for path in out.rglob("*") if path.is_file()} - {"SHA256SUMS"},
            )
        for name, original in before.items():
            self.assertEqual(hashlib.sha256(original).hexdigest(), reproduction.ARTIFACT_SHA256[name])
            self.assertEqual((REPO_ROOT / "docs" / name).read_bytes(), original)

    def test_corrupt_each_pinned_artifact_refuses_execution(self) -> None:
        for corrupt_name in reproduction.ARTIFACT_SHA256:
            with self.subTest(corrupt_name=corrupt_name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "docs").mkdir()
                for name in reproduction.ARTIFACT_SHA256:
                    shutil.copyfile(REPO_ROOT / "docs" / name, root / "docs" / name)
                with (root / "docs" / corrupt_name).open("ab") as stream:
                    stream.write(b"corruption")
                out = root / "evidence"
                with mock.patch.object(reproduction, "_run_command") as run:
                    report = reproduction.reproduce(root, out)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["error"], f"SHA-256 mismatch: docs/{corrupt_name}")
                run.assert_not_called()
                self.assertEqual(json.loads((out / "commands.json").read_text()), [])

    def test_existing_evidence_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "evidence"
            out.mkdir()
            sentinel = out / "sentinel"
            sentinel.write_bytes(b"keep")
            with self.assertRaisesRegex(reproduction.ReproductionError, "must not already exist"):
                reproduction.reproduce(REPO_ROOT, out)
            self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_dangling_evidence_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "evidence"
            out.symlink_to(Path(temporary) / "missing", target_is_directory=True)
            with self.assertRaisesRegex(reproduction.ReproductionError, "must not already exist"):
                reproduction.reproduce(REPO_ROOT, out)
            self.assertFalse((Path(temporary) / "missing").exists())


class ArchiveSafetyTests(unittest.TestCase):
    """Test unpinned malformed ZIPs at the validator boundary, never as accepted CLI input."""

    members: ClassVar[list[tuple[zipfile.ZipInfo, bytes]]]

    @classmethod
    def setUpClass(cls) -> None:
        archive = REPO_ROOT / "docs/Transformational_Intelligence_LaTeX.zip"
        with zipfile.ZipFile(archive) as bundle:
            cls.members = [(info, bundle.read(info)) for info in bundle.infolist()]

    def archive(self, entries: list[tuple[zipfile.ZipInfo, bytes]]) -> bytes:
        output = io.BytesIO()
        with warnings.catch_warnings(), zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
            warnings.simplefilter("ignore", UserWarning)
            for info, data in entries:
                bundle.writestr(copy.copy(info), data)
        return output.getvalue()

    def assert_rejected_before_writes(self, archive: bytes, message: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "extract"
            with self.assertRaisesRegex(reproduction.ReproductionError, message):
                reproduction._extract_companion(archive, destination)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_traversal_and_alternate_paths_rejected_before_writes(self) -> None:
        for name in (
            "Transformational_Intelligence/../escaped.txt",
            "/Transformational_Intelligence/frame_lab.py",
            "Transformational_Intelligence/./frame_lab.py",
            "Transformational_Intelligence\\frame_lab.py",
            "Transformational_Intelligence//frame_lab.py",
        ):
            with self.subTest(name=name):
                entries = self.members[:-1] + [(zipfile.ZipInfo(name), b"escape")]
                self.assert_rejected_before_writes(self.archive(entries), "unsafe archive member")

    def test_duplicate_allowlisted_member_rejected_before_writes(self) -> None:
        entries = self.members[:-1] + [self.members[0]]
        self.assert_rejected_before_writes(self.archive(entries), "Duplicate archive member")

    def test_symlink_with_allowlisted_name_rejected_before_writes(self) -> None:
        info = zipfile.ZipInfo(self.members[-1][0].filename)
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assert_rejected_before_writes(self.archive(self.members[:-1] + [(info, b"../escape")]), "regular file")

    def test_special_file_rejected_before_writes(self) -> None:
        info = zipfile.ZipInfo(self.members[-1][0].filename)
        info.create_system = 3
        info.external_attr = (stat.S_IFIFO | 0o600) << 16
        self.assert_rejected_before_writes(self.archive(self.members[:-1] + [(info, b"")]), "regular file")

    def test_oversize_member_rejected_before_writes(self) -> None:
        info = zipfile.ZipInfo(self.members[-1][0].filename)
        info.compress_type = zipfile.ZIP_DEFLATED
        entries = self.members[:-1] + [(info, b"a" * (reproduction.MAX_MEMBER_BYTES + 1))]
        self.assert_rejected_before_writes(self.archive(entries), "member exceeds size limit")

    def test_total_uncompressed_limit_rejected_before_writes(self) -> None:
        entries = []
        for index, (original, data) in enumerate(self.members):
            info = copy.copy(original)
            info.compress_type = zipfile.ZIP_DEFLATED
            entries.append((info, b"a" * reproduction.MAX_MEMBER_BYTES if index < 3 else data))
        self.assert_rejected_before_writes(self.archive(entries), "Uncompressed archive exceeds size limit")

    def test_missing_or_extra_member_rejected_before_writes(self) -> None:
        self.assert_rejected_before_writes(self.archive(self.members[:-1]), "exact published member set")
        entries = self.members + [(zipfile.ZipInfo("unexpected.txt"), b"unexpected")]
        self.assert_rejected_before_writes(self.archive(entries), "excess members")

    def test_manifest_failure_detects_modified_companion_before_execution(self) -> None:
        archive = (REPO_ROOT / "docs/Transformational_Intelligence_LaTeX.zip").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            companion = reproduction._extract_companion(archive, Path(temporary) / "extract")
            (companion / "frame_lab.py").write_bytes(b"modified source")
            with self.assertRaisesRegex(reproduction.ReproductionError, "Manifest SHA-256 mismatch: frame_lab.py"):
                reproduction._verify_manifest(companion)


if __name__ == "__main__":
    unittest.main()
