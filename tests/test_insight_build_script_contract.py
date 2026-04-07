# SPDX-License-Identifier: Apache-2.0
from pathlib import Path


def test_build_script_uses_targeted_script_tag_regexes() -> None:
    """Ensure dist pruning only removes explicit runtime script tags."""
    build_js = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build.js").read_text(
        encoding="utf-8"
    )
    assert "bundle\\.esm\\.min\\.js[^\"']*[\"'][^>]*>\\s*<\\/script>" in build_js
    assert "pyodide\\.js[^\"']*[\"'][^>]*>\\s*<\\/script>" in build_js
    assert "<script[\\s\\S]*?bundle\\.esm\\.min\\.js[\\s\\S]*?</script>" not in build_js
    assert "<script[\\s\\S]*?pyodide\\.js[\\s\\S]*?</script>" not in build_js


def test_build_script_rewrites_cdn_styles_to_local_bundle() -> None:
    build_js = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build.js").read_text(
        encoding="utf-8"
    )
    assert "https:\\/\\/cdn\\.jsdelivr\\.net\\/npm\\/daisyui@" in build_js
    assert "href=\"style.css\"" in build_js
