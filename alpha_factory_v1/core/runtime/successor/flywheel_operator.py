# SPDX-License-Identifier: Apache-2.0
"""Provisioned native Flywheel commands; imports cannot install credentials or authority."""

from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit
from pydantic import Field
from ..chain import RPC
from ..models import ChainConfig
from ..store import Journal, _private_recovery_bytes, private_write
from .flywheel_access import ENSAuthority, ENSPins, ResourceAccess, ServiceIdentity
from .flywheel_capsules import CapsuleManifest, ProtectedLibrary
from .flywheel_checkpoint import DurableCheckpoint
from .flywheel_costs import CostLedger
from .flywheel_frontier import FrontierConnector
from .protocol import StrictModel, canonical, safe_json_loads
from .transformation import DiscoveryRequest, SelectionProgram
from .transformation_library import TransformationLibrary
from .transport import read_document
from .trust import SignedEnvelope, validate_external_trust_bytes


class Deployment(StrictModel):
    schema_name: str = Field(pattern=r"^protected-flywheel-deployment/v1$")
    service: ServiceIdentity
    producer: str = Field(min_length=1, max_length=128)
    trust_path: str = Field(min_length=1, max_length=4096)
    checkpoint_path: str = Field(min_length=1, max_length=4096)
    readers: list[ChainConfig] = Field(min_length=2, max_length=2)
    ens_pins: ENSPins
    keys: dict[str, str]
    active_key: str = Field(min_length=1, max_length=80)


def load(journal: Journal, deployment_path: Path) -> ProtectedLibrary:
    """Require preprovisioned keys/checkpoint, trusted roles and two approved readers."""
    deployment_raw = _private_recovery_bytes(deployment_path, limit=131_072)
    deployment = Deployment.model_validate(safe_json_loads(deployment_raw))
    custody_files = {str(deployment_path.absolute()): hashlib.sha256(deployment_raw).hexdigest()}
    if any(reader.chain_id != 1 for reader in deployment.readers):
        raise ValueError("protected ENSv1 deployment supports Ethereum mainnet only")
    if len({urlsplit(reader.rpc_url).hostname for reader in deployment.readers}) != 2:
        raise ValueError("use two separately approved RPC providers with distinct hosts")
    trust_raw = _private_recovery_bytes(Path(deployment.trust_path), limit=131_072)
    trust = validate_external_trust_bytes(trust_raw)
    custody_files[str(Path(deployment.trust_path).absolute())] = hashlib.sha256(trust_raw).hexdigest()
    library = TransformationLibrary(journal, trust, producer=deployment.producer)
    costs = CostLedger(journal, trust)
    access = ResourceAccess(
        journal,
        deployment.service,
        ENSAuthority(
            (RPC(deployment.readers[0], timeout_seconds=2.0), RPC(deployment.readers[1], timeout_seconds=2.0)),
            deployment.ens_pins,
        ),
    )
    if not 1 <= len(deployment.keys) <= 16:
        raise ValueError("a bounded independently provisioned key inventory is required")
    keys = {key: _private_recovery_bytes(Path(path), limit=32) for key, path in deployment.keys.items()}
    custody_files.update(
        {str(Path(path).absolute()): hashlib.sha256(keys[key]).hexdigest() for key, path in deployment.keys.items()}
    )
    checkpoint = DurableCheckpoint(Path(deployment.checkpoint_path), journal)
    return ProtectedLibrary(
        library, costs, access, keys, deployment.active_key, checkpoint, custody_files=custody_files
    )


def add_commands(commands: Any) -> None:
    parser = commands.add_parser(
        "flywheel", help="Operate explicitly provisioned protected capsules on the existing journal"
    )
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    actions = parser.add_subparsers(dest="flywheel_action", required=True)
    actions.add_parser("status", help="Report connector and operating qualification limits without invoking providers")
    for action in (
        "configure",
        "plan",
        "evidence",
        "validate",
        "admit",
        "revoke",
        "rotate-key",
        "reuse-acceptance",
        "account",
    ):
        sub = actions.add_parser(action, help="Apply a separately signed bounded " + action + " decision")
        sub.add_argument("signed", type=Path)
    candidate = actions.add_parser(
        "candidate", help="Retain a frozen rights-cleared closed selector from accepted work"
    )
    candidate.add_argument("manifest", type=Path)
    candidate.add_argument("program", type=Path)
    candidate.add_argument("signed", type=Path)
    model = actions.add_parser(
        "model-run", help="One explicitly permitted actual provider attempt; never implicit retry"
    )
    model.add_argument("request", type=Path)
    model.add_argument("signed", type=Path)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("choose a new private evidence output")
    service = load(Journal(args.home), args.deployment)
    action = args.flywheel_action
    result: Any = None
    signed = SignedEnvelope.model_validate(read_document(args.signed)) if hasattr(args, "signed") else None
    if action == "status":
        result = {
            "protected_service": "provisioned-not-live-qualified",
            "execution_digest": service.execution_digest,
            "frontier": FrontierConnector(service.journal, service.trust, service.costs).status(),
            "costs": service.costs.report(),
            "live_identity_qualification": "requires deployment-specific owner-controlled signing and approved RPC evidence",
            "capsule_export": "controlled-invocation-only",
        }
    if action == "status":
        private_write(args.output, canonical({"action": action, "result": result}))
        return {"output": str(args.output.resolve()), "action": action, "qualified_live_operation": False}
    if signed is None:
        raise ValueError("a separately signed command is required")
    if action == "candidate":
        result = {
            "candidate_digest": service.retain(
                CapsuleManifest.model_validate(read_document(args.manifest)),
                SelectionProgram.model_validate(read_document(args.program)),
                signed,
            )
        }
    elif action == "model-run":
        result = FrontierConnector(service.journal, service.trust, service.costs).run(
            DiscoveryRequest.model_validate(read_document(args.request)), signed
        )
    elif action == "account":
        result = service.costs.apply(signed)
    elif action in {"validate", "admit", "revoke"}:
        service.control(signed, cast(Any, action))
    elif action == "configure":
        service.configure(signed)
    elif action == "plan":
        service.freeze(signed)
    elif action == "evidence":
        result = {"decision": service.evaluate(signed)}
    elif action == "rotate-key":
        service.rotate(signed)
    elif action == "reuse-acceptance":
        result = service.accept_reuse(signed)
    else:
        raise ValueError("unsupported protected Flywheel command")
    private_write(args.output, canonical({"action": action, "result": result, "spending_authority_granted": False}))
    return {"output": str(args.output.resolve()), "action": action, "qualified_live_operation": False}
