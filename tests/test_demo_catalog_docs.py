# SPDX-License-Identifier: Apache-2.0
"""Prevent catalog drift without modifying retained research and diagrams."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from scripts import sync_demo_catalog_docs as docs
from scripts import validate_demo_catalog as validator


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    paths = [docs.ROOT / "pyproject.toml", docs.ROOT / "alpha_factory_v1/demos/catalog.json"]
    paths.extend(docs.expected_documents())
    for source in paths:
        target = tmp_path / source.relative_to(docs.ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return tmp_path


def test_current_catalog_guides_match_every_entry() -> None:
    assert docs.synchronize(check=True) == []


def test_stale_guides_fail_read_only_and_preserve_research(checkout: Path) -> None:
    index = checkout / "alpha_factory_v1/demos/README.md"
    index.write_text(index.read_text().replace("All 17 finite", "All 99 finite"), encoding="utf-8")
    guide = checkout / "alpha_factory_v1/demos/alpha_agi_business_v1/README.md"
    preserved = '\n```mermaid\nflowchart TD\n A["Original vision"] --> B["Review"]\n```\n'
    original = guide.read_text() + preserved
    version = json.loads((checkout / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    guide.write_text(original.replace(f"path — {version}", "path — 0.0.0"), encoding="utf-8")
    before = {path: path.read_bytes() for path in (index, guide)}
    assert set(docs.synchronize(checkout, check=True)) == {index, guide}
    assert all(path.read_bytes() == content for path, content in before.items())
    docs.synchronize(checkout)
    assert guide.read_text() == original
    assert docs.synchronize(checkout, check=True) == []


def test_catalog_modes_propagate_to_both_indexes(checkout: Path) -> None:
    catalog = checkout / "alpha_factory_v1/demos/catalog.json"
    inventory = json.loads(catalog.read_text())
    inventory["entries"][0]["mode"] = "Explicit | revised mode"
    catalog.write_text(json.dumps(inventory), encoding="utf-8")
    changed = docs.synchronize(checkout, check=True)
    assert {path.name for path in changed} == {"README.md", "DEMO_VALIDATION.md"}
    docs.synchronize(checkout)
    assert "Explicit \\| revised mode" in (checkout / "docs/agent/DEMO_VALIDATION.md").read_text()


def test_unknown_demo_requires_validation_boundary(checkout: Path) -> None:
    catalog = checkout / "alpha_factory_v1/demos/catalog.json"
    inventory = json.loads(catalog.read_text())
    inventory["entries"][0]["id"] = "new-demo"
    catalog.write_text(json.dumps(inventory), encoding="utf-8")
    with pytest.raises(ValueError, match="explicit validation boundary"):
        docs.synchronize(checkout)


@pytest.mark.parametrize("text", ["no markers", "<!-- TEST:END --><!-- TEST:START -->", "<!-- TEST:START -->" * 2])
def test_ambiguous_regions_fail_without_replacing_content(text: str) -> None:
    with pytest.raises(ValueError, match="Missing or ambiguous"):
        docs.replace_region(text, "TEST", "replacement")


def test_release_inventory_rejects_stale_documentation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validator, "synchronize", lambda *args, **kwargs: [docs.ROOT / "docs/agent/DEMOS.md"])
    with pytest.raises(ValueError, match="Stale catalog guides.*sync_demo_catalog_docs"):
        validator.validate_inventory()
