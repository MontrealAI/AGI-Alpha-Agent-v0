# SPDX-License-Identifier: Apache-2.0
"""Authenticated local operator API with review and recovery controls."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .engine import Engine
from .models import Mission, StrictModel
from .store import Conflict, Journal


MAX_REQUEST_BYTES = 512 * 1024
BODY_TIMEOUT_SECONDS = 15.0
SECURITY_HEADERS = {
    b"cache-control": b"no-store",
    b"x-content-type-options": b"nosniff",
    b"referrer-policy": b"no-referrer",
    b"content-security-policy": (
        b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        b"connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
}


class RequestBoundary:
    """Bound actual incoming bytes and time before a mutation reaches the application."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() not in SECURITY_HEADERS]
                message = {**message, "headers": [*headers, *SECURITY_HEADERS.items()]}
            await send(message)

        async def reject(status: int, error: str) -> None:
            await JSONResponse({"error": error}, status_code=status)(scope, receive, secure_send)

        if scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, secure_send)
            return
        lengths = [v for k, v in scope["headers"] if k.lower() == b"content-length"]
        if len(lengths) > 1 or any(k.lower() == b"transfer-encoding" for k, _ in scope["headers"]):
            await reject(400, "Ambiguous request framing")
            return
        if not lengths or not lengths[0].isdigit():
            await reject(411, "Valid Content-Length required")
            return
        if len(lengths[0]) > 20 or int(lengths[0]) > MAX_REQUEST_BYTES:
            await reject(413, "Request exceeds 512 KiB")
            return
        request = Request(scope)
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            await reject(403, "Cross-origin mutation denied")
            return
        chunks: list[bytes] = []
        received = 0
        try:
            async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    received += len(chunk)
                    if received > MAX_REQUEST_BYTES:
                        await reject(413, "Request exceeds 512 KiB")
                        return
                    if received > int(lengths[0]):
                        await reject(400, "Request length mismatch")
                        return
                    chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await reject(408, "Request body timed out")
            return
        if received != int(lengths[0]):
            await reject(400, "Request length mismatch")
            return
        body = b"".join(chunks)
        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, secure_send)


class Review(StrictModel):
    """Bind an operator decision to one exact result."""

    revision: int = Field(ge=1)
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    approve: bool
    note: str = Field(min_length=1, max_length=2000)


class Control(StrictModel):
    """A persistent execution switch."""

    state: Literal["paused", "ready"]


def create_app(journal: Journal) -> FastAPI:
    """Create an app; bearer tokens are never embedded in HTML or URLs."""
    engine = Engine(journal)
    app = FastAPI(title="$AGIALPHA Agent", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
    app.add_middleware(RequestBoundary)
    token = (journal.root / "api.token").read_text().strip()
    static = Path(__file__).with_name("web")

    def authorize(authorization: str = Header(default="")) -> None:
        if not secrets.compare_digest(authorization.encode("utf-8"), f"Bearer {token}".encode("utf-8")):
            raise HTTPException(401, "Access token required")

    @app.exception_handler(Conflict)
    async def conflict_handler(_request: Request, exc: Conflict) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing_handler(_request: Request, _exc: KeyError) -> JSONResponse:
        return JSONResponse({"error": "Mission not found"}, status_code=404)

    @app.exception_handler(ValueError)
    async def input_handler(_request: Request, _exc: ValueError) -> JSONResponse:
        return JSONResponse({"error": "Input or evidence verification failed"}, status_code=422)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static / "index.html")

    @app.get("/app.js")
    def javascript() -> FileResponse:
        return FileResponse(static / "app.js", media_type="application/javascript")

    @app.get("/style.css")
    def stylesheet() -> FileResponse:
        return FileResponse(static / "style.css", media_type="text/css")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status", dependencies=[Depends(authorize)])
    def status() -> dict[str, Any]:
        from alpha_factory_v1 import __version__

        return {
            "version": __version__,
            "name": journal.config.name,
            **journal.verify(),
            "control": journal.latest("@control")["state"],
            "inference": journal.config.llm_model or "Extractive research · no model configured",
            "capabilities": ["research", "allocation", "schedule", "forecast", "code"],
            "code_execution_enabled": journal.config.allow_code_execution,
            "chain_configured": journal.config.chain is not None,
        }

    @app.get("/api/missions", dependencies=[Depends(authorize)])
    def missions() -> list[dict[str, Any]]:
        return journal.missions()

    @app.post("/api/missions", dependencies=[Depends(authorize)], status_code=201)
    def submit(mission: Mission, idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
        return journal.submit(mission, idempotency_key)

    @app.get("/api/missions/{ident}", dependencies=[Depends(authorize)])
    def get(ident: str) -> dict[str, Any]:
        return journal.latest(ident)

    @app.post("/api/missions/{ident}/execute", dependencies=[Depends(authorize)])
    def execute(ident: str) -> dict[str, Any]:
        try:
            return engine.execute(ident)
        except (Conflict, ValueError, KeyError):
            raise
        except Exception as exc:
            raise HTTPException(502, "Execution failed; inspect the retained mission state") from exc

    @app.post("/api/missions/{ident}/review", dependencies=[Depends(authorize)])
    def review(ident: str, decision: Review) -> dict[str, Any]:
        return engine.review(ident, decision.revision, decision.result_hash, decision.approve, decision.note)

    @app.post("/api/missions/{ident}/recover", dependencies=[Depends(authorize)])
    def recover(ident: str) -> dict[str, Any]:
        return engine.recover(ident)

    @app.get("/api/missions/{ident}/export", dependencies=[Depends(authorize)])
    def export(ident: str) -> dict[str, Any]:
        return engine.export(ident)

    @app.post("/api/control", dependencies=[Depends(authorize)])
    def control(request: Control) -> dict[str, Any]:
        return journal.control(request.state == "paused")

    return app
