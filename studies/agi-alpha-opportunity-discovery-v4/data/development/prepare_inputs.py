# SPDX-License-Identifier: Apache-2.0
"""Expand only the four hash-listed public Plate inputs for development reproduction."""

from pathlib import Path
import hashlib
import json
import zipfile


def main() -> None:
    """Extract known members and verify their original byte identities."""
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / "input_manifest.json").read_text())
    destination = base / "inputs"
    destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(base / "plate_public_inputs.zip") as archive:
        for item in manifest:
            name = item["file"]
            if Path(name).name != name:
                raise ValueError("Only flat, manifest-listed source names are accepted")
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"Source digest mismatch: {name}")
            (destination / name).write_bytes(data)
    print(f"Verified {len(manifest)} unchanged public Plate artifacts in {destination}")


if __name__ == "__main__":
    main()
