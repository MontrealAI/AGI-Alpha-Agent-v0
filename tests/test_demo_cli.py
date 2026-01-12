# SPDX-License-Identifier: Apache-2.0
import os
import csv
import json
import hashlib
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import pytest
from click.testing import CliRunner


from alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface import cli  # noqa: E402
from alpha_factory_v1.common.utils import logging, messaging  # noqa: E402
from alpha_factory_v1.core.eval.foresight import evaluate as foresight_evaluate  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")


def test_simulate_without_flag_does_not_start() -> None:
    runner = CliRunner()
    with patch.object(cli, "asyncio") as aio:
        with patch.object(cli.orchestrator, "Orchestrator"):
            res = runner.invoke(
                cli.main,
                [
                    "simulate",
                    "--horizon",
                    "1",
                    "--offline",
                    "--sectors",
                    "1",
                    "--pop-size",
                    "2",
                    "--generations",
                    "1",
                ],
            )
        assert res.exit_code == 0
        aio.run.assert_not_called()


def test_simulate_sets_llama_path() -> None:
    runner = CliRunner()
    with patch.object(cli, "asyncio"):
        with patch.object(cli.orchestrator, "Orchestrator"):
            result = runner.invoke(
                cli.main,
                [
                    "simulate",
                    "--horizon",
                    "1",
                    "--offline",
                    "--llama-model-path",
                    "weights.bin",
                ],
            )
    assert result.exit_code == 0
    assert os.environ.get("LLAMA_MODEL_PATH") == "weights.bin"


def test_show_results_table(tmp_path) -> None:
    ledger = tmp_path / "audit.db"
    ledger.touch()
    with patch.object(cli.config.CFG, "ledger_path", ledger):
        with patch.object(cli.logging, "Ledger") as led_cls:
            led = led_cls.return_value
            led.tail.return_value = [{"ts": 1.0, "sender": "a", "recipient": "b", "payload": {"x": 1}}]
            res = CliRunner().invoke(cli.main, ["show-results"])
            assert "sender" in res.output
            assert "a" in res.output


def test_agents_status_lists_all_agents(tmp_path) -> None:
    class Dummy:
        status_code = 200

        def __init__(self, data: dict) -> None:
            self._data = data

        def json(self) -> dict:
            return self._data

    payload = {
        "agents": [
            {"name": "AgentA", "last_beat": 1.0, "restarts": 0},
            {"name": "AgentB", "last_beat": 2.0, "restarts": 1},
        ]
    }

    with patch.object(cli.requests, "get", return_value=Dummy(payload)) as get:
        result = CliRunner().invoke(cli.main, ["agents-status"])

    get.assert_called_once()
    assert "AgentA" in result.output and "AgentB" in result.output
    assert "last_beat" in result.output


def test_agents_status_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("API_TOKEN", raising=False)
    with patch.object(cli.requests, "get") as get:
        res = CliRunner().invoke(cli.main, ["agents-status"])
    get.assert_not_called()
    assert res.exit_code == 1
    assert "API_TOKEN not configured" in res.output


def test_plain_table_handles_no_rows() -> None:
    assert cli._plain_table(["h1", "h2"], []) == "h1 | h2"


def test_orchestrator_command_runs() -> None:
    runner = CliRunner()
    with patch.object(cli, "asyncio") as aio:
        with patch.object(cli.orchestrator, "Orchestrator"):
            res = runner.invoke(cli.main, ["orchestrator"])
            assert res.exit_code == 0
        aio.run.assert_called_once()


def test_show_results_closes_ledger(tmp_path) -> None:
    ledger = tmp_path / "audit.db"
    ledger.touch()
    with patch.object(cli.config.CFG, "ledger_path", ledger):
        with patch.object(cli.logging, "Ledger") as led_cls:
            led = led_cls.return_value
            led.__enter__.return_value = led
            led.__exit__.side_effect = lambda *_: led.close()
            led.tail.return_value = [{"ts": 1.0, "sender": "a", "recipient": "b", "payload": {"x": 1}}]
            CliRunner().invoke(cli.main, ["show-results"])
        led.close.assert_called_once()


