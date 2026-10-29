# SPDX-License-Identifier: Apache-2.0
"""Native commands for executed comparisons and trusted-evidence verification."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any


def add_commands(commands: Any) -> None:
    command = commands.add_parser("experience", help="Compare retained LP experience with strong conventional controls")
    sub = command.add_subparsers(dest="experience_command", required=True)
    run = sub.add_parser("run")
    run.add_argument("base", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--cases-per-regime", type=int, default=8)
    run.add_argument("--repeats", type=int, default=3)
    run.add_argument("--cost-policy", type=Path)
    for name in ("check", "replay"):
        item = sub.add_parser(name)
        item.add_argument("directory", type=Path)
        item.add_argument("--seal-sha256", required=True)
        if name == "replay":
            item.add_argument("--output", type=Path, required=True)


def check_seal(directory: Path, expected: str) -> dict[str, Any]:
    from . import verifier

    seal_path = directory / "evidence-seal.json"
    if hashlib.sha256(seal_path.read_bytes()).hexdigest() != expected:
        raise ValueError("trusted evidence seal differs")
    seal: dict[str, Any] = verifier.read(seal_path)
    for name, sha in seal["files"].items():
        if Path(name).name != name or name.startswith("."):
            raise ValueError("evidence seal contains an unsupported path")
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != sha:
            raise ValueError("sealed evidence changed: " + name)
    return seal


def handle(args: argparse.Namespace) -> dict[str, Any]:
    from . import experiment, verifier

    if args.experience_command == "check":
        seal = check_seal(args.directory, args.seal_sha256)
        result = experiment.independent_audit(args.directory, seal["files"]["freeze.json"], save=False)
        return {"seal_verified": True, **result}
    if args.experience_command == "replay":
        check_seal(args.directory, args.seal_sha256)
        policy = verifier.read(args.directory / "protocol.json")
        result = experiment.run(
            verifier.read(args.directory / "base.json"), args.output,
            count=policy["cases_per_regime"], repeats=policy["repeats"],
            costs=verifier.read(args.directory / "cost-policy.json"), replay_from=args.directory,
        )
    else:
        result = experiment.run(
            verifier.read(args.base), args.output, count=args.cases_per_regime, repeats=args.repeats,
            costs=verifier.read(args.cost_policy) if args.cost_policy else None,
        )
    return {"output": str(args.output.resolve()), "overall_demonstration": result["overall_demonstration"],
            "measured_cpu_advantage": result["measured_cpu_advantage"],
            "complete_cost_advantage": result["complete_cost_advantage"],
            "best_observed_control": result["best_observed_control"],
            "evidence_seal_sha256": experiment.file_hash(args.output / "evidence-seal.json"),
            "confirmation": False}
