# SPDX-License-Identifier: Apache-2.0
import importlib
import sys
import types
import pytest


def test_aiga_bridge_no_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import bridge without agents packages and expect helpful error."""
    monkeypatch.delitem(sys.modules, "openai_agents", raising=False)
    monkeypatch.delitem(sys.modules, "agents", raising=False)
    orig_import_module = importlib.import_module

    def _blocked(name: str, *args, **kwargs):
        if name in {"openai_agents", "agents"}:
            raise ModuleNotFoundError(name)
        return orig_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", _blocked)

    # Reload backend so the missing SDK shim is installed
    importlib.reload(importlib.import_module("alpha_factory_v1.backend"))

    # Provide minimal curriculum_env to avoid gymnasium dependency
    env_stub = types.ModuleType("curriculum_env")

    class DummyEnv:
        pass

    env_stub.CurriculumEnv = DummyEnv  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env",
        env_stub,
    )

    with pytest.raises(ModuleNotFoundError, match="OpenAI Agents SDK is required"):
        importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge")
