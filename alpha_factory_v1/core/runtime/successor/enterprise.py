# SPDX-License-Identifier: Apache-2.0
"""Thin enterprise launch facade over the existing fixed-work SUCCESSOR runtime."""

from __future__ import annotations

import argparse
import sqlite3
import uuid
from pathlib import Path
from typing import Any, cast

from ..store import Conflict, Journal, private_write
from . import workbench
from .protocol import canonical, digest, safe_json_loads
from .transport import read_document

SCHEMA = "successor-enterprise/v1"
FAMILIES = ("reliability", "performance", "documentation", "public-data", "numerical")


def _key(enterprise_id: str) -> str:
    """Use canonical identities, never caller-supplied paths."""
    if not isinstance(enterprise_id, str) or str(uuid.UUID(enterprise_id)) != enterprise_id:
        raise ValueError("Enterprise ID must be a canonical UUID")
    return "@successor-enterprise:" + enterprise_id


def validate(config: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete inert configuration before persistence or execution."""
    value = safe_json_loads(canonical(config))
    if not isinstance(value, dict) or set(value) != {"schema", "enterprise_id", "name", "work", "parent"}:
        raise ValueError("Enterprise configuration has unexpected fields")
    if value["schema"] != SCHEMA:
        raise ValueError("Unsupported enterprise schema")
    _key(value["enterprise_id"])
    if not isinstance(value["name"], str) or not value["name"].strip() or len(value["name"]) > 200:
        raise ValueError("Enterprise name must contain 1–200 characters")
    if not isinstance(value["work"], dict):
        raise ValueError("Enterprise work must be an object")
    workbench.invoke({"operation": "plan", "spec": value["work"]})
    parent = value["parent"]
    if parent is not None:
        if not isinstance(parent, dict) or set(parent) != {"enterprise_id", "configuration_digest", "result_digest"}:
            raise ValueError("Invalid parent reference")
        _key(parent["enterprise_id"])
        if parent["enterprise_id"] == value["enterprise_id"]:
            raise ValueError("A successor needs a distinct enterprise ID")
        for name in ("configuration_digest", "result_digest"):
            if (
                not isinstance(parent[name], str)
                or len(parent[name]) != 64
                or any(c not in "0123456789abcdef" for c in parent[name])
            ):
                raise ValueError("Parent digests must be exact SHA-256 identities")
    return value


def new(family: str, name: str) -> dict[str, Any]:
    """Prepare an editable launch template without creating a journal or authority."""
    return validate(
        {
            "schema": SCHEMA,
            "enterprise_id": str(uuid.uuid4()),
            "name": name,
            "work": workbench.invoke({"operation": "example", "family": family}),
            "parent": None,
        }
    )


def _journal(home: Path) -> Journal:
    journal = Journal(home)
    journal.verify()
    return journal


def _record(journal: Journal, enterprise_id: str, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    record = journal.latest(_key(enterprise_id), connection)
    if digest("enterprise-configuration", record["configuration"]) != record["configuration_digest"]:
        raise ValueError("Enterprise configuration identity differs")
    return cast(dict[str, Any], record)


def _check_parent(journal: Journal, config: dict[str, Any], connection: sqlite3.Connection | None = None) -> None:
    parent = config["parent"]
    if parent is None:
        return
    retained = _record(journal, parent["enterprise_id"], connection)
    work = journal.latest(workbench._key(parent["enterprise_id"]), connection)
    if (
        retained["configuration_digest"] != parent["configuration_digest"]
        or work["state"] != "accepted"
        or work["result_digest"] != parent["result_digest"]
    ):
        raise Conflict("Successor requires the exact accepted parent in this journal")


def activate(home: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Register a local launch atomically with its existing workbench run record."""
    config = validate(config)
    if config["parent"] is not None and not home.exists():
        raise Conflict("A derived enterprise requires its retained parent journal")
    journal = _journal(home) if home.exists() else Journal.initialize(home)
    _check_parent(journal, config)
    identity = digest("enterprise-configuration", config)
    key, run_id = _key(config["enterprise_id"]), config["enterprise_id"]
    try:
        existing = _record(journal, run_id)
    except KeyError:
        existing = None
    if existing is not None:
        if existing["configuration_digest"] != identity:
            raise Conflict("Enterprise ID already binds another configuration; derive a new version")
        return show(home, run_id)
    lifecycle = workbench.freeze(journal, config["work"], run_id)
    with journal.transaction() as connection:
        _check_parent(journal, config, connection)
        try:
            existing = journal.latest(key, connection)
        except KeyError:
            existing = None
        if existing is not None:
            if existing["configuration_digest"] != identity:
                raise Conflict("Enterprise changed concurrently")
        else:
            # Do not adopt an unrelated pre-existing work ID, even if its input happens to match.
            try:
                journal.latest(workbench._key(run_id), connection)
            except KeyError:
                pass
            else:
                raise Conflict("This ID already belongs to another work run")
            journal.append(
                connection,
                workbench._key(run_id),
                {
                    "run_id": run_id,
                    "revision": 0,
                    "state": "planned",
                    "request": config["work"],
                    "lifecycle": lifecycle,
                    "request_digest": digest("workbench-request", config["work"]),
                    "result": None,
                    "attempts": 0,
                    "error": None,
                },
            )
            journal.append(connection, key, {"configuration": config, "configuration_digest": identity})
    return show(home, run_id)


def show(home: Path, enterprise_id: str) -> dict[str, Any]:
    """Read the existing authenticated execution state without replaying work."""
    journal = _journal(home)
    enterprise = _record(journal, enterprise_id)
    work = journal.latest(workbench._key(enterprise_id))
    return {
        **Journal.document(enterprise),
        "state": work["state"],
        "run_id": enterprise_id,
        "attempts": work["attempts"],
        "result_digest": work.get("result_digest"),
        "review": work.get("review"),
        "error": work.get("error"),
        "economics": work["result"].get("economics") if work.get("result") else None,
        "authority": [],
        "settlement": "NOT_CONNECTED",
        "independent_qualification": False,
        "scope": "local fixed-work execution; not a commissioned commercial enterprise",
    }


def operate(home: Path, enterprise_id: str, *, resume: bool = False) -> dict[str, Any]:
    """Execute the configured maintained worker; terminal reruns return retained results."""
    journal = _journal(home)
    config = _record(journal, enterprise_id)["configuration"]
    workbench.execute(home, config["work"], enterprise_id, resume=resume)
    return show(home, enterprise_id)


def derive(home: Path, enterprise_id: str, *, name: str, work: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reuse an accepted launch template without copying permission or acceptance."""
    journal = _journal(home)
    parent = _record(journal, enterprise_id)
    retained = journal.latest(workbench._key(enterprise_id))
    if retained["state"] != "accepted":
        raise Conflict("Review and accept the exact parent result before deriving a successor")
    return validate(
        {
            "schema": SCHEMA,
            "enterprise_id": str(uuid.uuid4()),
            "name": name,
            "work": work if work is not None else parent["configuration"]["work"],
            "parent": {
                "enterprise_id": enterprise_id,
                "configuration_digest": parent["configuration_digest"],
                "result_digest": retained["result_digest"],
            },
        }
    )


def adapters(home: Path) -> dict[str, Any]:
    """Expose existing integrations without importing credentials or claiming activation."""
    state: dict[str, Any] = {"configured": False, "profiles": []}
    if home.exists():
        from . import studio_operator

        state = studio_operator.status(_journal(home))
    return {
        "local": {"executor": "successor-work", "state": "AVAILABLE", "families": list(FAMILIES)},
        "studio": state,
        "routes": [
            {"repository": "AGI-Fleet-Linux", "role": "executor/reviewer", "command": "successor-cycle"},
            {"repository": "AGIJobsv0", "currency": "AGIALPHA", "activation": "SEPARATE_AUTHORIZATION"},
            {"repository": "AGIJobManager", "currency": "USDC", "activation": "SEPARATE_AUTHORIZATION"},
        ],
        "authority_created": False,
        "note": "Use installed companion adapters and explicit grants; this catalog is not a live connectivity test.",
    }


def handoff(home: Path, enterprise_id: str, plan: dict[str, Any], index: int) -> dict[str, Any]:
    """Bind a launch to the existing Studio transport, never to a newly invented protocol."""
    from . import studio

    config = _record(_journal(home), enterprise_id)["configuration"]
    return cast(
        dict[str, Any],
        studio.validate_request(
            {
                "schema": studio.REQUEST_SCHEMA,
                "project_id": enterprise_id,
                "cycle_id": enterprise_id,
                "plan": plan,
                "plan_index": index,
                "work_spec": config["work"],
            }
        ),
    )


def add_commands(commands: Any) -> None:
    root = commands.add_parser("successor-harness", help="Activate, operate and derive bounded SUCCESSOR enterprises")
    sub = root.add_subparsers(dest="enterprise_command", required=True)
    create = sub.add_parser("new")
    create.add_argument("family", choices=FAMILIES)
    create.add_argument("--name", required=True)
    create.add_argument("--output", type=Path, required=True)
    activate_command = sub.add_parser("activate")
    activate_command.add_argument("file", type=Path)
    sub.add_parser("adapters")
    for command in ("show", "operate", "control", "review", "export", "derive", "handoff"):
        child = sub.add_parser(command)
        child.add_argument("enterprise_id")
        if command == "operate":
            child.add_argument("--resume", action="store_true")
        elif command == "control":
            child.add_argument("--state", choices=("paused", "stopped", "retired"), required=True)
        elif command == "review":
            child.add_argument("--result-digest", required=True)
            child.add_argument("--decision", choices=("accepted", "rejected"), required=True)
            child.add_argument("--note", required=True)
        elif command in {"export", "derive", "handoff"}:
            child.add_argument("--output", type=Path, required=True)
            if command == "derive":
                child.add_argument("--name", required=True)
                child.add_argument("--work", type=Path)
            if command == "handoff":
                child.add_argument("--plan", type=Path, required=True)
                child.add_argument("--index", type=int, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Keep execution, review and adapter boundaries in their existing owners."""
    command = args.enterprise_command
    if command == "new":
        document = new(args.family, args.name)
    elif command == "activate":
        return activate(args.home, read_document(args.file))
    elif command == "adapters":
        return adapters(args.home)
    elif command == "show":
        return show(args.home, args.enterprise_id)
    elif command == "operate":
        return operate(args.home, args.enterprise_id, resume=args.resume)
    elif command == "derive":
        document = derive(
            args.home, args.enterprise_id, name=args.name, work=read_document(args.work) if args.work else None
        )
    elif command == "handoff":
        document = handoff(args.home, args.enterprise_id, read_document(args.plan), args.index)
    elif command in {"control", "review", "export"}:
        _record(_journal(args.home), args.enterprise_id)
        forwarded = argparse.Namespace(**vars(args), work_command=command, run_id=args.enterprise_id)
        return cast(dict[str, Any], workbench.handle(forwarded))
    else:
        raise ValueError("Unknown enterprise command")
    private_write(args.output, canonical(document))
    return {
        "output": str(args.output.resolve()),
        "enterprise_id": document.get("enterprise_id"),
        "authority_created": False,
    }
