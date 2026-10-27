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
from .flywheel_specialists import PlacementWorkflow
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
    receipt = actions.add_parser("receipt", help="Export an existing durable invocation request and receipt")
    receipt.add_argument("mission_id")
    execution_receipt = actions.add_parser("execution-receipt", help="Inspect a durable general mission or observation")
    execution_receipt.add_argument("operation_id")
    execution_receipt.add_argument("--event", help="Exact attempt label from the private mission receipt")
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
        "archive",
        "migrate",
        "gym-run",
        "general-acceptance",
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
    execution = actions.add_parser("mission-run", help="Explicit Responses reasoning/tool mission; no implicit retry")
    execution.add_argument("request", type=Path)
    execution.add_argument("profile", type=Path)
    execution.add_argument("signed", type=Path)
    environment = execution.add_mutually_exclusive_group(required=True)
    environment.add_argument("--tool-endpoint", type=Path, help="Private approved sandbox service contract")
    environment.add_argument("--computer-task", type=Path, help="Existing bounded ComputerTask")
    execution.add_argument("--computer-image", help="Approved immutable locally installed Docker image digest")


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
            "general_execution": {
                "interface": "flywheel-execution/v1",
                "command": "mission-run",
                "transport": "Responses reasoning, strict function calls, computer actions and resulting screenshots",
                "live_qualified": False,
                "dependencies": "separate signed permit, approved model account, budget and sandbox or browser image",
            },
            "costs": service.costs.report(),
            "live_identity_qualification": "requires deployment-specific owner-controlled signing and approved RPC evidence",
            "capsule_export": "controlled-invocation-only",
        }
    if action == "receipt":
        result = service.inspect_invocation(args.mission_id)
    if action == "execution-receipt":
        from .flywheel_execution import operation_key

        key = operation_key(args.operation_id)
        if args.event is not None:
            if len(args.event) > 500 or not args.event.startswith(("model/", "tool/")):
                raise ValueError("use the exact bounded attempt label from the private receipt")
            key += "/event/" + args.event
        with service.journal.transaction() as cx:
            service._state(cx)
            result = service.journal.document(service.journal.latest(key, cx))
    if action in {"status", "receipt", "execution-receipt"}:
        private_write(args.output, canonical({"action": action, "result": result}))
        return {"output": str(args.output.resolve()), "action": action, "qualified_live_operation": False}
    if signed is None:
        raise ValueError("a separately signed command is required")
    if action == "candidate":
        manifest = CapsuleManifest.model_validate(read_document(args.manifest))
        raw_program = read_document(args.program)
        candidate_digest = service.retain(
            manifest,
            (
                PlacementWorkflow.model_validate(raw_program)
                if manifest.supported_scope == "resilient-placement/v1"
                else SelectionProgram.model_validate(raw_program)
            ),
            signed,
        )
        result = {
            "candidate_digest": candidate_digest,
            "required_origin_input_digests": service.library.snapshot()["protected_network_v1"]["entries"][
                candidate_digest
            ]["origin_input_digests"],
        }
    elif action == "model-run":
        result = FrontierConnector(service.journal, service.trust, service.costs).run(
            DiscoveryRequest.model_validate(read_document(args.request)), signed
        )
    elif action == "mission-run":
        from .computer import ComputerTask
        from .flywheel_execution import (
            ExecutionEnvironment,
            ExecutionMission,
            ExecutionProfile,
            HTTPToolEnvironment,
            LazyDockerEnvironment,
            MissionExecutor,
            ResponsesTransport,
            ToolEndpoint,
        )

        task = ExecutionMission.model_validate(read_document(args.request))
        profile = ExecutionProfile.model_validate(read_document(args.profile))
        environment: ExecutionEnvironment
        browser = None
        if args.tool_endpoint is not None:
            if args.computer_image is not None:
                raise ValueError("computer image is unrelated to this sandbox service contract")
            raw = _private_recovery_bytes(args.tool_endpoint, limit=131_072)
            environment = HTTPToolEnvironment(ToolEndpoint.model_validate(safe_json_loads(raw)))
        else:
            if args.computer_image is None:
                raise ValueError("the existing computer sandbox requires its approved immutable image")
            browser = LazyDockerEnvironment(
                ComputerTask.model_validate(read_document(args.computer_task)), args.computer_image
            )
            environment = browser

        def qualify() -> None:
            if service._execution_binding() != service.execution_digest:
                raise ValueError("installed runtime or custody changed; restart and requalify")

        try:
            result = MissionExecutor(
                service.journal, service.trust, service.costs, ResponsesTransport(service.journal), environment, qualify
            ).run(task, profile, signed)
        finally:
            if browser is not None:
                browser.close()
    elif action == "account":
        result = service.costs.apply(signed)
    elif action == "gym-run":
        from .flywheel_gym import GymCampaign

        result = GymCampaign(
            service.costs, service.checkpoint, service.execution_digest, current_environment=service._execution_binding
        ).run(signed)
    elif action == "general-acceptance":
        result = service.accept_general_origin(signed)
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
    elif action == "archive":
        result = service.archive(signed)
    elif action == "migrate":
        service.migrate(signed)
    else:
        raise ValueError("unsupported protected Flywheel command")
    private_write(args.output, canonical({"action": action, "result": result, "spending_authority_granted": False}))
    return {"output": str(args.output.resolve()), "action": action, "qualified_live_operation": False}
