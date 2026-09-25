# SPDX-License-Identifier: Apache-2.0
"""Lightweight RPC façade exposed over HTTP."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .logger import get_logger


RPC_HOST = os.getenv("RPC_HOST", "0.0.0.0")
RPC_PORT = int(os.getenv("RPC_PORT", "8000"))
_ORIGINS = os.getenv("RPC_CORS_ORIGINS", "*")
_ORIGIN_LIST: List[str] = [o.strip() for o in _ORIGINS.split(",")]

log = get_logger(__name__)

app = FastAPI(title="Alpha‑Factory RPC", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGIN_LIST,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Task(BaseModel):
    """RPC payload accepted via :class:`POST /rpc`."""

    agent: str = Field(..., description="Target agent name")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task body")


class Ack(BaseModel):
    """Acknowledgement returned to the caller."""

    status: str
    agent: str


@app.get("/healthz", response_model=str)
async def healthcheck() -> str:
    """Simple liveness probe."""

    return "ok"


@app.post("/rpc", response_model=Ack, status_code=202)
async def rpc(task: Task) -> Ack:
    """Acknowledge incoming task."""

    log.info("Task for agent %s accepted", task.agent)
    return Ack(status="accepted", agent=task.agent)


def serve() -> None:
    """Run the RPC server with `uvicorn`."""

    uvicorn.run("alpha_factory_v1.backend.rpc_server:app", host=RPC_HOST, port=RPC_PORT)


if __name__ == "__main__":
    serve()
