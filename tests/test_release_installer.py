# SPDX-License-Identifier: Apache-2.0
"""Release installation rejects bad inputs before touching an existing environment."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

from scripts import install_agent


@pytest.fixture
def assets(tmp_path: Path) -> Path:
    root = tmp_path / "release assets"
    root.mkdir()
    for name in ("alpha_factory_v1-1.2.3-py3-none-any.whl", "requirements-agent.lock"):
        (root / name).write_bytes(b"fixture bytes\n")
    (root / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in sorted(root.iterdir()))
    )
    return root


def test_check_only_cli_has_no_installation_side_effects(assets: Path, tmp_path: Path) -> None:
    target = tmp_path / "environment with spaces"
    result = subprocess.run(
        [sys.executable, install_agent.__file__, "--release-dir", str(assets), "--venv", str(target), "--check-only"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "No environment was created" in result.stdout
    assert not target.exists()


@pytest.mark.parametrize("damage", ["missing", "changed", "duplicate", "unsafe", "malformed"])
def test_invalid_release_fails_before_creating_environment(assets: Path, tmp_path: Path, damage: str, capsys) -> None:
    lock = assets / "requirements-agent.lock"
    manifest = assets / "SHA256SUMS"
    if damage == "missing":
        lock.unlink()
    elif damage == "changed":
        lock.write_text("changed bytes")
    elif damage == "duplicate":
        manifest.write_text(manifest.read_text() * 2)
    elif damage == "unsafe":
        manifest.write_text("a" * 64 + "  ../outside.whl\n")
    else:
        manifest.write_text("not a checksum\n")
    target = tmp_path / "new-env"
    with mock.patch.object(install_agent.venv, "EnvBuilder") as builder:
        assert install_agent.main(["--release-dir", str(assets), "--venv", str(target)]) == 1
    builder.assert_not_called()
    assert not target.exists()
    error = capsys.readouterr().err
    assert "checking release inputs" in error and "Traceback" not in error


@pytest.mark.parametrize("kind", ["missing", "empty", "file"])
def test_invalid_offline_wheelhouse_never_falls_back_to_network(assets: Path, tmp_path: Path, kind: str) -> None:
    wheelhouse = tmp_path / "offline-wheels"
    if kind == "empty":
        wheelhouse.mkdir()
    elif kind == "file":
        wheelhouse.touch()
    with mock.patch.object(install_agent.venv, "EnvBuilder") as builder, mock.patch.object(subprocess, "run") as run:
        assert install_agent.main(["--release-dir", str(assets), "--wheelhouse", str(wheelhouse)]) == 1
    builder.assert_not_called()
    run.assert_not_called()


def test_existing_environment_is_retained(assets: Path, tmp_path: Path) -> None:
    target = tmp_path / "old-env"
    target.mkdir()
    retained = target / "keep.txt"
    retained.write_text("original")
    assert install_agent.main(["--release-dir", str(assets), "--venv", str(target)]) == 1
    assert retained.read_text() == "original"


def test_install_failure_reports_phase_and_preserves_partial_environment(assets: Path, tmp_path: Path, capsys) -> None:
    target = tmp_path / "new-env"

    def create(path: Path) -> None:
        path.mkdir()
        (path / "diagnostic.txt").write_text("retained")

    with (
        mock.patch.object(install_agent.venv.EnvBuilder, "create", side_effect=create),
        mock.patch.object(subprocess, "run", side_effect=subprocess.CalledProcessError(9, ["pip"])),
    ):
        assert install_agent.main(["--release-dir", str(assets), "--venv", str(target)]) == 1
    assert (target / "diagnostic.txt").read_text() == "retained"
    error = capsys.readouterr().err
    assert "installing hash-locked dependencies" in error and "new --venv path" in error


def test_interrupted_install_retains_partial_environment_and_reports_recovery(
    assets: Path, tmp_path: Path, capsys
) -> None:
    target = tmp_path / "interrupted-env"

    def create(path: Path) -> None:
        path.mkdir()
        (path / "diagnostic.txt").write_text("retained")

    with (
        mock.patch.object(install_agent.venv.EnvBuilder, "create", side_effect=create),
        mock.patch.object(subprocess, "run", side_effect=KeyboardInterrupt),
    ):
        assert install_agent.main(["--release-dir", str(assets), "--venv", str(target)]) == 130
    assert (target / "diagnostic.txt").read_text() == "retained"
    error = capsys.readouterr().err
    assert "interrupted while installing hash-locked dependencies" in error
    assert "new --venv path" in error and "Traceback" not in error


def test_offline_success_checks_environment_and_quotes_command(assets: Path, tmp_path: Path, capsys) -> None:
    wheelhouse = tmp_path / "dependency wheels"
    wheelhouse.mkdir()
    (wheelhouse / "dependency.whl").touch()
    target = tmp_path / "new environment"
    with mock.patch.object(install_agent.venv.EnvBuilder, "create"), mock.patch.object(subprocess, "run") as run:
        assert (
            install_agent.main(["--release-dir", str(assets), "--venv", str(target), "--wheelhouse", str(wheelhouse)])
            == 0
        )
    calls = [call.args[0] for call in run.call_args_list]
    assert "--no-index" in calls[0] and "--require-hashes" in calls[0]
    assert "--no-deps" in calls[1] and calls[2][-2:] == ["pip", "check"]
    assert calls[3][-1] == "--version"
    assert "new environment" in capsys.readouterr().out
