# SPDX-License-Identifier: Apache-2.0
"""Explicit CLI for local complete-campaign discovery-policy experiments."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..store import Journal, private_write
from .campaign_experiment import CampaignExperiment, CampaignUnit, PolicyStudy
from .protocol import canonical
from .transport import read_document


def _is_exact_type(value: object, expected: type[object]) -> bool:
    """Compare exact types without admitting bool or other subclasses."""
    return type(value) is expected


def add_commands(commands: Any) -> None:
    """Add proposed/approved/training/frozen/terminal study operations."""
    parser = commands.add_parser("successor-study", help="Compare bounded discovery policies across complete campaigns")
    parser.add_argument("--output", type=Path, required=True, help="New evidence file; never overwrite an artifact")
    actions = parser.add_subparsers(dest="study_action", required=True)
    create = actions.add_parser("create", help="Propose exact purpose, policies, budgets and whole-sample design")
    create.add_argument("spec", type=Path)
    approve = actions.add_parser("approve", help="Approve the exact free local study binding")
    approve.add_argument("study_id")
    approve.add_argument("--binding", required=True)
    for name in ("train", "confirm"):
        action = actions.add_parser(name, help="Run complete campaigns from a separately supplied batch")
        action.add_argument("study_id")
        action.add_argument("units", type=Path)
        if name == "confirm":
            action.add_argument("--freeze", required=True)
    for name in ("show", "export", "pause", "resume", "cancel"):
        action = actions.add_parser(name, help="Inspect or control the durable study")
        action.add_argument("study_id")
    actions.add_parser("operation-example", help="Write a finite synthetic source-operation envelope")
    start = actions.add_parser("operation-start", help="Approve and run one exact bounded source operation")
    start.add_argument("spec", type=Path)
    for name in ("run", "status", "export", "stop"):
        action = actions.add_parser(
            "operation-" + name, help="Run, inspect, export or permanently stop the existing operation"
        )
        action.add_argument("operation_id")


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Retain full evidence without granting promotion, payment or execution authority."""
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("choose a new output path; existing evidence is never replaced")
    action = args.study_action
    if action.startswith("operation-"):
        from .campaign_operation import CampaignOperation, OperationSpec, example

        if action == "operation-example":
            result = example().model_dump()
        else:
            operation = CampaignOperation(Journal(args.home))
            if action == "operation-start":
                proposed = OperationSpec.model_validate(read_document(args.spec))
                operation.start(proposed)
                result = operation.run(proposed.operation_id)
            elif action == "operation-run":
                result = operation.run(args.operation_id)
            elif action == "operation-status":
                result = operation.status(args.operation_id)
            elif action == "operation-export":
                result = operation.export(args.operation_id)
            else:
                result = operation.stop(args.operation_id)
        private_write(args.output, canonical(result))
        if action == "operation-example":
            return {
                "output": str(args.output.resolve()),
                "operation_id": result["operation_id"],
                "next": "Review the finite envelope, then use operation-start with this file.",
            }
        return (
            {"output": str(args.output.resolve()), **result}
            if action != "operation-export"
            else {"output": str(args.output.resolve()), "active_authority": []}
        )
    experiment = CampaignExperiment(Journal(args.home))
    if action == "create":
        result = experiment.create(PolicyStudy.model_validate(read_document(args.spec)))
    elif action == "approve":
        result = experiment.approve(args.study_id, args.binding)
    elif action in {"train", "confirm"}:
        batch = read_document(args.units)
        if set(batch) != {"schema", "units"} or batch["schema"] != "discovery-policy-campaigns/v1":
            raise ValueError("unsupported complete-campaign batch")
        if not _is_exact_type(batch["units"], list) or not 1 <= len(batch["units"]) <= 64:
            raise ValueError("supply a bounded whole batch")
        units = [CampaignUnit.model_validate(unit) for unit in batch["units"]]
        result = (
            experiment.train(args.study_id, units)
            if action == "train"
            else experiment.confirm(args.study_id, units, args.freeze)
        )
    elif action == "show":
        result = experiment.show(args.study_id)
    elif action == "export":
        result = experiment.export(args.study_id)
    elif action in {"pause", "resume", "cancel"}:
        result = experiment.control(args.study_id, action)
    else:
        raise ValueError("unsupported study operation")
    private_write(args.output, canonical(result))
    return {
        "output": str(args.output.resolve()),
        "state": result.get("state", result.get("study", {}).get("state")),
        "authority_granted": False,
        "scope": "bounded complete source campaigns; independent sampling and calibration require external evidence",
    }
