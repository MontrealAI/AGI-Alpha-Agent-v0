# SPDX-License-Identifier: Apache-2.0
"""Basic pub/sub behavior for :class:`A2ABus`."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from alpha_factory_v1.common.utils import config, messaging


def test_publish_to_async_subscriber() -> None:
    """Envelopes published to a subscribed coroutine should be delivered."""
    bus = messaging.A2ABus(config.Settings(bus_port=0))
    received: list[messaging.Envelope] = []

    async def handler(env: messaging.Envelope) -> None:
        received.append(env)

    bus.subscribe("x", handler)
    env = messaging.Envelope(sender="a", recipient="x", payload={"v": 42}, ts=0.0)

    async def run() -> None:
        bus.publish("x", env)
        await asyncio.sleep(0)  # allow handler task to run

    asyncio.run(run())
    assert len(received) == 1
    assert received[0].payload["v"] == 42


def test_start_stop_logging(caplog: Any) -> None:
    """Bus start and stop should emit informative log messages."""

    async def run() -> None:
        async with messaging.A2ABus(config.Settings(bus_port=0, broker_url="kafka:9092")):
            pass

    with caplog.at_level(logging.INFO):
        asyncio.run(run())

    messages = [record.getMessage() for record in caplog.records]
    assert any("A2ABus.start()" in m for m in messages)
    assert any("A2ABus.stop()" in m for m in messages)
