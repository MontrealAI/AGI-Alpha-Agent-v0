# SPDX-License-Identifier: Apache-2.0
import unittest
import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from alpha_factory_v1.backend.api_server import build_rest as _build_rest


class SimpleAgent:
    NAME = "simple"

    async def skill_test(self, payload: dict) -> dict:
        return {"ok": True}

    async def step(self) -> None:
        return None


class Runner:
    def __init__(self, inst: SimpleAgent) -> None:
        self.inst = inst
        self.next_ts = 0


class TestSkillTestRoute(unittest.TestCase):
    def test_skill_test_endpoint(self) -> None:
        app = _build_rest({"simple": Runner(SimpleAgent())})
        self.assertIsNotNone(app)
        headers = {"Authorization": "Bearer test-token"}
        with TestClient(app) as client:
            resp = client.post("/agent/simple/skill_test", json={"t": 1}, headers=headers)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
