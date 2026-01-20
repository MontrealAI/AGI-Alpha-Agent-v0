# SPDX-License-Identifier: Apache-2.0
"""Verify integrity attribute for the service worker registration script."""
from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import re


def sha384(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def test_service_worker_integrity(insight_dist: Path) -> None:
    html = (insight_dist / "index.html").read_text()
    match = re.search(r"const SW_HASH = ['\"]([^'\"]+)['\"]", html)
    assert match, "SW_HASH missing from index.html"
    expected = sha384(insight_dist / "service-worker.js")
    assert match.group(1) == expected
