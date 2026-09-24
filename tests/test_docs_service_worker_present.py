# SPDX-License-Identifier: Apache-2.0
"""Ensure service-worker.js is present in the built docs."""
from pathlib import Path
import re

DOCS_DIR = Path("docs/alpha_agi_insight_v1")


def test_docs_service_worker_present() -> None:
    html = (DOCS_DIR / "index.html").read_text()
    assert (DOCS_DIR / "service-worker.js").is_file()
    bootstrap = (DOCS_DIR / "bootstrap.js").read_text()
    assert re.search(r'<script[^>]+src="bootstrap.js"', html)
    assert '"service-worker.js"' in bootstrap
    assert "navigator.serviceWorker.register(SW_URL)" in bootstrap
