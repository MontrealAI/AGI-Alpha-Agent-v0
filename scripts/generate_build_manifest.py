# SPDX-License-Identifier: Apache-2.0
"""Synchronize build_assets.json checksums with fetch_assets.py."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import scripts.fetch_assets as fa  # noqa: E402


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / ("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build_assets.json")
    manifest = json.loads(manifest_path.read_text())
    manifest.pop("checksums", None)
    manifest["checksums"] = {k: fa.CHECKSUMS[k] for k in sorted(fa.CHECKSUMS)}
    new_content = json.dumps(manifest, indent=2) + "\n"
    if manifest_path.read_text() != new_content:
        manifest_path.write_text(new_content)
        print(f"Updated {manifest_path}")
    else:
        print(f"{manifest_path} already up to date")


if __name__ == "__main__":
    main()
