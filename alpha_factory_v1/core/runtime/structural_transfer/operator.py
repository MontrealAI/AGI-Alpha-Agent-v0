# SPDX-License-Identifier: Apache-2.0
"""Explicit offline CLI for source extraction and checked structural transfer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import engine
from .contracts import CAPTURE_SCHEMA, RESULT_SCHEMA, digest, read, write_new


def add_commands(commands: Any) -> None:
    """Add a separate command group without changing the existing transfer benchmark."""
    transfer = commands.add_parser("transfer", help="Execute, extract and check explicit typed structural transfer")
    sub = transfer.add_subparsers(dest="transfer_command", required=True)
    for name in ("extract", "run"):
        command = sub.add_parser(name)
        command.add_argument("file", type=Path)
        command.add_argument(
            "--output", type=Path, required=True, help="Create a new directory; retain all failed stages"
        )
    sub.add_parser("inspect").add_argument("file", type=Path)
    sub.add_parser("check").add_argument("directory", type=Path)


def _new_directory(path: Path, source: Path) -> None:
    """Reject path aliases, symlinks and existing outputs before beginning work."""
    if path.resolve() == source.resolve() or source.resolve() in path.resolve().parents:
        raise ValueError("input/output path collision")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("symlinked output paths are not supported")
    path.mkdir(parents=True, exist_ok=False)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Produce concrete inspectable artifacts and preserve failure evidence exclusively."""
    if args.transfer_command == "inspect":
        document = read(args.file)
        if document.get("schema") == CAPTURE_SCHEMA:
            return engine.inspect_capture(document)
        if document.get("schema") == RESULT_SCHEMA:
            return {
                "schema": document["schema"],
                "result_hash": document["result_hash"],
                "accepted": document.get("accepted") is True,
                "delivery": document["delivery"],
                "note": "use transfer check DIRECTORY for complete replay",
            }
        raise ValueError("capture or transfer result required")
    if args.transfer_command == "check":
        root = args.directory
        if root.is_symlink() or not root.is_dir():
            raise ValueError("regular transfer directory required")
        return engine.verify_result(read(root / "request.json"), read(root / "result.json"))
    document = read(args.file)
    _new_directory(args.output, args.file)
    write_new(args.output / ("source.json" if args.transfer_command == "extract" else "request.json"), document)
    stages: list[dict[str, Any]] = []

    def stage(name: str, detail: dict[str, Any]) -> None:
        entry = {"stage": name, "detail": detail}
        stages.append(entry)
        write_new(args.output / f"stage-{len(stages):02d}.json", entry)
        if name == "adaptation-construction":
            write_new(args.output / "constructed.json", detail["constructed"])
        elif name == "adaptation-execution":
            write_new(args.output / "artifact.json", detail["artifact"])
        elif name == "independent-acceptance":
            write_new(args.output / "acceptance.json", detail["verdict"])

    try:
        if args.transfer_command == "extract":
            capture = engine.extract(document, stage=stage)
            write_new(args.output / "capture.json", capture)
            inspected = engine.inspect_capture(capture)
            write_new(args.output / "extraction-check.json", inspected)
            return {"output": str(args.output.resolve()), **inspected}
        result = engine.run(document, stage)
        write_new(args.output / "result.json", result)
        verification = engine.verify_result(document, result)
        write_new(args.output / "delivery.json", result["delivery"])
        write_new(args.output / "verification.json", verification)
        return {"output": str(args.output.resolve()), **verification}
    except Exception as exc:
        # Error bodies can contain supplied source text; preserve only type and exact input/stage bindings.
        write_new(
            args.output / "failure.json",
            {
                "error": type(exc).__name__,
                "input_hash": digest(document),
                "completed_stages": [{"stage": item["stage"], "record_hash": digest(item)} for item in stages],
                "accepted": False,
            },
        )
        raise
