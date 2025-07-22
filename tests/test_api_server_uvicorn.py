# SPDX-License-Identifier: Apache-2.0
import os
import socket
import threading
import time
from typing import Iterator

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")
uvicorn = pytest.importorskip("uvicorn")

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def uvicorn_server() -> Iterator[str]:
    from alpha_factory_v1.core.interface import api_server

    port = _free_port()
    config = uvicorn.Config(api_server.app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_simulate_flow_uvicorn(uvicorn_server: str) -> None:
    url = uvicorn_server
    headers = {"Authorization": "Bearer test-token"}
    with httpx.Client(base_url=url) as client:
        r = client.post("/simulate", json={"horizon": 1, "pop_size": 2, "generations": 1}, headers=headers)
        assert r.status_code == 200
        sim_id = r.json()["id"]
        assert isinstance(sim_id, str) and sim_id
        for _ in range(200):
            r = client.get(f"/results/{sim_id}", headers=headers)
            if r.status_code == 200:
                data = r.json()
                break
            time.sleep(0.05)
        else:
            raise AssertionError("Timed out waiting for results")
        assert isinstance(data, dict)
        assert "forecast" in data
        r2 = client.get("/results/does-not-exist", headers=headers)
        assert r2.status_code == 404