def test_replay_closes_ledger(tmp_path) -> None:
    ledger = tmp_path / "audit.db"
    ledger.touch()
    with patch.object(cli.config.CFG, "ledger_path", ledger):
        with (
            patch.object(cli.logging, "Ledger") as led_cls,
            patch.object(cli.time, "sleep", return_value=None),
        ):
            led = led_cls.return_value
            led.__enter__.return_value = led
            led.__exit__.side_effect = lambda *_: led.close()
            led.tail.return_value = [{"ts": 0.0, "sender": "a", "recipient": "b", "payload": {"x": 1}}]
            CliRunner().invoke(cli.main, ["replay"])
        led.close.assert_called_once()


def test_replay_outputs_events(tmp_path: Path) -> None:
    """Replay should print formatted ledger rows."""
    path = tmp_path / "audit.db"
    with logging.Ledger(str(path), broadcast=False) as led:
        led.log(messaging.Envelope(sender="a", recipient="b", payload={"x": 1}, ts=0.0))
        led.log(messaging.Envelope(sender="b", recipient="c", payload={"y": 2}, ts=1.0))

    with patch.object(cli.config.CFG, "ledger_path", str(path)):
        with patch.object(cli.time, "sleep", return_value=None):
            res = CliRunner().invoke(cli.main, ["replay"])

    lines = [ln.strip() for ln in res.output.splitlines() if ln.strip()]
    assert '0.00 a -> b {"x": 1}' in lines[0]
    assert '1.00 b -> c {"y": 2}' in lines[1]


def test_replay_since_and_count(tmp_path: Path) -> None:
    path = tmp_path / "audit.db"
    with logging.Ledger(str(path), broadcast=False) as led:
        led.log(messaging.Envelope(sender="a", recipient="b", payload={"x": 1}, ts=0.0))
        led.log(messaging.Envelope(sender="b", recipient="c", payload={"y": 2}, ts=1.0))

    with patch.object(cli.config.CFG, "ledger_path", str(path)):
        with patch.object(cli.time, "sleep", return_value=None):
            res = CliRunner().invoke(cli.main, ["replay", "--since", "0.5", "--count", "1"])

    lines = [ln.strip() for ln in res.output.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert "b -> c" in lines[0]


def test_simulate_sectors_file_json(tmp_path: Path) -> None:
    """Run simulate with a sectors file and export JSON."""
    src = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/docs/sectors.sample.json")
    sectors_file = tmp_path / "sectors.json"
    sectors_file.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    runner = CliRunner()
    with patch.object(cli, "asyncio"):
        with patch.object(cli.orchestrator, "Orchestrator"):
            res = runner.invoke(
                cli.main,
                [
                    "simulate",
                    "--horizon",
                    "1",
                    "--offline",
                    "--sectors-file",
                    str(sectors_file),
                    "--pop-size",
                    "2",
                    "--generations",
                    "1",
                    "--export",
                    "json",
                ],
            )

    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data, list)
    assert data
    assert {"year", "capability", "affected"} <= set(data[0])


@pytest.mark.parametrize("export_fmt", ["json", "csv"])
def test_simulate_export_formats(export_fmt: str) -> None:
    """Ensure simulate exports JSON and CSV correctly."""
    runner = CliRunner()
    with patch.object(cli, "asyncio"):
        with patch.object(cli.orchestrator, "Orchestrator"):
            res = runner.invoke(
                cli.main,
                [
                    "simulate",
                    "--horizon",
                    "1",
                    "--offline",
                    "--sectors",
                    "1",
                    "--pop-size",
                    "1",
                    "--generations",
                    "1",
                    "--export",
                    export_fmt,
                ],
            )

    assert res.exit_code == 0
    if export_fmt == "json":
        assert res.output.startswith("[")
    else:
        reader = csv.reader(StringIO(res.output))
        rows = list(reader)
        assert rows[0] == ["year", "capability", "affected"]
        assert len(rows) > 1


