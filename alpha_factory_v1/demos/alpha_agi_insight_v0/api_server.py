#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded local Insight API; requests cannot select providers or server paths."""
from __future__ import annotations

import argparse
import hmac
import json
import os
from pathlib import Path
import sys
from threading import Lock
from typing import Literal

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

try:
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel, ConfigDict, Field, ValidationError
    from starlette.concurrency import run_in_threadpool
    import uvicorn
except ImportError as exc:
    FastAPI = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from .discovery import MAX_BYTES, evaluate, parse
from .insight_demo import DEFAULT_SECTORS, parse_sectors, run

if FastAPI is not None:
    app = FastAPI(title="Insight v0 — local discovery and search", version="1.0.0")
    _busy = Lock()

    class InsightRequest(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        episodes: int = Field(default=5, ge=1, le=500)
        exploration: float = Field(default=1.4, ge=0, le=10, allow_inf_nan=False)
        rewriter: Literal["random"] = "random"
        target: int = Field(default=3, ge=-10_000, le=10_000)
        seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
        model: None = None
        sectors: str | list[str] | None = None

    async def payload(request: Request, limit: int) -> object:
        token = os.getenv("API_TOKEN", "")
        if token and not hmac.compare_digest(
            request.headers.get("authorization", "").encode("utf-8"), ("Bearer " + token).encode("utf-8")
        ):
            raise HTTPException(401, "A valid bearer token is required")
        if request.headers.get("origin"):
            raise HTTPException(403, "Browser cross-origin requests are not supported; use the offline workbench")
        if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
            raise HTTPException(415, "Use application/json")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > limit:
                raise HTTPException(413, "Request exceeds the documented byte limit")
            data.extend(chunk)
        try:
            return parse(bytes(data))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "offline"}

    @app.get("/sectors")
    def list_sectors() -> list[str]:
        return list(DEFAULT_SECTORS)

    @app.post("/insight")
    async def insight(request: Request) -> dict:
        source = await payload(request, 16_000)
        try:
            req = InsightRequest.model_validate(source)
            # No environment or file-path resolution occurs for API input.
            sectors = parse_sectors(req.sectors, None, allow_files=False, use_env=False)
        except (ValidationError, ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        if not _busy.acquire(blocking=False):
            raise HTTPException(429, "A calculation is already running", headers={"Retry-After": "1"})
        try:
            result = await run_in_threadpool(
                run,
                req.episodes,
                req.exploration,
                "random",
                target=req.target,
                seed=req.seed,
                sectors=sectors,
                json_output=True,
                offline=True,
            )
            return json.loads(result)
        finally:
            _busy.release()

    @app.post("/discovery")
    async def discovery(request: Request) -> dict:
        source = await payload(request, MAX_BYTES)
        if not _busy.acquire(blocking=False):
            raise HTTPException(429, "A calculation is already running", headers={"Retry-After": "1"})
        try:
            return await run_in_threadpool(evaluate, source)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            _busy.release()

else:
    app = None


def main(argv: list[str] | None = None) -> None:
    if FastAPI is None:
        raise SystemExit("FastAPI is required. Install the project dependencies.") from _IMPORT_ERROR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--skip-verify", action="store_true", help="Retained for compatibility; startup never installs dependencies"
    )
    parser.add_argument(
        "--allow-network", action="store_true", help="Explicitly permit a non-loopback bind; requires API_TOKEN"
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("Port must be from 1 through 65535")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and (
        not args.allow_network or len(os.getenv("API_TOKEN", "")) < 24
    ):
        parser.error("Non-loopback binding requires --allow-network and API_TOKEN of at least 24 characters")
    uvicorn.run(app, host=args.host, port=args.port, limit_concurrency=16, timeout_keep_alive=5)


if __name__ == "__main__":
    main()
