# SPDX-License-Identifier: Apache-2.0
"""Package the complete research record with a deterministic member manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "AGI_ALPHA_Legal_Work_Evidence"
EXCLUDED_DIRECTORIES = {"__pycache__", ".mypy_cache", ".ruff_cache", ".git", "node_modules", "replay"}
TRANSIENT_TEX_SUFFIXES = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"}


def selected_files() -> list[Path]:
    """Retain source, original raw outputs and failures; omit disposable caches."""
    result = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
            continue
        if not path.is_file() or path.suffix == ".pyc":
            continue
        if relative.parts[0] == "paper" and path.suffix in TRANSIENT_TEX_SUFFIXES:
            continue
        if path.is_symlink():
            raise ValueError(f"Do not silently dereference evidence symlink: {relative}")
        if relative.as_posix() == "MANIFEST.sha256.json":
            raise ValueError("The archive manifest is generated, not read from the source root")
        result.append(path)
    return result


def write_member(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    """Use fixed portable metadata so identical research files give identical ZIPs."""
    info = zipfile.ZipInfo(f"{PREFIX}/{name}", date_time=(2026, 10, 26, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content, compresslevel=9)


def main() -> None:
    """Write a new full companion outside the evidence root."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Write the ZIP outside the source root to prevent recursive inclusion")
    if output.exists():
        raise FileExistsError("Refuse to replace an existing companion")
    files = selected_files()
    records = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x") as archive:
        for path in files:
            relative, data = path.relative_to(ROOT).as_posix(), path.read_bytes()
            records.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            write_member(archive, relative, data)
        manifest = {
            "schema": "agi-alpha-legal-work-complete-companion/v1",
            "study_date": "2026-10-26",
            "hash_algorithm": "SHA-256",
            "scope": "Every distributed member except this generated manifest",
            "excluded": ["disposable caches", "transient TeX intermediates", "separate replay directories"],
            "original_raw_outputs_included": True,
            "historical_failed_attempts_included": True,
            "case_annotations_released_after_prediction_seals": True,
            "files": records,
        }
        write_member(archive, "MANIFEST.sha256.json", (json.dumps(manifest, indent=2) + "\n").encode())
    print(
        json.dumps(
            {
                "output": str(output),
                "file_count_excluding_manifest": len(records),
                "uncompressed_bytes": sum(int(row["bytes"]) for row in records),
                "archive_bytes": output.stat().st_size,
                "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
