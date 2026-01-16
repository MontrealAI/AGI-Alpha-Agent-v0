# SPDX-License-Identifier: Apache-2.0
"""Wrapper around the REST and gRPC servers."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Dict, Optional

from ..api_server import start_servers


class APIServer:
    """Launch and manage the REST and gRPC API servers."""

    def __init__(
        self,
        runners: Dict[str, Any],
        model_max_bytes: int,
        mem: Any,
        rest_port: int,
        grpc_port: int,
        loglevel: str,
        ssl_disable: bool,
    ) -> None:
        self._runners = runners
        self._model_max_bytes = model_max_bytes
        self._mem = mem
        self._rest_port = rest_port
        self._grpc_port = grpc_port
        self._loglevel = loglevel
        self._ssl_disable = ssl_disable
        self._rest_task: Optional[asyncio.Task] = None
        self._rest_server: Optional[Any] = None
        self._grpc_server: Optional[Any] = None

    @property
    def rest_task(self) -> Optional[asyncio.Task]:
        return self._rest_task

    @property
    def grpc_server(self) -> Optional[Any]:
        return self._grpc_server

    async def start(self) -> None:
        self._rest_task, self._rest_server, self._grpc_server = await start_servers(
            self._runners,
            self._model_max_bytes,
            self._mem,
            self._rest_port,
            self._grpc_port,
            self._loglevel,
            self._ssl_disable,
        )

    async def stop(self) -> None:
        if self._rest_server:
            self._rest_server.should_exit = True
        if self._rest_task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._rest_task
        if self._grpc_server:
            await self._grpc_server.stop(0)
