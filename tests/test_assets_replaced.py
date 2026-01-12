# SPDX-License-Identifier: Apache-2.0
import pathlib

import pytest


BASE = pathlib.Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1")


def _assert_no_placeholder(path: pathlib.Path) -> None:
    data = path.read_text(errors="ignore")
    assert "placeholder" not in data.lower()


def test_assets_replaced() -> None:
    _assert_no_placeholder(BASE / "lib" / "workbox-sw.js")
    _assert_no_placeholder(BASE / "lib" / "bundle.esm.min.js")

    dist_dir = BASE / "dist"
    if dist_dir.exists():
        _assert_no_placeholder(dist_dir / "workbox-sw.js")
        _assert_no_placeholder(dist_dir / "bundle.esm.min.js")
    else:
        pytest.skip("Insight browser dist assets missing; run npm build to generate them")

    import json, base64, hashlib

    manifest = json.loads((BASE / "build_assets.json").read_text())
    for name, expected in manifest["checksums"].items():
        if name.startswith("lib/"):
            path = BASE / name
        else:
            path = BASE / "wasm" / name
        if not path.exists():
            continue
        digest = base64.b64encode(hashlib.sha384(path.read_bytes()).digest()).decode()
        assert expected.endswith(digest)
