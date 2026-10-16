# SPDX-License-Identifier: Apache-2.0
"""Project source identity, CSP and mandatory CI delivery checks (stdlib only)."""
from pathlib import Path
import base64
import hashlib
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectDelivery(unittest.TestCase):
    def test_exact_source_manifest_and_csp(self):
        manifest = json.loads((ROOT / "docs/successor/mission/sources.json").read_text())
        for name, expected in manifest["sources"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(
            hashlib.sha256(json.dumps(manifest["sources"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            manifest["sourceHash"],
        )
        html = (ROOT / "docs/successor/mission/index.html").read_text()
        for tag in ("script", "style"):
            content = re.search(rf"<{tag}>([\s\S]*?)</{tag}>", html).group(1)
            self.assertIn("sha256-" + base64.b64encode(hashlib.sha256(content.encode()).digest()).decode(), html)
        self.assertIn("connect-src 'none'", html)

    def test_browser_job_and_screenshots_are_mandatory(self):
        workflow = (ROOT / ".github/workflows/successor-mission.yml").read_text()
        self.assertIn("node --test examples/successor-project/engine.test.mjs", workflow)
        self.assertIn("python tests/test_successor_project_delivery.py", workflow)
        self.assertIn("python tests/browser/test_successor_project_browser.py", workflow)
        self.assertIn("PROJECT_SCREENSHOTS: ${{ github.workspace }}/discovery-screenshots/project", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertNotIn("continue-on-error", workflow)
        browser = (ROOT / "tests/browser/test_successor_project_browser.py").read_text()
        self.assertIn('len(list(screenshots.glob("*.png"))) == 5', browser)
        self.assertNotIn("wait_for_function", browser)
        self.assertIn("expect(page.locator", browser)
        self.assertIn('first["cycles"][0]["discovery"]["bytes"].encode() == discovery_bytes', browser)

    def test_native_validator_pins_are_unchanged(self):
        pins = {
            "examples/alpha-discovery/engine.mjs": "452a25348a3209a99fef9eecbd94bdbfafdc9595777dc5d2bd2a70e9245ea850",
            "examples/successor-workbench/mission-record.mjs": (
                "e80338a4c89905e33b6856189080fd22593a7208b078ddf49a58b296b459ba0f"
            ),
        }
        for path, expected in pins.items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
