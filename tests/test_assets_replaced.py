# SPDX-License-Identifier: Apache-2.0
import os
import pathlib

import pytest


BASE = pathlib.Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1")


def _asset_root() -> pathlib.Path:
    for env_var in ("INSIGHT_ASSET_ROOT", "FETCH_ASSETS_DIR"):
        value = os.environ.get(env_var)
        if value:
            root = pathlib.Path(value).expanduser().resolve()
            if root.exists():
                return root
    return BASE


def _assert_no_placeholder(path: pathlib.Path) -> None:
    data = path.read_text(errors="ignore")
    assert "placeholder" not in data.lower()


def test_assets_replaced() -> None:
    asset_root = _asset_root()
    _assert_no_placeholder(asset_root / "lib" / "workbox-sw.js")
    _assert_no_placeholder(asset_root / "lib" / "bundle.esm.min.js")

    dist_dir = BASE / "dist"
    if dist_dir.exists():
        lib_dir = dist_dir / "lib"
        assets_lib_dir = dist_dir / "assets" / "lib"
        workbox_path = (
            assets_lib_dir / "workbox-sw.js"
            if (assets_lib_dir / "workbox-sw.js").exists()
            else lib_dir / "workbox-sw.js"
        )
        bundle_path = (
            assets_lib_dir / "bundle.esm.min.js"
            if (assets_lib_dir / "bundle.esm.min.js").exists()
            else lib_dir / "bundle.esm.min.js"
        )
        _assert_no_placeholder(workbox_path)
        _assert_no_placeholder(bundle_path)
    else:
        pytest.skip("Insight browser dist assets missing; run npm build to generate them")

    import json, base64, hashlib

    manifest = json.loads((BASE / "build_assets.json").read_text())
    for name, expected in manifest["checksums"].items():
        if name.startswith("lib/"):
            path = asset_root / name
        else:
            path = asset_root / "wasm" / name
        if not path.exists():
            continue
        digest = base64.b64encode(hashlib.sha384(path.read_bytes()).digest()).decode()
        assert expected.endswith(digest)
