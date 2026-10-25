# SPDX-License-Identifier: Apache-2.0
"""Verify two transport parts and reconstruct the unchanged canonical ZIP.

Python 3.8+; standard library only. Run beside the two .part files.
An existing identical output is retained; a conflicting output is never replaced.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

NAME = "Nova_Seeds_Abundance_v1_Source.zip"
SIZE = 15317764
SHA256 = "b8785b08bf0a7d66e50dd28a5729e25705579a8774feb55aa02427710d2dba51"
PARTS = [
    (NAME + ".part01", 8000000,
     "bc04f61b715198d3736fb1a054d768e636a6387c8c098c2b8c6bf97630d75084"),
    (NAME + ".part02", 7317764,
     "c3fb0a9db4fd23c3d7e58a9c05ce91665cc2ddd5d95a9e0beb81966f79d27b57"),
]


def identity(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=base / NAME,
                        help="fresh destination, or an already identical archive")
    output = parser.parse_args().output.absolute()
    for name, size, digest in PARTS:
        if identity(base / name) != (size, digest):
            raise ValueError("Transport part identity mismatch: " + name)

    if output.exists():
        if not output.is_file() or identity(output) != (SIZE, SHA256):
            raise FileExistsError("Refusing to overwrite conflicting output: " + str(output))
        status = "already-identical; preserved"
    else:
        created_identity = None
        try:
            # Exclusive creation prevents an overwrite even if a file appears
            # between the existence check and opening the destination.
            with output.open("xb") as destination:
                stat = os.fstat(destination.fileno())
                created_identity = (stat.st_dev, stat.st_ino)
                for name, _, _ in PARTS:
                    with (base / name).open("rb") as source:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            destination.write(block)
                destination.flush()
                os.fsync(destination.fileno())
            if identity(output) != (SIZE, SHA256):
                raise ValueError("Reconstructed archive identity mismatch")
            status = "assembled-and-verified"
        except BaseException:
            # Remove only our own incomplete reconstruction, never a file that
            # existed before this invocation or replaced it concurrently.
            if created_identity is not None:
                try:
                    stat = output.lstat()
                    if (stat.st_dev, stat.st_ino) == created_identity:
                        output.unlink()
                except FileNotFoundError:
                    pass
            raise
    print(json.dumps({"status": status, "archive": str(output),
                      "bytes": SIZE, "sha256": SHA256,
                      "verifiedParts": len(PARTS)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Assembly failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
