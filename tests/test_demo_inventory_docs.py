# SPDX-License-Identifier: Apache-2.0
"""Prevent execution modes and complete demo inventories from drifting again."""

import json

import pytest

from scripts import sync_demo_catalog_docs as sync


def test_checked_in_catalog_descriptions_are_current():
    assert sync.synchronize(check=True) == []


def test_updated_catalog_changes_both_inventories_without_touching_diagrams(tmp_path):
    base = tmp_path / "alpha_factory_v1/demos"
    base.mkdir(parents=True)
    docs = tmp_path / "docs/agent"
    docs.mkdir(parents=True)
    catalog = {
        "release": "2.0.0",
        "entries": [
            {"id": "example", "title": "Example", "mode": "Local lab", "summary": "Review | retain", "smoke": True},
            {"id": "assets", "title": "Assets", "mode": "Reference", "summary": "Original media", "smoke": False},
        ],
    }
    (base / "catalog.json").write_text(json.dumps(catalog))
    original = "# Preserved\n```mermaid\nflowchart TD\n A --> B\n```\n"
    for path in (base / "README.md", docs / "DEMO_VALIDATION.md"):
        path.write_text(original + sync.START + "\nold\n" + sync.END + "\nTail\n")
    assert len(sync.synchronize(tmp_path, check=True)) == 2
    assert "old" in (base / "README.md").read_text()
    assert len(sync.synchronize(tmp_path)) == 2
    assert sync.synchronize(tmp_path, check=True) == []
    for path in (base / "README.md", docs / "DEMO_VALIDATION.md"):
        text = path.read_text()
        assert text.startswith(original) and text.endswith("\nTail\n")
        assert "2 entries; 1 finite offline launch checks" in text
        assert "Review &#124; retain" in text
        assert "Separate acceptance / prerequisites" in text
    assert "(example/README.md)" in (base / "README.md").read_text()
    assert "(../demos/example.md)" in (docs / "DEMO_VALIDATION.md").read_text()


def test_missing_markers_never_replace_unrelated_content(tmp_path):
    path = tmp_path / "alpha_factory_v1/demos/README.md"
    path.parent.mkdir(parents=True)
    path.write_text("Keep every diagram")
    with pytest.raises(ValueError, match="marker pair"):
        sync.synchronize(tmp_path)
    assert path.read_text() == "Keep every diagram"


def test_current_launch_heading_tracks_release_without_rewriting_history(tmp_path):
    base = tmp_path / "alpha_factory_v1/demos"
    demo = base / "example"
    demo.mkdir(parents=True)
    docs = tmp_path / "docs/agent"
    docs.mkdir(parents=True)
    (base / "catalog.json").write_text(
        json.dumps(
            {
                "release": "2.0.0",
                "entries": [{"id": "example", "title": "Example", "mode": "Local", "summary": "Test", "smoke": True}],
            }
        )
    )
    for path in (base / "README.md", docs / "DEMO_VALIDATION.md"):
        path.write_text(sync.START + "\nold\n" + sync.END)
    history = "\n## Current runnable path — 1.0.0\nOriginal publication\n```mermaid\nflowchart LR\n A --> B\n```\n"
    command = "\n```sh\npython -m example --version 1.0.0\n```\n"
    readme = demo / "README.md"
    readme.write_text(
        "<!-- CURRENT-DEMO:START -->\n## Current runnable path — 1.0.0\n"
        + command
        + "<!-- CURRENT-DEMO:END -->"
        + history
    )
    sync.synchronize(tmp_path)
    assert "## Current runnable path — 2.0.0" in readme.read_text()
    assert command in readme.read_text() and readme.read_text().endswith(history)
    assert sync.synchronize(tmp_path, check=True) == []
