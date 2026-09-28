# SPDX-License-Identifier: Apache-2.0
"""Tests for generate_gallery_html.py."""
from pathlib import Path

from scripts import generate_demo_docs as gdd
from scripts import generate_gallery_html as ggh


def test_release_updates_local_module_worker_and_data_urls(tmp_path):
    assets = tmp_path / "assets" / "workspace"
    assets.mkdir(parents=True)
    module = assets / "workbench.mjs"
    module.write_text(
        'import { calculate } from "../shared/engine.mjs?v=1.14.0";\n'
        "new Worker(new URL('./worker.mjs?v=1.14.0', import.meta.url));\n"
        'fetch(new URL("./scenarios.json?v=1.14.0", import.meta.url));\n'
        'const external = "https://example.com/engine.mjs?v=1.14.0";\n'
    )
    ggh.version_application_assets(tmp_path, "1.15.0")
    expected = (
        'import { calculate } from "../shared/engine.mjs?v=1.15.0";\n'
        "new Worker(new URL('./worker.mjs?v=1.15.0', import.meta.url));\n"
        'fetch(new URL("./scenarios.json?v=1.15.0", import.meta.url));\n'
        'const external = "https://example.com/engine.mjs?v=1.14.0";\n'
    )
    assert module.read_text() == expected
    ggh.version_application_assets(tmp_path, "1.15.0")
    assert module.read_text() == expected
    ggh.version_application_assets(tmp_path, "1.16.0")
    assert module.read_text() == expected.replace("v=1.15.0", "v=1.16.0")


def test_gallery_html(tmp_path, monkeypatch):
    repo = tmp_path
    demos = repo / "alpha_factory_v1" / "demos" / "demo_b"
    demos.mkdir(parents=True)
    (demos / "README.md").write_text("# Demo B\nText", encoding="utf-8")
    assets = repo / "docs" / "demo_b" / "assets"
    assets.mkdir(parents=True)
    (assets / "preview.png").write_text("data", encoding="utf-8")
    docs_demos = repo / "docs" / "demos"

    # generate docs
    monkeypatch.setattr(gdd, "REPO_ROOT", repo)
    monkeypatch.setattr(gdd, "DEMOS_DIR", repo / "alpha_factory_v1" / "demos")
    monkeypatch.setattr(gdd, "DOCS_DIR", docs_demos)
    gdd.generate_docs()

    # build gallery
    monkeypatch.setattr(ggh, "REPO_ROOT", repo)
    monkeypatch.setattr(ggh, "DEMOS_DIR", docs_demos)
    gallery = repo / "docs" / "gallery.html"
    monkeypatch.setattr(ggh, "GALLERY_FILE", gallery)
    index_file = repo / "docs" / "index.html"
    monkeypatch.setattr(ggh, "INDEX_FILE", index_file)

    html_text = ggh.build_html(ggh.collect_entries())
    gallery.write_text(html_text, encoding="utf-8")

    out = gallery.read_text(encoding="utf-8")
    assert "Demo B" in out
    assert "demo_b/assets/preview.png" in out
    assert 'href="demos/demo_b/"' in out
