# SPDX-License-Identifier: Apache-2.0
"""Install the pinned complete Pyodide runtime used by optional gallery examples."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen


def prepare(destination: Path, archive_path: Path | None = None) -> None:
    """Verify the npm archive and each selected member before atomic replacement."""
    manifest = json.loads(Path(__file__).with_name("pyodide_gallery_manifest.json").read_text())
    if all(
        (destination / name).is_file() and hashlib.sha256((destination / name).read_bytes()).hexdigest() == checksum
        for name, checksum in manifest["files"].items()
    ):
        return
    if archive_path:
        data = archive_path.read_bytes()
    else:
        with urlopen(manifest["url"], timeout=120) as response:
            data = response.read(16 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError("Pinned Pyodide npm archive checksum mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for name, expected in manifest["files"].items():
            member = archive.getmember("package/" + name)
            if not member.isfile() or member.size > 16 * 1024 * 1024:
                raise ValueError(f"Invalid Pyodide member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"Missing Pyodide member: {name}")
            content = stream.read()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError(f"Pyodide member checksum mismatch: {name}")
            temporary = destination / (name + ".tmp")
            temporary.write_bytes(content)
            temporary.replace(destination / name)
    (destination / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("docs/assets/pyodide"))
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    prepare(args.destination, args.archive)
    print("Complete pinned Pyodide gallery runtime verified")


if __name__ == "__main__":
    main()
