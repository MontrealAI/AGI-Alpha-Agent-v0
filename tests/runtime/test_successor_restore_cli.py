# SPDX-License-Identifier: Apache-2.0
"""Installed-friendly operator checkpoint and clean knowledge restore commands."""

from pathlib import Path

import pytest
from test_successor_state import add_release, build_store

from alpha_factory_v1.core.runtime.cli import parser
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.cli import handle
from alpha_factory_v1.core.runtime.successor.protocol import canonical
from alpha_factory_v1.core.runtime.successor.transport import read_document


def command(*arguments):
    return handle(parser().parse_args([str(argument) for argument in arguments]))


def test_snapshot_and_new_home_restore_have_empty_permission(tmp_path: Path):
    source, keys = build_store(tmp_path)
    add_release(source, keys)
    portable, checkpoint = tmp_path / "portable.json", tmp_path / "checkpoint.json"
    exported = command(
        "--home",
        source.journal.root,
        "successor-portable",
        "institution",
        "--output",
        portable,
        "--checkpoint-output",
        checkpoint,
    )
    assert exported["active_permission_exported"] is False
    restored_home = tmp_path / "new-home"
    restored = command(
        "--home",
        restored_home,
        "successor-restore",
        portable,
        "--source-public-key",
        source.journal.public,
        "--checkpoint",
        checkpoint,
        "--budget",
        "calls=3",
    )
    assert restored["status"] == "restored-stopped" and restored["active_grants"] == []
    state = Journal(restored_home).latest("@successor:institution")
    assert state["proofs"] == {} and state["grants"] == {} and state["admissions"] == {}
    assert state["resources"]["limits"] == {"calls": 3} and state["serving_release"] is None
    assert state["historical_records"]["proofs"]
    assert (restored_home / "successor-principals" / "local-controller.key").is_file()
    assert not any(".key" in name for name in read_document(portable)["payload"])
    current_checkpoint = tmp_path / "current-checkpoint.json"
    captured = command("--home", restored_home, "successor-checkpoint", "--output", current_checkpoint)
    assert captured["checkpoint"] == read_document(current_checkpoint)
    assert captured["checkpoint"]["identity"] == Journal(restored_home).identity
    before = Journal(restored_home).verify()
    with pytest.raises(FileExistsError, match="NEW"):
        command(
            "--home",
            restored_home,
            "successor-restore",
            portable,
            "--source-public-key",
            source.journal.public,
            "--checkpoint",
            checkpoint,
        )
    assert Journal(restored_home).verify() == before


def test_invalid_source_anchor_fails_before_creating_target(tmp_path: Path):
    source, keys = build_store(tmp_path)
    add_release(source, keys)
    portable, checkpoint = tmp_path / "portable.json", tmp_path / "checkpoint.json"
    command(
        "--home",
        source.journal.root,
        "successor-portable",
        "institution",
        "--output",
        portable,
        "--checkpoint-output",
        checkpoint,
    )
    invalid = read_document(checkpoint)
    invalid["head"] = "0" * 64
    wrong = tmp_path / "wrong-checkpoint.json"
    wrong.write_bytes(canonical(invalid))
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="checkpoint"):
        command(
            "--home",
            destination,
            "successor-restore",
            portable,
            "--source-public-key",
            source.journal.public,
            "--checkpoint",
            wrong,
        )
    assert not destination.exists()
    with pytest.raises(ValueError, match="budget"):
        command(
            "--home",
            destination,
            "successor-restore",
            portable,
            "--source-public-key",
            source.journal.public,
            "--checkpoint",
            checkpoint,
            "--budget",
            "calls=True",
        )
    assert not destination.exists()


def test_snapshot_refuses_reused_or_aliased_outputs(tmp_path: Path):
    source, keys = build_store(tmp_path)
    add_release(source, keys)
    output = tmp_path / "same.json"
    with pytest.raises(ValueError, match="distinct"):
        command(
            "--home",
            source.journal.root,
            "successor-portable",
            "institution",
            "--output",
            output,
            "--checkpoint-output",
            output,
        )
    assert not output.exists()
