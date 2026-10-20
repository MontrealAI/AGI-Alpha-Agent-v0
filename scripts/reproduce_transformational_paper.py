# SPDX-License-Identifier: Apache-2.0
"""Reproduce the hash-pinned paper's supplied finite model using the standard library."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any
import zipfile

PAPER_URL = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/Transformational_Intelligence.pdf"
PAPER_SOURCE_COMMIT = "d0d18127e3d75b2b1bd13ca448265ba7e75fc21e"
ARTIFACT_SHA256 = {
    "Transformational_Intelligence.pdf": "d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f",
    "Transformational_Intelligence.tex": "9d4a664d951d6b97f5136bf0b44f1ca458e90d585434a6a27a542694bb2ece5f",
    "Transformational_Intelligence_LaTeX.zip": "49b89b4ca5a0db766d4e38af27d39c2ccbe98c4eec2e9b52af023fbbbca0e9b1",
}
BUNDLED_CODE_SHA256 = {
    "frame_lab.py": "53f73924555c6f62ca0396b087d317c93d50dbafec9377ef813c238bb5459ac6",
    "test_frame_lab.py": "bffa3ac3a5a4fa0acf4bb40ffaf3c924968013e3100b7cbbe8936491c3b98774",
}
PACKAGE_ROOT = "Transformational_Intelligence"
PACKAGE_FILES = frozenset(
    {
        "CLAIMS_AND_EVIDENCE.md",
        "MANIFEST.sha256",
        "Makefile",
        "README.md",
        "REVISION_NOTES.md",
        "Transformational_Intelligence.pdf",
        "Transformational_Intelligence.tex",
        "artifact_status.json",
        "frame_lab.py",
        "reference_metadata.json",
        "references.bib",
        "results/accuracy.csv",
        "results/results.json",
        "results/run_output.txt",
        "results/tests.txt",
        "test_frame_lab.py",
    }
)
ARCHIVE_MEMBERS = frozenset(f"{PACKAGE_ROOT}/{name}" for name in PACKAGE_FILES)
MAX_MEMBER_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
SCOPE = (
    "Exact finite synthetic model supplied by the investigator; no autonomous discovery or general intelligence claim. "
    "Query costs exclude unmeasured discovery, setup, migration, verification and maintenance costs."
)


class ReproductionError(ValueError):
    """A pinned input, safe archive, test run or reproduced result failed verification."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_limited(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ReproductionError(f"Input exceeds {limit} bytes: {path.name}")
    return data


def _pinned_artifacts(repo_root: Path) -> dict[str, bytes]:
    artifacts = {}
    for name, expected in ARTIFACT_SHA256.items():
        data = _read_limited(repo_root / "docs" / name, MAX_ARCHIVE_BYTES)
        if _sha256(data) != expected:
            raise ReproductionError(f"SHA-256 mismatch: docs/{name}")
        artifacts[name] = data
    return artifacts


def _validated_members(archive: bytes) -> dict[str, bytes]:
    """Validate every ZIP record and payload before the caller creates any output."""
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ReproductionError("Archive exceeds size limit")
    members: dict[str, bytes] = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        infos = bundle.infolist()
        if len(infos) > len(ARCHIVE_MEMBERS):
            raise ReproductionError("Archive has duplicate or excess members")
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if (
                info.orig_filename != name
                or "\\" in name
                or path.is_absolute()
                or any(part in {"", ".", ".."} for part in name.split("/"))
                or str(path) != name
                or name not in ARCHIVE_MEMBERS
            ):
                raise ReproductionError(f"Unexpected or unsafe archive member: {name!r}")
            if name in members:
                raise ReproductionError(f"Duplicate archive member: {name}")
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                raise ReproductionError(f"Archive member is not a regular file: {name}")
            if info.flag_bits & 1 or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise ReproductionError(f"Unsupported archive encoding: {name}")
            if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
                raise ReproductionError(f"Archive member exceeds size limit: {name}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ReproductionError("Uncompressed archive exceeds size limit")
            with bundle.open(info) as stream:
                data = stream.read(MAX_MEMBER_BYTES + 1)
            if len(data) != info.file_size or len(data) > MAX_MEMBER_BYTES:
                raise ReproductionError(f"Archive member size mismatch: {name}")
            members[name] = data
    if set(members) != ARCHIVE_MEMBERS:
        raise ReproductionError("Archive does not contain the exact published member set")
    return members


def _extract_companion(archive: bytes, destination: Path) -> Path:
    """Extract a wholly validated member set into a new private directory."""
    members = _validated_members(archive)
    destination.mkdir(mode=0o700)
    for name, data in members.items():
        target = destination.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    return destination / PACKAGE_ROOT


def _verify_manifest(companion: Path) -> int:
    entries: dict[str, str] = {}
    for line in (companion / "MANIFEST.sha256").read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if not match or match[2] in entries or match[2] not in PACKAGE_FILES - {"MANIFEST.sha256"}:
            raise ReproductionError("Invalid or duplicate manifest entry")
        entries[match[2]] = match[1]
    if set(entries) != PACKAGE_FILES - {"MANIFEST.sha256"}:
        raise ReproductionError("Manifest does not cover the exact published member set")
    for name, expected in entries.items():
        if _sha256((companion / name).read_bytes()) != expected:
            raise ReproductionError(f"Manifest SHA-256 mismatch: {name}")
    for name, expected in {**BUNDLED_CODE_SHA256, **ARTIFACT_SHA256}.items():
        if not name.endswith(".zip") and entries[name] != expected:
            raise ReproductionError(f"Pinned companion SHA-256 mismatch: {name}")
    return len(entries)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_command(argv: list[str], cwd: Path, label: str, evidence: Path, commands: list[dict[str, Any]]) -> None:
    record: dict[str, Any] = {"argv": argv, "cwd": str(cwd), "label": label}
    commands.append(record)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"},
            capture_output=True,
            timeout=60,
            check=False,
        )
        stdout, stderr = completed.stdout, completed.stderr
        record["returncode"] = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        record["timed_out"] = True
    record["elapsed_seconds"] = time.monotonic() - started
    for suffix, data in (("stdout", stdout), ("stderr", stderr)):
        log = f"{label}.{suffix}.log"
        (evidence / log).write_bytes(data)
        record[suffix] = {"file": log, "sha256": _sha256(data)}
    if record.get("timed_out"):
        raise ReproductionError(f"Command timed out: {label}")
    if record["returncode"]:
        raise ReproductionError(f"Command failed: {label} (exit {record['returncode']})")


