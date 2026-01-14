# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
import os
import tempfile
from google.protobuf import json_format
from types import ModuleType
from typing import Any
from unittest import mock
import sys

from alpha_factory_v1.common.utils import logging as insight_logging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils import messaging


def test_compute_merkle_root_matches_manual() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(os.path.join(tmp, "l.db"), broadcast=False)

        envs = [
            messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0),
            messaging.Envelope(sender="b", recipient="c", payload={"v": 2}, ts=1.0),
            messaging.Envelope(sender="c", recipient="d", payload={"v": 3}, ts=2.0),
        ]
        for env in envs:
            ledger.log(env)

        computed = ledger.compute_merkle_root()

        hashes = []
        for env in envs:
            if hasattr(env, "DESCRIPTOR"):
                record = json_format.MessageToDict(env, preserving_proto_field_name=True)
            else:
                record = env.__dict__
            data = json.dumps(record, sort_keys=True).encode()
            hashes.append(insight_logging.blake3(data).hexdigest())  # type: ignore[attr-defined]

        manual = insight_logging._merkle_root(hashes)
        assert computed == manual


def test_broadcast_merkle_root_uses_async_client() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(os.path.join(tmp, "l.db"), rpc_url="http://rpc.test", broadcast=True)
        env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
        ledger.log(env)
        root = ledger.compute_merkle_root()

        calls: list[Any] = []

        class DummyClient:
            def __init__(self, url: str) -> None:
                calls.append(("url", url))

            async def send_transaction(self, tx: Any, *args: Any) -> None:
                calls.append(("sent", tx.instructions[0].data.decode()))

            async def close(self) -> None:
                pass

        class DummyTx:
            def __init__(self) -> None:
                self.instructions: list[Any] = []

            def add(self, instr: Any) -> "DummyTx":
                self.instructions.append(instr)
                return self

        class DummyInstr:
            def __init__(self, program_id: Any, data: bytes, keys: list[Any]):
                self.data = data

        class DummyPk:
            def __init__(self, val: str) -> None:
                pass

        # ensure mock module hierarchy exists for patching
        with (
            mock.patch.dict(
                sys.modules,
                {
                    "solana": ModuleType("solana"),
                    "solana.rpc": ModuleType("solana.rpc"),
                    "solana.rpc.async_api": ModuleType("solana.rpc.async_api"),
                },
            ),
            mock.patch("solana.rpc.async_api.AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "Transaction", DummyTx, create=True),
            mock.patch.object(insight_logging, "TransactionInstruction", DummyInstr, create=True),
            mock.patch.object(insight_logging, "PublicKey", DummyPk, create=True),
        ):
            asyncio.run(ledger.broadcast_merkle_root())

        assert ("url", "http://rpc.test") in calls
        assert ("sent", root) in calls


def test_broadcast_merkle_root_handles_network_errors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(os.path.join(tmp, "l.db"), rpc_url="http://rpc.test", broadcast=True)
        env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
        ledger.log(env)
        root = ledger.compute_merkle_root()

        captured: dict[str, Any] = {}

        class DummyClient:
            def __init__(self, url: str) -> None:
                captured["url"] = url

            async def send_transaction(self, tx: Any, *args: Any) -> None:
                captured["root"] = tx.instructions[0].data.decode()
                raise RuntimeError("fail")

            async def close(self) -> None:
                pass

        class DummyTx:
            def __init__(self) -> None:
                self.instructions: list[Any] = []

            def add(self, instr: Any) -> "DummyTx":
                self.instructions.append(instr)
                return self

        class DummyInstr:
            def __init__(self, program_id: Any, data: bytes, keys: list[Any]):
                self.data = data

        class DummyPk:
            def __init__(self, val: str) -> None:
                pass

        with (
            mock.patch.dict(
                sys.modules,
                {
                    "solana": ModuleType("solana"),
                    "solana.rpc": ModuleType("solana.rpc"),
                    "solana.rpc.async_api": ModuleType("solana.rpc.async_api"),
                },
            ),
            mock.patch("solana.rpc.async_api.AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "Transaction", DummyTx, create=True),
            mock.patch.object(insight_logging, "TransactionInstruction", DummyInstr, create=True),
            mock.patch.object(insight_logging, "PublicKey", DummyPk, create=True),
            mock.patch.object(insight_logging, "_log") as log,
        ):
            asyncio.run(ledger.broadcast_merkle_root())

        assert captured["root"] == root
        log.warning.assert_called()
