# SPDX-License-Identifier: Apache-2.0
"""Reject stale public release bytes and unsafe flagship source inventories."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any
from unittest import mock

from scripts import validate_successor_alpha as validation
from scripts.validate_successor_alpha import flagship_url, manifest_data, sha256, verify_packaged, verify_received


class FlagshipValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="successor-alpha-validation-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / "site"
        self.destination = self.site / "successor/alpha"
        self.destination.mkdir(parents=True)
        self.source = self.root / "source.mjs"
        self.source.write_bytes(b"export const version=1;\n")
        self.page = b"<!doctype html><html lang=en><title>Exact release</title></html>"
        self.manifest: dict[str, Any] = {
            "schema": "successor-alpha-source/v1",
            "sources": {"source.mjs": sha256(self.source.read_bytes())},
            "engineSourceHash": "1" * 64,
            "pageSha256": sha256(self.page),
        }
        self.write_package()

    def write_package(self) -> None:
        (self.destination / "index.html").write_bytes(self.page)
        (self.destination / "sources.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_exact_package_and_public_bytes_pass(self) -> None:
        expected = verify_packaged(self.site, self.root)
        self.assertEqual(expected["sourcesChecked"], 1)
        self.assertEqual(expected["pageSha256"], sha256(self.page))
        verify_received(self.page, (self.destination / "sources.json").read_bytes(), expected)

    def test_self_consistent_old_public_release_is_rejected(self) -> None:
        expected = verify_packaged(self.site, self.root)
        old_page = b"<!doctype html><title>Old release</title>"
        old_manifest = {**self.manifest, "pageSha256": sha256(old_page)}
        with self.assertRaisesRegex(ValueError, "exact packaged release bytes"):
            verify_received(old_page, json.dumps(old_manifest).encode(), expected)

    def test_changed_public_page_and_manifest_are_rejected(self) -> None:
        expected = verify_packaged(self.site, self.root)
        raw_manifest = (self.destination / "sources.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "advertised source identity"):
            verify_received(self.page + b" ", raw_manifest, expected)
        with self.assertRaisesRegex(ValueError, "exact packaged release bytes"):
            verify_received(self.page, json.dumps(self.manifest, indent=2).encode(), expected)

    def test_changed_checkout_source_or_package_page_is_rejected(self) -> None:
        self.source.write_text("export const version=2;\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from checkout"):
            verify_packaged(self.site, self.root)
        self.manifest["sources"]["source.mjs"] = sha256(self.source.read_bytes())
        self.write_package()
        (self.destination / "index.html").write_bytes(self.page + b" ")
        with self.assertRaisesRegex(ValueError, "differs from its source manifest"):
            verify_packaged(self.site, self.root)

    def test_source_inventory_cannot_escape_repository(self) -> None:
        for name in ("../outside", "/absolute", "nested/../source.mjs", "nested\\source.mjs"):
            manifest = {**self.manifest, "sources": {name: "1" * 64}}
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "inside the repository"):
                manifest_data(json.dumps(manifest).encode())

    def test_public_url_is_exact_https_without_credentials_or_queries(self) -> None:
        base = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
        exact = base + "successor/alpha/"
        self.assertEqual(flagship_url(base), exact)
        self.assertEqual(flagship_url(exact), exact)
        self.assertEqual(flagship_url(exact + "index.html"), exact)
        self.assertEqual(flagship_url(exact.rstrip("/")), exact)
        for value in (
            base.replace("https:", "http:"),
            "https://user:secret@example.com/",
            base + "?old=1",
            base + "#old",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                flagship_url(value)

    def test_relative_cli_paths_support_portable_download_file_uris(self) -> None:
        """Exercise CLI paths through the same loaded-module/download boundary as release CI."""
        browser_module = self.root / "tests/browser/test_successor_alpha_browser.py"
        browser_module.parent.mkdir(parents=True)
        browser_module.write_text(
            "def run_acceptance(entry, output, *, expected_page_sha256=None):\n"
            "    output.mkdir(parents=True, exist_ok=True)\n"
            "    portable = output / 'portable.html'\n"
            "    portable.write_text('<title>Retained workspace</title>', encoding='utf-8')\n"
            "    return {'passed': True, 'entryUrl': entry, 'checks': [], 'portableUri': portable.as_uri()}\n",
            encoding="utf-8",
        )
        axe = self.root / "axe.min.js"
        axe.write_text("/* installed accessibility auditor */", encoding="utf-8")
        expected = verify_packaged(self.site, self.root)
        identity = {
            key: expected[key] for key in ("pageSha256", "manifestSha256", "engineSourceHash", "sourcesChecked")
        }
        previous_cwd = Path.cwd()
        self.addCleanup(os.chdir, previous_cwd)
        os.chdir(self.root)
        with (
            mock.patch.object(validation, "ROOT", self.root),
            mock.patch.object(validation, "checkout_identity", return_value=("1" * 40, "1.34.0")),
            mock.patch.object(validation, "verify_packaged", side_effect=lambda site: verify_packaged(site, self.root)),
            mock.patch("scripts.successor_alpha_evidence.asset_identity", return_value=identity),
            mock.patch("scripts.successor_alpha_evidence.verify_report"),
            mock.patch.dict(os.environ),
            mock.patch(
                "sys.argv",
                [
                    "validate_successor_alpha",
                    "--site",
                    "site",
                    "--output",
                    "evidence/alpha",
                    "--axe-script",
                    "axe.min.js",
                ],
            ),
            redirect_stdout(StringIO()),
        ):
            validation.main()
            self.assertEqual(os.environ["AXE_SCRIPT"], str(axe))
            direct = validation.browser_acceptance((self.destination / "index.html").as_uri(), Path("direct-browser"))
            self.assertEqual(direct["portableUri"], (self.root / "direct-browser/portable.html").as_uri())
        report = json.loads((self.root / "evidence/alpha/report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["origin"], (self.destination / "index.html").as_uri())
        self.assertEqual(
            report["journey"]["portableUri"], (self.root / "evidence/alpha/browser/portable.html").as_uri()
        )


if __name__ == "__main__":
    unittest.main()
