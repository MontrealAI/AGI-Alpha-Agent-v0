#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Download the pinned browser ONNX baseline and verify every file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def download(output: Path) -> None:
    manifest = json.loads(Path(__file__).with_name("browser_model_manifest.json").read_text())
    for name, expected in manifest["files"].items():
        target = output / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source_name = manifest.get("sources", {}).get(name, name)
        url = f"https://huggingface.co/{manifest['repository']}/resolve/{manifest['revision']}/{source_name}"
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temp = Path(stream.name)
            try:
                digest = hashlib.sha256()
                with urlopen(url, timeout=120) as response:
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        stream.write(chunk)
                stream.close()
                if digest.hexdigest() != expected:
                    raise ValueError(f"Model checksum mismatch: {name}")
                temp.replace(target)
            finally:
                temp.unlink(missing_ok=True)
        print(f"Verified {name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    download(args.output)


if __name__ == "__main__":
    main()
