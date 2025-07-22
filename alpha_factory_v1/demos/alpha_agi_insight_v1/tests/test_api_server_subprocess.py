# SPDX-License-Identifier: Apache-2.0
import os
import socket
import subprocess
import threading
import sys
import time
from pathlib import Path

import pytest

# Ensure repository root is on the Python path for subprocess execution
REPO_ROOT = Path(__file__).resolve().parents[4]
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))
os.environ.setdefault("API_RATE_LIMIT", "1000")

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")
uvicorn = pytest.importorskip("uvicorn")
websockets = pytest.importorskip("websockets.sync.client")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_results(
    url: str,
    sim_id: str,
    headers: dict[str, str],
    proc: subprocess.Popen[str],
    max_attempts: int = 60,
) -> dict[str, object]:
    delay = 0.05
    for _ in range(max_attempts):
        if proc.poll() is not None:
            out, err = proc.communicate()
            raise AssertionError(
                f"server exited with {proc.returncode}:\n{out}{err}"
                if err
                else f"server exited with {proc.returncode}:\n{out}"
            )
        r = httpx.get(f"{url}/results/{sim_id}", headers=headers)
        if r.status_code == 200:
            data = r.json()
            if data.get("population") is not None:
                return data
        time.sleep(delay)
        delay = min(delay * 1.5, 1.0)
    raise AssertionError("Timed out waiting for results")


def test_docs_available() -> None:
    port = _free_port()
    env = os.environ.copy()
    env["API_TOKEN"] = "secret"
    env["PYTHONPATH"] = str(REPO_ROOT)
    cmd = [
        sys.executable,
        "-m",
        "alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if proc.poll() is not None:
                out, err = proc.communicate()
                raise AssertionError(
                    f"server exited with {proc.returncode}:\n{out}{err}"
                    if err
                    else f"server exited with {proc.returncode}:\n{out}"
                )
            try:
                r = httpx.get(url + "/docs")
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("server failed to start")
        assert r.status_code == 200
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_simulation_endpoints() -> None:
    port = _free_port()
    env = os.environ.copy()
    env["API_TOKEN"] = "secret"
    env["PYTHONPATH"] = str(REPO_ROOT)
    cmd = [
        sys.executable,
        "-m",
        "alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    url = f"http://127.0.0.1:{port}"
    headers = {"Authorization": "Bearer secret"}
    try:
        for _ in range(100):
            if proc.poll() is not None:
                out, err = proc.communicate()
                raise AssertionError(
                    f"server exited with {proc.returncode}:\n{out}{err}"
                    if err
                    else f"server exited with {proc.returncode}:\n{out}"
                )
            try:
                r = httpx.get(url + "/runs", headers=headers)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("server failed to start")

        progress: list[str] = []

        def _listen() -> None:
            ws_url = f"ws://127.0.0.1:{port}/ws/progress"
            with websockets.connect(ws_url, additional_headers=headers) as ws:
                try:
                    while True:
                        msg = ws.recv()
                        progress.append(msg)
                        if progress:
                            break
                except Exception:
                    pass

        th = threading.Thread(target=_listen, daemon=True)
        th.start()

        r = httpx.post(
            url + "/simulate",
            json={"horizon": 1, "pop_size": 2, "generations": 1, "k": 5.0, "x0": 0.0},
            headers=headers,
        )
        assert r.status_code == 200
        sim_id = r.json()["id"]
        data = _wait_results(url, sim_id, headers, proc)

        th.join(timeout=5)
        assert progress
        assert "forecast" in data
        assert isinstance(data.get("population"), list)

        r_latest = httpx.get(url + "/results", headers=headers)
        assert r_latest.status_code == 200
        latest = r_latest.json()
        assert latest["id"] == sim_id
        assert latest.get("population") == data["population"]

        r_pop = httpx.get(f"{url}/population/{sim_id}", headers=headers)
        assert r_pop.status_code == 200
        pop_data = r_pop.json()
        assert pop_data["id"] == sim_id
        assert pop_data["population"] == data["population"]

        r_runs = httpx.get(url + "/runs", headers=headers)
        assert r_runs.status_code == 200
        assert sim_id in r_runs.json().get("ids", [])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
