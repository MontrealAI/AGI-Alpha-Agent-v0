# SPDX-License-Identifier: Apache-2.0
import importlib
import sys
import types
import asyncio
import logging
import os
import subprocess
import hashlib
import json
from typing import Any, Iterator
from unittest import mock
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB_DIR = ROOT / "tests" / "resources"

MODULE = "alpha_factory_v1.demos.alpha_agi_business_3_v1.alpha_agi_business_3_v1"


@pytest.fixture(autouse=True)
def _reset_demo_globals() -> Iterator[None]:
    """Reset global state altered by the demo."""
    yield
    if MODULE in sys.modules:
        sys.modules[MODULE]._A2A = None


def test_adk_client_import(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = types.ModuleType("google_adk")

    class Client:
        pass

    dummy.Client = Client
    monkeypatch.setitem(sys.modules, "google_adk", dummy)
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)
    assert mod.ADKClient is Client  # type: ignore[attr-defined]


def test_a2a_port_zero(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_a2a_port_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_llm_comment_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_llm_comment` should use local_llm when OpenAIAgent is unavailable."""
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "OpenAIAgent", None)
    monkeypatch.setattr(mod.local_llm, "chat", lambda prompt: "offline")

    result = asyncio.run(mod._llm_comment(0.5))
    assert result == "offline"


def test_llm_comment_online(monkeypatch: pytest.MonkeyPatch) -> None:
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
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        result = asyncio.run(mod._llm_comment(1.23))

    assert result == "online"
    assert not m_chat.called


def test_llm_comment_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback to local LLM when ``OPENAI_API_KEY`` is empty."""
    mod = importlib.import_module(MODULE)

    class DummyAgent:
        def __init__(self, *_a: object, **_k: object) -> None:  # pragma: no cover - should not run
            raise AssertionError("should not be instantiated")

        async def __call__(self, prompt: str) -> str:  # pragma: no cover - should not run
            raise AssertionError("should not be called")

    monkeypatch.setattr(mod, "OpenAIAgent", DummyAgent)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setattr(mod.local_llm, "chat", lambda _p: "fallback")

    result = asyncio.run(mod._llm_comment(0.1))

    assert result == "fallback"


def test_run_cycle_async_logs_delta_g(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """One cycle should log the computed ΔG value."""
    mod = importlib.import_module(MODULE)

    caplog.set_level(logging.INFO)

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
            a2a_socket=None,
        )
    )

    assert any("ΔG" in r.getMessage() for r in caplog.records)


def test_main_subprocess(tmp_path: Path) -> None:
    """The maintained module entry point must produce an actual enterprise dossier."""
    stub = tmp_path / "check_env.py"
    stub.write_text("def main(args=None):\n    pass\n")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "dummy"
    env["PYTHONPATH"] = f"{tmp_path}:{STUB_DIR}:{ROOT}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.alpha_agi_business_3_v1",
            "--case",
            "industrial",
            "--output",
            str(tmp_path / "results"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert len(list((tmp_path / "results").glob("*/dossier.json"))) == 1


def test_cli_entrypoint(tmp_path: Path) -> None:
    """The console-entry module must execute rather than silently importing and exiting."""
    stub = tmp_path / "check_env.py"
    stub.write_text("def main(args=None):\n    pass\n")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "dummy"
    env["PYTHONPATH"] = f"{tmp_path}:{STUB_DIR}:{ROOT}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.demos.alpha_agi_business_3_v1.cli",
            "--case",
            "industrial",
            "--output",
            str(tmp_path / "results"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert len(list((tmp_path / "results").glob("*/dossier.json"))) == 1


def test_main_stops_a2a(monkeypatch: pytest.MonkeyPatch) -> None:
    """The A2A socket should start and stop when the loop exits."""
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
    monkeypatch.setattr(mod, "A2ASocket", lambda *a, **k: dummy)
    monkeypatch.setattr(mod, "ADKClient", None)
    monkeypatch.setattr(mod, "check_env", types.SimpleNamespace(main=lambda *_a, **_k: None), raising=False)
    monkeypatch.setenv("A2A_PORT", "1234")

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    asyncio.run(mod.main(["--cycles", "1", "--interval", "0", "--enable-integrations"]))

    assert dummy.started
    assert dummy.stopped
    assert mod._A2A is dummy


def test_run_cycle_posts_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """`post_alpha_job` should be called once when ΔG < 0."""
    mod = importlib.import_module(MODULE)

    orchestrator = mod.Orchestrator()
    fin = mod.AgentFin()
    res = mod.AgentRes()
    ene = mod.AgentEne()
    gdl = mod.AgentGdl()
    model = mod.Model()

    # dataclasses with ``slots=True`` disallow setting new attributes on
    # instances. Patch the method on the class instead so it works across
    # implementations.
    monkeypatch.setattr(type(orchestrator), "collect_signals", lambda self: {})
    monkeypatch.setattr(type(fin), "latent_work", lambda self, _b: 0.0)
    monkeypatch.setattr(type(res), "entropy", lambda self, _b: 1.0)
    monkeypatch.setattr(type(ene), "market_temperature", lambda self, _b: 1.0)

    calls: list[tuple[str, float]] = []

    def _post(bundle_id: str, delta_g: float) -> None:
        calls.append((bundle_id, delta_g))

    monkeypatch.setattr(type(orchestrator), "post_alpha_job", lambda self, b, d: _post(b, d))

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    asyncio.run(
        mod.run_cycle_async(
            orchestrator,
            fin,
            res,
            ene,
            gdl,
            model,
            a2a_socket=None,
        )
    )

    assert len(calls) == 1
    expected_hash = hashlib.sha256(json.dumps({}, sort_keys=True).encode()).hexdigest()[:8]
    assert calls[0] == (expected_hash, -1.0)


def test_bundle_hash_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bundle hash should remain stable across invocations."""
    mod = importlib.import_module(MODULE)

    orchestrator = mod.Orchestrator()
    fin = mod.AgentFin()
    res = mod.AgentRes()
    ene = mod.AgentEne()
    gdl = mod.AgentGdl()
    model = mod.Model()

    monkeypatch.setattr(type(fin), "latent_work", lambda self, _b: 0.0)
    monkeypatch.setattr(type(res), "entropy", lambda self, _b: 1.0)
    monkeypatch.setattr(type(ene), "market_temperature", lambda self, _b: 1.0)

    calls: list[str] = []

    def _post(bundle_id: str, delta_g: float) -> None:
        calls.append(bundle_id)

    monkeypatch.setattr(type(orchestrator), "post_alpha_job", lambda self, b, d: _post(b, d))

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    monkeypatch.setattr(type(orchestrator), "collect_signals", lambda self: dict([("b", 2), ("a", 1)]))
    asyncio.run(mod.run_cycle_async(orchestrator, fin, res, ene, gdl, model, a2a_socket=None))

    monkeypatch.setattr(type(orchestrator), "collect_signals", lambda self: dict([("a", 1), ("b", 2)]))
    asyncio.run(mod.run_cycle_async(orchestrator, fin, res, ene, gdl, model, a2a_socket=None))

    assert len(calls) == 2
    assert calls[0] == calls[1]


def test_cli_flags_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI options should set env vars for the runtime helpers."""
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "check_env", types.SimpleNamespace(main=lambda *_a, **_k: None), raising=False)

    captured: dict[str, str] = {}

    async def _llm(_: float) -> str:
        captured["api_key"] = os.getenv("OPENAI_API_KEY") or ""
        return "ok"

    class DummyADK:
        def __init__(self, host: str) -> None:  # pragma: no cover - init only
            captured["adk_host"] = host

        async def __aexit__(self, *_a: object, **_kw: object) -> None:  # pragma: no cover - close only
            pass

        def close(self) -> None:  # pragma: no cover - close only
            pass

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


def test_cli_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI options should override preset environment variables."""
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "check_env", types.SimpleNamespace(main=lambda *_a, **_k: None), raising=False)

    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("ADK_HOST", "http://env-adk:8")
    monkeypatch.setenv("A2A_PORT", "1234")
    monkeypatch.setenv("A2A_HOST", "env-host")
    monkeypatch.setenv("LOCAL_LLM_URL", "http://env-llm")
    monkeypatch.setenv("LLAMA_MODEL_PATH", "/env/model.gguf")
    monkeypatch.setenv("LLAMA_N_CTX", "99")

    captured: dict[str, Any] = {}

    async def _llm(_: float) -> str:
        captured["api_key"] = os.getenv("OPENAI_API_KEY")
        captured["local_llm_url"] = os.getenv("LOCAL_LLM_URL")
        captured["llama_model_path"] = os.getenv("LLAMA_MODEL_PATH")
        captured["llama_n_ctx"] = os.getenv("LLAMA_N_CTX")
        return "ok"

    class DummyADK:
        def __init__(self, host: str) -> None:  # pragma: no cover - init only
            captured["adk_host"] = host

        async def __aexit__(self, *_a: object, **_kw: object) -> None:  # pragma: no cover - close only
            pass

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
                "--local-llm-url",
                "http://cli-llm",
                "--llama-model-path",
                "/cli/model.gguf",
                "--llama-n-ctx",
                "120",
            ]
        )
    )

    assert captured["api_key"] == "cli-key"
    assert captured["adk_host"] == "http://cli-adk:9"
    assert captured["a2a"] == "cli-host:7777"
    assert captured["local_llm_url"] == "http://cli-llm"
    assert captured["llama_model_path"] == "/cli/model.gguf"
    assert captured["llama_n_ctx"] == "120"


def test_run_cycle_closes_adk_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """`run_cycle_async` should close the ADK client when available."""
    mod = importlib.import_module(MODULE)

    class DummyADK:
        def __init__(self) -> None:
            self.closed = False

        async def run(self, _msg: str) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    orchestrator = mod.Orchestrator()
    fin = mod.AgentFin()
    res = mod.AgentRes()
    ene = mod.AgentEne()
    gdl = mod.AgentGdl()
    model = mod.Model()

    monkeypatch.setattr(type(orchestrator), "collect_signals", lambda self: {})
    monkeypatch.setattr(type(fin), "latent_work", lambda self, _b: 0.0)
    monkeypatch.setattr(type(res), "entropy", lambda self, _b: 1.0)
    monkeypatch.setattr(type(ene), "market_temperature", lambda self, _b: 1.0)

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    adk = DummyADK()
    asyncio.run(
        mod.run_cycle_async(
            orchestrator,
            fin,
            res,
            ene,
            gdl,
            model,
            adk,
            a2a_socket=None,
        )
    )

    assert adk.closed


def test_main_closes_adk_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main` should close the ADK client when the loop exits."""
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(mod, "check_env", types.SimpleNamespace(main=lambda *_a, **_k: None), raising=False)

    class DummyADK:
        def __init__(self, *_a: object, **_kw: object) -> None:
            self.closed = False

        async def run(self, _msg: str) -> None:
            pass

        async def __aexit__(self, *_a: object, **_k: object) -> None:
            self.closed = True

    class DummySock:
        def __init__(self) -> None:
            self.started = False
            self.stopped = False

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stopped = True

        def sendjson(self, *_a: object, **_kw: object) -> None:
            pass

    adk = DummyADK()
    dummy_sock = DummySock()
    monkeypatch.setattr(mod, "ADKClient", lambda *_a, **_kw: adk)
    monkeypatch.setattr(mod, "A2ASocket", lambda *a, **k: dummy_sock)

    async def _llm(_: float) -> str:
        return "ok"

    monkeypatch.setattr(mod, "_llm_comment", _llm)

    asyncio.run(mod.main(["--cycles", "2", "--interval", "0", "--adk-host", "http://test-adk", "--a2a-port", "1234"]))

    assert mod._A2A is dummy_sock
    assert mod._A2A.stopped
    assert adk.closed


def test_run_cycle_uses_asyncio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """`run_cycle` should call ``asyncio.run`` when no loop is running."""
    mod = importlib.import_module(MODULE)

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError()))

    called: dict[str, Any] = {}

    def fake_run(coro: Any) -> None:
        called["coro"] = coro

    monkeypatch.setattr(asyncio, "run", fake_run)

    async def dummy_cycle(*_a: object, **_k: object) -> None:
        pass

    monkeypatch.setattr(mod, "run_cycle_async", dummy_cycle)

    mod.run_cycle(mod.Orchestrator(), mod.AgentFin(), mod.AgentRes(), mod.AgentEne(), mod.AgentGdl(), mod.Model())

    assert called.get("coro") is not None
    coro = called["coro"]
    assert getattr(coro, "cr_code", None) is dummy_cycle.__code__
    coro.close()


def test_run_cycle_creates_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """`run_cycle` should schedule a task when called from within a loop."""
    mod = importlib.import_module(MODULE)

    class DummyLoop:
        def __init__(self) -> None:
            self.coro: Any | None = None

        def create_task(self, coro: Any) -> None:
            self.coro = coro

    dummy_loop = DummyLoop()
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)
    monkeypatch.setattr(asyncio, "run", lambda _coro: (_ for _ in ()).throw(AssertionError("run called")))

    async def dummy_cycle(*_a: object, **_k: object) -> None:
        pass

    monkeypatch.setattr(mod, "run_cycle_async", dummy_cycle)

    mod.run_cycle(mod.Orchestrator(), mod.AgentFin(), mod.AgentRes(), mod.AgentEne(), mod.AgentGdl(), mod.Model())

    assert dummy_loop.coro is not None
    assert getattr(dummy_loop.coro, "cr_code", None) is dummy_cycle.__code__
    dummy_loop.coro.close()


def test_import_never_opens_inherited_a2a_port(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = types.ModuleType("a2a")
    dummy.A2ASocket = mock.Mock(side_effect=AssertionError("Import opened a socket"))
    monkeypatch.setitem(sys.modules, "a2a", dummy)
    monkeypatch.setenv("A2A_PORT", "12345")
    monkeypatch.delitem(sys.modules, MODULE, raising=False)
    mod = importlib.import_module(MODULE)
    assert mod._A2A is None
    dummy.A2ASocket.assert_not_called()


def test_verifier_fails_closed_and_model_retains_only_nonempty_proposals() -> None:
    mod = importlib.import_module(MODULE)
    assert mod.AgentGdl().provable({"proposal": 1}) is False
    assert mod.AgentGdl(lambda _: True).provable({}) is False
    assert mod.AgentGdl(lambda _: 1).provable({"proposal": 1}) is False
    assert mod.AgentGdl(lambda _: True).provable({"proposal": 1}) is True
    assert mod.AgentGdl(lambda _: 1 / 0).provable({"proposal": 1}) is False
    model = mod.Model()
    with pytest.raises(ValueError, match="empty"):
        model.commit({})
    proposal = {"candidate": [1, 2]}
    model.commit(proposal)
    proposal["candidate"].append(3)
    assert model.proposals == [{"candidate": [1, 2]}]


def test_default_research_run_ignores_inherited_integrations(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = importlib.import_module(MODULE)
    for key, value in {"A2A_PORT": "12345", "ADK_HOST": "https://unused.invalid", "OPENAI_API_KEY": "unused"}.items():
        monkeypatch.setenv(key, value)
    forbidden = mock.Mock(side_effect=AssertionError("Integration ran without opt-in"))
    monkeypatch.setattr(mod, "ADKClient", forbidden)
    monkeypatch.setattr(mod, "A2ASocket", forbidden)
    monkeypatch.setattr(mod, "_llm_comment", forbidden)
    asyncio.run(mod.main(["--cycles", "2", "--interval", "0"]))
    forbidden.assert_not_called()


def test_research_main_restores_environment_even_when_cycle_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = importlib.import_module(MODULE)
    monkeypatch.setenv("OPENAI_API_KEY", "original")
    monkeypatch.delenv("LLAMA_N_CTX", raising=False)

    async def fail(*_args, **_kwargs):
        assert os.environ["OPENAI_API_KEY"] == "temporary"
        raise RuntimeError("requested failure")

    monkeypatch.setattr(mod, "run_cycle_async", fail)
    with pytest.raises(RuntimeError, match="requested failure"):
        asyncio.run(mod.main(["--openai-api-key", "temporary", "--llama-n-ctx", "256"]))
    assert os.environ["OPENAI_API_KEY"] == "original"
    assert "LLAMA_N_CTX" not in os.environ


def test_adk_client_is_live_for_every_cycle_and_closed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = importlib.import_module(MODULE)
    events = []

    class Client:
        def __init__(self, _host):
            self.closed = False

        async def run(self, _message):
            assert not self.closed
            events.append("run")

        async def close(self):
            assert not self.closed
            self.closed = True
            events.append("close")

    monkeypatch.setattr(mod, "ADKClient", Client)
    asyncio.run(mod.main(["--cycles", "3", "--interval", "0", "--adk-host", "local-fixture"]))
    assert events == ["run", "run", "run", "close"]


@pytest.mark.parametrize(
    "arguments",
    [["--cycles", "-1"], ["--interval", "nan"], ["--interval", "-1"], ["--a2a-port", "65536"], ["--llama-n-ctx", "0"]],
)
def test_invalid_research_options_fail_before_inference(monkeypatch: pytest.MonkeyPatch, arguments: list[str]) -> None:
    mod = importlib.import_module(MODULE)
    forbidden = mock.Mock(side_effect=AssertionError("Invalid settings executed"))
    monkeypatch.setattr(mod, "run_cycle_async", forbidden)
    with pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main(arguments))
    assert exc.value.code == 2
    forbidden.assert_not_called()


def test_requested_local_model_failure_is_not_reported_as_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = importlib.import_module(MODULE)
    monkeypatch.setattr(mod.local_llm, "chat", lambda _: "[offline] unavailable")
    with pytest.raises(RuntimeError, match="did not load"):
        asyncio.run(mod.main(["--commentary", "local", "--llama-model-path", "/missing/model.gguf"]))


def test_standalone_cycle_closes_owned_client_when_requested_model_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = importlib.import_module(MODULE)
    client = types.SimpleNamespace(close=mock.AsyncMock())
    monkeypatch.setattr(mod, "_llm_comment", mock.AsyncMock(side_effect=RuntimeError("provider failure")))
    with pytest.raises(RuntimeError, match="provider failure"):
        asyncio.run(
            mod.run_cycle_async(
                mod.Orchestrator(),
                mod.AgentFin(),
                mod.AgentRes(),
                mod.AgentEne(),
                mod.AgentGdl(),
                mod.Model(),
                adk_client=client,
            )
        )
    client.close.assert_awaited_once()
