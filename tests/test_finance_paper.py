# SPDX-License-Identifier: Apache-2.0
"""Financial identities, causality, data rejection, replay and local service boundaries."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from alpha_factory_v1.demos.finance_alpha import delivery, paper
from alpha_factory_v1.demos.finance_alpha.server import create_server


def panel(prices, opens=None):
    return paper.csv_text(
        [
            {
                "date": (date(2025, 1, 1) + timedelta(days=i)).isoformat(),
                "symbol": "TEST",
                "open": opens[i] if opens else price,
                "close": price,
            }
            for i, price in enumerate(prices)
        ],
        ["date", "symbol", "open", "close"],
    )


def test_cash_and_known_buy_hold_accounting():
    source = panel([100] * 7 + [110])
    config = paper.Config(
        strategy="equal_weight", lookback=5, fee_bps=10, slippage_bps=5, max_exposure=0.5, max_position=0.5
    )
    report = paper.run(source, config)
    summary = report["result"]["summary"]
    assert summary["trades"] == 1
    # 50 units purchased at 100.05; 5.0025 fee; final mark 5,500.
    expected_cash = 10000 - 50 * 100.05 * 1.001
    assert summary["final_equity"] == pytest.approx(expected_cash + 5500)
    assert summary["net_pnl"] == pytest.approx(492.4975)
    assert summary["realized_pnl"] == 0
    assert summary["unrealized_pnl"] == pytest.approx(summary["net_pnl"])
    cash = paper.run(source, paper.Config(strategy="cash", lookback=5))["result"]
    assert cash["summary"]["net_return"] == 0 and cash["trades"] == []


def test_drawdown_liquidates_at_next_open_and_accounts_realized_costs():
    source = panel([100] * 7 + [70, 65], opens=[100] * 8 + [60])
    config = paper.Config(
        strategy="equal_weight",
        lookback=5,
        fee_bps=0,
        slippage_bps=0,
        max_exposure=1,
        max_position=1,
        max_drawdown=0.15,
    )
    result = paper.run(source, config)["result"]
    assert result["trades"][-1]["date"] == "2025-01-09"
    assert result["trades"][-1]["fill_price"] == 60
    assert result["trades"][-1]["signal_date"] == "2025-01-08"
    assert result["summary"]["net_pnl"] == -4000
    assert result["summary"]["realized_pnl"] == -4000
    assert result["summary"]["unrealized_pnl"] == 0
    assert result["summary"]["halted"] and not result["summary"]["pending_liquidation"]
    final_breach = paper.run(panel([100] * 7 + [70]), config)["result"]["summary"]
    assert final_breach["pending_liquidation"]


def test_no_lookahead_prefix_invariance_and_open_execution():
    source = paper.synthetic("reversal")
    rows = paper.parse_csv(source)
    cutoff = rows[200].date
    prefix = paper.csv_text([paper.asdict(b) for b in rows if b.date <= cutoff], ["date", "symbol", "open", "close"])
    full = paper.run(source)["result"]
    early = paper.run(prefix)["result"]
    assert early["equity"] == [r for r in full["equity"] if r["date"] <= cutoff]
    assert early["trades"] == [r for r in full["trades"] if r["date"] <= cutoff]
    assert early["decisions"] == [r for r in full["decisions"] if r["execution_date"] <= cutoff]
    assert all(r["signal_date"] < r["date"] for r in full["trades"])


@pytest.mark.parametrize("case", paper.CASES)
@pytest.mark.parametrize("strategy", paper.STRATEGIES)
def test_every_case_reconciles_and_replays(case, strategy):
    report = paper.run(config=paper.Config(strategy=strategy), case=case)
    assert delivery.verify(report)["verified"]
    for row in report["result"]["equity"]:
        assert row["cash"] >= -1e-8
        assert row["equity"] == pytest.approx(row["cash"] + row["market_value"])
        assert row["pnl"] == pytest.approx(row["realized_pnl"] + row["unrealized_pnl"])
    assert all(t["quantity"] > 0 and t["units_after"] >= -1e-8 for t in report["result"]["trades"])
    if case == "crash" and strategy == "momentum":
        assert report["result"]["summary"]["net_return"] < 0


def test_tail_risk_is_loss_or_zero_and_blocks_exposure():
    assert paper.tail_risk([0.01] * 20)["cvar95"] == 0
    risk = paper.tail_risk([-0.2, -0.1] + [0.01] * 18)
    assert risk["var95"] == 0.1 and risk["cvar95"] == 0.2
    report = paper.run(config=paper.Config(strategy="equal_weight", max_cvar=0.001))
    assert report["result"]["summary"]["risk_blocks"] > 0
    assert all(
        not any(d["targets"].values()) for d in report["result"]["decisions"] if d["reason"] == "tail_risk_to_cash"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fee_bps": float("nan")},
        {"initial_cash": float("inf")},
        {"lookback": True},
        {"lookback": 5.5},
        {"max_exposure": 1.01},
        {"slippage_bps": -1},
        {"strategy": "live"},
    ],
)
def test_config_rejects_invalid_or_unbounded_work(kwargs):
    with pytest.raises(ValueError):
        paper.Config(**kwargs)


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda s: s.replace("date,symbol,open,close", "date,symbol,close"),
        lambda s: s.replace(",100,100", ",nan,100", 1),
        lambda s: s.replace(",100,100", ",-1,100", 1),
        lambda s: s.replace("TEST", "=FORMULA", 1),
        lambda s: s + s.splitlines()[1] + "\n",
        lambda s: s.replace("2025-01-02", "2024-01-02"),
        lambda s: s.replace("TEST", "OTHER", 1),
        lambda s: s.replace("2025-01-02", "2025-02-30"),
        lambda s: s.replace(",100,100", ",100", 1),
        lambda s: s.replace("TEST", '"TEST', 1),
        lambda s: s.replace("TEST", "A" * 140000, 1),
    ],
)
def test_csv_rejects_ambiguity(corrupt):
    with pytest.raises(ValueError):
        paper.parse_csv(corrupt(panel([100] * 8)))


def test_export_preserves_existing_output_and_rejects_tampering(tmp_path):
    report = paper.run()
    output = tmp_path / "run"
    delivery.export(report, output)
    assert not (output / "INCOMPLETE").exists()
    manifest = json.loads((output / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    original = (output / "report.json").read_bytes()
    with pytest.raises(FileExistsError):
        delivery.export(report, output)
    assert (output / "report.json").read_bytes() == original
    changed = deepcopy(report)
    changed["result"]["summary"]["net_pnl"] += 1
    with pytest.raises(ValueError, match="exact replay"):
        delivery.verify(changed)
    assert "fetch(" not in (output / "report.html").read_text().split("const BOOTSTRAP")[0]


def test_strict_json_and_script_safe_export():
    for source in ['{"a":1,"a":2}', '{"a":NaN}']:
        with pytest.raises(ValueError):
            delivery.strict_json(source)
    rendered = delivery.render({"mode": "report", "test": "</script><script>alert(1)</script>"})
    assert rendered.count("</script>") == 1
    assert "sha256-" in rendered


def test_cli_actual_export_and_verify_outside_working_directory(tmp_path):
    import os

    command = [sys.executable, "-m", "alpha_factory_v1.demos.finance_alpha"]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    result = subprocess.run(
        command + ["--headless", "--case", "crash", "--output", "run"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        command + ["--verify", "run/report.json"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0 and '"verified": true' in result.stdout
    result = subprocess.run(
        command + ["--headless", "--output", "run"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 2


def test_server_rejects_cross_origin_missing_token_and_paths():
    with create_server(0) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request("GET", "/api/health")
            response = conn.getresponse()
            assert response.status == 200 and json.loads(response.read())["execution"] == "paper_only"
            conn.request("POST", "/api/run", body="{}", headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            assert response.status == 403
            response.read()
            conn.request("GET", "/", headers={"Origin": "https://untrusted.invalid"})
            response = conn.getresponse()
            assert response.status == 403
            response.read()
            conn.request("GET", "/../../pyproject.toml")
            response = conn.getresponse()
            assert response.status == 404
            response.read()
            conn.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_original_finance_sources_preserved():
    archive = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/finance_alpha/archive"
    for entry in json.loads((archive / "manifest.json").read_text())["files"]:
        assert hashlib.sha256((archive / entry["archive"]).read_bytes()).hexdigest() == entry["sha256"]
