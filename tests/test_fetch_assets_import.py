#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Tests for optional requests dependency in fetch_assets."""

from __future__ import annotations

import builtins
import importlib


def test_fetch_assets_import_without_requests(monkeypatch) -> None:
    """Ensure fetch_assets imports cleanly when requests is unavailable."""
    import scripts.fetch_assets as fetch_assets

    original_import = builtins.__import__

    def guarded_import(name: str, *args, **kwargs):
        if name == "requests":
            raise ModuleNotFoundError("No module named 'requests'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    importlib.reload(fetch_assets)
