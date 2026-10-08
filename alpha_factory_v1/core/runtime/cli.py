# SPDX-License-Identifier: Apache-2.0
"""Operator CLI for the complete, persistent mission lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from alpha_factory_v1 import __version__
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

from .engine import Engine, verify_export
from .models import Mission, RuntimeConfig
from .store import Journal, canonical, private_write, public_error


def parser() -> argparse.ArgumentParser:
    """Build the explicit operator command surface."""
    root = argparse.ArgumentParser(description="$AGIALPHA Agent — evidence, optimization and reviewed work")
    root.add_argument("--home", type=Path, default=Path.home() / ".local/share/agialpha-agent")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    from .successor.cli import add_commands

    add_commands(commands)
    samples = commands.add_parser("examples", help="List or copy the five editable, packaged mission examples")
    samples.add_argument("--output", type=Path, help="Create a NEW directory; existing files are never overwritten")
    for name in ("ascension-compile", "ascension-check"):
        command = commands.add_parser(name, help="Compile or verify exact on-chain FusionPlan commitments offline")
        command.add_argument("file", type=Path)
        if name == "ascension-compile":
            command.add_argument("--output", type=Path, required=True)
    handoff = commands.add_parser("ascension-deliver", help="Bind an approved native mission to a FusionPlan job")
    handoff.add_argument("file", type=Path, help="Verified compiled FusionPlan")
    handoff.add_argument("--index", type=int, required=True)
    handoff.add_argument("--mission", required=True)
    handoff.add_argument("--output", type=Path, required=True)
    inspect = commands.add_parser(
        "ascension-verify-delivery", help="Verify exact delivery bytes against a trusted key/root"
    )
    inspect.add_argument("file", type=Path)
    inspect.add_argument("--public-key", required=True)
    inspect.add_argument("--plan-root", required=True)
    inspect.add_argument("--replay-code", action="store_true", help="Permit code benchmark replay in isolated Docker")
    initialize = commands.add_parser("init", help="Create a new private identity and journal")
    initialize.add_argument("--config", type=Path)
    run = commands.add_parser("run", help="Execute a mission file and stop at review")
    run.add_argument("file", type=Path)
    run.add_argument("--request-id", help="UUID for idempotent submission")
    for name in ("show", "execute", "recover"):
        commands.add_parser(name).add_argument("id")
    for name in ("list", "verify", "doctor", "pause", "resume"):
        commands.add_parser(name)
    review = commands.add_parser("review", help="Review the exact result and revision")
    review.add_argument("id")
    review.add_argument("--revision", type=int, required=True)
    review.add_argument("--result-hash", required=True)
    decision = review.add_mutually_exclusive_group(required=True)
    decision.add_argument("--approve", action="store_true")
    decision.add_argument("--reject", action="store_true")
    review.add_argument("--note", required=True)
    export = commands.add_parser("export", help="Export approved work with a verifiable receipt")
    export.add_argument("id")
    export.add_argument("--output", type=Path, required=True)
    proof = commands.add_parser("verify-export", help="Verify a public receipt against an independently trusted key")
    proof.add_argument("file", type=Path)
    proof.add_argument("--public-key", required=True)
    commands.add_parser("backup", help="Create a private recovery ZIP, including the identity key").add_argument(
        "file", type=Path
    )
    commands.add_parser("restore", help="Restore a backup to a NEW --home directory").add_argument("file", type=Path)
    commands.add_parser("configure", help="Apply configuration while paused").add_argument("file", type=Path)
    serve = commands.add_parser("serve", help="Open the local, authenticated operator console")
    serve.add_argument("--port", type=int, default=8765)
    for name in ("wallet-challenge", "balance"):
        commands.add_parser(name)
    commands.add_parser("wallet-bind").add_argument("signature")
    invoice = commands.add_parser("invoice", help="Record AGIALPHA payment terms for approved work")
    invoice.add_argument("id")
    invoice.add_argument("--payer", required=True)
    invoice.add_argument("--amount-units", required=True)
    settle = commands.add_parser("settle", help="Verify and record one confirmed AGIALPHA Transfer")
    settle.add_argument("id")
    settle.add_argument("--transaction", required=True)
    settle.add_argument("--log-index", type=int, required=True)
    transfer = commands.add_parser("transfer-run", help="Freeze a policy and measure held-out future tasks")
    transfer.add_argument("--scenario", choices=["seasonal", "shift", "ablation"], default="seasonal")
    transfer.add_argument("--seed", type=int, default=37)
    transfer.add_argument("--spec", type=Path)
    transfer.add_argument("--output", type=Path, required=True)
    for name in ("transfer-verify", "transfer-review", "transfer-docket"):
        command = commands.add_parser(name, help="Replay, review or export a manuscript Evidence Docket")
        command.add_argument("file", type=Path)
        if name != "transfer-verify":
            command.add_argument("--output", type=Path, required=True)
        if name == "transfer-review":
            command.add_argument("--decision", choices=["accept", "reject", "repair"], required=True)
            command.add_argument("--reviewer", required=True)
            command.add_argument("--reason", required=True)
            command.add_argument("--control-ms", type=int, required=True)
            command.add_argument("--treatment-ms", type=int, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    """Execute a command and emit machine-readable output with useful exit codes."""
    args = parser().parse_args(argv)
    try:
        result: Any
        if args.command.startswith("successor-"):
            from .successor.cli import handle

            result = handle(args)
        elif args.command == "examples":
            from .samples import examples

            result = examples(args.output)
        elif args.command.startswith("ascension-"):
            from . import ascension

            limit = (
                ascension.MAX_DELIVERY_BYTES
                if args.command == "ascension-verify-delivery"
                else ascension.MAX_PLAN_BYTES
            )
            with args.file.open("rb") as source:
                data = source.read(limit + 1)
            document = ascension.parse(data, limit)
            if args.command == "ascension-compile":
                compiled = ascension.compile_plan(document)
                private_write(args.output, canonical(compiled))
                result = {"output": str(args.output.resolve()), **ascension.verify_plan(compiled)}
            elif args.command == "ascension-check":
                result = ascension.verify_plan(document)
            elif args.command == "ascension-deliver":
                journal = Journal(args.home)
                delivered = ascension.delivery(journal, document, args.index, args.mission)
                private_write(args.output, delivered)
                result = {
                    "output": str(args.output.resolve()),
                    "planRoot": document["planRoot"],
                    "jobIndex": args.index,
                    "resultHash": "0x" + ascension.keccak(delivered).hex(),
                    "publicKey": journal.public,
                    "onChainSubmitted": False,
                }
            else:
                result = ascension.verify_delivery(
                    data, args.public_key, args.plan_root, allow_code_replay=args.replay_code
                )
        elif args.command.startswith("transfer-"):
            from . import transfer

            if args.command == "transfer-run":
                if args.spec and args.spec.stat().st_size > transfer.MAX_BYTES:
                    raise ValueError("Transfer specification exceeds size limit")
                spec = (
                    transfer.parse(args.spec.read_text()) if args.spec else transfer.example(args.scenario, args.seed)
                )
                report = transfer.run(spec)
                private_write(args.output, transfer.canonical(report).encode())
                result = {"output": str(args.output.resolve()), **transfer.verify(report)}
            else:
                if args.file.stat().st_size > transfer.MAX_BYTES * 3:
                    raise ValueError("Transfer input exceeds size limit")
                if args.command == "transfer-verify" and args.file.suffix.lower() == ".zip":
                    result = transfer.verify_docket(args.file.read_bytes())
                else:
                    report = transfer.parse(args.file.read_text())
                    result = transfer.verify(report)
                    if args.command == "transfer-review":
                        report = transfer.review_run(
                            report, args.decision, args.reviewer, args.reason, args.control_ms, args.treatment_ms
                        )
                        private_write(args.output, transfer.canonical(report).encode())
                        result = {"output": str(args.output.resolve()), **transfer.verify(report)}
                    elif args.command == "transfer-docket":
                        private_write(args.output, transfer.export_docket(report))
                        result = {"output": str(args.output.resolve()), **result}
        elif args.command == "init":
            config = RuntimeConfig.model_validate_json(args.config.read_bytes()) if args.config else RuntimeConfig()
            journal = Journal.initialize(args.home, config)
            result = {**journal.verify(), "home": str(journal.root), "token_file": str(journal.root / "api.token")}
        elif args.command == "restore":
            result = Journal.restore(args.file, args.home).verify()
        elif args.command == "verify-export":
            if args.file.stat().st_size > 2 * 1024**2:
                raise ValueError("export exceeds 2 MiB")
            result = verify_export(json.loads(args.file.read_bytes()), args.public_key)
        else:
            journal = Journal(args.home)
            engine = Engine(journal)
            if args.command in {"wallet-challenge", "wallet-bind", "balance", "invoice", "settle"}:
                from .chain import Economics

                economics = Economics(journal)
                if args.command == "wallet-challenge":
                    result = economics.challenge()
                elif args.command == "wallet-bind":
                    result = economics.bind(args.signature)
                elif args.command == "balance":
                    result = economics.balance()
                elif args.command == "invoice":
                    result = economics.invoice(args.id, args.payer, args.amount_units)
                else:
                    result = economics.settle(args.id, args.transaction, args.log_index)
            elif args.command == "run":
                if args.file.stat().st_size > 512 * 1024:
                    raise ValueError("mission file exceeds 512 KiB")
                mission = Mission.model_validate_json(args.file.read_bytes())
                record = journal.submit(mission, args.request_id)
                result = engine.execute(record["id"]) if record["state"] == "queued" else record
            elif args.command == "show":
                result = journal.latest(args.id)
            elif args.command == "execute":
                result = engine.execute(args.id)
            elif args.command == "recover":
                result = engine.recover(args.id)
            elif args.command == "review":
                result = engine.review(args.id, args.revision, args.result_hash, args.approve, args.note)
            elif args.command == "list":
                result = [
                    {
                        "id": item["id"],
                        "state": item["state"],
                        "goal": item["request"]["goal"],
                        "revision": item["revision"],
                    }
                    for item in journal.missions()
                ]
            elif args.command == "verify":
                result = journal.verify()
            elif args.command == "doctor":
                import shutil

                result = {
                    "version": __version__,
                    **journal.verify(),
                    "control": journal.latest("@control")["state"],
                    "inference": (
                        "configured; validate with a research mission" if journal.config.llm_url else "extractive mode"
                    ),
                    "sandbox": (
                        "Docker binary found; execution checks daemon availability and isolation"
                        if shutil.which("docker")
                        else "unavailable; generated code blocked"
                    ),
                    "capabilities": ["research", "allocation", "schedule", "forecast", "code"],
                    "code_execution_enabled": journal.config.allow_code_execution,
                    "chain": "configured; verify with balance" if journal.config.chain else "unconfigured",
                    "general_intelligence": "not claimed",
                }
            elif args.command in {"pause", "resume"}:
                result = journal.control(args.command == "pause")
            elif args.command == "export":
                private_write(args.output, canonical(engine.export(args.id)))
                result = {"output": str(args.output.resolve())}
            elif args.command == "backup":
                result = journal.backup(args.file)
            elif args.command == "configure":
                journal.configure(RuntimeConfig.model_validate_json(args.file.read_bytes()))
                result = journal.verify()
            elif args.command == "serve":
                import uvicorn
                from .api import create_app

                print(
                    f"Operator console: http://127.0.0.1:{args.port}\n"
                    f"Read the access token from {journal.root / 'api.token'}",
                    file=sys.stderr,
                )
                uvicorn.run(create_app(journal), host="127.0.0.1", port=args.port, access_log=False)
                return 0
            else:  # pragma: no cover - argparse enumerates the commands
                raise ValueError("unknown command")
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        # Validation errors can contain supplied source text; don't emit them to
        # shared logs. Operators can inspect the retained mission and stage.
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": public_error(exc),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
