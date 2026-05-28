# SPDX-License-Identifier: Apache-2.0
"""Ensure service-worker.js is present in the built docs."""
from pathlib import Path
import re

DOCS_DIR = Path("docs/alpha_agi_insight_v1")


def test_docs_service_worker_present() -> None:
    html = (DOCS_DIR / "index.html").read_text()
    assert (DOCS_DIR / "service-worker.js").is_file()
    # Service worker bootstrapping now lives in bootstrap.js while index.html
    # carries the SW hash marker consumed during registration.
    assert re.search(r"bootstrap\.js", html)
    assert "SW_HASH" in html
