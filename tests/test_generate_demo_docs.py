# SPDX-License-Identifier: Apache-2.0
"""Tests for generate_demo_docs.py."""
from pathlib import Path

from scripts import generate_demo_docs as gdd


def test_generate_docs(tmp_path, monkeypatch):
    repo = tmp_path
    demos = repo / "alpha_factory_v1" / "demos" / "demo_a"
    demos.mkdir(parents=True)
    (demos / "README.md").write_text("# Demo A\nHello", encoding="utf-8")
    assets = repo / "docs" / "demo_a" / "assets"
    assets.mkdir(parents=True)
    (assets / "preview.png").write_text("data", encoding="utf-8")
    docs_demos = repo / "docs" / "demos"

    monkeypatch.setattr(gdd, "REPO_ROOT", repo)
    monkeypatch.setattr(gdd, "DEMOS_DIR", repo / "alpha_factory_v1" / "demos")
    monkeypatch.setattr(gdd, "DOCS_DIR", docs_demos)

    gdd.generate_docs()

    page = docs_demos / "demo_a.md"
    text = page.read_text(encoding="utf-8")
    assert "# Demo A" in text
    assert "![preview](../demo_a/assets/preview.png){.demo-preview}" in text
    base = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/"
    assert f"[View README on GitHub]({base}alpha_factory_v1/demos/demo_a/README.md)" in text


def test_relative_links_converted(tmp_path, monkeypatch):
    repo = tmp_path
    demo = repo / "alpha_factory_v1" / "demos" / "demo_b"
    demo.mkdir(parents=True)
    (demo / "colab_demo.ipynb").write_text("data", encoding="utf-8")
    (demo / "assets").mkdir()
    (demo / "assets" / "graph.png").write_text("img", encoding="utf-8")

    readme = (
        "# Demo B\n"
        "See [Guide](../../../docs/OFFLINE_SETUP.md).\n"
        "Open [Notebook](colab_demo.ipynb).\n"
        "![shot](assets/graph.png)\n"
    )
    (demo / "README.md").write_text(readme, encoding="utf-8")

    assets = repo / "docs" / "demo_b" / "assets"
    assets.mkdir(parents=True)
    (assets / "preview.png").write_text("data", encoding="utf-8")
    docs_demos = repo / "docs" / "demos"

    monkeypatch.setattr(gdd, "REPO_ROOT", repo)
    monkeypatch.setattr(gdd, "DEMOS_DIR", repo / "alpha_factory_v1" / "demos")
    monkeypatch.setattr(gdd, "DOCS_DIR", docs_demos)

    gdd.generate_docs()

    page = docs_demos / "demo_b.md"
    text = page.read_text(encoding="utf-8")
    base = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/"
    assert f"[Notebook]({base}alpha_factory_v1/demos/demo_b/colab_demo.ipynb)" in text
    assert f"![shot]({base}alpha_factory_v1/demos/demo_b/assets/graph.png)" in text
