# SPDX-License-Identifier: Apache-2.0
"""Explicit local source-audit controls; no model, network, payment or self-signing."""
from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any

from ..store import Journal, private_write
from .measurement import MeasurementLedger
from .protocol import canonical, digest
from .transformation import assert_public_content
from .transformation_source_audit import AuditRequest, SourceAuditDiscovery, SourcePackage
from .transport import read_document
from .trust import SignedEnvelope, validate_external_trust_bytes


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new private evidence file; never overwritten")
    parser.add_argument("--trust", type=Path, help="separately installed public signer registry for measurement")
    parser.add_argument("--producer", help="configured producer identity; required with --trust")
    actions = parser.add_subparsers(dest="action", required=True)
    demo = actions.add_parser("demo", help="new-home bounded free comparison of supplied immutable fixtures")
    demo.add_argument("fixture", type=Path)
    demo.add_argument("--approve-free-local-audit", action="store_true", required=True)
    demo.add_argument("--campaign-id", default=None)
    create = actions.add_parser("create")
    create.add_argument("request", type=Path)
    for name in ("show", "freeze"):
        actions.add_parser(name).add_argument("campaign_id")
    approve = actions.add_parser("approve")
    approve.add_argument("campaign_id")
    approve.add_argument("binding_digest")
    confirm = actions.add_parser("confirm")
    confirm.add_argument("campaign_id")
    confirm.add_argument("packages", type=Path, help="object with complete committed packages list")
    confirm.add_argument("freeze_digest")
    control = actions.add_parser("control")
    control.add_argument("campaign_id")
    control.add_argument("operation", choices=("pause", "resume", "cancel"))
    proposal = actions.add_parser("propose-measurement")
    proposal.add_argument("package", type=Path)
    revise = actions.add_parser("revise-measurement", help="consume supplied distinct verifier/controller signatures")
    revise.add_argument("proposal_digest")
    revise.add_argument("validation", type=Path)
    revise.add_argument("approval", type=Path)
    revise.add_argument("--operation-id", required=True)
    actions.add_parser("context")
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("existing output is preserved; choose a new evidence path")
    if bool(args.trust) != bool(args.producer):
        raise ValueError("measurement trust and configured producer must be supplied together")
    if args.action == "demo" and (args.home.exists() or args.home.is_symlink()):
        raise FileExistsError("demo requires a new home; retained journals are never overwritten")
    # Screen and freeze supplied documents before initialization or ledger writes.
    loaded: dict[str, Any] = {}
    action = args.action
    if action == "demo":
        fixture = read_document(args.fixture)
        assert_public_content(fixture)
        loaded["development"] = [SourcePackage.model_validate(p) for p in fixture["development"]]
        loaded["confirmation"] = [SourcePackage.model_validate(p) for p in fixture["confirmation"]]
    elif action == "create":
        loaded["request"] = AuditRequest.model_validate(read_document(args.request))
    elif action == "confirm":
        loaded["packages"] = [SourcePackage.model_validate(p) for p in read_document(args.packages)["packages"]]
    elif action == "propose-measurement":
        loaded["package"] = SourcePackage.model_validate(read_document(args.package))
    elif action == "revise-measurement":
        loaded["validation"] = SignedEnvelope.model_validate(read_document(args.validation))
        loaded["approval"] = SignedEnvelope.model_validate(read_document(args.approval))
        assert_public_content([loaded["validation"].model_dump(), loaded["approval"].model_dump()])
    trust = validate_external_trust_bytes(canonical(read_document(args.trust))) if args.trust else None
    journal = Journal.initialize(args.home) if args.action == "demo" else Journal(args.home)
    ledger = None
    if trust is not None:
        ledger = MeasurementLedger(journal, trust, producer=args.producer)
    loop = SourceAuditDiscovery(journal, ledger)
    if action == "demo":
        development, confirmation = loaded["development"], loaded["confirmation"]
        request = AuditRequest(
            campaign_id=args.campaign_id or str(uuid.uuid4()),
            development=development,
            confirmation_digest=digest("source-audit-confirmation", confirmation),
            confirmation_count=len(confirmation),
            permitted_actions=["parse-static-source", "compare-local", "write-artifact"],
            **loop.measurement_context(),
        )
        queued = loop.create(request)
        loop.approve(request.campaign_id, queued["binding_digest"])
        frozen = loop.freeze(request.campaign_id)
        if frozen["state"] == "frozen":
            loop.confirm(request.campaign_id, confirmation, frozen["freeze"]["digest"])
        result = loop.envelope(request.campaign_id)
    elif action == "create":
        result = loop.create(loaded["request"])
    elif action == "approve":
        result = loop.approve(args.campaign_id, args.binding_digest)
    elif action == "freeze":
        result = loop.freeze(args.campaign_id)
    elif action == "confirm":
        result = loop.confirm(args.campaign_id, loaded["packages"], args.freeze_digest)
    elif action == "control":
        result = loop.control(args.campaign_id, args.operation)
    elif action == "propose-measurement":
        result = loop.propose_revision(loaded["package"])
    elif action == "revise-measurement":
        result = loop.revise_measurement(
            args.proposal_digest,
            loaded["validation"],
            loaded["approval"],
            operation_id=args.operation_id,
        )
    elif action == "context":
        result = loop.measurement_context()
    elif action == "show":
        result = loop.envelope(args.campaign_id)
    else:
        raise ValueError("unknown source audit command")
    private_write(args.output, canonical(result) + b"\n")
    return {"output": str(args.output.resolve()), "operation": action, "authority_granted": False}


if __name__ == "__main__":
    print(main())
