# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json

import pytest

pytestmark = pytest.mark.smoke


def test_cache_version_matches_package() -> None:
    repo = Path(__file__).resolve().parents[1]
    browser = repo / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
    version = json.loads((browser / "package.json").read_text())["version"]
    sw_path = browser / "dist" / "sw.js"
    if not sw_path.exists():
        pytest.skip("service worker not built")
    sw = sw_path.read_text()
    if "__CACHE_VERSION__" in sw:
        pytest.skip("version placeholder not expanded")
    assert f'CACHE_VERSION="{version}"' in sw or f"CACHE_VERSION = '{version}'" in sw
