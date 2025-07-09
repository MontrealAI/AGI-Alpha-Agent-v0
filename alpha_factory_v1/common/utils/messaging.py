# SPDX-License-Identifier: Apache-2.0
"""Lightweight pub/sub bus used by the agents.

Envelopes are published to in-memory subscribers and optionally forwarded via
gRPC or Kafka. Use :class:`A2ABus` to subscribe handlers and to start the
optional transport servers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import contextlib
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, TypeAlias
from cachetools import TTLCache

from .config import Settings
from google.protobuf import json_format
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from alpha_factory_v1.core.utils.tracing import span, bus_messages_total
    from alpha_factory_v1.core.utils import a2a_pb2 as pb

    Envelope: TypeAlias = pb.Envelope
else:  # pragma: no cover - runtime fallback
    Envelope: TypeAlias = Any


class EnvelopeLike(Protocol):
    sender: str
    recipient: str
    ts: float
    payload: Any
    __dict__: Dict[str, Any]


try:
    import grpc
except ModuleNotFoundError:  # pragma: no cover - optional
    grpc = None

try:  # pragma: no cover - optional broker
    from aiokafka import AIOKafkaProducer
except ModuleNotFoundError:  # pragma: no cover - broker optional
    AIOKafkaProducer = None


logger = logging.getLogger(__name__)


class A2ABus:
    """In-memory pub/sub with best-effort gRPC transport."""

    PROTO_VERSION = "proto_schema=1"

    HANDSHAKE_TTL = 60

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._subs: Dict[str, List[Callable[[EnvelopeLike], Awaitable[None] | None]]] = {}
        self._server: "grpc.aio.Server | None" = None
        self._producer: Optional[AIOKafkaProducer] = None
        self._handshake_peers: set[str] = set()
        self._handshake_failures: TTLCache[str, int] = TTLCache(maxsize=1024, ttl=self.HANDSHAKE_TTL)
        self._handshake_nonces: TTLCache[str, None] = TTLCache(maxsize=1024, ttl=self.HANDSHAKE_TTL)

    async def __aenter__(self) -> "A2ABus":
        """Start the bus when entering an async context."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the bus when exiting an async context."""
        await self.stop()

    def subscribe(self, topic: str, handler: Callable[[EnvelopeLike], Awaitable[None] | None]) -> None:
        self._subs.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[EnvelopeLike], Awaitable[None] | None]) -> None:
        """Remove a previously subscribed handler."""
        handlers = self._subs.get(topic)
        if not handlers:
            return
        with contextlib.suppress(ValueError):
            handlers.remove(handler)
        if not handlers:
            self._subs.pop(topic, None)

    def publish(self, topic: str, env: EnvelopeLike) -> None:
        from alpha_factory_v1.core.utils.tracing import span, bus_messages_total
        from alpha_factory_v1.core.utils import a2a_pb2 as pb

        with span("bus.publish"):
            bus_messages_total.labels(topic).inc()
            if self._producer:
                if isinstance(env, pb.Envelope):
                    payload = json_format.MessageToDict(env, preserving_proto_field_name=True)
                else:  # support SimpleNamespace in tests
                    payload = env.__dict__
                data = json.dumps(payload).encode()
                asyncio.create_task(self._producer.send_and_wait(topic, data))
            for h in list(self._subs.get(topic, [])):
                try:
                    res = h(env)
                    if asyncio.iscoroutine(res):
                        try:
                            asyncio.get_running_loop().create_task(res)
                        except RuntimeError:  # pragma: no cover - sync context
                            asyncio.run(res)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "handler error %s -> %s on %s",
                        env.sender,
                        env.recipient,
                        topic,
                    )

    async def _fail_handshake(self, peer: str, context: Any) -> bytes:
        """Record a handshake failure and abort if the limit is exceeded."""
        count = self._handshake_failures.get(peer, 0) + 1
        self._handshake_failures[peer] = count
        if count >= self.settings.bus_fail_limit:
            if grpc:
                await context.abort(grpc.StatusCode.PERMISSION_DENIED, "too many handshake failures")
            return b"denied"
        if grpc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "handshake required")
        return b"handshake required"

    async def _handle_rpc(self, request: bytes, context: Any) -> bytes:
        text = request.decode()
        peer = context.peer() if grpc else ""
        if peer not in self._handshake_peers:
            parts = text.strip().split()
            if len(parts) != 2 or parts[0] != self.PROTO_VERSION:
                return await self._fail_handshake(peer, context)
            nonce = parts[1]
            if nonce in self._handshake_nonces:
                return await self._fail_handshake(peer, context)
            self._handshake_nonces[nonce] = None
            self._handshake_peers.add(peer)
            if grpc and hasattr(context, "add_callback"):
                context.add_callback(lambda: self._handshake_peers.discard(peer))
            return self.PROTO_VERSION.encode()
        data = json.loads(text)
        token = data.pop("token", None)
        if self.settings.bus_token and token != self.settings.bus_token:
            if grpc:
                await context.abort(grpc.StatusCode.PERMISSION_DENIED, "unauthenticated")
            return b"denied"
        env = Envelope(
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            ts=float(data.get("ts", 0.0)),
        )
        if isinstance(data.get("payload"), dict):
            env.payload.update(data["payload"])
        self.publish(env.recipient, env)
        if grpc and hasattr(context, "add_callback"):
            context.add_callback(lambda: self._handshake_peers.discard(peer))
        return b"ok"

    async def start(self) -> None:
        logger.info(
            "A2ABus.start() called: port=%s broker=%s",
            self.settings.bus_port,
            self.settings.broker_url or "disabled",
        )
        self._handshake_peers.clear()
        self._handshake_failures.clear()
        self._handshake_nonces.clear()
        if self.settings.broker_url and AIOKafkaProducer:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.settings.broker_url)
            await self._producer.start()

        if not self.settings.bus_port or grpc is None:
            return
        server = grpc.aio.server()
        method = grpc.unary_unary_rpc_method_handler(
            self._handle_rpc,
            request_deserializer=lambda b: b,
            response_serializer=lambda b: b,
        )
        service = grpc.method_handlers_generic_handler("bus.Bus", {"Send": method})
        server.add_generic_rpc_handlers((service,))
        if self.settings.bus_cert and self.settings.bus_key:
            key = Path(self.settings.bus_key).read_bytes()
            crt = Path(self.settings.bus_cert).read_bytes()
            creds = grpc.ssl_server_credentials(((key, crt),))
            server.add_secure_port(f"[::]:{self.settings.bus_port}", creds)
        elif self.settings.allow_insecure:
            server.add_insecure_port(f"[::]:{self.settings.bus_port}")
        else:
            raise RuntimeError("AGI_INSIGHT_BUS_CERT and AGI_INSIGHT_BUS_KEY are required")
        await server.start()
        self._server = server

    async def stop(self) -> None:
        logger.info(
            "A2ABus.stop() called: port=%s broker=%s",
            self.settings.bus_port,
            self.settings.broker_url or "disabled",
        )
        if self._server:
            await self._server.stop(0)
            self._server = None
        if self._producer:
            await self._producer.stop()
            self._producer = None
        self._handshake_peers.clear()
        self._handshake_failures.clear()
        self._handshake_nonces.clear()
