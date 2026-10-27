# SPDX-License-Identifier: Apache-2.0
"""Create deterministic research/capability archives and an exact byte manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TRANSIENT_SUFFIXES = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".xdv", ".pyc"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and not path.is_symlink()
        and not any(part.startswith(".") or part == "__pycache__" for part in relative.parts)
        and path.suffix not in TRANSIENT_SUFFIXES
    )


def metadata(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
        "mode": "100644",
    }


def archive(output: Path, files: list[Path], prefix: str, relative_root: Path) -> None:
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in files:
            name = prefix + "/" + path.relative_to(relative_root).as_posix()
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 27, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            handle.writestr(entry, path.read_bytes(), compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("archive output must be outside the preserved study")
    files = sorted(path for path in ROOT.rglob("*") if included(path) and path.name != "ARTIFACT_MANIFEST.json")
    manifest = {
        "schema": "agialpha.research-artifacts.v1",
        "source_base": "47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4",
        "excludes": ["this self-referential manifest", "build logs/cache/auxiliary files", "symlinks"],
        "files": {path.relative_to(ROOT).as_posix(): metadata(path) for path in files},
    }
    manifest_path = ROOT / "ARTIFACT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if args.manifest_only:
        print(json.dumps({"files": len(files), "manifest": str(manifest_path)}))
        return
    output.mkdir(parents=True, exist_ok=False)
    archive(output / "agi-alpha-flywheel-research-package.zip", sorted([*files, manifest_path]), ROOT.name, ROOT)
    capability_files = sorted(path for path in (ROOT / "capability").iterdir() if included(path))
    archive(
        output / "original-obligation-capability-v1.zip",
        capability_files,
        "original-obligation-capability-v1",
        ROOT / "capability",
    )
    archive_report = {path.name: metadata(path) for path in sorted(output.iterdir()) if path.is_file()}
    (output / "DOWNLOADS.json").write_text(json.dumps(archive_report, indent=2) + "\n")
    print(json.dumps(archive_report, indent=2))


if __name__ == "__main__":
    main()
