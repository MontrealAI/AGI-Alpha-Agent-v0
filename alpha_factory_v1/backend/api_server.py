# SPDX-License-Identifier: Apache-2.0
"""REST and gRPC endpoints used by the orchestrator."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from types import SimpleNamespace

from .agent_runner import AgentRunner

with contextlib.suppress(ModuleNotFoundError):
    from fastapi import FastAPI, HTTPException, File, Request, Depends
    from fastapi.responses import PlainTextResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    import uvicorn

with contextlib.suppress(ModuleNotFoundError):
    import grpc

log = logging.getLogger(__name__)


# REST API ---------------------------------------------------------------


def build_rest(
    runners: Dict[str, AgentRunner],
    model_max_bytes: int = 10 * 1024 * 1024,
    mem: Any | None = None,
) -> Optional["FastAPI"]:
    if "FastAPI" not in globals():
        return None
    if mem is None:
        import sys

        for mod_name in ("alpha_factory_v1.backend.orchestrator", "backend.orchestrator"):
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "mem"):
                mem = mod.mem
                break
        if mem is None:
            mem = SimpleNamespace(
                vector=SimpleNamespace(
                    recent=lambda *_a, **_k: [],
                    search=lambda *_a, **_k: [],
                )
            )

    token = os.getenv("API_TOKEN")
    if not token:
        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            token = "test-token"
        else:
            raise RuntimeError("API_TOKEN environment variable must be set")

    security = HTTPBearer()

    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> None:
        if credentials.credentials != token:
            raise HTTPException(status_code=403, detail="Invalid token")

    app = FastAPI(
        title="Alpha-Factory Orchestrator",
        version="3.0.0",
        docs_url="/docs",
        redoc_url=None,
        dependencies=[Depends(verify_token)],
    )

    @app.get("/healthz", response_class=PlainTextResponse)
    async def _health() -> str:  # noqa: D401
        return "ok"

    @app.get("/agents")
    async def _agents() -> List[str]:  # noqa: D401
        return list(runners)

    @app.post("/agent/{name}/trigger")
    async def _trigger(name: str) -> Dict[str, bool]:  # noqa: D401
        if name not in runners:
            raise HTTPException(404, "Agent not found")
        runners[name].next_ts = 0
        return {"queued": True}

    upload_param = File(...) if "FastAPI" in globals() else None  # type: ignore

    @app.post("/agent/{name}/update_model")
    async def _update_model(request: Request, name: str, file: Optional[bytes] = upload_param) -> Dict[str, str]:
        if "FastAPI" not in globals() and file is None:
            file = await request.body()
        if name not in runners:
            raise HTTPException(404, "Agent not found")
        inst = runners[name].inst
        if not hasattr(inst, "load_weights"):
            raise HTTPException(501, "Agent does not support model updates")
        import io
        import stat
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(io.BytesIO(file)) as zf:
                base = Path(td).resolve()
                total = 0
                for info in zf.infolist():
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise HTTPException(400, "Symlinks not allowed")
                    if info.is_dir():
                        continue
                    total += info.file_size
                    if total > model_max_bytes:
                        raise HTTPException(400, "Archive too large")
                    dest = (base / info.filename).resolve()
                    if not str(dest).startswith(str(base)):
                        raise HTTPException(400, "Unsafe path in archive")
                    zf.extractall(td)
            inst.load_weights(td)  # type: ignore[attr-defined]
        return {"status": "ok"}

    @app.post("/agent/{name}/skill_test")  # type: ignore[misc]
    async def _skill_test(request: Request, name: str) -> Any:
        payload = await request.json()
        if name not in runners:
            raise HTTPException(404, "Agent not found")
        inst = runners[name].inst
        if not hasattr(inst, "skill_test"):
            raise HTTPException(501, "Agent does not support skill_test")
        return await inst.skill_test(payload)  # type: ignore[func-returns-value]

    @app.get("/memory/{agent}/recent")  # type: ignore[misc]
    async def _recent(agent: str, n: int = 25) -> Any:  # noqa: D401
        return mem.vector.recent(agent, n)

    @app.get("/memory/search")  # type: ignore[misc]
    async def _search(q: str, k: int = 5) -> Any:  # noqa: D401
        return mem.vector.search(q, k)

    @app.get("/metrics", response_class=PlainTextResponse)  # type: ignore[misc]
    async def _metrics() -> PlainTextResponse:  # noqa: D401
        if "generate_latest" not in globals():
            raise HTTPException(503, "prometheus_client not installed")
        from .telemetry import generate_latest, CONTENT_TYPE_LATEST

        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


# gRPC server ------------------------------------------------------------
async def serve_grpc(runners: Dict[str, AgentRunner], port: int, ssl_disable: bool) -> Optional["grpc.aio.Server"]:
    if not port or "grpc" not in globals():
        return None
    try:
        from backend.proto import a2a_pb2, a2a_pb2_grpc
    except ModuleNotFoundError:
        log.warning("A2A_PORT set but proto stubs missing – gRPC disabled")
        return None

    class Peer(a2a_pb2_grpc.PeerServiceServicer):  # type: ignore
        async def Stream(self, req_iter, ctx):  # noqa: N802
            async for req in req_iter:
                kind = req.WhichOneof("payload")
                if kind == "trigger" and req.trigger.name in runners:
                    runners[req.trigger.name].next_ts = 0
                    yield a2a_pb2.StreamReply(ack=a2a_pb2.Ack(id=req.id))
                elif kind == "status":
                    stats = [a2a_pb2.AgentStat(name=n, next_run=int(r.next_ts)) for n, r in runners.items()]
                    yield a2a_pb2.StreamReply(status_reply=a2a_pb2.StatusReply(stats=stats))

    creds = None
    if not ssl_disable:
        cert_dir = Path(os.getenv("TLS_CERT_DIR", "/certs"))
        crt, key = cert_dir / "server.crt", cert_dir / "server.key"
        if crt.exists() and key.exists():
            creds = grpc.ssl_server_credentials(((key.read_bytes(), crt.read_bytes()),))

    server = grpc.aio.server()
    a2a_pb2_grpc.add_PeerServiceServicer_to_server(Peer(), server)
    bind = f"[::]:{port}"
    server.add_secure_port(bind, creds) if creds else server.add_insecure_port(bind)
    await server.start()
    asyncio.create_task(server.wait_for_termination())
    log.info("gRPC A2A server listening on %s (%s)", bind, "TLS" if creds else "plaintext")
    return server


async def start_rest(app: Optional["FastAPI"], port: int, loglevel: str) -> Optional[asyncio.Task]:
    """Run the FastAPI app on the given port if dependencies are available."""

    if not app or "uvicorn" not in globals():
        return None
    cfg = uvicorn.Config(app, host="0.0.0.0", port=port, log_level=loglevel.lower())
    task = asyncio.create_task(uvicorn.Server(cfg).serve())
    log.info("REST UI →  http://localhost:%d/docs", port)
    return task


async def start_servers(
    runners: Dict[str, AgentRunner],
    model_max_bytes: int,
    mem: Any,
    rest_port: int,
    grpc_port: int,
    loglevel: str,
    ssl_disable: bool,
) -> tuple[Optional[asyncio.Task], Optional["grpc.aio.Server"]]:
    """Convenience helper to launch REST and gRPC services."""

    app = build_rest(runners, model_max_bytes, mem)
    rest_task = await start_rest(app, rest_port, loglevel)
    grpc_server = await serve_grpc(runners, grpc_port, ssl_disable)
    return rest_task, grpc_server


__all__ = [
    "build_rest",
    "serve_grpc",
    "start_rest",
    "start_servers",
]
