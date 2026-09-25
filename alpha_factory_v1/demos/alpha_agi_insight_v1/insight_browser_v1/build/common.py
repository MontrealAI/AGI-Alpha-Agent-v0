# SPDX-License-Identifier: Apache-2.0
"""Shared build helpers for the Insight browser."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha384(path: Path) -> str:
    """Return the SHA-384 digest of ``path`` in SRI format."""
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def check_gzip_size(path: Path, max_bytes: int = 5 * 1024 * 1024) -> None:
    """Exit if gzip-compressed ``path`` exceeds ``max_bytes``."""
    compressed = gzip.compress(path.read_bytes())
    if len(compressed) > max_bytes:
        sys.exit(f"gzip size {len(compressed)} bytes exceeds limit")


from typing import Any


def generate_service_worker(root: Path, dist_dir: Path, manifest: dict[str, Any]) -> None:
    """Use the shared bundled Workbox pipeline; build failures remain fatal."""
    root = root.resolve()
    dist_dir = dist_dir.resolve()
    version = json.loads((root / "package.json").read_text())["version"]
    script = (
        "import {generateServiceWorker} from './build/common.js';"
        f"await generateServiceWorker({json.dumps(str(dist_dir))},"
        f"{json.dumps(manifest)},{json.dumps(version)});"
    )
    subprocess.run(["node", "--input-type=module", "-e", script], cwd=root, check=True)
