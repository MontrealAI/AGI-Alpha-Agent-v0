# SPDX-License-Identifier: Apache-2.0
"""Mirrored flagship identity follows rewritten document bytes without changing implementation pins."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import mirror_demo_pages


def test_source_bound_ti_document_keeps_its_single_canonical_route(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    for name in ("transformational-intelligence", "ordinary"):
        source = docs / name
        source.mkdir(parents=True)
        (source / "index.html").write_text('<html><script>const text="../assets/example";</script></html>')
    (docs / "DISCLAIMER_SNIPPET.md").write_text("Public prototype")
    monkeypatch.setattr(mirror_demo_pages, "DOCS_DIR", docs)
    monkeypatch.setattr(mirror_demo_pages, "SUBDIR_ROOT", docs / "alpha_factory_v1/demos")
    monkeypatch.setattr(mirror_demo_pages, "REPO_ROOT", tmp_path)
    original = (docs / "transformational-intelligence/index.html").read_bytes()
    mirror_demo_pages.main()
    assert (docs / "transformational-intelligence/index.html").read_bytes() == original
    assert not (docs / "alpha_factory_v1/demos/transformational-intelligence").exists()
    assert (docs / "alpha_factory_v1/demos/ordinary/index.html").is_file()


def test_flagship_mirror_binds_rewritten_page(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    source = docs / "successor/alpha"
    source.mkdir(parents=True)
    original = '<a href="../../agent/SUCCESSOR_ALPHA/">Guide</a>'
    (source / "index.html").write_text(original)
    manifest = {
        "schema": "successor-alpha-source/v1",
        "sources": {"module.mjs": "a" * 64},
        "engineSourceHash": "b" * 64,
        "pageSha256": hashlib.sha256(original.encode()).hexdigest(),
    }
    (source / "sources.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(mirror_demo_pages, "DOCS_DIR", docs)
    target = docs / "alpha_factory_v1/demos/successor"
    mirror_demo_pages.shutil.copytree(docs / "successor", target)
    mirror_demo_pages.fix_paths(target)
    copied = target / "alpha/index.html"
    checked = json.loads(copied.with_name("sources.json").read_text())
    assert copied.read_text() != original
    assert checked["pageSha256"] == hashlib.sha256(copied.read_bytes()).hexdigest()
    assert checked["sources"] == manifest["sources"]
    assert checked["engineSourceHash"] == manifest["engineSourceHash"]
    assert json.loads((source / "sources.json").read_text()) == manifest
