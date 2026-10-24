# SPDX-License-Identifier: Apache-2.0
"""Fetch the four preregistered public matrices without altering their bytes."""
import hashlib
import json
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    config = json.loads((ROOT / "protocol.json").read_text())
    target = ROOT / "data"
    target.mkdir(exist_ok=True)
    rows = []
    for name in config["matrices_in_order"]:
        url = f"https://sparse-files.engr.tamu.edu/MM/HB/{name}.tar.gz"
        archive = target / f"{name}.tar.gz"
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=25) as response:
                raw = response.read(10_000_001)
            if len(raw) > 10_000_000:
                raise ValueError("Matrix archive exceeds declared size cap")
            archive.write_bytes(raw)
        raw = archive.read_bytes()
        with tarfile.open(archive, "r:gz") as tar:
            member = tar.getmember(f"{name}/{name}.mtx")
            if not member.isfile() or member.size > 20_000_000:
                raise ValueError("Unexpected Matrix Market payload")
            handle = tar.extractfile(member)
            if handle is None:
                raise ValueError("Missing matrix data")
            matrix = handle.read()
        rows.append({"name": name, "group": "HB", "source": url,
                     "metadata_url": f"https://sparse.tamu.edu/HB/{name}",
                     "archive_sha256": hashlib.sha256(raw).hexdigest(),
                     "matrix_sha256": hashlib.sha256(matrix).hexdigest(),
                     "archive_bytes": len(raw), "matrix_bytes": len(matrix),
                     "license": "CC-BY-4.0", "modifications": "none"})
    (target / "manifest.json").write_text(json.dumps({"fetched_utc": datetime.now(timezone.utc).isoformat(),
        "attribution": "SuiteSparse Matrix Collection; Davis and Hu (2011); original HB metadata retained",
        "matrices": rows}, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
