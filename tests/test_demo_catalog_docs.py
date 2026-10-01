# SPDX-License-Identifier: Apache-2.0
"""Check walkthrough counts and all current-heading variants without changing history."""

import json
from pathlib import Path
import shutil

import pytest

from scripts import sync_demo_catalog_docs as docs


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    paths = [
        docs.ROOT / "alpha_factory_v1/demos/catalog.json",
        docs.ROOT / "alpha_factory_v1/demos/README.md",
        docs.ROOT / "docs/agent/DEMOS.md",
        docs.ROOT / "docs/agent/DEMO_VALIDATION.md",
    ]
    paths.extend((docs.ROOT / "alpha_factory_v1/demos").glob("*/README.md"))
    for source in paths:
        target = tmp_path / source.relative_to(docs.ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return tmp_path


def test_walkthrough_count_drift_is_read_only_then_repaired(checkout: Path) -> None:
    path = checkout / "docs/agent/DEMOS.md"
    original = path.read_text()
    changed = original.replace("all 17 from the wheel", "all 15 from the wheel")
    assert changed != original
    path.write_text(changed)
    assert docs.synchronize(checkout, check=True) == ["docs/agent/DEMOS.md"]
    assert path.read_text() == changed
    docs.synchronize(checkout)
    assert path.read_text() == original


@pytest.mark.parametrize(
    "name", ["alpha_agi_insight_v0", "meta_agentic_agi_v3", "muzero_planning", "muzeromctsllmagent_v0"]
)
def test_all_current_heading_variants_track_release(checkout: Path, name: str) -> None:
    catalog = checkout / "alpha_factory_v1/demos/catalog.json"
    version = json.loads(catalog.read_text())["release"]
    path = checkout / "alpha_factory_v1/demos" / name / "README.md"
    original = path.read_text()
    changed = original.replace(f"— {version}", "— 0.0.0", 1)
    assert changed != original
    path.write_text(changed)
    assert docs.synchronize(checkout, check=True) == [str(path.relative_to(checkout))]
    assert path.read_text() == changed
    docs.synchronize(checkout)
    assert path.read_text() == original


@pytest.mark.parametrize("marker", ["CURRENT-DEMO:START", "CURRENT-DEMO:END", "CATALOG-COUNTS:START"])
def test_ambiguous_markers_fail_before_any_write(checkout: Path, marker: str) -> None:
    path = checkout / (
        "docs/agent/DEMOS.md" if marker.startswith("CATALOG") else "alpha_factory_v1/demos/finance_alpha/README.md"
    )
    path.write_text(path.read_text().replace(f"<!-- {marker} -->", f"<!-- {marker} -->" * 2))
    before = {file: file.read_bytes() for file in checkout.rglob("*.md")}
    with pytest.raises(ValueError, match="marker pair"):
        docs.synchronize(checkout)
    assert all(file.read_bytes() == content for file, content in before.items())
