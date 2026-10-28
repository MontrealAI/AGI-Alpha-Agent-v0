# SPDX-License-Identifier: Apache-2.0
"""Package all study evidence; exclude only caches and publication intermediates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "AGI_ALPHA_FLYWHEEL_COMPANION_v1.zip"
MANIFEST = ROOT / "MANIFEST.sha256"
EXCLUDED_PARTS = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
EXCLUDED_NAMES = {ARCHIVE.name, MANIFEST.name, "PACKAGE_RECEIPT.json", "PUBLICATION_RECEIPT.json"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if MANIFEST.exists():
        required_paths = [line.split("  ", 1)[1] for line in MANIFEST.read_text().splitlines() if line]
        missing = [path for path in required_paths if not (ROOT / path).is_file() or (ROOT / path).is_symlink()]
        if missing:
            raise SystemExit(
                f"Cannot repackage: {len(missing)} existing manifest members are absent. "
                "Extract the full companion into a new directory first; "
                "the archive, manifest and receipt have not been changed."
            )
    elif ARCHIVE.exists():
        raise SystemExit(
            "Cannot repackage an existing archive without its manifest. "
            "Extract the full companion into a new directory first."
        )
    files = sorted(
        p for p in ROOT.rglob("*")
        if p.is_file() and not p.is_symlink()
        and not (set(p.relative_to(ROOT).parts) & EXCLUDED_PARTS)
        and p.name not in EXCLUDED_NAMES
        and p.suffix not in {".pyc", ".aux", ".toc", ".out"}
        and p.relative_to(ROOT).as_posix() != "publication/body.html"
        and not ("publication_qa" in p.parts and p.suffix == ".png")
    )
    hashes = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in files}
    MANIFEST.write_text("".join(f"{sha}  {path}\n" for path, sha in hashes.items()))
    files.append(MANIFEST)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_LZMA) as archive:
        for p in files:
            info = zipfile.ZipInfo("possibility-engine-v1/" + p.relative_to(ROOT).as_posix(), (2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_LZMA
            info.external_attr = 0o100644 << 16
            archive.writestr(info, p.read_bytes())
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        for path, sha in hashes.items():
            assert digest(archive.read("possibility-engine-v1/" + path)) == sha, path
        assert archive.read("possibility-engine-v1/MANIFEST.sha256") == MANIFEST.read_bytes()
    frozen = json.loads((ROOT / "FREEZE.json").read_text())["files"]
    assert all(hashes[path] == sha for path, sha in frozen.items())
    receipt = {
        "archive": ARCHIVE.name, "archive_sha256": digest(ARCHIVE.read_bytes()),
        "archive_bytes": ARCHIVE.stat().st_size, "entries": len(files),
        "manifest_sha256": digest(MANIFEST.read_bytes()), "content_bytes": sum(p.stat().st_size for p in files),
        "crc_and_all_entry_hashes_verified": True, "frozen_identities_preserved": len(frozen),
        "compression": "ZIP LZMA; extract using Python zipfile or a compatible archive utility.",
        "excluded": "Caches, symlinks, publication auxiliaries, body.html, reproducible positive visual-QA PNGs, package self/receipts. Exact PDFs, QA receipts and all raw science/economic/failure evidence are retained.",
        "scope": "Complete study evidence. Packaging is not repository release qualification.",
    }
    (ROOT / "PACKAGE_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
