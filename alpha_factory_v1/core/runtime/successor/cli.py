# SPDX-License-Identifier: Apache-2.0
"""Explicit native operator commands for the SUCCESSOR mission lifecycle."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..store import Journal, private_write
from .protocol import RehearsalRequest, canonical, schema_bundle
from .state import SuccessorStore, checked_resources
from .transport import read_document, request_from_file, verify_result
from .trust import (
    JournalCheckpoint,
    TrustRegistry,
    local_principals,
    retained_local_principals,
    validate_external_trust_bytes,
)


def add_commands(commands: Any) -> None:
    """Add compatible commands without changing legacy mission arguments."""
    demo = commands.add_parser("successor-demo", help="Run a complete offline two-generation SUCCESSOR rehearsal")
    demo.add_argument(
        "--output", type=Path, required=True, help="New evidence directory; existing work is never overwritten"
    )
    demo.add_argument("--language", choices=["en", "fr"], default="en")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--max-candidates", type=int, default=4)
    demo.add_argument("--formation-trials", type=int, default=2)
    demo.add_argument("--max-events", type=int, default=1000)
    run = commands.add_parser(
        "successor-run", help="Validate and execute a browser request with a signed native return"
    )
    run.add_argument("file", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--resume", action="store_true", help="Resume explicitly after an interrupted bounded rehearsal")
    verify = commands.add_parser(
        "successor-verify", help="Verify exact request binding and an optional independently trusted signer"
    )
    verify.add_argument("file", type=Path)
    verify.add_argument("--request", type=Path, required=True)
    verify.add_argument("--public-key", help="Independently retained raw Ed25519 public key, hex")
    show = commands.add_parser("successor-show", help="Inspect an authenticated retained rehearsal")
    show.add_argument("request_id")
    export = commands.add_parser("successor-export", help="Export a completed retained rehearsal without remeasuring")
    export.add_argument("request_id")
    export.add_argument("--output", type=Path, required=True)
    schemas = commands.add_parser("successor-schemas", help="Write machine-readable version-one protocol schemas")
    schemas.add_argument("--output", type=Path, required=True)
    checkpoint = commands.add_parser(
        "successor-checkpoint", help="Export the verified current journal head for independent retention"
    )
    checkpoint.add_argument("--output", type=Path, required=True)
    portable = commands.add_parser(
        "successor-portable", help="Export an atomic institutional knowledge snapshot with a separate checkpoint"
    )
    portable.add_argument("institution_id")
    portable.add_argument("--output", type=Path, required=True)
    portable.add_argument("--checkpoint-output", type=Path, required=True)
    restore = commands.add_parser(
        "successor-restore",
        help="Restore authenticated institutional knowledge into a NEW --home with no active permission",
    )
    restore.add_argument("file", type=Path, help="Signed portable institutional snapshot")
    restore.add_argument(
        "--source-public-key", required=True, help="Raw Ed25519 source key retained independently, hex"
    )
    restore.add_argument(
        "--checkpoint", type=Path, required=True, help="Independently retained exact source snapshot checkpoint"
    )
    restore.add_argument(
        "--budget",
        action="append",
        default=[],
        metavar="UNIT=COUNT",
        help="Explicit new bounded resource allowance; defaults to no allocation",
    )
    restore.add_argument(
        "--trust",
        type=Path,
        help="Separately configured destination public trust registry; default creates fresh local rehearsal role keys",
    )
    help_command = commands.add_parser("successor-help", help="English or French first-run and trust-boundary guidance")
    help_command.add_argument("--language", choices=["en", "fr"], default="en")


def help_text(language: str) -> dict[str, Any]:
    """Keep the primary journey available in both languages with stable commands."""
    if language == "fr":
        return {
            "titre": "SUCCESSOR Ω — première mission locale",
            "commande": "alpha-agent --home nouvel-agent successor-demo --output nouvelles-preuves --language fr",
            "parcours": [
                "Choisir la mission",
                "Comparer les solutions",
                "Autoriser l'étude",
                "Construire",
                "Figer",
                "Évaluer",
                "Décider",
                "Conserver et renouveler",
            ],
            "portee": (
                "Calcul réel sur des données synthétiques publiques. Aucun portefeuille, modèle ou compte"
                " payant requis."
            ),
            "qualification": "Une preuve locale ne confère ni qualification indépendante ni autorité de production.",
            "retour_navigateur": "alpha-agent --home nouvel-agent successor-run requete.json --output retour.json",
            "verification": (
                "alpha-agent successor-verify retour.json --request requete.json --public-key "
                "CLE_CONSERVEE_SEPAREMENT"
            ),
            "arret": "Ctrl+C conserve l'état interrompu. Utiliser --resume explicitement avec la même requête.",
            "instantane": (
                "alpha-agent --home agent-source successor-portable ID_INSTITUTION --output "
                "connaissance.json --checkpoint-output ancrage-separe.json"
            ),
            "restauration": (
                "alpha-agent --home nouvel-agent successor-restore connaissance.json --source-public-key "
                "CLE_CONSERVEE_SEPAREMENT --checkpoint ancrage-separe.json"
            ),
            "ancrage": (
                "Conserver la clé et l'ancrage séparément du paquet. L'historique est préservé; les "
                "preuves actives, admissions et autorisations sont vides."
            ),
        }
    return {
        "title": "SUCCESSOR Ω — first local mission",
        "command": "alpha-agent --home new-agent successor-demo --output new-evidence",
        "journey": [
            "Choose mission",
            "Compare alternatives",
            "Underwrite evidence",
            "Construct",
            "Freeze",
            "Evaluate",
            "Decide",
            "Preserve and renew",
        ],
        "scope": "Actual computation on public synthetic inputs. No wallet, downloaded model or paid account required.",
        "qualification": "Local evidence confers neither independent qualification nor production authority.",
        "browser_return": "alpha-agent --home new-agent successor-run request.json --output return.json",
        "verification": (
            "alpha-agent successor-verify return.json --request request.json --public-key " "SEPARATELY_RETAINED_KEY"
        ),
        "stop": "Ctrl+C retains interrupted state. Explicitly use --resume with the same request to continue.",
        "snapshot": (
            "alpha-agent --home source-agent successor-portable INSTITUTION_ID --output "
            "knowledge.json --checkpoint-output separate-checkpoint.json"
        ),
        "restoration": (
            "alpha-agent --home new-agent successor-restore knowledge.json --source-public-key "
            "SEPARATELY_RETAINED_KEY --checkpoint separate-checkpoint.json"
        ),
        "anchor": (
            "Retain the source key and checkpoint independently of the package. Historical records "
            "survive; active proof, admission and authority start empty."
        ),
    }


def _checkpoint_document(checkpoint: JournalCheckpoint) -> dict[str, Any]:
    return {"identity": checkpoint.identity, "sequence": checkpoint.sequence, "head": checkpoint.head}


def _checkpoint_from_file(path: Path) -> JournalCheckpoint:
    value = read_document(path)
    if not isinstance(value, dict) or set(value) != {"identity", "sequence", "head"}:
        raise ValueError("checkpoint file must contain exactly identity, sequence and head")
    return JournalCheckpoint(value["identity"], value["sequence"], value["head"])


def _budgets(entries: list[str]) -> dict[str, int]:
    budgets = {}
    for entry in entries:
        unit, separator, raw = entry.partition("=")
        if not separator or not raw.isascii() or not raw.isdigit() or len(raw) > 16 or unit in budgets:
            raise ValueError("each budget must be a unique UNIT=COUNT with a nonnegative safe integer")
        budgets[unit] = int(raw)
    checked_resources(budgets)
    canonical(budgets)
    return budgets


def _external_trust(path: Path) -> TrustRegistry:
    return validate_external_trust_bytes(canonical(read_document(path)))


def _restore(args: argparse.Namespace) -> dict[str, Any]:
    package = read_document(args.file)
    checkpoint = _checkpoint_from_file(args.checkpoint)
    budgets = _budgets(args.budget)
    if args.home.exists() or args.home.is_symlink():
        raise FileExistsError("institution restore requires a NEW --home; existing state is never replaced")
    registry = _external_trust(args.trust) if args.trust else local_principals()[0]
    with TemporaryDirectory(prefix="successor-restore-preflight-") as temporary:
        rehearsal = SuccessorStore(Journal.initialize(Path(temporary) / "validation"), registry)
        rehearsal.restore_portable(package, budgets, source_public_key=args.source_public_key, checkpoint=checkpoint)
    journal = Journal.initialize(args.home)
    if args.trust is None:
        registry, _ = retained_local_principals(journal.root / "successor-principals")
    else:
        private_write(journal.root / "successor-trust.json", canonical(read_document(args.trust)))
    restored = SuccessorStore(journal, registry).restore_portable(
        package, budgets, source_public_key=args.source_public_key, checkpoint=checkpoint
    )
    return {
        "home": str(journal.root),
        "institution_id": restored["institution"]["id"],
        "status": "restored-stopped",
        "active_proofs": [],
        "active_grants": [],
        "serving_release": None,
        "resource_allowance": budgets,
        "source_identity": checkpoint.identity,
        "source_checkpoint": _checkpoint_document(checkpoint),
        "scope": "authenticated knowledge and historical records only; re-examine, admit and grant before operation",
    }


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Validate external inputs before creating any mission state."""
    from .orchestration import rehearse, retained_result, show_run, write_demo

    if args.command == "successor-restore":
        return _restore(args)
    if args.command == "successor-help":
        return help_text(args.language)
    if args.command == "successor-schemas":
        private_write(args.output, canonical(schema_bundle()))
        return {"output": str(args.output.resolve()), "schema_version": 1}
    if args.command == "successor-verify":
        return verify_result(read_document(args.file), request_from_file(args.request), args.public_key)
    if args.command == "successor-demo":
        request = RehearsalRequest(
            request_id=str(uuid.uuid4()),
            seed=args.seed,
            max_candidates=args.max_candidates,
            formation_trials=args.formation_trials,
            max_events=args.max_events,
            language=args.language,
        )
        return write_demo(args.home, request, args.output)
    if args.command == "successor-run":
        request = request_from_file(args.file)
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError("evidence output already exists; choose a new file")
        result = rehearse(args.home, request, resume=args.resume)
        private_write(args.output, canonical(result))
        return {
            "output": str(args.output.resolve()),
            **verify_result(result, request, result["signature"]["public_key"]),
        }
    journal = Journal(args.home)
    journal.verify()
    if args.command == "successor-checkpoint":
        checkpoint = JournalCheckpoint.capture(journal)
        private_write(args.output, canonical(_checkpoint_document(checkpoint)))
        return {
            "output": str(args.output.resolve()),
            "source_public_key": journal.public,
            "checkpoint": _checkpoint_document(checkpoint),
            "instruction": "Retain this checkpoint independently of portable packages.",
        }
    if args.command == "successor-portable":
        if args.output.resolve() == args.checkpoint_output.resolve():
            raise ValueError("portable data and independently retained checkpoint require distinct files")
        for output in (args.output, args.checkpoint_output):
            if output.exists() or output.is_symlink():
                raise FileExistsError("snapshot output already exists; choose new paths")
        package = SuccessorStore(journal, TrustRegistry({})).export_portable(args.institution_id)
        private_write(args.output, canonical(package))
        private_write(args.checkpoint_output, canonical(package["payload"]["checkpoint"]))
        return {
            "output": str(args.output.resolve()),
            "checkpoint_output": str(args.checkpoint_output.resolve()),
            "source_public_key": journal.public,
            "active_permission_exported": False,
            "instruction": "Retain the source key and checkpoint independently of this package.",
        }
    if args.command == "successor-show":
        return show_run(journal, args.request_id)
    result = retained_result(journal, args.request_id)
    private_write(args.output, canonical(result))
    return {"output": str(args.output.resolve()), "remeasured": False, "scope": result["scope"]}
