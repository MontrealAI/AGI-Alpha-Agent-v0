# SPDX-License-Identifier: Apache-2.0
"""Build a deterministic, hash-checked standalone research archive."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "publication" / "AGI_ALPHA_FLYWHEEL_reproducible_study.zip"
MANIFEST = ROOT / "MANIFEST.sha256"
EXCLUDED = {TARGET.name, MANIFEST.name, "PUBLICATION_RECEIPT.json"}


def files() -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and p.name not in EXCLUDED
        and p.suffix != ".pyc"
        and "__pycache__" not in p.parts
        and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
    )


def main() -> None:
    source_files = files()
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    MANIFEST.write_text("".join(f"{digest}  {name}\n" for name, digest in hashes.items()))
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted([*source_files, MANIFEST]):
            member = zipfile.ZipInfo(
                "agi-alpha-geospatial-delivery-v1/" + str(path.relative_to(ROOT)),
                date_time=(2026, 10, 27, 0, 0, 0),
            )
            # Fixed metadata normalizes archive construction; this is not a file creation timestamp.
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o100644 << 16
            archive.writestr(member, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(TARGET) as archive:
        assert archive.testzip() is None
        for name, digest in hashes.items():
            payload = archive.read("agi-alpha-geospatial-delivery-v1/" + name)
            assert hashlib.sha256(payload).hexdigest() == digest, name
    print(
        json.dumps(
            {
                "archive": str(TARGET),
                "bytes": TARGET.stat().st_size,
                "sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
                "manifest_files": len(hashes),
                "archive_members": len(hashes) + 1,
                "integrity": "all member hashes match",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
