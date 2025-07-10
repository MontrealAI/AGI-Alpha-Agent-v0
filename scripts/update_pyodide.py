#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Update Pyodide runtime checksums in fetch_assets.py."""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict

import requests  # type: ignore


def fetch(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def sha384_b64(data: bytes) -> str:
    digest = hashlib.sha384(data).digest()
    return base64.b64encode(digest).decode()


def update_pyodide(version: str) -> None:
    base_url = f"https://cdn.jsdelivr.net/pyodide/v{version}/full"
    root = Path(__file__).resolve().parent
    fetch_assets = root / "fetch_assets.py"
    text = fetch_assets.read_text()

    text = re.sub(r"DEFAULT_PYODIDE_BASE_URL = \"[^\"]+\"", f'DEFAULT_PYODIDE_BASE_URL = "{base_url}"', text)
    text = re.sub(r"# Updated to Pyodide [^\n]+", f"# Updated to Pyodide {version}", text)

    files = ["pyodide.js", "pyodide.asm.wasm"]
    checksums: Dict[str, str] = {}
    for name in files:
        data = fetch(f"{base_url}/{name}")
        checksums[name] = f"sha384-{sha384_b64(data)}"

    for name, checksum in checksums.items():
        pattern = rf'"{name}":\s*"[^"]+"'
        text = re.sub(pattern, f'"{name}": "{checksum}"', text)

    fetch_assets.write_text(text)

    subprocess.run([sys.executable, str(root / "generate_build_manifest.py")], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Pyodide version string, e.g. 0.28.0")
    args = parser.parse_args()
    update_pyodide(args.version)


if __name__ == "__main__":
    main()
