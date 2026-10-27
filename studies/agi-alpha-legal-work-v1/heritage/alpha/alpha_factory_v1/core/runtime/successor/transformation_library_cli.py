# SPDX-License-Identifier: Apache-2.0
"""Explicit archive and signed local-reuse controls; no signing or self-approval."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..store import Journal, private_write
from .protocol import canonical
from .transformation_library import ReuseConditions, RouterContext, TransformationLibrary
from .transport import read_document
from .trust import SignedEnvelope, validate_external_trust_bytes


def add_commands(commands: Any) -> None:
    """Add a native operator surface without generating credentials or approvals."""
    parser = commands.add_parser(
        "successor-library", help="Archive and explicitly review, select or retire local methods"
    )
    parser.add_argument(
        "--trust", type=Path, required=True, help="Separately installed public principal trust registry"
    )
    parser.add_argument(
        "--producer", required=True, help="Configured producing principal; not taken from campaign data"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New output file; existing artifacts are never replaced"
    )
    actions = parser.add_subparsers(dest="library_action", required=True)
    archive = actions.add_parser(
        "archive", help="Retain a native campaign and explicit reuse conditions as pending review"
    )
    archive.add_argument("campaign", type=Path)
    archive.add_argument("conditions", type=Path)
    archive.add_argument("--operation-id", required=True)
    review = actions.add_parser("review", help="Apply a previously signed distinct verifier's scoped review")
    review.add_argument("archive_digest")
    review.add_argument("signed", type=Path)
    review.add_argument("--operation-id", required=True)
    control = actions.add_parser("control", help="Apply signed controller promotion, rollback or retirement")
    control.add_argument("archive_digest")
    control.add_argument("signed", type=Path)
    control.add_argument("--behavior-digest", required=True)
    control.add_argument("--operation-id", required=True)
    route = actions.add_parser("route", help="Select local behavior for an independently authorized target charter")
    route.add_argument("context", type=Path)
    actions.add_parser("show", help="Export retained versions, reviews and control history without granting authority")


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Require explicit installed trust and supplied signatures; preserve output files."""
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("choose a new library evidence output; existing files are never replaced")
    trust = validate_external_trust_bytes(canonical(read_document(args.trust)))
    library = TransformationLibrary(Journal(args.home), trust, producer=args.producer)
    action = args.library_action
    if action == "archive":
        result = library.archive(
            read_document(args.campaign),
            ReuseConditions.model_validate(read_document(args.conditions)),
            operation_id=args.operation_id,
        )
    elif action == "review":
        result = library.review(
            args.archive_digest,
            SignedEnvelope.model_validate(read_document(args.signed)),
            operation_id=args.operation_id,
        )
    elif action == "control":
        result = library.control(
            args.archive_digest,
            SignedEnvelope.model_validate(read_document(args.signed)),
            expected_behavior_digest=args.behavior_digest,
            operation_id=args.operation_id,
        )
    elif action == "route":
        result = library.route(RouterContext.model_validate(read_document(args.context)))
    elif action == "show":
        result = library.snapshot()
    else:
        raise ValueError("unsupported library command")
    private_write(args.output, canonical(result))
    return {
        "output": str(args.output.resolve()),
        "operation": action,
        "authority_granted": False,
        "execution_approved": False,
        "spending_approved": False,
        "scope": "local structural reuse; target execution still requires its own charter authorization",
    }
