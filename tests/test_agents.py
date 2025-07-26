# SPDX-License-Identifier: Apache-2.0
import asyncio
from queue import Queue
from unittest.mock import patch
import contextlib

import json
import socket
from datetime import datetime, timedelta
from pathlib import Path

import grpc
import pytest

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    HAVE_CRYPTO = True
except Exception:  # pragma: no cover - optional
    HAVE_CRYPTO = False

from alpha_factory_v1.backend import agents
from alpha_factory_v1.backend.agents import registry as agents_registry
from alpha_factory_v1.backend.agents.base import AgentBase


class DummyHB(AgentBase):
    NAME = "dummy_hb"
    CAPABILITIES = ["x"]

    async def step(self) -> None:
        return None


def test_agent_registration_and_heartbeat() -> None:
    meta = agents.AgentMetadata(
        name=DummyHB.NAME,
        cls=DummyHB,
        version="0.1",
        capabilities=DummyHB.CAPABILITIES,
        compliance_tags=[],
    )
    q: Queue = Queue()
    with patch.object(agents, "_HEALTH_Q", q), patch.object(agents_registry, "_HEALTH_Q", q):
        agents.register_agent(meta)
        agent = agents.get_agent("dummy_hb")
        asyncio.run(agent.step())
        name, _, ok = q.get(timeout=1)
        assert name == "dummy_hb"
        assert ok
    agents.AGENT_REGISTRY.pop("dummy_hb", None)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("localhost", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _make_cert(tmp: Path) -> tuple[str, str, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), False)
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    cert_path = tmp / "cert.pem"
    key_path = tmp / "key.pem"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)
    return str(cert_path), str(key_path), cert_pem


@pytest.mark.skipif(not HAVE_CRYPTO, reason="cryptography not installed")
def test_grpc_bus_tls_message_exchange(tmp_path: Path) -> None:
    from alpha_factory_v1.common.utils import config, messaging

    port = _free_port()
    cert, key, ca = _make_cert(tmp_path)
    cfg = config.Settings(bus_port=port, bus_cert=cert, bus_key=key, bus_token="tok")
    received: list[messaging.Envelope] = []

    async def run() -> None:
        async with messaging.A2ABus(cfg) as bus:
            bus.subscribe("b", lambda e: received.append(e))
            creds = grpc.ssl_channel_credentials(root_certificates=ca)
            async with grpc.aio.secure_channel(f"localhost:{port}", creds) as ch:
                stub = ch.unary_unary("/bus.Bus/Send")
                await stub(f"{messaging.A2ABus.PROTO_VERSION} n1".encode())
                payload = {
                    "sender": "a",
                    "recipient": "b",
                    "payload": {"v": 1},
                    "ts": 0.0,
                    "token": "tok",
                }
                await stub(json.dumps(payload).encode())
            await asyncio.sleep(0.05)

    asyncio.run(run())
    assert received and received[0].payload["v"] == 1


@pytest.mark.skipif(not HAVE_CRYPTO, reason="cryptography not installed")
def test_grpc_bus_tls_bad_token(tmp_path: Path) -> None:
    from alpha_factory_v1.common.utils import config, messaging

    port = _free_port()
    cert, key, ca = _make_cert(tmp_path)
    cfg = config.Settings(bus_port=port, bus_cert=cert, bus_key=key, bus_token="tok")

    async def run() -> None:
        async with messaging.A2ABus(cfg):
            creds = grpc.ssl_channel_credentials(root_certificates=ca)
            async with grpc.aio.secure_channel(f"localhost:{port}", creds) as ch:
                stub = ch.unary_unary("/bus.Bus/Send")
                await stub(f"{messaging.A2ABus.PROTO_VERSION} n2".encode())
                payload = {
                    "sender": "a",
                    "recipient": "b",
                    "payload": {},
                    "ts": 0.0,
                    "token": "bad",
                }
                with pytest.raises(grpc.aio.AioRpcError):
                    await stub(json.dumps(payload).encode())

    asyncio.run(run())


