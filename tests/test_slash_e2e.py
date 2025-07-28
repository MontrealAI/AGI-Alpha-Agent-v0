# SPDX-License-Identifier: Apache-2.0
import pytest

from alpha_factory_v1.demos.alpha_agi_insight_v1.src import orchestrator
from alpha_factory_v1.common.utils import messaging, config

pytestmark = [pytest.mark.e2e]


def test_slash_on_forged_ledger(tmp_path, monkeypatch) -> None:
    settings = config.Settings(bus_port=0, ledger_path=str(tmp_path / "ledger.db"))
    monkeypatch.setattr(orchestrator.Orchestrator, "_init_agents", lambda self: [])
    orch = orchestrator.Orchestrator(settings)
    orch.registry.set_stake("A", 100)
    original_root = orch.ledger.compute_merkle_root()
    env = messaging.Envelope(sender="A", recipient="b", payload={"v": 1}, ts=0.0)
    orch.ledger.log(env)
    orch.verify_merkle_root(original_root, "A")
    assert orch.registry.stakes["A"] == 90
