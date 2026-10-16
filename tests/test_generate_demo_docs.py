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
    raw = "https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/main/"
    assert f"![shot]({raw}alpha_factory_v1/demos/demo_b/assets/graph.png)" in text


def test_images_change_destination_without_changing_diagrams_or_code(tmp_path, monkeypatch):
    demo = tmp_path / "alpha_factory_v1/demos/example"
    demo.mkdir(parents=True)
    diagram = '```mermaid\nflowchart LR\n A["Input"] --> B["Review"]\n```'
    code = '```python\ntext = "![image](local.png)"\n```'
    (demo / "README.md").write_text(
        f"# Example\n{diagram}\n{code}\n![plot](assets/plot.svg)\n[Source](assets/plot.svg)\n"
        "[![Notebook](https://example.com/badge.svg)](demo.ipynb)\n"
    )
    monkeypatch.setattr(gdd, "REPO_ROOT", tmp_path)
    text = gdd.build_page(demo)
    assert diagram in text and code in text
    assert "![plot](https://raw.githubusercontent.com/" in text
    assert "[Source](https://github.com/" in text
    assert "[![Notebook](https://example.com/badge.svg)](https://github.com/" in text


def test_late_original_title_survives_current_instructions_and_code(tmp_path, monkeypatch):
    demo = tmp_path / "alpha_factory_v1/demos/late_title"
    demo.mkdir(parents=True)
    code = "```sh\n# A shell comment is not the title\n```"
    original = "Original research title — preserved"
    (demo / "README.md").write_text(
        "# [See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)\n"
        + "Current launch instructions.\n" * 120
        + code
        + "\n# "
        + original
        + "\nOriginal narrative.\n"
    )
    monkeypatch.setattr(gdd, "REPO_ROOT", tmp_path)
    assert gdd.extract_title(demo / "README.md") == original
    page = gdd.build_page(demo)
    assert page.count("# " + original) == 1
    assert code in page and "Original narrative." in page


def test_current_business2_and_macro_titles_match_original_readmes():
    root = Path(__file__).resolve().parents[1]
    for name, marker in (("alpha_agi_business_2_v1", "Bloom"), ("macro_sentinel", "Sentinel")):
        demo = root / "alpha_factory_v1/demos" / name
        title = gdd.extract_title(demo / "README.md")
        assert marker in title
        assert "# " + title in gdd.build_page(demo)
