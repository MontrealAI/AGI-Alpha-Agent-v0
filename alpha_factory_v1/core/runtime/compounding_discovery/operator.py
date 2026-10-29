# SPDX-License-Identifier: Apache-2.0
"""Offline discovery commands, durable failed attempts and explicit memory promotion."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..structural_transfer.contracts import digest, read, write_new
from . import engine


def resume(request: dict[str, Any], directory: Path, memory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recover completed results; never automatically retry a charged incomplete attempt."""
    memory = memory if memory is not None else engine.empty_memory()
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError("symlink output not supported")
    if directory.exists():
        if read(directory / "request.json") != request or read(directory / "memory.json") != memory:
            raise ValueError("resume request or memory differs")
        if read(directory / "freeze.json") != engine.source_hashes():
            raise ValueError("resume source qualification differs")
        result_path = directory / "result.json"
        if result_path.exists():
            result: dict[str, Any] = read(result_path)
            engine.verify_result(request, result)
            return result
        # Failed CPU, calls and partial stages remain incurred. New work needs a
        # separately recorded allocation, rather than silently resetting a cap.
        raise ValueError("incomplete attempt preserved; inspect costs and allocate an explicit new request")
    directory.mkdir(parents=True, exist_ok=False)
    write_new(directory / "request.json", request)
    write_new(directory / "memory.json", memory)
    write_new(directory / "freeze.json", engine.source_hashes())
    index = 0

    def checkpoint(snapshot: dict[str, Any]) -> None:
        nonlocal index
        index += 1
        write_new(directory / f"resource-{index:04d}.json", snapshot)

    try:
        result = engine.execute(request, memory, _checkpoint=checkpoint)
        write_new(directory / "result.json", result)
        write_new(directory / "verification.json", engine.verify_result(request, result))
        return result
    except Exception as error:
        write_new(
            directory / "failure.json",
            {
                "error": type(error).__name__,
                "request_hash": digest(request),
                "resource_records": index,
                "accepted": False,
                "funding": "seed-funded-research",
            },
        )
        raise


def add_commands(commands: Any) -> None:
    """Register explicit commands alongside the ordinary mission interface."""
    command = commands.add_parser("discovery", help="Execute bounded compositional discovery offline")
    sub = command.add_subparsers(dest="discovery_command", required=True)
    for name in ("run", "resume"):
        run = sub.add_parser(name)
        run.add_argument("file", type=Path)
        run.add_argument("--memory", type=Path)
        run.add_argument("--output", type=Path, required=True)
    sub.add_parser("check").add_argument("directory", type=Path)
    promote = sub.add_parser("learn")
    promote.add_argument("directory", type=Path)
    promote.add_argument("--output", type=Path, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Preserve exact captures and stop promotion at an explicit operator command."""
    if args.discovery_command in {"run", "resume"}:
        if args.discovery_command == "run" and args.output.exists():
            raise ValueError("new output directory required; use resume for completed work")
        request = read(args.file)
        result = resume(request, args.output, read(args.memory) if args.memory else None)
        return {"output": str(args.output.resolve()), **engine.verify_result(request, result)}
    request = read(args.directory / "request.json")
    result = read(args.directory / "result.json")
    if args.discovery_command == "check":
        return engine.verify_result(request, result)
    memory = engine.learn(read(args.directory / "memory.json"), result)
    write_new(args.output, memory)
    return {"memory_hash": memory["memory_hash"], "version": memory["version"], "output": str(args.output.resolve())}
