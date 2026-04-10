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
    if not (insight_dist / "index.html").exists() or not (insight_dist / "service-worker.js").exists():
        pytest.skip("Insight dist assets are missing")
    html = (insight_dist / "index.html").read_text()
    match = re.search(r"SW_HASH\s*=\s*['\"](sha384-[^'\"]+)['\"]", html)
    assert match, "SW_HASH missing"
    expected = sha384(insight_dist / "service-worker.js")
    assert match.group(1) == expected
