# SPDX-License-Identifier: Apache-2.0
"""Keep long homepage anchor journeys instant without a JavaScript dependency."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_homepage_overrides_inherited_smooth_scrolling_without_media_query() -> None:
    """The default homepage rule must also cover no-JS/non-reduced-motion users."""
    css = (ROOT / "docs/assets/portal/welcome.css").read_text(encoding="utf-8")
    root_rule = re.search(r":root\s*\{([^}]+)\}", css)
    assert root_rule is not None
    assert re.search(r"\bscroll-behavior\s*:\s*auto\s*;", root_rule.group(1))


def test_homepage_scroll_override_loads_after_legacy_portal_styles() -> None:
    """Preserve cascade order instead of changing shared portal behavior."""
    html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert html.index('href="assets/portal/portal.css') < html.index('href="assets/portal/welcome.css')
