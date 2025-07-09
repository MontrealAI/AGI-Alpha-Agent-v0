# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
import os
import tempfile
import unittest
from unittest import mock

from alpha_factory_v1.core import orchestrator
from alpha_factory_v1.core.utils import config
from alpha_factory_v1.common.utils import messaging, logging as insight_logging


class TestInsightOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = config.Settings(bus_port=0, ledger_path=os.path.join(self.tmp.name, "ledger.db"))
        self.orch = orchestrator.Orchestrator(self.settings)

    def tearDown(self) -> None:
        asyncio.run(self.orch.bus.stop())
        asyncio.run(self.orch.ledger.stop_merkle_task())
        self.orch.ledger.close()
        self.tmp.cleanup()

    def test_registration_records(self) -> None:
        count = self.orch.ledger.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        self.assertEqual(count, len(self.orch.runners))


class TestMessaging(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = config.Settings(bus_port=0)
        self.bus = messaging.A2ABus(self.settings)

    def tearDown(self) -> None:
        asyncio.run(self.bus.stop())

    def test_publish_subscribe(self) -> None:
        received = []

        async def handler(env: messaging.Envelope) -> None:
            received.append(env)

        self.bus.subscribe("x", handler)
        env = messaging.Envelope("a", "x", {"v": 1}, 0.0)
        self.bus.publish("x", env)
        asyncio.run(asyncio.sleep(0.01))
        self.assertEqual(received[0].payload["v"], 1)

    def test_rpc_auth(self) -> None:
        self.settings.bus_token = "s3cr3t"
        bus = messaging.A2ABus(self.settings)

        class Ctx:
            def abort(self, *_a, **_kw):
                raise RuntimeError("denied")

        payload = {
            "sender": "a",
            "recipient": "b",
            "payload": {},
            "ts": 0.0,
            "token": "s3cr3t",
        }
        asyncio.run(bus._handle_rpc(json.dumps(payload).encode(), Ctx()))


class TestLedger(unittest.TestCase):
    def test_merkle_root_and_broadcast(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        led = orchestrator.Ledger(
            os.path.join(tmp.name, "l.db"),
            rpc_url="http://rpc.test",
            broadcast=True,
        )
        env1 = messaging.Envelope("a", "b", {"v": 1}, 0.0)
        env2 = messaging.Envelope("b", "c", {"v": 2}, 0.0)
        led.log(env1)
        led.log(env2)
        root = led.compute_merkle_root()

        captured: dict[str, str] = {}

        class DummyClient:
            def __init__(self, url: str) -> None:
                captured["url"] = url

            async def send_transaction(self, tx: object, *args: object) -> None:
                captured["root"] = tx.instructions[0].data.decode()

            async def close(self) -> None:
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
            def __init__(self, val: str) -> None:
                pass

        with (
            mock.patch.object(insight_logging, "AsyncClient", DummyClient, create=True),
            mock.patch.object(insight_logging, "Transaction", DummyTx, create=True),
            mock.patch.object(insight_logging, "TransactionInstruction", DummyInstr, create=True),
            mock.patch.object(insight_logging, "PublicKey", DummyPk, create=True),
        ):
            asyncio.run(led.broadcast_merkle_root())

        self.assertEqual(captured["url"], "http://rpc.test")
        self.assertEqual(captured["root"], root)
        led.start_merkle_task(0.1)
        asyncio.run(asyncio.sleep(0.2))
        asyncio.run(led.stop_merkle_task())
        tmp.cleanup()


if __name__ == "__main__":  # pragma: no cover - manual
    unittest.main()
