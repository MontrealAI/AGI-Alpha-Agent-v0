# SPDX-License-Identifier: Apache-2.0
"""Restore only manifest-selected NIST source members from pinned archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ARCHIVES = {
    "nist_box_mtc.zip": (
        "https://data.nist.gov/od/ds/73AE20D288CF02F1E05324570681502B1955/mtc.zip",
        "6bc4693f4b072116329decb0d07ac126eaaac86aa7c09e1276942279fbdb567c",
    ),
    "qif-ontology-dataset-V2.zip": (
        "https://data.nist.gov/od/ds/mds2-2146/qif-ontology-dataset-V2.zip",
        "9ae303335274645f14d8ceacf56f8defd174271fd645308905f0395d82ef1085",
    ),
}


def sha(path: Path) -> str:
    """Hash a large file incrementally."""
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    """Copy exact explicit members, never an archive-controlled destination."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "protected" / "input_manifest.json").read_text())
    destination = root / "protected" / "inputs"
    destination.mkdir(parents=True, exist_ok=True)
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for name, (url, expected_hash) in ARCHIVES.items():
        archive_path = args.archive_dir / name
        if not archive_path.exists():
            if not args.download:
                raise FileNotFoundError("Supply pinned archive or opt in with --download: " + str(archive_path))
            temporary = archive_path.with_suffix(".partial")
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open("xb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            if sha(temporary) != expected_hash:
                raise ValueError("archive download hash mismatch")
            temporary.rename(archive_path)
        if archive_path.is_symlink() or sha(archive_path) != expected_hash:
            raise ValueError("archive identity mismatch: " + name)
        with zipfile.ZipFile(archive_path) as archive:
            for item in manifest:
                if item["archive"] != name:
                    continue
                filename = item["file"]
                if Path(filename).name != filename:
                    raise ValueError("destination must be a plain filename")
                data = archive.read(item["member"])
                if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                    raise ValueError("source member identity mismatch")
                target = destination / filename
                if target.is_symlink() or (target.exists() and target.read_bytes() != data):
                    raise ValueError("refuse changed or linked destination")
                target.write_bytes(data)
                count += 1
    print(json.dumps({"verified_members": count, "original_source_mutations": 0}))


if __name__ == "__main__":
    main()
