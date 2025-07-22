# SPDX-License-Identifier: Apache-2.0
import os
import time
import asyncio
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")


from typing import Any, cast
import importlib


def make_client() -> TestClient:
    from alpha_factory_v1.core.interface import api_server

    api_server = importlib.reload(api_server)
    return TestClient(cast(Any, api_server.app))


def test_api_endpoints() -> None:
    client = make_client()
    headers = {"Authorization": "Bearer test-token"}

    resp = client.post(
        "/simulate",
        json={"horizon": 1, "pop_size": 2, "generations": 1, "k": 5.0, "x0": 0.0},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    sim_id = data.get("id")
    assert isinstance(sim_id, str) and sim_id

    for _ in range(200):
        r = client.get(f"/results/{sim_id}", headers=headers)
        if r.status_code == 200:
            results = r.json()
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Timed out waiting for results")

    assert isinstance(results, dict)
    assert results.get("id") == sim_id
    assert "forecast" in results and isinstance(results["forecast"], list)
    assert "population" in results and isinstance(results["population"], list)

    runs = client.get("/runs", headers=headers)
    assert runs.status_code == 200
    runs_data = runs.json()
    assert isinstance(runs_data, dict)
    assert "ids" in runs_data and isinstance(runs_data["ids"], list)
    assert sim_id in runs_data["ids"]


def test_background_run_direct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Call the internal worker directly and verify progress and output."""

    monkeypatch.setenv("SIM_RESULTS_DIR", str(tmp_path))

    import importlib

    from alpha_factory_v1.core.interface import api_server as api

    api = importlib.reload(api)

    messages: list[dict[str, object]] = []

    class DummyWS:
        async def send_json(self, data: dict[str, object]) -> None:
            messages.append(data)

    ws = DummyWS()
    api._progress_ws.add(ws)

    sim_id = "unit-test"
    cfg = api.SimRequest(horizon=1, pop_size=2, generations=1, k=5.0, x0=0.0)
    asyncio.run(api._background_run(sim_id, cfg))

    api._progress_ws.discard(ws)

    assert (tmp_path / f"{sim_id}.json").exists()
    assert messages and messages[0]["id"] == sim_id


def test_results_dir_permissions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Directory is created with 0700 permissions."""

    path = tmp_path / "results"
    monkeypatch.setenv("SIM_RESULTS_DIR", str(path))

    import importlib

    from alpha_factory_v1.core.interface import api_server as api

    api = importlib.reload(api)

    assert path.exists()
    assert (path.stat().st_mode & 0o777) == 0o700


def test_root_serves_spa() -> None:
    client = make_client()
    r = client.get("/")
    assert r.status_code == 200
    assert '<div id="root">' in r.text
