# SPDX-License-Identifier: Apache-2.0
"""Fuzz tests for SafetyGuardianAgent."""

from __future__ import annotations

import asyncio

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402
from hypothesis.strategies import composite  # noqa: E402

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import safety_agent  # noqa: E402
from alpha_factory_v1.common.utils import config, messaging  # noqa: E402


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
def malformed_envelopes(draw: st.DrawFn) -> messaging.Envelope:
    sender = draw(st.one_of(st.text(max_size=5), st.integers(), st.none()))
    recipient = draw(st.one_of(st.text(max_size=5), st.integers(), st.none()))
    ts = draw(st.floats(allow_nan=False, allow_infinity=False))
    payload = draw(st.dictionaries(st.text(min_size=1, max_size=5), json_values, max_size=3))
    code = draw(st.text(min_size=0, max_size=100).map(lambda s: "import os" + s))
    payload["code"] = code
    return messaging.Envelope(sender=sender, recipient=recipient, payload=payload, ts=ts)


@settings(max_examples=25)
@given(env=malformed_envelopes())
def test_fuzz_blocks_malformed(env: messaging.Envelope) -> None:
    bus = DummyBus(config.Settings(bus_port=0))
    led = DummyLedger()
    agent = safety_agent.SafetyGuardianAgent(bus, led)
    asyncio.run(agent.handle(env))
    assert bus.published[-1][1].payload["status"] == "blocked"
