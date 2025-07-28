# SPDX-License-Identifier: Apache-2.0
"""End-to-end test broadcasting a Merkle root to Solana devnet."""

from __future__ import annotations

import os
import tempfile

import pytest

from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging

pytestmark = [pytest.mark.e2e]


async def _devnet_available() -> bool:
    try:
        from solana.rpc.async_api import AsyncClient
    except Exception:
        return False
    try:
        client = AsyncClient("https://api.devnet.solana.com")
        await client.get_version()
        await client.close()
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_broadcast_merkle_root_devnet_e2e() -> None:
    if os.getenv("PYTEST_NET_OFF") == "1" or not await _devnet_available():
        pytest.skip("network disabled or devnet unreachable")
    tmp = tempfile.TemporaryDirectory()
    ledger = Ledger(os.path.join(tmp.name, "l.db"), rpc_url="https://api.devnet.solana.com", broadcast=True)
    env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
    ledger.log(env)
    try:
        await ledger.broadcast_merkle_root()
    finally:
        await ledger.stop_merkle_task()
        ledger.close()
        tmp.cleanup()
