# SPDX-License-Identifier: Apache-2.0
"""Verify integrity attribute for the service worker registration script."""
from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import re
import pytest


def sha384(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def test_service_worker_integrity(insight_dist: Path) -> None:
    index_file = insight_dist / "index.html"
    sw_file = insight_dist / "service-worker.js"
    if not index_file.is_file() or not sw_file.is_file():
        pytest.skip("Insight dist artifacts missing; run npm build to generate bundled assets")
    html = index_file.read_text()
    match = re.search(r"SW_HASH\s*=\s*['\"](sha384-[^'\"]+)['\"]", html)
    assert match, "SW_HASH missing"
    expected = sha384(sw_file)
    assert match.group(1) == expected
