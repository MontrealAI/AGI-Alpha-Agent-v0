# SPDX-License-Identifier: Apache-2.0
"""Launch the local Sovereign console or run one finite, explicitly reviewed workflow stage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
import uuid

from cryptography.exceptions import InvalidSignature

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from alpha_factory_v1.core.runtime.models import RuntimeConfig
from alpha_factory_v1.core.runtime.store import Journal, canonical, private_write, public_error

from .models import Mandate
from .service import create_app, examples, read_json
from .workbench import Workbench, verify_packet


def main(argv: list[str] | None = None) -> int:
    """Keep execution, approval and export separate; default to the local browser console."""
    parser = argparse.ArgumentParser(description="Sovereign Workbench — bounded work, explicit review, signed evidence")
    parser.add_argument("--home", type=Path, default=Path.home() / ".local/share/agialpha-sovereign")
    parser.add_argument("--port", type=int, default=7865)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("serve")
    commands.add_parser("status")
    commands.add_parser("init")
    samples = commands.add_parser("examples")
    samples.add_argument("--case", choices=list(examples()), default="balanced")
    create = commands.add_parser("create")
    create.add_argument("--case", choices=list(examples()), default="balanced")
    create.add_argument("--file", type=Path)
    create.add_argument("--request-id", default=None)
    for name in ("show", "advance", "recover"):
        commands.add_parser(name).add_argument("id")
    for name in ("pause", "resume"):
        commands.add_parser(name)
    review = commands.add_parser("review")
    review.add_argument("id")
    review.add_argument("--revision", type=int, required=True)
    review.add_argument("--result-hash", required=True)
    decision = review.add_mutually_exclusive_group(required=True)
    decision.add_argument("--approve", action="store_true")
    decision.add_argument("--reject", action="store_true")
    review.add_argument("--note", required=True)
    export = commands.add_parser("export")
    export.add_argument("id")
    export.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("file", type=Path)
    verify.add_argument("--public-key", required=True)
    smoke = commands.add_parser("smoke", help="One offline portfolio computation in a temporary workspace; no approval")
    smoke.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result: Any
        command = args.command or "serve"
        if command == "examples":
            result = examples()[args.case]
        elif command == "verify":
            result = verify_packet(read_json(args.file), args.public_key)
        elif command == "smoke":
            if args.output.exists():
                raise FileExistsError("Choose a new output path")
            with tempfile.TemporaryDirectory(prefix="sovereign-smoke-") as directory:
                bench = Workbench(Journal.initialize(Path(directory) / "workspace"))
                ident = str(uuid.uuid4())
                bench.create(Mandate.model_validate(examples()["balanced"]), ident)
                snapshot = bench.advance(ident)
                if snapshot["state"] != "review" or len(snapshot["jobs"]) != 1:
                    raise ValueError("Smoke workflow did not stop at portfolio review")
                private_write(args.output, canonical(snapshot))
                result = {
                    "state": snapshot["state"],
                    "approved": False,
                    "output": str(args.output),
                    "selected": snapshot["jobs"]["portfolio"]["result"]["selected"],
                }
        else:
            if command == "init":
                journal = Journal.initialize(args.home, RuntimeConfig(name="sovereign-agent"))
            elif command == "serve" and not args.home.exists():
                journal = Journal.initialize(args.home, RuntimeConfig(name="sovereign-agent"))
            else:
                journal = Journal(args.home)
            bench = Workbench(journal)
            if command == "serve":
                import uvicorn

                if not 1024 <= args.port <= 65535:
                    raise ValueError("Choose a port between 1024 and 65535")
                print(f"Sovereign Workbench\nOpen http://127.0.0.1:{args.port}\nWorkspace: {journal.root}", flush=True)
                print("Local access code: " + (journal.root / "api.token").read_text().strip(), flush=True)
                print("Paste this code into your local console. Keep it private. Stop: Ctrl+C.", flush=True)
                uvicorn.run(create_app(journal), host="127.0.0.1", port=args.port, access_log=False)
                return 0
            if command in {"status", "init"}:
                result = {**journal.verify(), "public_key": journal.public, "workflows": bench.list()}
            elif command == "create":
                spec = Mandate.model_validate(read_json(args.file) if args.file else examples()[args.case])
                result = bench.create(spec, args.request_id or str(uuid.uuid4()))
            elif command == "show":
                result = bench.snapshot(args.id)
            elif command == "advance":
                result = bench.advance(args.id)
            elif command == "recover":
                result = bench.recover(args.id)
            elif command == "review":
                result = bench.review(args.id, args.revision, args.result_hash, args.approve, args.note)
            elif command == "export":
                packet = bench.export(args.id)
                verify_packet(packet, journal.public)
                private_write(args.output, canonical(packet))
                result = {"output": str(args.output), "sha256": packet["sha256"], "public_key": journal.public}
            else:
                result = journal.control(command == "pause")
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except InvalidSignature:
        print("Sovereign: Signature verification failed; do not trust this evidence.", file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print(f"Sovereign: {public_error(exc)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
