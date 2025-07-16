import asyncio
import json
from unittest import mock
from alpha_factory_v1.backend.trace_ws import TraceHub, TraceEvent


async def _run_broadcast():
    hub = TraceHub()
    q = await hub.subscribe()
    with mock.patch("alpha_factory_v1.backend.trace_ws.asyncio.create_task", asyncio.ensure_future):
        await hub.broadcast({"label": "hi", "type": "tool_call"})
        await asyncio.sleep(0)
    payload = await asyncio.wait_for(q.get(), timeout=1)
    await hub.unsubscribe(q)
    return json.loads(payload.decode())


def test_tracehub_broadcast():
    event = asyncio.run(_run_broadcast())
    assert event["label"] == "hi"
    assert event["type"] == "tool_call"


async def _run_unsubscribe():
    hub = TraceHub()
    q = await hub.subscribe()
    await hub.unsubscribe(q)
    with mock.patch("alpha_factory_v1.backend.trace_ws.asyncio.create_task", asyncio.ensure_future):
        await hub.broadcast(TraceEvent(label="bye"))
        await asyncio.sleep(0.1)
    assert q.empty()


def test_unsubscribe_stops_delivery():
    asyncio.run(_run_unsubscribe())
