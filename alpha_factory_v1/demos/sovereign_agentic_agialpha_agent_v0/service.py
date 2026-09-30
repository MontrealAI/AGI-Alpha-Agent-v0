# SPDX-License-Identifier: Apache-2.0
"""Authenticated loopback console; no arbitrary tool, path, provider or shell routes."""
from __future__ import annotations

import json
from pathlib import Path
import secrets
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from alpha_factory_v1.core.runtime.api import Control, RequestBoundary, Review
from alpha_factory_v1.core.runtime.store import Conflict, Journal, public_error

from .models import Mandate
from .workbench import Workbench

ROOT = Path(__file__).parent
MAX_FILE_BYTES = 4 * 1024 * 1024


def parse_json(raw: str) -> Any:
    """Reject duplicate fields and non-finite numbers before validating schemas."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def constant(_value: str) -> None:
        raise ValueError("Non-finite JSON value")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def read_json(path: Path) -> Any:
    """Bound CLI imports without trusting reported file size."""
    with path.open("rb") as source:
        raw = source.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("JSON input exceeds 4 MiB")
    return parse_json(raw.decode("utf-8"))


def examples() -> dict[str, Any]:
    """Load the packaged, explicitly synthetic operational mandates."""
    value: dict[str, Any] = json.loads((ROOT / "examples.json").read_text(encoding="utf-8"))
    return value


def create_app(journal: Journal) -> FastAPI:
    """Reuse the maintained runtime's body/origin boundary and durable execution engine."""
    bench = Workbench(journal)
    app = FastAPI(title="Sovereign Workbench", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.add_middleware(RequestBoundary)
    token = (journal.root / "api.token").read_bytes().strip()

    def authorize(authorization: str = Header(default="")) -> None:
        if not secrets.compare_digest(authorization.encode(), b"Bearer " + token):
            raise HTTPException(401, "Unlock with the access code printed by your local launcher")

    @app.exception_handler(Conflict)
    async def conflict(_request: Request, exc: Conflict) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing(_request: Request, _exc: KeyError) -> JSONResponse:
        return JSONResponse({"error": "Workflow not found; refresh the workspace"}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"error": public_error(exc)}, status_code=422)

    async def body(request: Request) -> Any:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            raise HTTPException(415, "Send application/json")
        try:
            return parse_json((await request.body()).decode("utf-8"))
        except (UnicodeError, RecursionError) as exc:
            raise ValueError("Malformed JSON input") from exc

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(ROOT / "web/index.html")

    @app.get("/app.js")
    def javascript() -> FileResponse:
        return FileResponse(ROOT / "web/app.js", media_type="application/javascript")

    @app.get("/style.css")
    def stylesheet() -> FileResponse:
        return FileResponse(ROOT / "web/style.css", media_type="text/css")

    @app.get("/examples.json")
    def sample_inputs() -> dict[str, Any]:
        return examples()

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "local_operator_review"}

    @app.get("/api/status", dependencies=[Depends(authorize)])
    def status() -> dict[str, Any]:
        return {
            **journal.verify(),
            "public_key": journal.public,
            "control": journal.latest("@control")["state"],
            "workflows": bench.list(),
            "model": journal.config.llm_model or "No model · deterministic analytical tools",
        }

    @app.post("/api/workflows", dependencies=[Depends(authorize)], status_code=201)
    async def create(request: Request) -> dict[str, Any]:
        value = await body(request)
        if not isinstance(value, dict) or set(value) != {"id", "mandate"} or not isinstance(value["id"], str):
            raise ValueError("Expected a request ID and mandate")
        return bench.create(Mandate.model_validate(value["mandate"]), value["id"])

    @app.post("/api/validate", dependencies=[Depends(authorize)])
    async def validate(request: Request) -> dict[str, Any]:
        return Mandate.model_validate(await body(request)).model_dump()

    @app.get("/api/workflows/{ident}", dependencies=[Depends(authorize)])
    def show(ident: str) -> dict[str, Any]:
        return bench.snapshot(ident)

    @app.post("/api/workflows/{ident}/advance", dependencies=[Depends(authorize)])
    def advance(ident: str) -> dict[str, Any]:
        try:
            return bench.advance(ident)
        except (Conflict, ValueError, KeyError):
            raise
        except Exception as exc:
            raise HTTPException(
                502, "Execution failed. Refresh to inspect retained state; recover before retrying."
            ) from exc

    @app.post("/api/workflows/{ident}/review", dependencies=[Depends(authorize)])
    async def review(ident: str, request: Request) -> dict[str, Any]:
        decision = Review.model_validate(await body(request))
        return bench.review(ident, decision.revision, decision.result_hash, decision.approve, decision.note)

    @app.post("/api/workflows/{ident}/recover", dependencies=[Depends(authorize)])
    def recover(ident: str) -> dict[str, Any]:
        return bench.recover(ident)

    @app.get("/api/workflows/{ident}/export", dependencies=[Depends(authorize)])
    def export(ident: str) -> dict[str, Any]:
        return bench.export(ident)

    @app.post("/api/control", dependencies=[Depends(authorize)])
    async def control(request: Request) -> dict[str, Any]:
        decision = Control.model_validate(await body(request))
        return journal.control(decision.state == "paused")

    return app
