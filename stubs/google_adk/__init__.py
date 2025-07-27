"""Compatibility shim for the `google_adk` package.

If the real package is installed under ``google.adk`` this module re-exports
its symbols so imports using ``google_adk`` continue to work. When the real
package is missing a minimal stub is provided so demos and tests can import
it without failures.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import sys

try:
    _mod = importlib.import_module("google.adk")
except Exception:  # pragma: no cover - package absent
    _mod = None

if _mod is not None:
    globals().update(_mod.__dict__)
else:
    __spec__ = importlib.machinery.ModuleSpec("google_adk", None)
    __version__ = "0.0.0"

    def task(*_a, **_kw):
        def decorator(func):
            return func

        return decorator

    class Router:
        def __init__(self) -> None:
            self.app = type("app", (), {"middleware": lambda *_a, **_kw: lambda f: f})

        def register_agent(self, _agent) -> None:  # pragma: no cover - stub
            pass

    class AgentException(Exception):
        pass

__all__ = [k for k in globals().keys() if not k.startswith("_")]
