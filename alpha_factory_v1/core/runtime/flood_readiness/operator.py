# SPDX-License-Identifier: Apache-2.0
"""Actual installed beneficiary workflow over an explicitly supplied NOAA snapshot."""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from . import readiness
from ..claim_probe.contracts import write_new


def add_commands(commands: Any) -> None:
    """Register an additive offline user entry point."""
    command = commands.add_parser(
        "flood-readiness", help="Audit a NOAA flood snapshot; preserve unknown loss and geography meaning"
    )
    command.add_argument("source", type=Path)
    command.add_argument("--year", type=int, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--language", choices=["en", "fr"], default="en")


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Produce the real report and independently reconstruct its acceptance."""
    from . import checker

    if args.source.is_symlink() or not args.source.is_file() or args.source.stat().st_size > 25_000_000:
        raise ValueError("regular source of at most25000000 bytes required")
    task = readiness.task_for(args.source, args.year)
    artifact, csv_text, _ = readiness.build_report(task, args.source)
    verdict = checker.verify(task, artifact, args.source, csv_text)
    if verdict.get("accepted") is not True:
        raise ValueError("independent beneficiary acceptance failed")
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / "task.json", task)
    write_new(args.output / "readiness-report.json", artifact)
    write_new(args.output / "acceptance.json", verdict)
    with (args.output / "native-counts.csv").open("x") as f:
        f.write(csv_text)
    scope = {
        "en": "Reported historical records only. Unknown damage is not zero; forecast zones are not counties. Complete loss and risk rankings are unqualified.",
        "fr": "Observations historiques déclarées seulement. Une estimation absente ne vaut pas zéro; les zones de prévision ne sont pas des comtés. Les classements complets des pertes et du risque restent non qualifiés.",
    }
    return {
        "output": str(args.output),
        "acceptance": verdict,
        "sourceSha256": task["source_sha256"],
        "scope": scope[args.language],
    }
