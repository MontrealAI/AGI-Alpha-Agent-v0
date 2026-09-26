# SPDX-License-Identifier: Apache-2.0
"""Exercise transport-edge failures against the real authenticated mission API."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from alpha_factory_v1.core.runtime import api
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal

ROOT = Path(__file__).resolve().parents[2]


async def request(
    journal: Journal,
    chunks: list[bytes],
    lengths: list[bytes],
    *,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    delay: float = 0,
    disconnect: bool = False,
) -> list[dict[str, Any]]:
    """Supply independent ASGI headers/chunks, which ordinary HTTP clients normalize."""
    token = (journal.root / "api.token").read_bytes()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http",
        "method": "POST",
        "path": "/api/missions",
        "raw_path": b"/api/missions",
        "query_string": b"",
        "root_path": "",
        "server": ("127.0.0.1", 8765),
        "client": ("127.0.0.1", 10000),
        "headers": [
            (b"host", b"127.0.0.1:8765"),
            (b"authorization", b"Bearer " + token),
            (b"content-type", b"application/json"),
            *((b"content-length", length) for length in lengths),
            *(extra_headers or []),
        ],
    }
    incoming = iter(chunks)
    sent: list[dict[str, Any]] = []
    consumed = 0

    async def receive() -> dict[str, Any]:
        nonlocal consumed
        if delay:
            await asyncio.sleep(delay)
        if consumed >= len(chunks):
            return {"type": "http.disconnect"}
        consumed += 1
        return {
            "type": "http.request",
            "body": next(incoming),
            "more_body": consumed < len(chunks) or disconnect,
        }

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await api.create_app(journal)(scope, receive, send)
    return sent


@pytest.mark.parametrize(
    ("chunks", "lengths", "headers", "status"),
    [
        ([b"{}"], [], [], 411),
        ([b"{}"], [b"-2"], [], 411),
        ([b"{}"], [b"\xb2"], [], 411),
        ([b"{}"], [b"2", b"2"], [], 400),
        ([b"{}"], [b"2"], [(b"transfer-encoding", b"chunked")], 400),
        ([b"{}"], [b"9" * 100], [], 413),
        ([b"{}"], [b"2"], [(b"origin", b"https://attacker.example")], 403),
        ([b"{", b"}"], [b"1"], [], 400),
        ([b"{}"], [b"3"], [], 400),
        ([b"x" * (api.MAX_REQUEST_BYTES + 1)], [b"2"], [], 413),
    ],
)
def test_rejected_framing_never_mutates_and_keeps_security_headers(
    tmp_path: Path, chunks: list[bytes], lengths: list[bytes], headers: list[tuple[bytes, bytes]], status: int
) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    before = journal.verify()
    messages = asyncio.run(request(journal, chunks, lengths, extra_headers=headers))
    start = next(message for message in messages if message["type"] == "http.response.start")
    assert start["status"] == status
    assert dict(start["headers"]).items() >= api.SECURITY_HEADERS.items()
    assert journal.verify() == before
    assert journal.missions() == []


def test_fragmented_valid_request_reaches_real_mission_validation(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    mission = Mission.model_validate_json((ROOT / "examples/missions/allocation.json").read_bytes())
    body = mission.model_dump_json().encode()
    messages = asyncio.run(request(journal, [body[:31], body[31:100], body[100:]], [str(len(body)).encode()]))
    assert next(message for message in messages if message["type"] == "http.response.start")["status"] == 201
    assert journal.missions()[0]["request"] == mission.model_dump()


def test_stalled_and_disconnected_uploads_leave_no_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    before = journal.verify()
    monkeypatch.setattr(api, "BODY_TIMEOUT_SECONDS", 0.01)
    messages = asyncio.run(request(journal, [b"{}"], [b"2"], delay=0.1))
    start = next(message for message in messages if message["type"] == "http.response.start")
    assert start["status"] == 408
    assert dict(start["headers"])[b"cache-control"] == b"no-store"
    assert asyncio.run(request(journal, [b"{"], [b"2"], disconnect=True)) == []
    assert journal.verify() == before


def test_auth_and_host_rejections_have_security_headers(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    with TestClient(api.create_app(journal)) as client:
        for response in [client.get("/api/status"), client.get("/", headers={"Host": "attacker.example"})]:
            assert response.status_code in {400, 401}
            assert response.headers["cache-control"] == "no-store"
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
