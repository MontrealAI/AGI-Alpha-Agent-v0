# SPDX-License-Identifier: Apache-2.0
"""Regression tests for scripts.fetch_assets import behavior."""

from __future__ import annotations

import builtins
import importlib
import sys


def test_fetch_assets_import_without_requests(monkeypatch) -> None:
    """Ensure scripts.fetch_assets imports even when requests is unavailable."""

    import scripts.fetch_assets as fetch_assets

    original_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "requests":
            raise ModuleNotFoundError("No module named 'requests'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    saved_requests = sys.modules.pop("requests", None)
    try:
        importlib.reload(fetch_assets)
    finally:
        if saved_requests is not None:
            sys.modules["requests"] = saved_requests

    assert fetch_assets.requests is None
