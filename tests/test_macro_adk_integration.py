# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib
import sys
from types import ModuleType
from unittest.mock import patch

import pytest

pytest.importorskip("google_adk")


def test_macro_entrypoint_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADK launch should be triggered when the env flag is set."""

    monkeypatch.setenv("ALPHA_FACTORY_ENABLE_ADK", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    # Provide a minimal openai_agents stub when the package is absent
    if "openai_agents" not in sys.modules:
        stub = ModuleType("openai_agents")

        class _Agent:
            def __init__(self, *a: object, **kw: object) -> None:
                self.name = kw.get("name", "agent")

        class _OpenAI:
            def __init__(self, *a: object, **kw: object) -> None:
                pass

            def __call__(self, *_a: object, **_k: object) -> str:
                return ""

        def _tool(*_a: object, **_kw: object) -> object:
            def _decorator(func: object) -> object:
                return func

            return _decorator

        setattr(stub, "Agent", _Agent)
        setattr(stub, "OpenAIAgent", _OpenAI)
        setattr(stub, "Tool", _tool)
        sys.modules["openai_agents"] = stub

    mod_path = "alpha_factory_v1.demos.macro_sentinel.agent_macro_entrypoint"
    sys.modules.pop(mod_path, None)

    with patch("alpha_factory_v1.backend.adk_bridge.auto_register"), patch(
        "alpha_factory_v1.backend.adk_bridge.maybe_launch"
    ) as maybe_launch:
        importlib.import_module(mod_path)
        maybe_launch.assert_called_once_with()


def test_macro_entrypoint_missing_openai_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the entrypoint without openai_agents should exit."""

    monkeypatch.delenv("ALPHA_FACTORY_ENABLE_ADK", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sys.modules.pop("openai_agents", None)
    mod_path = "alpha_factory_v1.demos.macro_sentinel.agent_macro_entrypoint"
    sys.modules.pop(mod_path, None)

    with pytest.raises(SystemExit, match="check_env.py --demo macro_sentinel"):
        importlib.import_module(mod_path)
