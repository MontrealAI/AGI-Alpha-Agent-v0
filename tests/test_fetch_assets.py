# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import builtins
import importlib
import sys


def test_fetch_assets_imports_without_requests(monkeypatch) -> None:
    real_import = builtins.__import__

    def _guarded_import(name: str, *args, **kwargs):
        if name == "requests":
            raise ImportError("requests is unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _guarded_import)
    sys.modules.pop("scripts.fetch_assets", None)

    module = importlib.import_module("scripts.fetch_assets")

    assert hasattr(module, "download_with_retry")
