# SPDX-License-Identifier: Apache-2.0
"""Narrow evidence-grounded critic commands; precursor money flows excluded."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def add_commands(commands: Any) -> None:
    parser = commands.add_parser("invention", help="Source-bound criticism; static and Docker gates remain separate")
    sub = parser.add_subparsers(dest="invention_command", required=True)
    run = sub.add_parser("critic-loop")
    run.add_argument("file", type=Path)
    run.add_argument("--context", type=Path, required=True)
    run.add_argument("--freeze", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--objections", type=Path)
    resume = sub.add_parser("critic-resume")
    resume.add_argument("--output", type=Path, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    from . import critic_loop

    if args.invention_command == "critic-resume":
        result = critic_loop.resume(args.output)
    elif args.invention_command == "critic-loop":
        result = critic_loop.run(args.file, args.context, args.freeze, args.output, objections_path=args.objections)
    else:
        raise ValueError("uninstalled invention command")
    return {
        "output": str(args.output.resolve()),
        "candidate_hash": result["candidate_hash"],
        "verdicts": result["verdicts"],
        "complete_loop_status": result["complete_loop_status"],
        "acceptance": result["acceptance"],
        "confirmation": False,
    }
