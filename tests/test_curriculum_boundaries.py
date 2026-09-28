# SPDX-License-Identifier: Apache-2.0
"""Regression tests for unsafe execution, leaked answers and royalty accounting."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
from unittest.mock import Mock

import pytest

from alpha_factory_v1.demos.meta_agentic_agi_v3 import isolation
from alpha_factory_v1.demos.meta_agentic_agi_v3.core.physics.gibbs import free_energy
from alpha_factory_v1.demos.meta_agentic_agi_v3.curriculum.azr_engine import AZREngine, Triplet
from alpha_factory_v1.demos.meta_agentic_agi_v3.businesses import royalty_radar as radar


def test_legacy_search_import_requires_no_optional_packages() -> None:
    root = Path(__file__).resolve().parents[1]
    code = (
        f"import sys; sys.path.insert(0, {str(root)!r}); "
        "from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_search.search import _safe_exec"
    )
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_legacy_search_retries_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_search import search

    attempts = Mock(side_effect=RuntimeError("provider unavailable"))
    delays = []
    monkeypatch.setattr(search.LLMClient, "_chat_once", attempts)
    monkeypatch.setattr(search.time, "sleep", delays.append)
    with pytest.raises(RuntimeError, match="unavailable"):
        search.LLMClient("openai", "model").chat("test")
    assert attempts.call_count == 3 and delays == [1, 2]


def test_legacy_archive_creates_database_and_preserves_rows(tmp_path: Path) -> None:
    from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_search import archive

    path = tmp_path / "lineage #?.sqlite"
    candidate = archive._example_candidate()
    archive.insert(candidate, path)
    assert archive.load(path)[0].code == candidate.code
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        with archive._cx(missing, readonly=True):
            pass
    assert not missing.exists()


def test_generated_program_never_executes_on_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / "must-not-exist"
    code = f"from pathlib import Path\nPath({str(marker)!r}).write_text('escaped')\ndef main(x): return x"
    seen = []

    def sandbox(command):
        seen.append(Path(command[1]).read_text())
        return subprocess.CompletedProcess(command, 0, "4\n", "")

    monkeypatch.setattr(isolation, "secure_run", sandbox)
    assert isolation.run_python(code, "main", (4,)) == "4"
    assert not marker.exists() and code in seen[0]
    monkeypatch.setattr(isolation, "secure_run", Mock(side_effect=RuntimeError("Docker unavailable")))
    with pytest.raises(RuntimeError, match="unavailable"):
        isolation.run_python(code)
    assert not marker.exists()


def test_all_legacy_execution_adapters_use_same_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.demos.meta_agentic_agi_v3.agents.agent_base import SafeExec
    from alpha_factory_v1.demos.meta_agentic_agi_v3.core import tools
    from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_search.search import _safe_exec

    runner = Mock(return_value="[1, 2]")
    monkeypatch.setattr(isolation, "run_python", runner)
    monkeypatch.setattr(tools, "SANDBOX_TRUSTED", True)
    assert SafeExec().run("code", "f", 1) == [1, 2]
    assert _safe_exec("code", [[1]]) == [1, 2]
    assert asyncio.run(tools.sandbox_exec("code")) == "[1, 2]"
    assert runner.call_count == 3


def test_solver_cannot_observe_expected_answer() -> None:
    class Provider:
        seen = []

        def chat(self, **kw):
            self.seen.append(kw)
            return "4"

    provider = Provider()
    engine = AZREngine(provider)
    task = Triplet("def main(x): return x * x", "2", "4")
    result = engine.solve([task])[0]
    assert result.solved
    assert json.loads(provider.seen[0]["user"]) == {"program": task.program, "input": 2}
    engine.learn([result, result])
    assert engine.buffer == [task]


def test_finite_free_energy_and_invalid_distributions() -> None:
    assert free_energy([1000, 1000], 1, 1) == pytest.approx(1 - __import__("math").log(2))
    assert free_energy([0, -10000], 1, 7) == pytest.approx(7)
    for values, temp, cost in [([], 1, 1), ([float("nan")], 1, 1), ([0], -1, 1), ([0], 1, float("inf"))]:
        with pytest.raises(ValueError):
            free_energy(values, temp, cost)


def test_royalty_counts_group_by_track_and_use_paid_money(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def a(isrc):
        return {"a": 1000, "b": 2000}[isrc]

    async def b(isrc):
        return {"a": 3000, "b": 4000}[isrc]

    monkeypatch.setitem(radar.ADAPTERS, "one", a)
    monkeypatch.setitem(radar.ADAPTERS, "two", b)
    csv = tmp_path / "statement.csv"
    csv.write_text("isrc,streams,eur\na,500,1.00\na,500,2.00\nb,2000,5.00\n")
    cfg = radar.RoyaltyRadarConfig(
        "Artist",
        ["a", "b"],
        csv,
        "unverified",
        ["one", "two"],
        gap_eur_floor=0,
        eur_per_stream="0.01",
        lineage_path=tmp_path / "ledger.jsonl",
    )
    result = radar.RoyaltyRadarBusiness(cfg).run()
    assert result["evidence"]["public_streams"] == {"a": 2000, "b": 3000}
    assert result["gap_eur"] == "42.00"  # 20 − 3 + 30 − 5, not a dimensionless unpaid fraction
    radar.RoyaltyRadarBusiness(cfg).run()
    assert len(cfg.lineage_path.read_text().splitlines()) == 2
    cfg.demo_mode = False
    with pytest.raises(ValueError, match="not implemented"):
        radar.RoyaltyRadarBusiness(cfg)
    with pytest.raises(RuntimeError, match="ERC-20"):
        radar._dispatch_payout(42, "wallet")


def test_royalty_rng_does_not_reset_global_state() -> None:
    before = random.getstate()
    assert asyncio.run(radar.dsp_mock("example")) == asyncio.run(radar.dsp_mock("example"))
    assert before == random.getstate()


def test_pareto_compares_minimized_objectives_too() -> None:
    from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_search.scorer import TaskResult, compute_pareto

    rows = [
        TaskResult(candidate_id="a", objective_values={"accuracy": 0.9, "cost": 10}, meta={}),
        TaskResult(candidate_id="b", objective_values={"accuracy": 0.9, "cost": 3}, meta={}),
        TaskResult(candidate_id="c", objective_values={"accuracy": 0.8, "cost": 1}, meta={}),
    ]
    assert compute_pareto(rows, ["accuracy"]) == [1, 2]


def test_large_rate_limit_request_completes_with_a_fake_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.demos.meta_agentic_agi_v3.agents import agent_base

    clock = [0.0]
    monkeypatch.setattr(agent_base.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(agent_base.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    limiter = agent_base.RateLimiter(3)
    limiter.acquire(10)
    assert 2 <= clock[0] <= 3
    for invalid in (0, -1, float("nan")):
        with pytest.raises(ValueError):
            agent_base.RateLimiter(invalid)


def test_royalty_outputs_stay_outside_installed_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package = tmp_path / "installed"
    package.mkdir()
    settings = package / "settings.yml"
    settings.write_text(
        "artist_name: Example\nisrc_codes: [EXAMPLE]\nstatement_csv: statement.csv\n"
        "payout_wallet: unverified\nlineage_path: royalty-runs/ledger.jsonl\n"
    )
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    cfg = radar.RoyaltyRadarConfig.from_yaml(settings)
    assert cfg.statement_csv == package / "statement.csv"
    assert cfg.lineage_path == work / "royalty-runs/ledger.jsonl"
