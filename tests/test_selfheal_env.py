# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
import asyncio
import importlib
import sys
import types
import subprocess

import alpha_factory_v1.core.utils.config as cfg


class DummyBlocks:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


class DummyMarkdown:
    def __init__(self, *a, **k):
        pass


class DummyButton:
    def __init__(self, *a, **k):
        pass

    def click(self, *a, **kw):
        pass


def test_run_tests_respects_config(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    (repo / "test_calc.py").write_text(
        "import calc\n\n" "def test_add():\n    assert calc.add(1, 2) == 3\n",
        encoding="utf-8",
    )

    env_file = tmp_path / "config.env"
    env_file.write_text(
        f"OPENAI_MODEL=my-model\nMODEL_NAME=my-model\nCLONE_DIR={repo}\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    cfg.init_config(str(env_file))

    monkeypatch.setitem(
        sys.modules,
        "gradio",
        types.SimpleNamespace(Blocks=DummyBlocks, Markdown=DummyMarkdown, Button=DummyButton),
    )

    agent_args = {}

    class FakeAgent:
        def __init__(self, *a, **kw):
            agent_args.update(kw)

        def __call__(self, *_a, **_k):
            return "ok"

    stub = types.SimpleNamespace(
        Agent=lambda *a, **k: object(),
        OpenAIAgent=FakeAgent,
        Tool=lambda *a, **k: (lambda f: f),
    )
    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    monkeypatch.setitem(
        sys.modules,
        "alpha_factory_v1.demos.self_healing_repo.patcher_core",
        types.SimpleNamespace(
            generate_patch=lambda *_a, **_k: "",
            apply_patch=lambda *_a, **_k: None,
        ),
    )

    sys.modules.pop(
        "alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint",
        None,
    )
    entrypoint = importlib.import_module("alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint")
    entrypoint.apply_patch_and_retst = lambda *_a, **_k: None
    monkeypatch.setattr(entrypoint, "CLONE_DIR", str(repo))

    result = asyncio.run(entrypoint.run_tests())
    assert result["rc"] == 0
    assert agent_args.get("model") == "my-model"


def test_run_tests_timeout(tmp_path, monkeypatch):
    """run_tests should report a timeout error when pytest hangs."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setitem(
        sys.modules,
        "gradio",
        types.SimpleNamespace(Blocks=DummyBlocks, Markdown=DummyMarkdown, Button=DummyButton),
    )

    sys.modules.pop(
        "alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint",
        None,
    )
    entrypoint = importlib.import_module("alpha_factory_v1.demos.self_healing_repo.agent_selfheal_entrypoint")
    monkeypatch.setattr(entrypoint, "CLONE_DIR", str(repo))

    def fake_run(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd=_a[0], timeout=300)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = asyncio.run(entrypoint.run_tests())
    assert result["rc"] == 1
    assert "timed out" in result["out"]
