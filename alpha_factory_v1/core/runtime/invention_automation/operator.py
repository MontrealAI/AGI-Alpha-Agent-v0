# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..structural_transfer.contracts import digest, read, write_new
from . import engine, programs


def add_commands(commands: Any) -> None:
    parser = commands.add_parser("invention", help="Restricted contingent strategy construction; exploratory SIM only")
    sub = parser.add_subparsers(dest="invention_command", required=True)
    run = sub.add_parser("run")
    run.add_argument("file", type=Path)
    run.add_argument("--output", type=Path, required=True)
    critique = sub.add_parser("repair")
    critique.add_argument("file", type=Path)
    critique.add_argument("--witness", type=Path, required=True)
    critique.add_argument("--output", type=Path, required=True)
    probe = sub.add_parser("meter-probe")
    probe.add_argument("--meter", type=Path, required=True)
    probe.add_argument("--weather", type=Path, required=True)
    probe.add_argument("--output", type=Path, required=True)
    critic = sub.add_parser(
        "critic-loop", help="Evidence-bound creator/critic/test/correction loop; Docker execution only"
    )
    critic.add_argument("file", type=Path)
    critic.add_argument("--context", type=Path, required=True)
    critic.add_argument("--freeze", type=Path, required=True)
    critic.add_argument("--output", type=Path, required=True)
    critic.add_argument("--objections", type=Path, help="Optional inert typed host-model objections")
    critic_resume = sub.add_parser("critic-resume", help="Verify an existing critic checkpoint without regeneration")
    critic_resume.add_argument("--output", type=Path, required=True)
    for name in ["qualify", "qualify-resume", "qualify-reproduce"]:
        qualify = sub.add_parser(
            name, help="Retired legacy protocol; use critic-loop with frozen source field/span context"
        )
        qualify.add_argument("file", type=Path)
        qualify.add_argument("--output", type=Path, required=True)
        if name == "qualify":
            qualify.add_argument("--freeze", type=Path, required=True, help="Externally frozen source/protocol hashes")
        if name == "qualify-reproduce":
            qualify.add_argument("--checkpoint", type=Path, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    if args.invention_command in {"critic-loop", "critic-resume"}:
        from . import critic_loop

        result = (
            critic_loop.resume(args.output)
            if args.invention_command == "critic-resume"
            else critic_loop.run(args.file, args.context, args.freeze, args.output, objections_path=args.objections)
        )
        return {
            "output": str(args.output.resolve()),
            "candidate_hash": result["candidate_hash"],
            "verdicts": result["verdicts"],
            "complete_loop_status": result["complete_loop_status"],
            "acceptance": result["acceptance"],
            "confirmation": False,
        }
    if args.invention_command in {"qualify", "qualify-resume", "qualify-reproduce"}:
        from . import specification_run

        specification_run.reject_legacy_qualification()
    if args.invention_command == "meter-probe":
        from .data_probe import analyze

        result = analyze(args.meter, args.weather)
        write_new(args.output, result)
        return {"output": str(args.output.resolve()), "hash": digest(result), "scope": result["scope"]}
    request = read(args.file)
    if set(request) != {"program", "cases", "opening"}:
        raise ValueError("request fields")
    if any(p.is_symlink() for p in [args.output, *args.output.parents]):
        raise ValueError("symlink output refused")
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / "request.json", request)
    if args.invention_command == "repair":
        witness = read(args.witness)
        constraint = engine.validate_criticism(
            request["program"],
            request["cases"],
            witness,
            args.output / "reproduction.sqlite",
            opening=request["opening"],
        )
        revised = programs.adapt(request["program"], constraint)
        write_new(args.output / "constraint.json", constraint)
        write_new(args.output / "revised-request.json", {**request, "program": revised})
        return {
            "output": str(args.output.resolve()),
            "candidate_hash": digest(revised),
            "validated_constraint": constraint["family"],
            "confirmed": False,
        }
    result = engine.execute(
        request["program"], request["cases"], args.output / "exchange.sqlite", opening=request["opening"]
    )
    write_new(args.output / "result.json", result)
    write_new(args.output / "criticisms.json", engine.failures(request["cases"], result))
    return {"output": str(args.output.resolve()), "summary": result["summary"], "confirmed": False}