def _save_evidence(source: Path, destination: Path, report: dict[str, Any], commands: list[dict[str, Any]]) -> None:
    _write_json(source / "report.json", report)
    _write_json(source / "commands.json", commands)
    files = sorted(path for path in source.rglob("*") if path.is_file())
    checksums = "".join(f"{_sha256(path.read_bytes())}  {path.relative_to(source).as_posix()}\n" for path in files)
    (source / "SHA256SUMS").write_text(checksums, encoding="ascii")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def reproduce(repo_root: Path, out: Path | None = None) -> dict[str, Any]:
    """Verify the published bytes, run its 50 tests, and compare actual output bytes."""
    if out is not None and (out.exists() or out.is_symlink()):
        raise ReproductionError("Evidence directory must not already exist")
    report: dict[str, Any] = {
        "status": "failed",
        "scope": SCOPE,
        "paper_source_commit": PAPER_SOURCE_COMMIT,
        "paper_url": PAPER_URL,
        "python": platform.python_version(),
        "runner_sha256": _sha256(Path(__file__).read_bytes()),
        "artifacts_sha256": ARTIFACT_SHA256,
        "model_provider_calls": 0,
    }
    commands: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="transformational-paper-") as temporary:
        temporary_root = Path(temporary)
        evidence = temporary_root / "evidence"
        evidence.mkdir()
        try:
            artifacts = _pinned_artifacts(repo_root)
            companion = _extract_companion(
                artifacts["Transformational_Intelligence_LaTeX.zip"], temporary_root / "source"
            )
            report["manifest_checks_passed"] = _verify_manifest(companion)
            _run_command(
                [sys.executable, "-I", "-m", "unittest", "-v"], companion, "companion-tests", evidence, commands
            )
            test_log = (evidence / "companion-tests.stderr.log").read_text(encoding="utf-8")
            if not re.search(r"^Ran 50 tests in .+s$", test_log, re.MULTILINE):
                raise ReproductionError("Expected exactly 50 companion tests")
            report["companion_tests_passed"] = 50
            results = evidence / "results"
            _run_command(
                [sys.executable, "-I", "frame_lab.py", "--out", str(results)],
                companion,
                "regenerate-results",
                evidence,
                commands,
            )
            comparisons = {}
            for name in ("results.json", "accuracy.csv"):
                actual = (results / name).read_bytes()
                retained = (companion / "results" / name).read_bytes()
                if actual != retained:
                    raise ReproductionError(f"Regenerated bytes differ from published results: {name}")
                comparisons[name] = {"sha256": _sha256(actual), "bytes": len(actual), "byte_identical": True}
            data = json.loads((results / "results.json").read_text(encoding="utf-8"))
            last = data["accuracy_table"][-1]
            report.update(
                status="passed",
                results=comparisons,
                finite_model={
                    "maximum_queries": last["horizon"],
                    "enumerated_traces": last["enumerated_traces"],
                    "active_accuracy": last["accuracy"]["exact"],
                    "passive_accuracy": last["passive_accuracy"]["exact"],
                    "unrestricted_planner_matches": True,
                },
            )
        except (ReproductionError, OSError, zipfile.BadZipFile, RuntimeError, UnicodeError, KeyError) as exc:
            report["error"] = str(exc)
        if out is not None:
            report["evidence_directory"] = str(out)
            _save_evidence(evidence, out, report, commands)
    return report


def main(argv: list[str] | None = None) -> int:
    """Print one JSON report and exit nonzero on any failed verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, help="Save actual command logs, results and checksums in a new directory")
    args = parser.parse_args(argv)
    try:
        report = reproduce(args.repo_root.resolve(), args.out.absolute() if args.out else None)
    except (ReproductionError, OSError) as exc:
        report = {"status": "failed", "error": str(exc), "scope": SCOPE}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
