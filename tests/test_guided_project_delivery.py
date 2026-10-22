# SPDX-License-Identifier: Apache-2.0
"""Frozen native receiver closure and mandatory complete-journey delivery gates."""

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GuidedDelivery(unittest.TestCase):
    def test_reviewed_receivers_and_licenses_are_exact(self) -> None:
        manifest = json.loads((ROOT / "examples/successor-project/vendor/provenance.json").read_text())
        self.assertEqual(manifest["schema"], "alpha-guided-receivers-source/v1")
        self.assertEqual(set(manifest["sources"]), {"manager", "jobs", "fleet"})
        for source in manifest["sources"].values():
            self.assertRegex(source["commit"], r"^[a-f0-9]{40}$")
            self.assertEqual(source["publication"], "published-exact-source")
        tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
        for relative, identity in manifest["files"].items():
            self.assertIn(relative, tracked, "Vendored receiver source must be present in the checkout")
            self.assertTrue(relative.startswith("examples/successor-project/vendor/"))
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), identity["sha256"], relative)
        for name in ("manager", "jobs", "fleet"):
            paths = [p for p in manifest["files"] if f"/vendor/{name}/" in p]
            self.assertTrue(any(p.endswith("/LICENSE") for p in paths))
            self.assertTrue(any(p.endswith("/agijobs/LICENSE") for p in paths))
            self.assertTrue(any(p.endswith("/agijobs/provenance.json") for p in paths))
        context = (ROOT / "examples/successor-project/vendor/manager-context.mjs").read_text()
        match = re.search(r"export const CONTEXT = freezeGraph\((\{[\s\S]*\})\);", context)
        assert match is not None
        payload = json.loads(match.group(1))
        self.assertEqual(payload["sourceManifest"]["commit"], manifest["sources"]["manager"]["commit"])

    def test_complete_cycle_and_browser_are_required_release_dependencies(self) -> None:
        workflow = (ROOT / ".github/workflows/successor-mission.yml").read_text()
        for required in (
            "examples/successor-project/journey-native.test.mjs",
            "examples/successor-project/journey.test.mjs",
            "python tests/test_guided_project_delivery.py",
            "python tests/browser/test_guided_successor_browser.py",
            "GUIDED_SCREENSHOTS: ${{ github.workspace }}/discovery-screenshots/guided",
            "GUIDED_FLEET_SOURCE:",
            "ref: ${{ steps.fleet-source.outputs.commit }}",
        ):
            self.assertIn(required, workflow)
        self.assertNotIn("continue-on-error", workflow)
        release = (ROOT / ".github/workflows/agent-release.yml").read_text()
        journey = re.search(r"^  successor-journey:\n((?:    [^\n]*\n)+)", release, re.MULTILINE)
        self.assertIsNotNone(journey)
        self.assertEqual(
            set(journey.group(1).splitlines()),
            {
                "    if: ${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}",
                "    needs: [paper-scope, publication-preflight]",
                "    uses: ./.github/workflows/successor-mission.yml",
            },
        )
        self.assertIn("  paper-scope:\n    uses: ./.github/workflows/paper-scope.yml\n", release)
        package_start = release.index("  package:")
        package = release[package_start:]
        self.assertIn("successor-journey", package.split("steps:", 1)[0])

    def test_guided_page_is_source_bound_and_explicit(self) -> None:
        source = (ROOT / "docs/successor/mission/index.html").read_text()
        self.assertIn("Find your Alpha", source)
        for element in (
            "journey-route",
            "jobs-amount",
            "jobs-run",
            "fleet-export",
            "journey-export",
            "journey-import",
            "recovery-export",
            "recovery-confirm",
            "recovery-save",
        ):
            self.assertIn(f'id="{element}"', source)
        self.assertIn("connect-src 'none'", source)
        self.assertNotIn("{{", source)
        match = re.search(r"<script>([\s\S]*?)</script>", source)
        assert match is not None
        script = match.group(1)
        self.assertNotRegex(script, r"(?m)^import\s")
        self.assertIn("alpha-guided-project/v1", script)
        self.assertIn("historical-internal", script)
        self.assertIn("16_000_000", script)


if __name__ == "__main__":
    unittest.main()
