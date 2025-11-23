"""Compatibility shim for the `google_adk` package.

If the real package is installed under ``google.adk`` this module re-exports
its symbols so imports using ``google_adk`` continue to work. When the real
package is missing a minimal stub is provided so demos and tests can import
it without failures.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import os
import sys

force_stub = os.environ.get("GOOGLE_ADK_FORCE_STUB")

try:
    if force_stub not in {None, "0", "false", "False"}:
        raise ImportError("Forcing stub for google.adk")
    _mod = importlib.import_module("google.adk")
except Exception:  # pragma: no cover - package absent
    _mod = None

if _mod is not None:
    globals().update(_mod.__dict__)

    if "task" not in globals():

        def task(*_a, **_kw):
            def decorator(func):
                return func

            return decorator

    if "Router" not in globals():

        class Router:
            def __init__(self) -> None:
                self.app = type("app", (), {"middleware": lambda *_a, **_kw: lambda f: f})

            def register_agent(self, _agent) -> None:  # pragma: no cover - stub
                pass

    if "AgentException" not in globals():

        class AgentException(Exception):
            pass

    if "Agent" not in globals():

        class Agent:
            def __init__(self, *args, **kwargs):
                pass

    if "JsonSchema" not in globals():

        class JsonSchema(dict):
            """Lightweight placeholder used when the real google_adk package is absent."""

            pass

    # Ensure both module aliases refer to this shim
    sys.modules[__name__] = sys.modules.get(__name__, sys.modules[__name__])
    sys.modules["google.adk"] = sys.modules[__name__]

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

    class Agent:
        def __init__(self, *args, **kwargs):
            pass

    class JsonSchema(dict):
        """Lightweight placeholder used when the real google_adk package is absent."""

        pass


__all__ = [k for k in globals().keys() if not k.startswith("_")]
