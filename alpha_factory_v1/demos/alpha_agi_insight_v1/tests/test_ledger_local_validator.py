# SPDX-License-Identifier: Apache-2.0
"""Broadcast a Merkle root to a local Solana validator running in Docker."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator

import asyncio
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging

requests = pytest.importorskip("requests")

if os.getenv("PYTEST_NET_OFF") == "1" or not shutil.which("docker"):
    pytest.skip("docker unavailable or network disabled", allow_module_level=True)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("localhost", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _wait_rpc(url: str, timeout: int = 30) -> bool:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash"}
    for _ in range(timeout):
        try:
            r = requests.post(url, json=payload, timeout=2)
            if r.status_code == 200 and "result" in r.json():
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="module")
def validator() -> Iterator[str]:
    port = _free_port()
    cid = (
        subprocess.check_output(
            [
                "docker",
                "run",
                "-d",
                "-p",
                f"{port}:8899",
                "solanalabs/solana:edge",
                "solana-test-validator",
                "--quiet",
            ]
        )
        .decode()
        .strip()
    )
    url = f"http://localhost:{port}"
    try:
        if not _wait_rpc(url):
            subprocess.run(["docker", "logs", cid], check=False)
            raise RuntimeError("validator not ready")
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)


@pytest.mark.asyncio
async def test_broadcast_merkle_root_local_validator(tmp_path: Path, validator: str) -> None:
    ledger = Ledger(str(tmp_path / "ledger.db"), rpc_url=validator, broadcast=True)
    env = messaging.Envelope("a", "b", {"v": 1}, 0.0)
    ledger.log(env)
    resp = requests.post(validator, json={"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash"})
    start_slot = resp.json()["result"]["context"]["slot"]
    try:
        await ledger.broadcast_merkle_root()
        for _ in range(20):
            time.sleep(1)
            resp = requests.post(
                validator,
                json={"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash"},
            )
            if resp.json()["result"]["context"]["slot"] > start_slot:
                break
        else:
            raise AssertionError("no new block produced")
    finally:
        await ledger.stop_merkle_task()
        ledger.close()
