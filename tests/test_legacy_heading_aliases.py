# SPDX-License-Identifier: Apache-2.0
"""Keep published 1.36.0 fragments at their corresponding current sections."""

import json
from pathlib import Path
import re
import shutil

import pytest

from scripts import generate_demo_docs as generator
from scripts import sync_demo_catalog_docs as catalog_docs

ROOT = Path(__file__).resolve().parents[1]
# These are published routes, deliberately independent of the current catalog.
CURRENT_PATH_DEMOS = (
    "aiga_meta_evolution alpha_agi_business_2_v1 alpha_agi_business_3_v1 alpha_agi_business_v1 "
    "alpha_agi_insight_v0 alpha_agi_insight_v1 alpha_agi_marketplace_v1 alpha_asi_world_model "
    "alpha_super_planner_v1 cross_industry_alpha_factory era_of_experience gpt2_small_cli "
    "macro_sentinel meta_agentic_agi meta_agentic_agi_v2 meta_agentic_tree_search_v0 "
    "omni_factory_demo presentation self_healing_repo solving_agi_governance "
    "sovereign_agentic_agialpha_agent_v0 utils"
).split()
DEMO_HEADINGS = dict.fromkeys(CURRENT_PATH_DEMOS, "Current runnable path") | {
    "finance_alpha": "Start locally",
    "meta_agentic_agi_v3": "Start in two minutes",
    "muzero_planning": "Start here",
    "muzeromctsllmagent_v0": "Start in three steps",
}


def assert_alias(text: str, alias: str, heading: str, *, demo: bool = True) -> None:
    """Require one inert alias immediately before its actual matching section."""
    ids = re.findall(r'\bid=["\']([^"\']+)["\']', text)
    assert ids.count(alias) == 1
    marker = r"<!-- CURRENT-DEMO:START -->\s*" if demo else ""
    assert re.search(r'<a id="' + re.escape(alias) + r'"></a>\s*' + marker + re.escape(heading), text)


@pytest.mark.parametrize("name, title", sorted(DEMO_HEADINGS.items()))
def test_published_demo_alias_survives_generation(name: str, title: str) -> None:
    alias = title.lower().replace(" ", "-") + "-1360"
    readme = ROOT / "alpha_factory_v1/demos" / name / "README.md"
    assert_alias(readme.read_text(), alias, "## " + title + " — ")
    generated = generator.build_page(readme.parent)
    assert_alias(generated, alias, "## " + title + " — ")
    assert generated == (ROOT / "docs/demos" / f"{name}.md").read_text()
    assert generator.build_page(readme.parent) == generated


def test_published_readiness_alias() -> None:
    assert_alias(
        (ROOT / "docs/agent/RELEASE_READINESS.md").read_text(),
        "release-readiness-1360-source-candidate",
        "# Release readiness — ",
        demo=False,
    )


def test_version_sync_keeps_aliases_and_generation_deterministic(tmp_path: Path, monkeypatch) -> None:
    paths = [
        "alpha_factory_v1/demos/catalog.json",
        "alpha_factory_v1/demos/README.md",
        "docs/agent/DEMO_VALIDATION.md",
        "docs/agent/DEMOS.md",
    ]
    paths.extend(str(path.relative_to(ROOT)) for path in (ROOT / "alpha_factory_v1/demos").glob("*/README.md"))
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    catalog_path = tmp_path / "alpha_factory_v1/demos/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["release"] = "9.8.7"
    catalog_path.write_text(json.dumps(catalog))
    catalog_docs.synchronize(tmp_path)
    assert catalog_docs.synchronize(tmp_path, check=True) == []
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "DEMOS_DIR", tmp_path / "alpha_factory_v1/demos")
    monkeypatch.setattr(generator, "DOCS_DIR", tmp_path / "docs/demos")
    generator.generate_docs()
    first = {path: path.read_bytes() for path in generator.DOCS_DIR.glob("*.md")}
    generator.generate_docs()
    assert all(path.read_bytes() == contents for path, contents in first.items())
    for name, title in DEMO_HEADINGS.items():
        assert_alias(
            (generator.DOCS_DIR / f"{name}.md").read_text(),
            title.lower().replace(" ", "-") + "-1360",
            "## " + title + " — 9.8.7",
        )


def test_rendered_legacy_ids_are_unique_and_precede_matching_headings() -> None:
    markdown = pytest.importorskip("markdown", reason="Install documentation dependencies for rendered checks")
    pages = [
        (ROOT / "docs/demos" / f"{name}.md", title.lower().replace(" ", "-") + "-1360", title)
        for name, title in DEMO_HEADINGS.items()
    ]
    pages.append(
        (ROOT / "docs/agent/RELEASE_READINESS.md", "release-readiness-1360-source-candidate", "Release readiness")
    )
    for path, alias, title in pages:
        html = markdown.markdown(path.read_text(), extensions=["toc", "fenced_code", "attr_list", "tables"])
        ids = re.findall(r'\bid="([^"]+)"', html)
        assert ids.count(alias) == 1, path
        assert len(ids) == len(set(ids)), path
        after_alias = html.split(f'<a id="{alias}"></a>', 1)[1]
        assert re.match(
            r'(?:\s|</p>|<!-- CURRENT-DEMO:START -->)*<h[12] id="[^"]+">' + re.escape(title) + " — ",
            after_alias,
        ), path
