# SPDX-License-Identifier: Apache-2.0
"""Regression test for optional requests dependency in fetch_assets."""

from __future__ import annotations

import builtins
import importlib
import sys
from types import ModuleType
from typing import Callable

from pytest import MonkeyPatch


def test_fetch_assets_import_without_requests(monkeypatch: MonkeyPatch) -> None:
    """Ensure fetch_assets imports even when requests is unavailable."""

    original_import: Callable[..., ModuleType] = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> ModuleType:
        if name == "requests":
            raise ModuleNotFoundError("No module named 'requests'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("scripts.fetch_assets", None)

    module = importlib.import_module("scripts.fetch_assets")
    assert module.requests is None
