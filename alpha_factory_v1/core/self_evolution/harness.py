# SPDX-License-Identifier: Apache-2.0
"""Patch evaluation harness using Docker-in-Docker."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

from alpha_factory_v1.core.eval.preflight import run_preflight
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry
from alpha_factory_v1.demos.self_healing_repo import patcher_core

IMAGE = os.getenv("SELF_EVOLUTION_IMAGE", "python:3.11-slim")
MAX_SOURCE_FILES = 10_000
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_FILE_BYTES = 8 * 1024 * 1024

__all__ = [
    "apply_patch",
    "vote_and_merge",
    "patcher_core",
    "_run_tests",
    "run_preflight",
]


def _run_tests(repo: Path) -> int:
    """Run the repository's test suite in a Docker container.

    Args:
        repo: Path to the repository to test.

    Returns:
        The pytest return code.
    """
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{repo}:/work",
    ]
    wheelhouse = os.getenv("WHEELHOUSE")
    if wheelhouse:
        cmd.extend(["-e", f"WHEELHOUSE={wheelhouse}", "-v", f"{wheelhouse}:{wheelhouse}"])
    cmd.extend(
        [
            "-w",
            "/work",
            IMAGE,
            "bash",
            "-c",
            'python check_env.py --auto-install${WHEELHOUSE:+ --wheelhouse "$WHEELHOUSE"} && pytest -q',
        ]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode


class SourceSnapshotMismatch(ValueError):
    """The copied base cannot use approval for the proposal's original source."""


def apply_patch(repo: str | Path, diff: str, *, expected_source_fingerprint: str | None = None) -> Tuple[bool, Path]:
    """Apply `diff` to `repo` in isolation and run the tests.

    Args:
        repo: Repository path to patch.
        diff: Unified diff to apply.
        expected_source_fingerprint: If supplied, require this exact copied base
            before patching or validation. Omitted legacy calls gain no source binding.

    Returns:
        Tuple containing the test result and sandbox path.
    """
    if expected_source_fingerprint is not None and re.fullmatch(r"[0-9a-f]{64}", expected_source_fingerprint) is None:
        raise ValueError("Expected source fingerprint must be an exact SHA256 identity")
    src = Path(repo).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="self-evo-"))
    try:
        # Bound proposals preserve any transient links for rejection, rather than
        # following them outside the source during the copy.
        shutil.copytree(src, tmp, dirs_exist_ok=True, symlinks=expected_source_fingerprint is not None)
        if expected_source_fingerprint is not None:
            try:
                copied_source = _source_fingerprint(tmp)
            except (OSError, ValueError) as error:
                raise SourceSnapshotMismatch("Copied base cannot be bound to the proposal source") from error
            if copied_source != expected_source_fingerprint:
                raise SourceSnapshotMismatch("Copied base differs from the proposal source")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    patcher_core.apply_patch(diff, repo_path=str(tmp))
    run_preflight(tmp)
    rc = _run_tests(tmp)
    return rc == 0, tmp


