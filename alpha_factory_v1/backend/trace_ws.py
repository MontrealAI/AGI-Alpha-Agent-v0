# SPDX-License-Identifier: Apache-2.0
# backend/trace_ws.py
"""
ASGI WebSocket hub for live Trace‑graph events
=============================================

*   Mounts a high‑performance WebSocket endpoint at **/ws/trace**.
*   In‑memory fan‑out; swapping to Redis / NATS later is a one‑class change.
*   **CSRF‑aware**: the client must fetch ``/api/csrf`` and echo the token
    as the *very first* frame; otherwise the server closes with *4401*.

Schema
------
Outbound messages follow the *TraceEvent* model::

    {
        "id":   "uuid4‑hex",            # unique node id
        "ts":   1713612345.123,         # POSIX seconds
        "type": "tool_call|planner",    # enum
        "label":"User‑friendly label",  # ≤128 chars
        "edges":["uuid3", ...]          # optional parents
    }

Quick‑start
-----------
>>> from backend.trace_ws import hub, attach
>>> attach(fastapi_app)
>>> await hub.broadcast({"label": "order sent", "type": "tool_call"})
"""

from __future__ import annotations

import asyncio
import time
import typing as _t
from dataclasses import dataclass, field, asdict
from importlib import import_module
from uuid import uuid4

# Tokens expire after this many seconds
TOKEN_TTL = 300


def prune_expired_tokens(buffer: dict[str, float]) -> None:
    """Remove tokens older than ``TOKEN_TTL`` from *buffer*."""
    now = time.time()
    expired = [t for t, ts in buffer.items() if now - ts > TOKEN_TTL]
    for t in expired:
        buffer.pop(t, None)


# --------------------------------------------------------------------- #
# Zero‑copy JSON → bytes helper                                         #
# --------------------------------------------------------------------- #
try:
    import orjson as _json

    def _dumps(obj: _t.Any) -> bytes:  # noqa: D401
        return _json.dumps(obj)

except ModuleNotFoundError:  # pragma: no cover
    import json as _json

    def _dumps(obj: _t.Any) -> bytes:  # noqa: D401
        return _json.dumps(obj).encode()


# --------------------------------------------------------------------- #
# Public dataclass for events                                           #
# --------------------------------------------------------------------- #
@dataclass(slots=True, frozen=True)
class TraceEvent:
    """Immutable, hash‑able trace event with optional metadata."""

    id: str = field(default_factory=lambda: uuid4().hex)
    ts: float = field(default_factory=time.time)
    type: str = "generic"
    label: str = ""
    edges: list[str] | None = None
    meta: dict[str, _t.Any] | None = None

    # cache serialisation; fastest path for broadcast
    def to_bytes(self) -> bytes:  # noqa: D401
        return _dumps(asdict(self))


# --------------------------------------------------------------------- #
# Hub                                                                   #
# --------------------------------------------------------------------- #
class TraceHub:
    """In‑process broadcast hub (fan‑out)."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[bytes]] = set()
        self._lock = asyncio.Lock()

    # ------------- subscription management --------------------------- #
    async def subscribe(self) -> asyncio.Queue[bytes]:
        """Return a queue that will receive broadcast messages."""
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[bytes]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    # ------------------- broadcasting -------------------------------- #
    async def broadcast(self, event: TraceEvent | dict[str, _t.Any]) -> None:
        """
        Send *event* to every live WebSocket.

        *event* may be a ``TraceEvent`` or a raw ``dict`` matching the schema.
        The call returns immediately (fire‑and‑forget).
        """
        if isinstance(event, dict):
            event = TraceEvent(**event)  # type: ignore[arg-type]
        payload = event.to_bytes()

        async with self._lock:
            targets = list(self._subscribers)  # snapshot under lock

        coros: list[_t.Coroutine[_t.Any, _t.Any, _t.Any]] = []
        for q in targets:
            # back‑pressure: drop oldest if queue is full
            if q.full():
                try:
                    _ = q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            coros.append(q.put(payload))

        if coros:  # schedule fan‑out concurrently, don’t await in caller
            asyncio.create_task(
                asyncio.gather(*coros, return_exceptions=True),
            )


# Singleton – imported by other modules
hub = TraceHub()


# --------------------------------------------------------------------- #
# FastAPI / Starlette integration                                       #
# --------------------------------------------------------------------- #
def attach(app, prefix: str = "") -> None:  # noqa: D401
    """
    Dynamically mount the ``/ws/trace`` WebSocket endpoint on *app*.

    ```python
    from fastapi import FastAPI
    from backend.trace_ws import attach

    fast = FastAPI()
    attach(fast)
    ```
    """

    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.routing import APIRouter

    # Import the CSRF token buffer exposed by backend.__init__
    _api_buffer: dict[str, float] = import_module("backend")._api_buffer  # type: ignore[attr-defined]

    router = APIRouter(prefix=prefix)

    @router.websocket("/ws/trace")
    async def _trace_ws(websocket: WebSocket):
        """
        WebSocket stream with race‑free, CSRF‑checked loop.

        A shielded gather prevents the rare disconnect race where the
        client closes exactly between queue.put() and websocket.send_bytes().
        """
        # -----------------------------------------------------------------
        # ▼ secure: require the very first frame to echo the CSRF token
        #    (token was fetched by the front‑end from /api/csrf)
        # -----------------------------------------------------------------
        await websocket.accept()
        queue = await hub.subscribe()

        try:
            # first frame **must** be {"csrf": "<token>"}
            init = await websocket.receive_json()
            # prune expired tokens before validation
            prune_expired_tokens(_api_buffer)
            if not (isinstance(init, dict) and "csrf" in init and init["csrf"] in _api_buffer):
                await websocket.close(code=4401)  # 4401 = “unauthorised”
                return

            _api_buffer.pop(init["csrf"], None)  # single‑use token

            ping_task: asyncio.Task | None = asyncio.create_task(websocket.receive_text())
            queue_task: asyncio.Task | None = asyncio.create_task(queue.get())

            while True:
                done, _ = await asyncio.wait(
                    {ping_task, queue_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if queue_task in done:
                    payload = queue_task.result()
                    try:
                        await websocket.send_bytes(payload)
                    finally:
                        # immediately replace consumed task
                        queue_task = asyncio.create_task(queue.get())

                if ping_task in done:
                    try:
                        _ = ping_task.result()  # ignore payload
                    finally:
                        ping_task = asyncio.create_task(websocket.receive_text())

        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        finally:
            for task in (ping_task, queue_task):
                if task is not None:
                    task.cancel()
            await hub.unsubscribe(queue)

    app.include_router(router)
