# SPDX-License-Identifier: Apache-2.0
"""Package this fixed study root, preserving original evidence and file identities."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {"downloads", "__pycache__", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".aux", ".log", ".out", ".toc", ".pyc"}
GENERATED_RECORDS = {"provenance/package_manifest.json", "provenance/archive_validation.json"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_files() -> list[Path]:
    paths = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in relative.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        if path.is_symlink():
            raise ValueError(f"Refuse symlink: {relative}")
        if path.is_file() and str(relative) not in GENERATED_RECORDS:
            path.resolve().relative_to(ROOT)
            paths.append(path)
    return paths


def write_zip(path: Path, files: list[Path], prefix: str) -> dict[str, object]:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in files:
            relative = source.relative_to(ROOT)
            info = zipfile.ZipInfo(f"{prefix}/{relative}", (2026, 10, 27, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive CRC failure")
        for source in files:
            name = f"{prefix}/{source.relative_to(ROOT)}"
            if hashlib.sha256(archive.read(name)).hexdigest() != digest(source):
                raise ValueError(f"Archive member mismatch: {name}")
    return {
        "file": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
        "members": len(files),
        "crc_and_all_member_sha256": "PASS",
    }


def main() -> None:
    output = ROOT / "downloads"
    output.mkdir(exist_ok=True)
    files = selected_files()
    archive_only = [p for p in files if p.stat().st_size > 750_000 and "results" in p.relative_to(ROOT).parts]
    remote = {
        "rule": "Only large generated results are archive-only; full original bytes remain in the study ZIP.",
        "archive_only": [
            {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in archive_only
        ],
    }
    (ROOT / "provenance/remote_inventory.json").write_text(json.dumps(remote, indent=2) + "\n")
    files = selected_files()
    manifest = {
        "edition": "PAID-PROGRESS-20261027-R1",
        "self_excluded": sorted(GENERATED_RECORDS),
        "excluded": "downloads and reproducible build/cache intermediates",
        "files": [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in files],
    }
    manifest_path = ROOT / "provenance/package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    files.append(manifest_path)
    study = write_zip(output / "AGI_ALPHA_FLYWHEEL_Study.zip", files, ROOT.name)
    latex_files = [
        p for p in files if p.relative_to(ROOT).parts[0] in {"publication", "figures"} or p.name == "LICENSE"
    ]
    latex = write_zip(output / "AGI_ALPHA_FLYWHEEL_LaTeX.zip", latex_files, "AGI_ALPHA_FLYWHEEL_LaTeX")
    validation = {
        "archives": [study, latex],
        "member_manifest_sha256": digest(manifest_path),
        "original_evidence_mutated": False,
        "safe_archive_names": True,
        "note": "This receipt is excluded from the archive to avoid a self-referential checksum. The study includes the prior clean-copy replay receipt.",
    }
    (ROOT / "provenance/archive_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
