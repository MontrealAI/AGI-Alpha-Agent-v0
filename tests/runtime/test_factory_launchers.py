# SPDX-License-Identifier: Apache-2.0
"""Check-only launchers, path handling and failed bootstrap recovery contracts."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

from alpha_factory_v1 import quickstart, run
from alpha_factory_v1.scripts import preflight


def test_check_only_uses_repository_paths_without_installing_or_changing_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with mock.patch.object(quickstart, "_create_venv") as create, mock.patch("subprocess.check_call") as call:
        assert quickstart.main(["--profile", "agent", "--preflight", "--offline", "--venv", "not-created"]) == 0
    create.assert_not_called()
    command = call.call_args.args[0]
    assert Path(command[1]).is_file()
    assert command[2:] == ["--profile", "agent", "--offline"]
    assert not list(tmp_path.iterdir()) and Path.cwd() == tmp_path


def test_failed_preflight_never_launches(tmp_path: Path) -> None:
    with (
        mock.patch.object(quickstart, "_create_venv"),
        mock.patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(1, ["preflight"])) as call,
    ):
        assert quickstart.main(["--profile", "agent", "--venv", str(tmp_path / "env")]) == 1
    assert call.call_count == 1


def test_explicit_skip_preserves_native_arguments_and_invoking_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with mock.patch.object(quickstart, "_create_venv"), mock.patch("subprocess.check_call") as call:
        assert (
            quickstart.main(
                ["--profile", "agent", "--skip-preflight", "--venv", "env space", "--", "--home", "state space", "init"]
            )
            == 0
        )
    command = call.call_args.args[0]
    assert command == [
        str(quickstart._venv_python(tmp_path / "env space")),
        "-m",
        "alpha_factory_v1.core.runtime.cli",
        "--home",
        "state space",
        "init",
    ]
    assert "cwd" not in call.call_args.kwargs
    assert not list(tmp_path.iterdir())


def test_offline_without_wheels_never_installs(tmp_path: Path) -> None:
    with mock.patch.object(quickstart, "_create_venv") as create:
        assert quickstart.main(["--profile", "agent", "--offline", "--venv", str(tmp_path / "new")]) == 1
    create.assert_not_called()


def test_interrupted_install_is_retained_and_cannot_be_reused(tmp_path: Path) -> None:
    venv = tmp_path / "environment"
    requirements = tmp_path / "requirements-agent.lock"
    requirements.write_text("example==1.0 --hash=sha256:fixture\n")
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    calls = []

    def execute(command: list[str]) -> None:
        calls.append(command)
        if command[:3] == [sys.executable, "-m", "venv"]:
            py = quickstart._venv_python(venv)
            py.parent.mkdir(parents=True)
            py.touch()
        else:
            raise subprocess.CalledProcessError(1, command)

    with mock.patch("subprocess.check_call", side_effect=execute):
        with pytest.raises(subprocess.CalledProcessError):
            quickstart._create_venv(venv, requirements, wheels)
    assert "--require-hashes" in calls[1] and "--no-index" in calls[1]
    assert calls[1][-2:] == ["--find-links", str(wheels)]
    marker = venv / ".alpha-factory-bootstrap.json"
    assert json.loads(marker.read_text())["complete"] is False
    with mock.patch("subprocess.check_call") as call:
        with pytest.raises(ValueError, match="Partial"):
            quickstart._create_venv(venv, requirements, wheels)
        call.assert_not_called()


def test_completed_environment_rejects_lock_drift_without_installing(tmp_path: Path) -> None:
    import hashlib

    venv = tmp_path / "environment"
    py = quickstart._venv_python(venv)
    py.parent.mkdir(parents=True)
    py.touch()
    requirements = tmp_path / "requirements-agent.lock"
    original = b"example==1.0 --hash=sha256:old\n"
    requirements.write_bytes(original)
    marker = venv / ".alpha-factory-bootstrap.json"
    marker.write_text(
        json.dumps(
            {"requirements": requirements.name, "lock_sha256": hashlib.sha256(original).hexdigest(), "complete": True}
        )
    )
    with mock.patch("subprocess.check_call") as call:
        quickstart._create_venv(venv, requirements)
        call.assert_called_once()
    requirements.write_bytes(b"example==2.0 --hash=sha256:new\n")
    before = marker.read_bytes()
    with mock.patch("subprocess.check_call") as call:
        with pytest.raises(ValueError, match="changed-lock"):
            quickstart._create_venv(venv, requirements)
        call.assert_not_called()
    assert marker.read_bytes() == before


@pytest.mark.parametrize(
    "version,expected", [((3, 10), False), ((3, 11), True), ((3, 12), True), ((3, 13), True), ((3, 14), False)]
)
def test_supported_python_range(version: tuple[int, int], expected: bool) -> None:
    with mock.patch.object(sys, "version_info", version):
        assert preflight.check_python() is expected


def test_operator_preflight_does_not_probe_optional_services_or_modify_files() -> None:
    with (
        mock.patch.object(preflight, "check_pkg", return_value=True),
        mock.patch.object(preflight, "check_cmd") as cmd,
        mock.patch.object(preflight, "check_network") as network,
        mock.patch.object(preflight, "check_docker_daemon") as docker,
        mock.patch.object(preflight, "ensure_dir") as directory,
    ):
        preflight.main(["--profile", "agent", "--offline"])
    for probe in (cmd, network, docker, directory):
        probe.assert_not_called()


def test_factory_routes_native_and_demo_commands_without_starting_legacy_services() -> None:
    with (
        mock.patch.object(sys, "argv", ["alpha-factory", "mission", "examples"]),
        mock.patch("alpha_factory_v1.core.runtime.cli.main", return_value=0) as native,
    ):
        with pytest.raises(SystemExit) as exit_code:
            run.run()
        assert exit_code.value.code == 0
        native.assert_called_once_with(["examples"])
    with (
        mock.patch.object(sys, "argv", ["alpha-factory", "demos", "list"]),
        mock.patch("alpha_factory_v1.demos.catalog.main", return_value=0) as catalog,
    ):
        with pytest.raises(SystemExit):
            run.run()
        catalog.assert_called_once_with(["list"])
