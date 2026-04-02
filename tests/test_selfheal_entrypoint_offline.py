# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
import builtins
import importlib
import sys
import types


class DummyBlocks:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def launch(self, *a, **k):
        pass


class DummyMarkdown:
    def __init__(self, *a, **k):
        pass


class DummyButton:
    def __init__(self, *a, **k):
        pass

    def click(self, *a, **k):
        pass


def test_entrypoint_offline(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "gradio",
        types.SimpleNamespace(Blocks=DummyBlocks, Markdown=DummyMarkdown, Button=DummyButton),
    )

    called = {}

    class DummyResp:
        def __init__(self, text: str = "local") -> None:
            self._data = {"choices": [{"message": {"content": text}}]}

        def json(self) -> dict:
            return self._data

        def raise_for_status(self) -> None:
            pass

    def fake_post(url: str, json=None, timeout=None):
        called["url"] = url
        called["json"] = json
        return DummyResp()

    monkeypatch.setattr("af_requests.post", fake_post)

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai_agents":
            raise ModuleNotFoundError(name)
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example.com/v1")
    sys.modules.pop("alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint", None)
    entrypoint = importlib.import_module("alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint")

    assert entrypoint.LLM("hi") == "local"
    assert called["url"] == "http://example.com/v1/chat/completions"


def test_run_heal_cycle_skips_patch_when_initial_pass(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "gradio",
        types.SimpleNamespace(Blocks=DummyBlocks, Markdown=DummyMarkdown, Button=DummyButton),
    )

    sys.modules.pop("alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint", None)
    entrypoint = importlib.import_module("alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint")

    async def fake_run_tests():
        return {"rc": 0, "out": "ok"}

    async def fail_suggest_patch():
        raise AssertionError("suggest_patch should not run when tests pass")

    monkeypatch.setattr(entrypoint, "run_tests", fake_run_tests)
    monkeypatch.setattr(entrypoint, "suggest_patch", fail_suggest_patch)

    import asyncio

    out1, patch, out2 = asyncio.run(entrypoint._run_heal_cycle())
    assert out1["rc"] == 0
    assert patch is None
    assert out2 is None