def test_simulate_invalid_option() -> None:
    """Invoke simulate with an invalid export option."""
    res = CliRunner().invoke(
        cli.main,
        ["simulate", "--horizon", "1", "--offline", "--export", "xml"],
    )
    assert res.exit_code != 0
    assert "Invalid value for '--export'" in res.output


def test_simulate_invalid_values() -> None:
    """Invalid numeric options should exit with an error."""
    res = CliRunner().invoke(cli.main, ["simulate", "--pop-size", "0"])
    assert res.exit_code != 0
    assert "Invalid value for '--pop-size'" in res.output

    res = CliRunner().invoke(cli.main, ["simulate", "--mut-rate", "1.5"])
    assert res.exit_code != 0
    assert "Invalid value for '--mut-rate'" in res.output


def test_simulate_dry_run_mut_rate() -> None:
    """Running simulate with --dry-run and custom mutation rate should succeed."""
    runner = CliRunner()
    with patch.object(cli, "asyncio"):
        with patch.object(cli.orchestrator, "Orchestrator"):
            res = runner.invoke(
                cli.main,
                ["simulate", "--dry-run", "--mut-rate", "0.2"],
            )
    assert res.exit_code == 0


def test_simulate_save_plots(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch.object(cli, "asyncio"):
        with patch.object(cli.orchestrator, "Orchestrator"):
            with runner.isolated_filesystem(temp_dir=tmp_path):
                res = runner.invoke(
                    cli.main,
                    [
                        "simulate",
                        "--horizon",
                        "1",
                        "--offline",
                        "--sectors",
                        "1",
                        "--pop-size",
                        "1",
                        "--generations",
                        "1",
                        "--save-plots",
                    ],
                )
                assert res.exit_code == 0
                assert Path("pareto.png").exists()
                assert Path("pareto.json").exists()


def test_simulate_seed_reproducible(tmp_path: Path) -> None:
    """Output should be identical when running with the same seed."""
    ledger = tmp_path / "audit.db"
    args = [
        "simulate",
        "--horizon",
        "1",
        "--offline",
        "--sectors",
        "1",
        "--pop-size",
        "1",
        "--generations",
        "1",
        "--export",
        "json",
        "--no-broadcast",
        "--seed",
        "42",
    ]
    runner = CliRunner()
    with patch.object(cli, "asyncio"):
        with patch.object(cli.orchestrator, "Orchestrator"):
            with patch.object(cli.config.CFG, "ledger_path", ledger):
                res1 = runner.invoke(cli.main, args)
                res2 = runner.invoke(cli.main, args)

    assert res1.exit_code == 0
    assert res2.exit_code == 0
    digest1 = hashlib.sha256(res1.output.encode()).hexdigest()
    digest2 = hashlib.sha256(res2.output.encode()).hexdigest()
    assert digest1 == digest2


def test_foresight_evaluate_nonzero_metrics() -> None:
    repo = Path(__file__).resolve().parents[1]
    scores = foresight_evaluate(repo)
    assert scores["rmse"] > 0
    assert scores["lead_time"] != 0


def test_simulate_llama_model_path_forecast_table(tmp_path: Path) -> None:
    """Ensure simulate prints a table with a local Llama model."""
    cli_mod = pytest.importorskip("alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.cli")

    dummy = tmp_path / "weights.bin"
    dummy.touch()

    runner = CliRunner()
    with (
        patch.object(cli_mod, "asyncio"),
        patch.object(
            cli_mod.orchestrator,
            "Orchestrator",
        ),
    ):
        res = runner.invoke(
            cli_mod.main,
            [
                "simulate",
                "--horizon",
                "1",
                "--llama-model-path",
                str(dummy),
                "--offline",
            ],
        )

    assert res.exit_code == 0
    assert "year" in res.output and "capability" in res.output
