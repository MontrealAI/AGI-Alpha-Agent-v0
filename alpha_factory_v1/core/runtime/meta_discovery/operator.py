# SPDX-License-Identifier: Apache-2.0
"""Additive native Alpha operator commands for reproducible investigation."""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from .instrument import compile_plan, read, write_new, update_belief
from .checker import check
from .models import make_task, investigate


def add_commands(commands: Any) -> None:
    root = commands.add_parser(
        "meta-discovery", help="Construct and check decision-separating experiments; no physical or spending authority"
    )
    sub = root.add_subparsers(dest="meta_action", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("file", type=Path)
    plan.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("check")
    verify.add_argument("file", type=Path)
    verify.add_argument("--plan", type=Path, required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--family", choices=["catalyst", "membrane", "photovoltaic"], default="membrane")
    demo.add_argument("--output", type=Path, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    if args.meta_action == "plan":
        task = read(args.file)
        result = compile_plan(task)
        write_new(args.output, result)
        return {"output": str(args.output), "plan": result, "check": check(task, result)}
    if args.meta_action == "check":
        return check(read(args.file), read(args.plan))
    args.output.mkdir(parents=True, exist_ok=False)
    task, private = make_task(args.family, 20261028)
    plan = compile_plan(task)
    verdict = check(task, plan)
    observations = investigate(task, private, plan["selected"]) if plan["selected"] else {}
    result = {
        "plan": plan,
        "check": verdict,
        "observations": observations,
        "decision": update_belief(task, observations) if observations else {"status": "NO_DECISIVE_EXPERIMENT"},
        "authority": "local-simulation-only",
        "physicalQualified": False,
    }
    write_new(args.output / "task.json", task)
    write_new(args.output / "result.json", result)
    return result
