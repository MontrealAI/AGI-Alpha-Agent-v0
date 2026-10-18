# SPDX-License-Identifier: Apache-2.0
"""Check the public read-only deployment directory against the tested source bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.url.rstrip("/") + "/deployments/2026-10-18/"
    if base != "https://montrealai.github.io/AGI-Alpha-Agent-v0/deployments/2026-10-18/":
        raise ValueError("Unexpected public deployment origin")
    files = {}
    for name in ("index.html", "manifest.json", "directory.css"):
        expected = (root / "docs/deployments/2026-10-18" / name).read_bytes()
        request = Request(base + name, headers={"Cache-Control": "no-cache"})
        with urlopen(request, timeout=30) as response:
            if response.geturl() != base + name:
                raise ValueError("Unexpected redirect")
            actual = response.read()
        if actual != expected:
            raise ValueError(f"Public deployment bytes differ: {name}")
        files[name] = hashlib.sha256(actual).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"passed": True, "origin": base, "sha256": files}, indent=2) + "\n")


if __name__ == "__main__":
    main()
