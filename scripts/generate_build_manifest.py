# SPDX-License-Identifier: Apache-2.0
"""Synchronize build_assets.json checksums with fetch_assets.py."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.fetch_assets as fa


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / ("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build_assets.json")
    manifest = json.loads(manifest_path.read_text())
    checksums = manifest.get("checksums", {})
    checksums.update(fa.CHECKSUMS)
    manifest["checksums"] = {k: checksums[k] for k in sorted(checksums)}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Updated {manifest_path}")


if __name__ == "__main__":
    main()
