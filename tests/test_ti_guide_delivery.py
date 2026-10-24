# SPDX-License-Identifier: Apache-2.0
"""Keep the guide deterministic, self-contained and bound to its real sources."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GuideDeliveryTests(unittest.TestCase):
    def test_source_identity_and_reproduction(self) -> None:
        paths = [ROOT / "docs/try" / name for name in ("index.html", "sources.json")]
        before = [p.read_bytes() for p in paths]
        subprocess.run([sys.executable, "scripts/generate_ti_guide.py"], cwd=ROOT, check=True)
        self.assertEqual(before, [p.read_bytes() for p in paths])
        manifest = json.loads(before[1])
        self.assertEqual(manifest["pageSha256"], hashlib.sha256(before[0]).hexdigest())
        for path, digest in manifest["sources"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path)
        self.assertIn("examples/successor-alpha/engine.mjs", manifest["sources"])
        self.assertIn("examples/successor-alpha/research.mjs", manifest["sources"])
        self.assertFalse(any("harness" in x or "fleet" in x for x in manifest["sources"]))

    def test_csp_and_local_data_boundary(self) -> None:
        page = (ROOT / "docs/try/index.html").read_text()
        self.assertIn("connect-src 'none'", page)
        self.assertNotRegex(page, r"<(?:script|link)\b[^>]*(?:src|href)=")
        for kind in ("script", "style"):
            body = re.search(r"<" + kind + r">(.*?)</" + kind + ">", page, re.S)
            self.assertIsNotNone(body)
            digest = base64.b64encode(hashlib.sha256(body[1].encode()).digest()).decode()
            self.assertIn("sha256-" + digest, page)
        sources = json.loads((ROOT / "docs/try/sources.json").read_text())["sources"]
        code = "\n".join((ROOT / p).read_text() for p in sources if p.endswith((".mjs", ".js")))
        self.assertNotRegex(code, r"\b(?:fetch|XMLHttpRequest|WebSocket|sendBeacon|eval)\s*\(")

    def test_executable_fixtures(self) -> None:
        subprocess.run(["node", "--test", "examples/ti-guide/guide.test.mjs"], cwd=ROOT, check=True)