def _source_fingerprint(repo: Path) -> str:
    """Hash a bounded stable ordinary-file snapshot, excluding only Git metadata.

    This is an identity check, not execution admission or operating-system isolation.
    Symlinks, special files, unreadable files and changing snapshots fail closed.
    """

    def inventory() -> dict[str, tuple[int, int, int, int, int]]:
        rows: dict[str, tuple[int, int, int, int, int]] = {}
        total = 0

        pending = [repo]
        visited = 0
        while pending:
            directory = pending.pop()
            if not stat.S_ISDIR(directory.lstat().st_mode):
                raise ValueError("Proposal source contains a symlink or non-directory")
            with os.scandir(directory) as children:
                for child in children:
                    visited += 1
                    if visited > MAX_SOURCE_FILES * 2:
                        raise ValueError("Proposal source exceeds its finite entry limit")
                    path = Path(child.path)
                    info = child.stat(follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        raise ValueError("Proposal source contains a symlink")
                    if path == repo / ".git":
                        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                            raise ValueError("Invalid Git metadata in proposal source")
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        pending.append(path)
                        continue
                    if not stat.S_ISREG(info.st_mode):
                        raise ValueError("Proposal source contains a special file")
                    total += info.st_size
                    if (
                        len(rows) >= MAX_SOURCE_FILES
                        or info.st_size > MAX_SOURCE_FILE_BYTES
                        or total > MAX_SOURCE_BYTES
                    ):
                        raise ValueError("Proposal source exceeds its finite snapshot limits")
                    rows[path.relative_to(repo).as_posix()] = (
                        info.st_dev,
                        info.st_ino,
                        info.st_mode,
                        info.st_size,
                        info.st_mtime_ns,
                    )
        return rows

    before = inventory()
    hashes: list[tuple[str, int, str]] = []
    for name, expected in sorted(before.items()):
        directory = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in Path(name).parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                os.close(directory)
                directory = child
            descriptor = os.open(Path(name).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(descriptor, "rb") as stream:
                first = os.fstat(stream.fileno())
                raw = stream.read(MAX_SOURCE_FILE_BYTES + 1)
                last = os.fstat(stream.fileno())
                identities = [
                    (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns) for info in (first, last)
                ]
                if identities != [expected, expected] or len(raw) != expected[3] or len(raw) > MAX_SOURCE_FILE_BYTES:
                    raise ValueError("Proposal source changed during its snapshot")
                hashes.append((name, first.st_mode & 0o7777, hashlib.sha256(raw).hexdigest()))
        finally:
            os.close(directory)
    if inventory() != before:
        raise ValueError("Proposal source changed during its snapshot")
    raw_identity = json.dumps(["alpha-self-evolution-source/v1", hashes], separators=(",", ":")).encode()
    return hashlib.sha256(raw_identity).hexdigest()


def proposal_identity(repo: Path, diff: str, baseline: str) -> tuple[str, str]:
    """Create a fresh content/context identity; legacy vote keys are never aliases."""
    body = json.dumps(
        ["alpha-self-evolution-proposal/v2", str(repo.resolve()), _source_fingerprint(repo), baseline, diff],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "self-evolution-v2:sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest(), body


def vote_and_merge(repo: str | Path, diff: str, registry: StakeRegistry, agent_id: str = "orch") -> bool:
    """Apply patch and merge into `repo` when tests pass and the metric improves.

    Args:
        repo: Repository path to modify.
        diff: Unified diff to apply.
        registry: Vote registry used for consensus.
        agent_id: Identifier for the voting agent.

    Returns:
        ``True`` if the patch was merged into the repository.
    """
    repo_path = Path(repo).resolve()
    baseline_text = (repo_path / "metric.txt").read_text()
    proposal, body = proposal_identity(repo_path, diff, baseline_text)
    source_before = json.loads(body)[2]
    # Keep old votes untouched, but do not treat unbound or differently bound votes
    # as authority for this new proposal namespace.
    bodies = getattr(registry, "_self_evolution_proposal_bodies", None)
    if bodies is None:
        bodies = {}
        setattr(registry, "_self_evolution_proposal_bodies", bodies)
    if not isinstance(bodies, dict):
        raise ValueError("Invalid self-evolution proposal bindings")
    if proposal in bodies:
        if bodies[proposal] != body:
            return False
    elif proposal in registry.votes or proposal in registry.thresholds:
        return False
    bodies[proposal] = body
    baseline = float(baseline_text.strip())
    try:
        ok, patched = apply_patch(repo_path, diff, expected_source_fingerprint=source_before)
    except SourceSnapshotMismatch:
        return False
    try:
        unchanged = _source_fingerprint(repo_path) == source_before
    except (OSError, ValueError):
        shutil.rmtree(patched)
        raise
    if not unchanged:
        shutil.rmtree(patched)
        return False
    if not ok:
        registry.vote(proposal, agent_id, False)
        shutil.rmtree(patched)
        return False
    try:
        new_score = float((patched / "metric.txt").read_text().strip())
    except Exception:
        new_score = baseline
    improved = new_score < baseline
    registry.vote(proposal, agent_id, improved)
    accepted = improved and registry.accepted(proposal)
    if accepted:
        try:
            unchanged = _source_fingerprint(repo_path) == source_before
        except (OSError, ValueError):
            shutil.rmtree(patched)
            raise
        if not unchanged:
            shutil.rmtree(patched)
            return False
        for src_file in patched.rglob("*"):
            if src_file.is_file():
                rel = src_file.relative_to(patched)
                dest = repo_path / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)
        registry.archive_accept(agent_id)
    shutil.rmtree(patched)
    return accepted
