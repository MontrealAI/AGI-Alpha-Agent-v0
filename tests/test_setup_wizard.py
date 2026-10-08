# SPDX-License-Identifier: Apache-2.0
"""The source setup wizard honors interpreter boundaries and its checkout root."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from scripts import setup_wizard


@pytest.mark.parametrize("version, supported", [((3, 10), False), ((3, 11), True), ((3, 13), True), ((3, 14), False)])
def test_supported_python_boundary(version: tuple[int, int], supported: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_wizard.sys, "version_info", version)
    assert setup_wizard.check_python() is supported


def test_unsupported_python_stops_before_any_tool_probe_or_menu(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(setup_wizard.sys, "version_info", (3, 14))

    def unexpected_probe(*args: object) -> None:
        pytest.fail("An unsupported interpreter must not proceed to setup actions")

    monkeypatch.setattr(setup_wizard, "check_cmd", unexpected_probe)
    monkeypatch.setattr("builtins.input", unexpected_probe)
    assert setup_wizard.main([]) == 1
    assert "Restart with a supported Python" in capsys.readouterr().out


def test_action_runs_from_checkout_even_when_launched_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "source checkout"
    checkout.mkdir()
    caller = tmp_path / "unrelated folder"
    caller.mkdir()
    monkeypatch.chdir(caller)
    monkeypatch.setattr(setup_wizard, "REPO_ROOT", checkout)
    command = "from pathlib import Path; Path('working-directory.txt').write_text(str(Path.cwd()))"
    assert setup_wizard.run([sys.executable, "-c", command])
    assert (checkout / "working-directory.txt").read_text() == str(checkout)
    assert not (caller / "working-directory.txt").exists()


def test_failed_and_missing_commands_report_recovery_without_crashing(tmp_path: Path, capsys) -> None:
    assert not setup_wizard.run([sys.executable, "-c", "raise SystemExit(7)"])
    assert "exit status 7" in capsys.readouterr().out
    assert not setup_wizard.run([str(tmp_path / "missing-program")])
    assert "Check the required tool" in capsys.readouterr().out


def test_direct_uninstalled_help_and_eof_exit_have_no_setup_side_effects(tmp_path: Path) -> None:
    script = Path(setup_wizard.__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-I", str(script), "--help"], cwd=tmp_path, text=True, capture_output=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert "install_agent.py" in result.stdout and "Choose an action explicitly" in " ".join(result.stdout.split())
    result = subprocess.run(
        [sys.executable, "-I", str(script)], cwd=tmp_path, input="", text=True, capture_output=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert "Setup wizard closed; no further action was started." in result.stdout
    assert list(tmp_path.iterdir()) == []
