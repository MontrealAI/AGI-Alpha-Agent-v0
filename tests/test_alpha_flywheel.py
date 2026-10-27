# SPDX-License-Identifier: Apache-2.0
"""Protect Flywheel publication identities and the canonical generator boundary."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.generate_alpha_flywheel import build
from scripts.validate_alpha_flywheel import (
    CANONICAL_SOURCES,
    flagship_url,
    manifest_data,
    sha256,
    verify_csp,
    verify_packaged,
    verify_received,
)

ROOT = Path(__file__).resolve().parents[1]


def page_bytes(script: str = "document.body.dataset.ready='yes';", style: str = "body{color:#111}") -> bytes:
    script_hash = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    style_hash = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    return (
        "<!doctype html><html lang=en><head><title>Exact Flywheel</title>"
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        f"script-src 'sha256-{script_hash}'; style-src 'sha256-{style_hash}'; "
        "connect-src 'none'; form-action 'none'\">"
        f"<style>{style}</style></head><body><script>{script}</script></body></html>"
    ).encode()


class FlywheelSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="alpha-flywheel-source-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in CANONICAL_SOURCES:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        build(self.root)
        self.site = self.root / "docs"
        self.destination = self.site / "flywheel"
        self.source = self.root / "examples/alpha-flywheel/engine.mjs"
        self.original_source = self.source.read_bytes()
        self.page = (self.destination / "index.html").read_bytes()
        self.manifest = json.loads((self.destination / "sources.json").read_bytes())

    @staticmethod
    def make_manifest(page: bytes, sources: dict[str, str]) -> dict[str, Any]:
        return {
            "schema": "alpha-flywheel-source/v1",
            "sources": sources,
            "sourceHash": sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()),
            "pageSha256": sha256(page),
        }

    def write_package(self) -> None:
        (self.destination / "index.html").write_bytes(self.page)
        (self.destination / "sources.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_exact_source_package_and_served_bytes_pass(self) -> None:
        expected = verify_packaged(self.site, self.root)
        self.assertEqual(expected["sourcesChecked"], len(CANONICAL_SOURCES))
        verify_received(self.page, (self.destination / "sources.json").read_bytes(), expected)

    def test_self_consistent_historical_page_cannot_qualify_current_release(self) -> None:
        expected = verify_packaged(self.site, self.root)
        old = page_bytes("document.body.dataset.ready='old';")
        older_manifest = self.make_manifest(old, self.manifest["sources"])
        with self.assertRaisesRegex(ValueError, "exact packaged release bytes"):
            verify_received(old, json.dumps(older_manifest).encode(), expected)

    def test_manifest_reformatting_and_page_drift_fail_exact_public_identity(self) -> None:
        expected = verify_packaged(self.site, self.root)
        with self.assertRaisesRegex(ValueError, "exact packaged release bytes"):
            verify_received(self.page, json.dumps(self.manifest, indent=2).encode(), expected)
        with self.assertRaisesRegex(ValueError, "advertised identity"):
            verify_received(self.page + b" ", expected["manifest"], expected)

    def test_edited_checkout_sources_and_package_page_are_rejected(self) -> None:
        self.source.write_bytes(self.original_source + b"// changed source\n")
        with self.assertRaisesRegex(ValueError, "differs from checkout"):
            verify_packaged(self.site, self.root)
        self.source.write_bytes(self.original_source)
        (self.destination / "index.html").write_bytes(self.page + b" ")
        with self.assertRaisesRegex(ValueError, "differs from its source manifest"):
            verify_packaged(self.site, self.root)

    def test_source_inventory_is_bound_and_cannot_escape_or_include_symlinks(self) -> None:
        for name in ("../source.mjs", "/source.mjs", "nested/../source.mjs", "nested\\source.mjs", "./source.mjs"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "inside the repository"):
                manifest_data(json.dumps(self.make_manifest(self.page, {name: "1" * 64})).encode())
        changed = {**self.manifest, "sourceHash": "0" * 64}
        with self.assertRaisesRegex(ValueError, "inventory hash differs"):
            manifest_data(json.dumps(changed).encode())
        real_source = self.source.with_name("real-engine.mjs")
        self.source.rename(real_source)
        self.source.symlink_to(real_source)
        with self.assertRaisesRegex(ValueError, "cannot be a symlink"):
            verify_packaged(self.site, self.root)

    def test_rehashed_page_with_changed_script_or_style_cannot_bypass_csp(self) -> None:
        for old, new in ((b"dataset.ready='yes'", b"dataset.ready='no!'"), (b"color:#111", b"color:#222")):
            with self.subTest(old=old):
                self.page = page_bytes().replace(old, new)
                self.manifest = self.make_manifest(self.page, self.manifest["sources"])
                self.write_package()
                with self.assertRaisesRegex(ValueError, "CSP hash"):
                    verify_packaged(self.site, self.root)

    def test_remote_executable_or_enabled_connection_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "self-contained"):
            verify_csp(page_bytes().replace(b"<script>", b'<script src="https://example.com/x.js">'))
        with self.assertRaisesRegex(ValueError, "external operation"):
            verify_csp(page_bytes().replace(b"connect-src 'none'", b"connect-src https:"))

    def test_self_consistent_changed_page_and_reduced_inventory_cannot_qualify(self) -> None:
        self.page = page_bytes("document.body.dataset.ready='fabricated';")
        self.manifest = self.make_manifest(self.page, self.manifest["sources"])
        self.write_package()
        with self.assertRaisesRegex(ValueError, "trusted canonical rebuild"):
            verify_packaged(self.site, self.root)
        self.manifest = self.make_manifest(self.page, {"LICENSE": self.manifest["sources"]["LICENSE"]})
        self.write_package()
        with self.assertRaisesRegex(ValueError, "complete canonical source closure"):
            verify_packaged(self.site, self.root)

    def test_public_url_resolves_stable_route_without_credential_or_cache_bypass(self) -> None:
        base = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
        exact = base + "flywheel/"
        for source in (base, exact, exact + "index.html", exact.rstrip("/")):
            self.assertEqual(flagship_url(source), exact)
        for source in (
            base.replace("https:", "http:"),
            "https://user:password@example.com/",
            base + "?old=1",
            base + "#old",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                flagship_url(source)


class FlywheelGeneratorTests(unittest.TestCase):
    def test_rebuild_is_deterministic_csp_bound_and_preserves_existing_experiences(self) -> None:
        sources = CANONICAL_SOURCES
        with tempfile.TemporaryDirectory(prefix="alpha-flywheel-build-") as directory:
            root = Path(directory)
            for name in sources:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            preserved = root / "docs/successor/alpha/index.html"
            preserved.parent.mkdir(parents=True)
            preserved.write_bytes(b"unchanged existing flagship")
            build(root)
            expected = verify_packaged(root / "docs", root)
            before = (expected["page"], expected["manifest"])
            build(root)
            after = verify_packaged(root / "docs", root)
            self.assertEqual(before, (after["page"], after["manifest"]))
            self.assertEqual(preserved.read_bytes(), b"unchanged existing flagship")
            self.assertIn(b"PUBLIC SIMULATION", after["page"])
            self.assertIn(b"connect-src 'none'", after["page"])
            self.assertNotIn(b"{{SCRIPT}}", after["page"])
            self.assertIn("examples/successor-alpha/project.mjs", json.loads(after["manifest"])["sources"])


if __name__ == "__main__":
    unittest.main()
