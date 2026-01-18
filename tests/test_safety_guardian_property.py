# SPDX-License-Identifier: Apache-2.0
"""Property-based tests for SafetyGuardianAgent."""

from __future__ import annotations

import asyncio
import pathlib
import tempfile
from unittest import mock

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402
from hypothesis.strategies import composite  # noqa: E402

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import safety_agent  # noqa: E402
from alpha_factory_v1.common.utils import config, messaging  # noqa: E402
from alpha_factory_v1.common.utils import logging as insight_logging  # noqa: E402


class DummyBus:
    def __init__(self, settings: config.Settings) -> None:
        self.settings = settings
        self.published: list[tuple[str, messaging.Envelope]] = []

    def publish(self, topic: str, env: messaging.Envelope) -> None:
        self.published.append((topic, env))

    def subscribe(self, topic: str, handler) -> None:  # pragma: no cover - dummy
        pass


class DummyLedger:
    def __init__(self) -> None:
        self.logged: list[messaging.Envelope] = []

    def log(self, env: messaging.Envelope) -> None:  # type: ignore[override]
        self.logged.append(env)

    def start_merkle_task(self, *a, **kw) -> None:  # pragma: no cover - dummy
        pass

    async def stop_merkle_task(self) -> None:  # pragma: no cover - interface
        pass

    def close(self) -> None:  # pragma: no cover - dummy
        pass


@settings(max_examples=30)
@given(code=st.text(min_size=0, max_size=100).map(lambda s: f"import os{s}"))
def test_blocks_import_os(code: str) -> None:
    bus = DummyBus(config.Settings(bus_port=0))
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    env = messaging.Envelope(
        sender="codegen",
        recipient="safety",
        payload={"code": code},
        ts=0.0,
    )
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "blocked"


@settings(max_examples=30)
@given(code=st.text(min_size=0, max_size=100).map(lambda s: s.replace("import os", "import_os")))
def test_allows_safe_code(code: str) -> None:
    bus = DummyBus(config.Settings(bus_port=0))
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    env = messaging.Envelope(
        sender="codegen",
        recipient="safety",
        payload={"code": code},
        ts=0.0,
    )
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "ok"


json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=20),
)

json_values = st.recursive(
    json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=3),
        st.dictionaries(st.text(min_size=1, max_size=5), children, max_size=3),
    ),
    max_leaves=5,
)


@composite
def payloads(draw: st.DrawFn, include_code: bool, malicious: bool = False) -> dict[str, object]:
    extra = draw(st.dictionaries(st.text(min_size=1, max_size=5), json_values, max_size=3))
    if include_code:
        code = draw(st.text(min_size=0, max_size=100))
        if malicious:
            code = f"import os{code}"
        else:
            code = code.replace("import os", "import_os")
        extra["code"] = code
        return extra
    return extra


@settings(max_examples=25)
@given(
    sender=st.text(max_size=5),
    recipient=st.text(max_size=5),
    ts=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    payload=payloads(include_code=True, malicious=True),
)
def test_fuzz_envelope_blocks_malicious(sender: str, recipient: str, ts: float, payload: dict[str, object]) -> None:
    bus = DummyBus(config.Settings(bus_port=0))
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    env = messaging.Envelope(sender=sender, recipient=recipient, payload=payload, ts=ts)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "blocked"


@settings(max_examples=25)
@given(
    sender=st.text(max_size=5),
    recipient=st.text(max_size=5),
    ts=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    payload=payloads(include_code=True, malicious=False),
)
def test_fuzz_envelope_allows_safe(sender: str, recipient: str, ts: float, payload: dict[str, object]) -> None:
    bus = DummyBus(config.Settings(bus_port=0))
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    env = messaging.Envelope(sender=sender, recipient=recipient, payload=payload, ts=ts)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "ok"


@settings(max_examples=20)
@given(payload=payloads(include_code=False))
def test_missing_code_defaults_to_ok(payload: dict[str, object]) -> None:
    bus = DummyBus(config.Settings(bus_port=0))
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    env = messaging.Envelope(sender="src", recipient="safety", payload=payload, ts=0.0)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "ok"


def _dummy_classes():
    captured: dict[str, str] = {}

    class DummyClient:
        def __init__(self, url: str) -> None:
            captured["url"] = url

        async def send_transaction(self, tx: object, *args: object) -> None:
            captured["data"] = tx.instructions[0].data.decode()

        async def close(self) -> None:  # pragma: no cover - dummy
            pass

    class DummyTx:
        def __init__(self) -> None:
            self.instructions: list[object] = []

        def add(self, instr: object) -> "DummyTx":
            self.instructions.append(instr)
            return self

    class DummyInstr:
        def __init__(self, program_id: object, data: bytes, keys: list[object]):
            self.data = data

    class DummyPk:
        def __init__(self, val: str) -> None:  # pragma: no cover - dummy
            pass

    return captured, DummyClient, DummyTx, DummyInstr, DummyPk


@settings(max_examples=10)
@given(count=st.integers(min_value=0, max_value=3), broadcast=st.booleans())
def test_broadcast_merkle_root_property(count: int, broadcast: bool) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        led = insight_logging.Ledger(str(tmp_path / "l.db"), rpc_url="http://rpc.test", broadcast=broadcast)
        for i in range(count):
            env = messaging.Envelope(
                sender=f"s{i}",
                recipient=f"r{i}",
                payload={"v": i},
                ts=float(i),
            )
            led.log(env)
        root = led.compute_merkle_root()
        captured, DummyClient, DummyTx, DummyInstr, DummyPk = _dummy_classes()
        with (
            mock.patch.object(insight_logging, "AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "Transaction", DummyTx, create=True),
            mock.patch.object(insight_logging, "TransactionInstruction", DummyInstr, create=True),
            mock.patch.object(insight_logging, "PublicKey", DummyPk, create=True),
        ):
            asyncio.run(led.broadcast_merkle_root())
        if broadcast:
            assert captured["url"] == "http://rpc.test"
            assert captured["data"] == root
        else:
            assert captured == {}
