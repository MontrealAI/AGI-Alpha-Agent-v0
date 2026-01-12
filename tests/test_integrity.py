# SPDX-License-Identifier: Apache-2.0
"""Verify wasm assets are real."""

from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import json
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
BROWSER = ROOT.joinpath(
    "alpha_factory_v1",
    "demos",
    "alpha_agi_insight_v1",
    "insight_browser_v1",
)


def asset_files() -> list[Path]:
    paths = []
    for sub in ("wasm", "wasm_llm"):
        root = BROWSER / sub
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file():
                    paths.append(p)
    return paths


def test_no_placeholder() -> None:
    files = asset_files()
    assert files, "no wasm assets found"
    for path in files:
        data = path.read_bytes()
        if b"placeholder" in data.lower():
            pytest.skip(f"placeholder found in {path}")


def test_workbox_sri() -> None:
    index_file = BROWSER / "dist/index.html"
    if not index_file.is_file():
        pytest.skip("dist/index.html missing; run npm build to generate bundled assets")
    html = index_file.read_text()
    pattern = r'<script[^>]*src=["\']lib/workbox-sw.js["\'][^>]*>'
    match = re.search(pattern, html)
    if not match:
        pytest.skip("lib/workbox-sw.js script tag missing")
        return
    tag = match.group(0)
    integrity = re.search(r'integrity=["\']([^"\']+)["\']', tag)
    assert integrity, "integrity attribute missing"
    sri = integrity.group(1)
    assets = json.loads((BROWSER / "build_assets.json").read_text())
    expected = assets["checksums"]["lib/workbox-sw.js"]
    assert sri == expected and "placeholder" not in sri.lower(), "integrity mismatch"  # noqa: E501


def test_csp_meta_tag() -> None:
    index_file = BROWSER / "dist/index.html"
    if not index_file.is_file():
        pytest.skip("dist/index.html missing; run npm build to generate bundled assets")
    html = index_file.read_text()
    pattern = r'<meta[^>]*http-equiv=["\']Content-Security-Policy["\'][^>]*>'
    match = re.search(pattern, html)
    assert match, "Content Security Policy meta tag missing"
    tag = match.group(0)
    content = re.search(r'content="([^"]+)"', tag)
    assert content, "content attribute missing"
    policy = content.group(1)
    expected_part = "script-src 'self' 'wasm-unsafe-eval'"
    assert expected_part in policy, "CSP missing script-src 'self' 'wasm-unsafe-eval'"  # noqa: E501


def test_unbundled_sri() -> None:
    index_file = BROWSER / "index.html"
    html = index_file.read_text()
    assets = {
        "d3.v7.min.js": BROWSER / "d3.v7.min.js",
        "bundle.esm.min.js": BROWSER / "lib/bundle.esm.min.js",
        "pyodide.js": BROWSER / "lib/pyodide.js",
    }
    for name, path in assets.items():
        pattern = rf'<script[^>]*src=["\']{name}["\'][^>]*>'
        match = re.search(pattern, html)
        assert match, f"{name} script tag missing"
        tag = match.group(0)
        integrity = re.search(r'integrity=["\']([^"\']+)["\']', tag)
        assert integrity, f"integrity attribute missing for {name}"
        sri = integrity.group(1)
        digest = hashlib.sha384(path.read_bytes()).digest()
        expected = base64.b64encode(digest).decode()
        assert sri.endswith(expected), f"integrity mismatch for {name}"
