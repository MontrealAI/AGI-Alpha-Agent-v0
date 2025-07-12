# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from alpha_factory_v1.demos.alpha_agi_insight_v1.src import orchestrator
from alpha_factory_v1.common.utils import config, messaging


def test_verify_ledger_slashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = config.Settings(bus_port=0, ledger_path=str(tmp_path / "ledger.db"))
    monkeypatch.setattr(orchestrator.Orchestrator, "_init_agents", lambda self: [])
    orch = orchestrator.Orchestrator(settings)
    orch.registry.set_stake("A", 100)
    original = orch.ledger.compute_merkle_root()
    env = messaging.Envelope(sender="A", recipient="b", ts=0.0)
    env.payload.update({"v": 1})
    orch.ledger.log(env)
    orch.verify_ledger(original, "A")
    assert orch.registry.stakes["A"] == 90
