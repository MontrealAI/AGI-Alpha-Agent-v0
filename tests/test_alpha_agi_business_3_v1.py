# SPDX-License-Identifier: Apache-2.0
import importlib
import sys
import types
import asyncio
import logging
import os
import subprocess
from unittest import mock

MODULE = "alpha_factory_v1.demos.alpha_agi_business_3_v1.alpha_agi_business_3_v1"

def test_adk_client_import(monkeypatch):
    dummy = types.ModuleType("google_adk")
    class Client:
        pass
    dummy.Client = Client
    monkeypatch.setitem(sys.modules, "google_adk", dummy)
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)
    assert mod.ADKClient is Client


def test_a2a_port_zero(monkeypatch):
    """`_A2A` should remain ``None`` when ``A2A_PORT=0``."""
    dummy = types.ModuleType("a2a")

    class DummySocket:
        def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - dummy
            raise AssertionError("should not be instantiated")

    dummy.A2ASocket = DummySocket
    monkeypatch.setitem(sys.modules, "a2a", dummy)
    monkeypatch.setenv("A2A_PORT", "0")
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)
    assert mod._A2A is None


def test_a2a_port_invalid(monkeypatch):
    """Invalid ``A2A_PORT`` values should not crash the import."""
    dummy = types.ModuleType("a2a")

    class DummySocket:
        def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - dummy
            raise AssertionError("should not be instantiated")

    dummy.A2ASocket = DummySocket
    monkeypatch.setitem(sys.modules, "a2a", dummy)
    monkeypatch.setenv("A2A_PORT", "abc")
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)
    assert mod._A2A is None


def test_llm_comment_offline(monkeypatch):
    """`_llm_comment` should use local_llm when OpenAIAgent is unavailable."""
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "OpenAIAgent", None)
    monkeypatch.setattr(mod.local_llm, "chat", lambda prompt: "offline")

    result = asyncio.run(mod._llm_comment(0.5))
    assert result == "offline"


def test_llm_comment_online(monkeypatch):
    """`_llm_comment` should call OpenAIAgent when available."""
    mod = importlib.import_module(MODULE)

    class DummyAgent:
        def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - args ignored
            pass

        async def __call__(self, prompt: str) -> str:
            self.prompt = prompt
            return "online"

    with mock.patch.object(mod.local_llm, "chat", return_value="bad") as m_chat:
        monkeypatch.setattr(mod, "OpenAIAgent", DummyAgent)
        result = asyncio.run(mod._llm_comment(1.23))

    assert result == "online"
    assert not m_chat.called


def test_run_cycle_async_logs_delta_g(monkeypatch, caplog):
    """One cycle should log the computed ΔG value."""
    mod = importlib.import_module(MODULE)

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(mod, "_A2A", None)
    async def _fake_comment(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _fake_comment)

    asyncio.run(
        mod.run_cycle_async(
            mod.Orchestrator(),
            mod.AgentFin(),
            mod.AgentRes(),
            mod.AgentEne(),
            mod.AgentGdl(),
            mod.Model(),
        )
    )

    assert any("ΔG" in r.getMessage() for r in caplog.records)


def test_main_subprocess(tmp_path) -> None:
    """Running the demo via ``python -m`` should output the ΔG message."""
    stub = tmp_path / "check_env.py"
    stub.write_text("def main(args=None):\n    pass\n")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "dummy"
    env["PYTHONPATH"] = f"{tmp_path}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.alpha_agi_business_3_v1",
            "--cycles",
            "1",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ΔG" in (result.stdout + result.stderr)


def test_cli_entrypoint(tmp_path) -> None:
    """Running the ``alpha-agi-business-3-v1`` script should output the ΔG message."""
    stub = tmp_path / "check_env.py"
    stub.write_text("def main(args=None):\n    pass\n")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "dummy"
    env["PYTHONPATH"] = f"{tmp_path}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        ["alpha-agi-business-3-v1", "--cycles", "1"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ΔG" in (result.stdout + result.stderr)


def test_main_stops_a2a(monkeypatch) -> None:
    """`_A2A.stop()` should be called when the loop exits."""
    mod = importlib.import_module(MODULE)

    class DummySocket:
        def __init__(self) -> None:
            self.started = False
            self.stopped = False

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stopped = True

        def sendjson(self, *_a: object, **_kw: object) -> None:  # pragma: no cover - unused
            pass

    dummy = DummySocket()

    monkeypatch.setattr(mod, "_A2A", dummy)
    monkeypatch.setattr(mod, "ADKClient", None)
    monkeypatch.setattr(mod, "check_env", types.SimpleNamespace(main=lambda *_a, **_k: None), raising=False)

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    asyncio.run(mod.main(["--cycles", "1", "--interval", "0"]))

    assert dummy.started
    assert dummy.stopped


def test_run_cycle_posts_job(monkeypatch) -> None:
    """`post_alpha_job` should be called once when ΔG < 0."""
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "_A2A", None)

    orchestrator = mod.Orchestrator()
    fin = mod.AgentFin()
    res = mod.AgentRes()
    ene = mod.AgentEne()
    gdl = mod.AgentGdl()
    model = mod.Model()

    monkeypatch.setattr(orchestrator, "collect_signals", lambda: {})
    monkeypatch.setattr(fin, "latent_work", lambda _b: 0.0)
    monkeypatch.setattr(res, "entropy", lambda _b: 1.0)
    monkeypatch.setattr(ene, "market_temperature", lambda _b: 1.0)

    calls: list[tuple[str, float]] = []

    def _post(bundle_id: str, delta_g: float) -> None:
        calls.append((bundle_id, delta_g))

    monkeypatch.setattr(orchestrator, "post_alpha_job", _post)

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    asyncio.run(
        mod.run_cycle_async(orchestrator, fin, res, ene, gdl, model)
    )

    assert len(calls) == 1


def test_cli_flags_override_env(monkeypatch) -> None:
    """CLI options should set env vars for the runtime helpers."""
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "check_env", types.SimpleNamespace(main=lambda *_a, **_k: None), raising=False)

    captured: dict[str, str] = {}

    async def _llm(_: float) -> str:
        captured["api_key"] = os.getenv("OPENAI_API_KEY")
        return "ok"

    class DummyADK:
        def __init__(self, host: str) -> None:  # pragma: no cover - init only
            captured["adk_host"] = host

    class DummySock:
        def __init__(self, host: str, port: int, app_id: str) -> None:
            captured["a2a"] = f"{host}:{port}"  # pragma: no cover - record args

        def start(self) -> None:  # pragma: no cover - unused
            pass

        def stop(self) -> None:  # pragma: no cover - unused
            pass

        def sendjson(self, *_a: object, **_kw: object) -> None:  # pragma: no cover - unused
            pass

    monkeypatch.setattr(mod, "_llm_comment", _llm)
    monkeypatch.setattr(mod, "ADKClient", DummyADK)
    monkeypatch.setattr(mod, "A2ASocket", DummySock)
    monkeypatch.setattr(mod, "_A2A", None)

    asyncio.run(
        mod.main(
            [
                "--cycles",
                "1",
                "--interval",
                "0",
                "--openai-api-key",
                "cli-key",
                "--adk-host",
                "http://cli-adk:9",
                "--a2a-port",
                "7777",
                "--a2a-host",
                "cli-host",
            ]
        )
    )

    assert captured["api_key"] == "cli-key"
    assert captured["adk_host"] == "http://cli-adk:9"
    assert captured["a2a"] == "cli-host:7777"

