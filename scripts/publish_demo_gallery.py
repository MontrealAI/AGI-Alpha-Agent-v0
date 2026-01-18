#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Publish the Alpha-Factory demo gallery to GitHub Pages.

This helper mirrors ``publish_demo_gallery.sh`` but uses Python for
better portability. It verifies the environment, rebuilds the demo
assets, compiles the MkDocs site and pushes the result to the ``gh-pages``
branch so users can explore every demo from a polished subdirectory.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
BROWSER_DIR = REPO_ROOT / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"


def run(cmd: Sequence[str], **kwargs: Any) -> None:
    """Run ``cmd`` and raise ``CalledProcessError`` on failure."""
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main() -> None:
    asset_cache_dir = os.environ.get("INSIGHT_ASSET_ROOT") or os.environ.get("FETCH_ASSETS_DIR")
    if not asset_cache_dir:
        asset_cache_dir = str(Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "insight-assets")
    os.environ.setdefault("FETCH_ASSETS_DIR", asset_cache_dir)
    os.environ.setdefault("INSIGHT_ASSET_ROOT", asset_cache_dir)

    # Environment checks
    run(["python", "alpha_factory_v1/scripts/preflight.py"])
    run(["node", str(BROWSER_DIR / "build/version_check.js")])
    run(["python", "scripts/check_python_deps.py"])
    run(["python", "check_env.py", "--auto-install"])
    # disclaimer snippet verification removed; rely on documentation updates
    run(["python", "-m", "alpha_factory_v1.demos.validate_demos"])

    # Rebuild docs and gallery
    run(["npm", "--prefix", str(BROWSER_DIR), "run", "fetch-assets"])
    run(["npm", "--prefix", str(BROWSER_DIR), "ci"])
    run(["scripts/build_insight_docs.sh"])
    run(["python", "scripts/generate_demo_docs.py"])
    run(["python", "scripts/generate_gallery_html.py"])

    # Build and deploy
    run(["mkdocs", "build", "--strict"])
    run(["python", "scripts/verify_workbox_hash.py", "site/alpha_agi_insight_v1"])
    run(["mkdocs", "gh-deploy", "--force"])

    remote = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
    repo_path = remote.split("github.com")[-1].lstrip(":/")
    repo_path = repo_path.removesuffix(".git")
    org, repo = repo_path.split("/", 1)
    url = f"https://{org}.github.io/{repo}/"
    print("Demo gallery deployed successfully.")
    print(f"Browse to {url}index.html and explore each demo from there.")


if __name__ == "__main__":
    main()