def test_monitor_restart_and_ledger_log(monkeypatch) -> None:
    from alpha_factory_v1.core.agents.base_agent import BaseAgent
    from alpha_factory_v1.core import orchestrator
    from alpha_factory_v1.backend.orchestrator_utils import monitor_agents
    from alpha_factory_v1.core.utils import config

    events: list[str] = []

    class DummyLedger:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def log(self, env) -> None:  # type: ignore[override]
            events.append(env.payload.get("event") if hasattr(env.payload, "get") else env.payload["event"])

        def start_merkle_task(self, *_a, **_kw) -> None:
            pass

        async def stop_merkle_task(self) -> None:
            pass

        def close(self) -> None:
            pass

    settings = config.Settings(bus_port=0)

    class FreezeAgent(BaseAgent):
        """Agent whose run_cycle blocks."""

        NAME = "freeze"
        CYCLE_SECONDS = 0.1

        def __init__(self, bus, ledger) -> None:  # type: ignore[override]
            super().__init__("freeze", bus, ledger)

        async def run_cycle(self) -> None:
            await asyncio.sleep(999)

        async def handle(self, _env) -> None:  # pragma: no cover - test helper
            pass

    monkeypatch.setattr(orchestrator, "Ledger", DummyLedger)
    monkeypatch.setattr(orchestrator.Orchestrator, "_init_agents", lambda self: [FreezeAgent(self.bus, self.ledger)])

    orch = orchestrator.Orchestrator(settings)
    runner = orch.runners["freeze"]

    async def run() -> None:
        async with orch.bus:
            runner.start(orch.bus, orch.ledger)
            monitor = asyncio.create_task(
                monitor_agents(
                    orch.runners,
                    orch.bus,
                    orch.ledger,
                    err_threshold=orchestrator.ERR_THRESHOLD,
                    backoff_exp_after=orchestrator.BACKOFF_EXP_AFTER,
                    on_restart=orch._record_restart,
                )
            )
            await asyncio.sleep(5)
            monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor
            if runner.task:
                runner.task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner.task

    asyncio.run(run())
    assert "restart" in events


def test_research_agent_adapters_invoked(monkeypatch) -> None:
    from alpha_factory_v1.common.utils import config, messaging
    from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import research_agent

    class DummyLedger:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def log(self, _env) -> None:  # type: ignore[override]
            pass

        def start_merkle_task(self, *_a, **_kw) -> None:
            pass

        async def stop_merkle_task(self) -> None:
            pass

        def close(self) -> None:
            pass

    settings = config.Settings(bus_port=0)
    bus = messaging.A2ABus(settings)
    agent = research_agent.ResearchAgent(bus, DummyLedger())

    adk_mock = type("A", (), {"heartbeat": lambda self: None})()
    mcp_mock = type("M", (), {"heartbeat": lambda self: None})()
    monkeypatch.setattr(agent, "adk", adk_mock, raising=False)
    monkeypatch.setattr(agent, "mcp", mcp_mock, raising=False)
    with patch.object(adk_mock, "heartbeat") as adk_hb, patch.object(mcp_mock, "heartbeat") as mcp_hb:
        asyncio.run(agent.run_cycle())
        adk_hb.assert_called_once()
        mcp_hb.assert_called_once()


def test_codegen_agent_sandbox_blocks_import(monkeypatch) -> None:
    from alpha_factory_v1.common.utils import config, messaging
    from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import codegen_agent

    class DummyLedger:
        def __init__(self, *_a, **_kw) -> None:
            self.records: list[messaging.Envelope] = []

        def log(self, env) -> None:  # type: ignore[override]
            self.records.append(env)

        def start_merkle_task(self, *_a, **_kw) -> None:
            pass

        async def stop_merkle_task(self) -> None:
            pass

        def close(self) -> None:
            pass

    settings = config.Settings(bus_port=0, openai_api_key="k")
    bus = messaging.A2ABus(settings)
    ledger = DummyLedger()
    agent = codegen_agent.CodeGenAgent(bus, ledger)

    agent.execute_in_sandbox("import os\nprint('hi')")
    errs = [r.payload.get("stderr", "") for r in ledger.records if "stderr" in r.payload]
    assert errs and "ImportError" in errs[-1]


def test_planning_agent_no_openai_sdk() -> None:
    """Agent should run even when openai.agents is missing."""
    from alpha_factory_v1.common.utils import config, messaging
    from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import planning_agent

    class DummyLedger:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def log(self, _env) -> None:  # type: ignore[override]
            pass

        def start_merkle_task(self, *_a, **_kw) -> None:
            pass

        async def stop_merkle_task(self) -> None:
            pass

        def close(self) -> None:
            pass

    settings = config.Settings(bus_port=0, openai_api_key="k")
    bus = messaging.A2ABus(settings)
    agent = planning_agent.PlanningAgent(bus, DummyLedger())

    assert agent.oai_ctx is None
    asyncio.run(agent.run_cycle())


def test_base_agent_no_openai_sdk(monkeypatch) -> None:
    """BaseAgent should fall back when ``openai.agents`` is unavailable."""
    import builtins
    import importlib
    import sys

    from alpha_factory_v1.common.utils import config, messaging

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai.agents":
            raise ModuleNotFoundError
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    if "alpha_factory_v1.core.agents.base_agent" in sys.modules:
        del sys.modules["alpha_factory_v1.core.agents.base_agent"]
    base_agent = importlib.import_module("alpha_factory_v1.core.agents.base_agent")

    class DummyLedger:
        def log(self, _env) -> None:  # type: ignore[override]
            pass

        def start_merkle_task(self, *_a, **_kw) -> None:
            pass

        async def stop_merkle_task(self) -> None:
            pass

        def close(self) -> None:
            pass

    bus = messaging.A2ABus(config.Settings(bus_port=0))
    agent = base_agent.BaseAgent("base", bus, DummyLedger())
    assert agent.oai_ctx is None
