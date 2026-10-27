# SPDX-License-Identifier: Apache-2.0
"""Create a deterministic complete study archive without modifying recorded evidence."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = "DISTRIBUTION_MANIFEST.json"
ARCHIVE = "AGI_ALPHA_FLYWHEEL_microscopy_v1.zip"


def included(path: Path) -> bool:
    """Select source, licensed data, evidence and final publication assets."""
    relative = path.relative_to(ROOT)
    parts = relative.parts
    if any(part in {"__pycache__", ".mypy_cache", ".ruff_cache"} for part in parts):
        return False
    if parts[0] == "distribution" or relative.as_posix() in {
        MANIFEST,
        "publication/readback.json",
        "publication/submission.json",
    }:
        return False
    if parts[:2] == ("paper", "qa"):
        return False
    if parts[0] == "paper" and path.suffix in {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk"}:
        return path.name == "build.log"
    if parts[0] == "data" and path.suffix == ".npy":
        return False
    return path.is_file()


def main() -> None:
    """Hash and package every selected regular file with fixed ZIP metadata."""
    paths = sorted(p for p in ROOT.rglob("*") if included(p))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Distribution requires ordinary files, not symbolic links")
    files = {
        str(p.relative_to(ROOT)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
        for p in paths
    }
    manifest = {
        "edition": "agi-alpha-microscopy-transfer/1.0.0",
        "source_base": "47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4",
        "scope": "Complete study source, evidence and publication capture; later public-readback receipts excluded.",
        "array_distribution": "Three public arrays are lossless gzip streams; reproduce.py verifies and materializes exact original bytes.",
        "files": files,
    }
    manifest_path = ROOT / MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output = ROOT / "distribution"
    output.mkdir(exist_ok=True)
    archive = output / ARCHIVE
    prefix = "agi-alpha-microscopy-transfer-v1/"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted([*paths, manifest_path]):
            info = zipfile.ZipInfo(prefix + str(path.relative_to(ROOT)), (2026, 10, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("Archive CRC verification failed")
        for relative, record in files.items():
            if hashlib.sha256(bundle.read(prefix + relative)).hexdigest() != record["sha256"]:
                raise ValueError(f"Archive source mismatch: {relative}")
    print(
        json.dumps(
            {
                "archive": str(archive),
                "files": len(files) + 1,
                "bytes": archive.stat().st_size,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "verification": "all member hashes and CRCs match",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
