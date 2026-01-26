# SPDX-License-Identifier: Apache-2.0
"""Fuzz tests for :class:`A2ABus` envelope handling."""

from __future__ import annotations

import asyncio
import string
import types
from typing import Any

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402
from hypothesis.strategies import composite  # noqa: E402

from alpha_factory_v1.common.utils import config, messaging  # noqa: E402


INT_BOUND = 1000
FLOAT_BOUND = 1e6
SAFE_TEXT_ALPHABET = string.ascii_letters + string.digits + string.punctuation + " "

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-INT_BOUND, max_value=INT_BOUND),
    st.floats(min_value=-FLOAT_BOUND, max_value=FLOAT_BOUND, allow_nan=False, allow_infinity=False),
    st.text(alphabet=SAFE_TEXT_ALPHABET, max_size=20),
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
def envelopes(draw: st.DrawFn) -> messaging.Envelope | types.SimpleNamespace:
    as_proto = draw(st.booleans())
    big_payload = draw(st.booleans())
    if as_proto:
        sender = draw(st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=0, max_size=5))
        recipient = draw(st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=0, max_size=5))
        ts = draw(st.floats(min_value=-FLOAT_BOUND, max_value=FLOAT_BOUND, allow_nan=False, allow_infinity=False))
        payload: dict[str, Any] = draw(
            st.dictionaries(
                st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=1, max_size=5),
                json_values,
                max_size=3,
            )
        )
        if big_payload:
            payload["data"] = draw(st.text(alphabet=SAFE_TEXT_ALPHABET, max_size=500))
        env = messaging.Envelope(sender=sender, recipient=recipient, ts=ts)
        env.payload.update(payload)
        return env
    sender = draw(
        st.one_of(
            st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=0, max_size=5),
            st.integers(min_value=-INT_BOUND, max_value=INT_BOUND),
            st.none(),
        )
    )
    recipient = draw(
        st.one_of(
            st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=0, max_size=5),
            st.integers(min_value=-INT_BOUND, max_value=INT_BOUND),
            st.none(),
        )
    )
    ts = draw(
        st.one_of(
            st.floats(min_value=-FLOAT_BOUND, max_value=FLOAT_BOUND, allow_nan=False, allow_infinity=False),
            st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=0, max_size=5),
            st.none(),
        )
    )
    payload = draw(
        st.dictionaries(
            st.text(alphabet=SAFE_TEXT_ALPHABET, min_size=1, max_size=5),
            st.one_of(json_values, st.text(alphabet=SAFE_TEXT_ALPHABET, max_size=500)),
            max_size=3,
        )
    )
    return types.SimpleNamespace(sender=sender, recipient=recipient, payload=payload, ts=ts)


@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow], deadline=5000)
@given(env=envelopes())
def test_bus_handles_arbitrary_envelopes(env: messaging.Envelope | types.SimpleNamespace) -> None:
    """Publishing arbitrary envelopes should not raise exceptions."""

    bus = messaging.A2ABus(config.Settings(bus_port=0))
    received: list[object] = []

    def handler(e: object) -> None:
        received.append(e)

    bus.subscribe("x", handler)
    bus.publish("x", env)
    assert received


def test_bus_extreme_envelopes() -> None:
    """Large or malformed messages should not crash the bus."""

    bus = messaging.A2ABus(config.Settings(bus_port=0))
    received: list[object] = []

    def handler(env: object) -> None:
        received.append(env)

    bus.subscribe("x", handler)
    for size in (0, 1, 100, 1000, 5000, 10000):
        env = messaging.Envelope(sender="s" * size, recipient="x", ts=1e308)
        env.payload["data"] = "p" * size
        bus.publish("x", env)
    bus.publish("x", messaging.Envelope(sender="", recipient="x", ts=float("inf")))
    bus.publish("x", messaging.Envelope(sender="", recipient="x", ts=float("-inf")))
    bus.publish("x", types.SimpleNamespace(sender=None, recipient="x", payload={}, ts=None))
    assert received


def test_bus_async_handler_runs() -> None:
    """Async handlers should execute when published from an async context."""

    bus = messaging.A2ABus(config.Settings(bus_port=0))
    received: list[object] = []
    delivered = asyncio.Event()

    async def handler(env: object) -> None:
        received.append(env)
        delivered.set()

    bus.subscribe("x", handler)

    async def run() -> None:
        bus.publish("x", messaging.Envelope(sender="s", recipient="x", ts=0.0))
        await asyncio.wait_for(delivered.wait(), timeout=5)

    asyncio.run(run())
    assert received
