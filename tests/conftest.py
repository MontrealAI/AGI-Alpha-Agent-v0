# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration and compatibility shims."""

from __future__ import annotations

from typing import Any

import pytest


def pytest_configure() -> None:
    """Patch Playwright's executable_path for call-style access."""
    import sys
    import types

    try:
        import rocketry  # noqa: F401
    except Exception:
        stub = types.ModuleType("rocketry")

        class Rocketry:  # type: ignore[no-redef]
            def __init__(self, *_, **__) -> None:
                pass

        conds = types.ModuleType("rocketry.conds")

        def every(interval: str) -> str:
            return interval

        stub.Rocketry = Rocketry
        conds.every = every
        stub.conds = conds
        sys.modules["rocketry"] = stub
        sys.modules["rocketry.conds"] = conds

    try:
        from google.protobuf import struct_pb2
    except Exception:
        struct_pb2 = None

    if struct_pb2 is not None and not hasattr(struct_pb2.Struct, "get"):
        def _struct_get(self: struct_pb2.Struct, key: str, default: Any = None) -> Any:  # type: ignore[name-defined]
            try:
                return self[key]
            except Exception:
                return default

        struct_pb2.Struct.get = _struct_get  # type: ignore[assignment]

    try:
        from alpha_factory_v1.common.utils import messaging
        from alpha_factory_v1.core.utils import a2a_pb2 as pb
    except Exception:
        pb = None
    else:
        def _coercing_envelope(*, sender: Any = "", recipient: Any = "", payload: Any = None, ts: Any = 0.0) -> Any:
            if pb is None:
                return None
            env = pb.Envelope(
                sender=str(sender) if sender is not None else "",
                recipient=str(recipient) if recipient is not None else "",
                ts=float(ts) if ts is not None else 0.0,
            )
            if isinstance(payload, dict):
                env.payload.update(payload)
            return env

        messaging.Envelope = _coercing_envelope  # type: ignore[assignment]

    try:
        from playwright.sync_api import BrowserType
    except Exception:
        return

    if isinstance(getattr(BrowserType, "executable_path", None), property):
        class _CallablePath(str):
            def __call__(self) -> str:
                return str(self)

        def _callable_path(self: BrowserType) -> _CallablePath:  # type: ignore[name-defined]
            return _CallablePath(self._impl_obj.executable_path)

        BrowserType.executable_path = property(_callable_path)  # type: ignore[assignment]


@pytest.fixture
def non_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_NET_OFF", "1")
    return None
