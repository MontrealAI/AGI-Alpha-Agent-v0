# SPDX-License-Identifier: Apache-2.0
import asyncio
import os
import tempfile
import unittest
from unittest import mock

from alpha_factory_v1.common.utils import logging as insight_logging
from alpha_factory_v1.demos.alpha_agi_insight_v1.src import orchestrator
from alpha_factory_v1.common.utils import messaging


class TestMerkleBroadcast(unittest.TestCase):
    """Verify Merkle root broadcasting and error handling."""

    def _ledger(self):
        tmp = tempfile.TemporaryDirectory()
        led = orchestrator.Ledger(os.path.join(tmp.name, "l.db"), rpc_url="http://rpc.test", broadcast=True)
        self.addCleanup(tmp.cleanup)
        return led

    def _dummy_classes(self, raise_err=False):
        captured = {}

        class DummyClient:
            def __init__(self, url: str) -> None:
                captured["url"] = url

            async def send_transaction(self, tx: object, *args: object) -> None:
                if raise_err:
                    raise RuntimeError("fail")
                captured["root"] = tx.instructions[0].data.decode()

            async def close(self) -> None:  # pragma: no cover - dummy
                pass

        class DummyTx:
            def __init__(self) -> None:
                self.instructions = []

            def add(self, instr: object) -> "DummyTx":
                self.instructions.append(instr)
                return self

        class DummyInstr:
            def __init__(self, program_id: object, data: bytes, keys: list[object]):
                self.data = data

        class DummyPk:
            def __init__(self, val: str) -> None:  # pragma: no cover - dummy
                pass

        return captured, DummyClient, DummyTx, DummyInstr, DummyPk

    def test_broadcast_success(self) -> None:
        led = self._ledger()
        env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
        led.log(env)
        root = led.compute_merkle_root()
        captured, DummyClient, DummyTx, DummyInstr, DummyPk = self._dummy_classes()
        with (
            mock.patch.object(insight_logging, "AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "Transaction", DummyTx, create=True),
            mock.patch.object(insight_logging, "TransactionInstruction", DummyInstr, create=True),
            mock.patch.object(insight_logging, "PublicKey", DummyPk, create=True),
        ):
            asyncio.run(led.broadcast_merkle_root())
        self.assertEqual(captured["url"], "http://rpc.test")
        self.assertEqual(captured["root"], root)

    def test_broadcast_error(self) -> None:
        led = self._ledger()
        env = messaging.Envelope(sender="a", recipient="b", payload={"v": 1}, ts=0.0)
        led.log(env)
        captured, DummyClient, DummyTx, DummyInstr, DummyPk = self._dummy_classes(True)
        with (
            mock.patch.object(insight_logging, "AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "Transaction", DummyTx, create=True),
            mock.patch.object(insight_logging, "TransactionInstruction", DummyInstr, create=True),
            mock.patch.object(insight_logging, "PublicKey", DummyPk, create=True),
            mock.patch.object(insight_logging, "_log") as log,
        ):
            asyncio.run(led.broadcast_merkle_root())
        log.warning.assert_called()  # ensure warning emitted
