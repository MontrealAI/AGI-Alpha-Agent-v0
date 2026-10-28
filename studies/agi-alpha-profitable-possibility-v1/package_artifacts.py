# SPDX-License-Identifier: Apache-2.0
"""Build a complete, byte-verified research archive without transient build files.

Run after the manuscript is compiled and results/local_verification.json exists.
The ZIP includes original and gzip ledgers; GitHub stores only the large gzip
copies outside the ZIP. No remote action is performed by this script.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "publication/AGI_ALPHA_Profitable_Possibility_Engine_Reproducibility.zip"
MANIFEST = ROOT / "MANIFEST.sha256"
CHECKSUM = ARCHIVE.with_suffix(".zip.sha256")


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if not path.is_file() or path in {ARCHIVE, MANIFEST, CHECKSUM}:
        return False
    if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
        return False
    if relative.parts[0] == "publication" and path.suffix in {
        ".aux", ".log", ".out", ".toc", ".xdv", ".fls", ".fdb_latexmk", ".synctex.gz"
    }:
        return False
    return True


def main() -> None:
    required = [ROOT / "results/local_verification.json",
                ROOT / "publication/AGI_ALPHA_Profitable_Possibility_Engine.pdf"]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    verification = json.loads(required[0].read_text())
    if hashlib.sha256(required[1].read_bytes()).hexdigest() != verification["pdf"]["sha256"]:
        raise ValueError("The PDF differs from its recorded inspection; inspect this version before packaging")
    files = sorted(path for path in ROOT.rglob("*") if included(path))
    digests = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in files}
    MANIFEST.write_text("".join(f"{digest}  {name}\n" for name, digest in digests.items()))
    files.append(MANIFEST)
    prefix = "agi-alpha-profitable-possibility-v1/"
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            name = prefix + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=9)
    with zipfile.ZipFile(ARCHIVE) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("Archive CRC check failed")
        for name, digest in digests.items():
            if hashlib.sha256(bundle.read(prefix + name)).hexdigest() != digest:
                raise ValueError(f"Archive bytes changed: {name}")
    archive_digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    CHECKSUM.write_text(f"{archive_digest}  {ARCHIVE.name}\n")
    print(json.dumps({"archive": str(ARCHIVE), "files": len(files),
                      "bytes": ARCHIVE.stat().st_size, "sha256": archive_digest,
                      "all_manifest_entries_verified_inside_zip": True}, indent=2))


if __name__ == "__main__":
    main()
