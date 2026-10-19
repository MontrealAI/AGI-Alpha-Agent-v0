# SPDX-License-Identifier: Apache-2.0
"""Explicit local model discovery commands; no implicit inference or auto approval."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..store import Journal, private_write
from .protocol import canonical
from .transformation import DiscoveryRequest, SourceDocument
from .transformation_model import LocalModelConfig, ModelDiscovery
from .transport import read_document


def add_commands(commands: Any) -> None:
    """Expose the same bounded model lifecycle through the installed product CLI."""
    parser = commands.add_parser("successor-model", help="Propose closed local-model programs and compare natively")
    _actions(parser)


def _actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("request", type=Path)
    create.add_argument("config", type=Path)
    for name in ("approve", "approve-native"):
        action = actions.add_parser(name)
        action.add_argument("campaign_id")
        action.add_argument("--binding", required=True)
    for name in ("show", "propose", "prepare-native", "pause", "resume", "cancel"):
        actions.add_parser(name).add_argument("campaign_id")
    step = actions.add_parser("step")
    step.add_argument("campaign_id")
    step.add_argument("--operation-id", required=True)
    confirm = actions.add_parser("confirm")
    confirm.add_argument("campaign_id")
    confirm.add_argument("documents", type=Path)
    confirm.add_argument("--freeze", required=True)
    export = actions.add_parser("export")
    export.add_argument("campaign_id")
    export.add_argument("--output", type=Path, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Require a distinct reviewable binding for the call and native computation."""
    result: dict[str, Any]
    if args.action == "create":
        request = DiscoveryRequest.model_validate(read_document(args.request))
        config = LocalModelConfig.model_validate(read_document(args.config))
        journal = Journal(args.home) if (args.home / "journal.sqlite3").exists() else Journal.initialize(args.home)
        result = ModelDiscovery(journal).create(request, config)
    else:
        driver = ModelDiscovery(Journal(args.home))
        if args.action == "show":
            result = driver.show(args.campaign_id)
        elif args.action == "approve":
            result = driver.approve(args.campaign_id, args.binding)
        elif args.action == "propose":
            result = driver.propose(args.campaign_id)
        elif args.action in {"pause", "resume", "cancel"}:
            result = driver.control(args.campaign_id, args.action)
        elif args.action == "export":
            if args.output.exists() or args.output.is_symlink():
                raise FileExistsError("choose a new model evidence output")
            private_write(args.output, canonical(driver.envelope(args.campaign_id)))
            result = {"output": str(args.output.resolve()), "authority_exported": False}
        elif args.action == "confirm":
            document = read_document(args.documents)
            if set(document) != {"documents"} or not isinstance(document["documents"], list):
                raise ValueError("confirmation requires exactly a documents array")
            result = driver.compare(
                args.campaign_id, [SourceDocument.model_validate(item) for item in document["documents"]], args.freeze
            )
        else:
            loop, request = driver.native(args.campaign_id)
            if args.action == "prepare-native":
                result = loop.show(request.campaign_id)
            elif args.action == "approve-native":
                result = loop.approve(request.campaign_id, args.binding)
            elif args.action == "step":
                result = loop.step(request.campaign_id, operation_id=args.operation_id)
            else:
                raise ValueError("unknown model discovery action")
    return result


def main() -> None:
    """Preserve the explicit standalone command while sharing product behavior."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    _actions(parser)
    print(canonical(handle(parser.parse_args())).decode())


if __name__ == "__main__":
    main()
