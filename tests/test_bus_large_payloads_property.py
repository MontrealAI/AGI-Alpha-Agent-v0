# SPDX-License-Identifier: Apache-2.0
"""Property-based tests for large payload handling in :class:`A2ABus`."""

from __future__ import annotations

import asyncio
import os
import types
from unittest import mock

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from alpha_factory_v1.common.utils import config, messaging  # noqa: E402


_CI_LIMITED = bool(os.getenv("CI")) or bool(os.getenv("PYTEST_MEM_MB"))
_SENDER_MAX_SIZE = 4_096 if _CI_LIMITED else 8_192
_RECIPIENT_MAX_SIZE = 4_096 if _CI_LIMITED else 8_192
_PAYLOAD_MAX_SIZE = 8_192 if _CI_LIMITED else 16_384


@settings(max_examples=5, deadline=None)
@given(
    sender=st.text(min_size=1, max_size=_SENDER_MAX_SIZE),
    recipient=st.text(min_size=1, max_size=_RECIPIENT_MAX_SIZE),
    payload_text=st.text(min_size=1, max_size=_PAYLOAD_MAX_SIZE),
    ts=st.floats(
        min_value=-1e308,
        max_value=1e308,
        allow_infinity=False,
        allow_nan=False,
    ),
)
def test_large_payloads_delivered_intact(
    sender: str,
    recipient: str,
    payload_text: str,
    ts: float,
) -> None:  # type: ignore[misc]
    """Envelopes with huge strings should round-trip through the bus."""

    bus = messaging.A2ABus(config.Settings(bus_port=0))
    received: list[messaging.Envelope] = []

    def handler(env: messaging.Envelope) -> None:
        received.append(env)

    bus.subscribe(recipient, handler)
    env = messaging.Envelope(sender=sender, recipient=recipient, ts=ts)
    env.payload["data"] = payload_text
    bus.publish(recipient, env)

    assert received
    assert received[0].sender == sender
    assert received[0].recipient == recipient
    assert received[0].payload["data"] == payload_text
    assert received[0].ts == ts


invalid_values = st.one_of(st.builds(object), st.builds(set, st.lists(st.integers())))


@settings(max_examples=10, deadline=None)
@given(bad=invalid_values)
def test_publish_invalid_payload_errors(bad: object) -> None:  # type: ignore[misc]
    """Non-JSON payloads should raise ``TypeError`` during publish."""

    class Prod:
        def __init__(self, bootstrap_servers: str) -> None:
            pass

        async def start(self) -> None:
            return None

        async def send_and_wait(self, topic: str, data: bytes) -> None:
            return None

        async def stop(self) -> None:
            return None

    cfg = config.Settings(bus_port=0, broker_url="k:1")
    with mock.patch.object(messaging, "AIOKafkaProducer", Prod):

        async def run() -> None:
            async with messaging.A2ABus(cfg) as bus:
                env = types.SimpleNamespace(sender="s", recipient="x", payload={"bad": bad}, ts=0.0)
                with pytest.raises(TypeError):
                    bus.publish("x", env)
                    await asyncio.sleep(0)

        asyncio.run(run())
