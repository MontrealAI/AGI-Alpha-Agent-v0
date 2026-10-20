# SPDX-License-Identifier: Apache-2.0
"""Run packaged fixed work adapters through the existing signed operator journal."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from ..store import Conflict, Journal, private_write, private_write_batch
from .protocol import (
    BehaviorArtifact,
    CandidateReleaseManifest,
    Institution,
    MissionConstitution,
    ResourceBudget,
    canonical,
    digest,
    safe_json_loads,
)
from .state import SuccessorStore
from .transport import read_document
from .trust import SignedEnvelope, TrustAnchor, TrustRegistry, retained_local_principals, sign_record

WORKER = Path(__file__).with_name("workbench_worker.mjs")


def freeze(journal: Journal, spec: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Register this work method in the existing lifecycle without granting proof or operation."""
    trust, _ = retained_local_principals(journal.root / "workbench-principals")
    store = SuccessorStore(journal, trust)
    institution_id = "work-" + run_id
    spec_digest = digest("workbench-request", spec)
    source = json.loads(WORKER.with_name("workbench_sources.json").read_text())
    budget = ResourceBudget(
        limits={"attempts": 3, "milliseconds": 60000},
        units={"attempts": "pure work attempts", "milliseconds": "wall time per attempt"},
        enforceable=["attempts", "milliseconds"],
        unknown_costs=["compute", "human-review"],
    )
    constitution = MissionConstitution(
        mission_id="mission-" + spec_digest,
        owner="local-controller",
        objective="Produce and inspect bounded " + spec["family"] + " work",
        scope="public local work; no independent qualification or live settlement",
        mission_distribution="Exact user-supplied inputs committed by " + spec_digest,
        evidence_rights=[spec["rights"]["dataClass"], spec["rights"]["source"], spec["rights"]["license"]],
        constraints=["Declared owner: " + spec["owner"], "Frozen maintained adapter; no arbitrary supplied code"],
        prohibited_actions=["live-settlement", "network", "host-code", "automatic-admission"],
        budget=budget,
        reviewer_budget_minutes=spec["reviewMinutes"],
        authority_ceiling="none",
        stop_conditions=["Cancellation, budget exhaustion, invalid inputs, corrupted persistence"],
    )
    institution = Institution(id=institution_id, constitution=constitution, controller="local-controller")
    try:
        existing = store.read(institution_id)
        if existing["institution"] != institution.model_dump(mode="json"):
            raise Conflict("Existing work institution binds a different request")
    except KeyError:
        store.create_institution(institution, {"attempts": 3})
    manifest = CandidateReleaseManifest(
        release_id="work-method-v1",
        institution_id=institution_id,
        mission_id=constitution.mission_id,
        producer="local-producer",
        budget=budget,
        environment_digest=digest(
            "workbench-environment",
            {
                "runtime": subprocess.run(
                    [shutil.which("node") or "node", "--version"], capture_output=True, text=True, timeout=5, check=True
                ).stdout.strip(),
                "platform": platform.system(),
                "architecture": platform.machine(),
                "family": spec["family"],
            },
        ),
        artifacts=[
            BehaviorArtifact(name="input", role="other", digest=spec_digest),
            BehaviorArtifact(name="adapter-sources", role="source", digest=source["sourceHash"]),
        ],
        configuration={"family": spec["family"], "independent": False, "network": False},
    )
    state = store.register_release(institution_id, manifest, request_id="freeze-" + run_id)
    return {
        "institution": institution.model_dump(mode="json"),
        "candidate": manifest.model_dump(mode="json"),
        "release_digest": state["nominated_release"],
        "active_proof": [],
        "active_authority": [],
    }


def write_receipt(
    journal: Journal, record: dict[str, Any], destination: Path, domain: str, *, include_record: bool = False
) -> None:
    """Attribute a local observation; the recipient must supply its trusted source key separately."""
    envelope = sign_record(journal.key, journal.identity, domain, Journal.document(record))
    files = [
        (destination / "signed-receipt.json", canonical(envelope.model_dump(mode="json"))),
        (destination / "source-key.txt", (journal.public + "\n").encode()),
    ]
    if include_record:
        files.insert(0, (destination / "receipt.json", canonical(record)))
    private_write_batch(files)


def invoke(request: dict[str, Any], checkpoint: Callable[[], None] = lambda: None) -> dict[str, Any]:
    """Execute shipped fixed code only; imports never select an executable or command."""
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js 22 or later is required for the optional workbench; legacy commands are unchanged")
    # Scrub the version probe as well as the worker: no inherited preload or credential paths.
    import os

    environment = {key: value for key, value in os.environ.items() if key in {"PATH", "SYSTEMROOT", "WINDIR", "TMPDIR"}}
    version = subprocess.run(
        [node, "--version"], capture_output=True, text=True, timeout=5, check=True, env=environment
    ).stdout
    if int(version.lstrip("v").split(".")[0]) < 22:
        raise ValueError("Node.js 22 or later is required")
    payload = canonical(request)
    if len(payload) > 2_000_000:
        raise ValueError("Work adapter input exceeds its limit")
    # A private, seekable stdin avoids partially-written pipes when communicate times out.
    # Polling still drains stdout/stderr and checks cancellation without replaying any input.
    with tempfile.TemporaryFile() as input_file:
        input_file.write(payload)
        input_file.seek(0)
        process = subprocess.Popen(
            [node, str(WORKER)], stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment
        )
        started = time.monotonic()
        try:
            while True:
                checkpoint()
                if time.monotonic() - started > 65:
                    raise TimeoutError("Work adapter exceeded its wall-clock limit")
                try:
                    output, errors = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode:
                # Worker traces may contain input bytes. Expose only a bounded first error classification.
                message = next((line for line in errors.decode(errors="replace").splitlines() if "Error:" in line), "")
                raise ValueError("Work adapter rejected the request: " + message[:200])
            if len(output) > 2_000_000:
                raise ValueError("Work adapter output exceeds its limit")
            result = safe_json_loads(output)
            if not isinstance(result, dict):
                raise ValueError("Work adapter returned an invalid document")
            checkpoint()
            return result
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()


def _key(run_id: str) -> str:
    if str(uuid.UUID(run_id)) != run_id:
        raise ValueError("Run ID must be a canonical UUID")
    return "@successor-work:" + run_id


def _change(journal: Journal, key: str, revision: int, **values: Any) -> dict[str, Any]:
    with journal.transaction() as connection:
        before = journal.latest(key, connection)
        if before["revision"] != revision:
            raise Conflict("Work changed concurrently; inspect its current state")
        after = {**Journal.document(before), **values}
        return journal.append(connection, key, after)


def execute(home: Path, spec: dict[str, Any], run_id: str, *, resume: bool = False) -> dict[str, Any]:
    """Checkpoint bounded pure work; interruption never silently replays an external effect."""
    key = _key(run_id)
    # Validate and compile before creating a new operator identity or durable run.
    invoke({"operation": "plan", "spec": spec})
    journal = Journal(home) if home.exists() else Journal.initialize(home)
    journal.verify()
    lifecycle = freeze(journal, spec, run_id)
    identity = digest("workbench-request", spec)
    with journal.transaction() as connection:
        try:
            record = journal.latest(key, connection)
        except KeyError:
            record = {
                "run_id": run_id,
                "revision": 0,
                "state": "planned",
                "request": spec,
                "lifecycle": lifecycle,
                "request_digest": identity,
                "result": None,
                "attempts": 0,
                "error": None,
            }
            record = journal.append(connection, key, record)
        if record["request_digest"] != identity:
            raise Conflict("Run ID already belongs to a different request")
    if record["state"] in {"review", "accepted", "rejected"}:
        return record
    if record["state"] != "planned" and not resume:
        raise Conflict("Interrupted work requires explicit --resume; inspect the retained record first")
    if record["state"] in {"stopped", "retired"}:
        raise Conflict("Stopped or retired work cannot resume; create a new run")
    if record["state"] == "running" and record.get("lease_until", 0) > int(time.time()):
        raise Conflict("A current execution lease remains active; pause or wait for recovery")
    if record["attempts"] >= 3:
        raise Conflict("The three-attempt budget is exhausted")
    record = _change(
        journal,
        key,
        record["revision"],
        state="running",
        attempts=record["attempts"] + 1,
        lease_until=int(time.time()) + 70,
        error=None,
    )

    def checkpoint() -> None:
        if journal.latest("@control")["state"] != "ready":
            raise Conflict("Operator paused execution")
        latest = journal.latest(key)
        if latest["revision"] != record["revision"] or latest["state"] != "running":
            raise Conflict("Work was paused, stopped, or changed")

    try:
        pack = invoke({"operation": "run", "spec": spec}, checkpoint)
        return _change(
            journal,
            key,
            record["revision"],
            state="review",
            result=pack,
            result_digest=digest("workbench-result", pack),
            authority=[],
            settlement="NOT_CONNECTED",
        )
    except BaseException as error:
        latest = journal.latest(key)
        if latest["state"] == "running" and latest["revision"] == record["revision"]:
            _change(journal, key, record["revision"], state="interrupted", error=type(error).__name__)
        raise


def write_artifacts(pack: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Export bounded inert records and inspectable source into a new directory only."""
    invoke({"operation": "inspect", "pack": pack})
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Choose a new output directory; existing files are preserved")
    destination.mkdir(parents=True, mode=0o700)
    private_write(destination / "mission.json", canonical(pack["spec"]))
    private_write(destination / "evidence.json", canonical(pack))
    for artifact in pack["result"]["artifacts"]:
        private_write(destination / artifact["name"], artifact["content"].encode())
    private_write(
        destination / "READ_ME.txt",
        (
            "SUCCESSOR Ω local work artifacts\n\nReview the files before use. "
            "No live permission or settlement is included.\n"
            "Reproduce: alpha-agent successor-work run mission.json --output NEW_DIRECTORY\n"
            "mission.json binds the original inputs; evidence.json retains all local results and limitations.\n"
        ).encode(),
    )
    return {
        "output": str(destination.resolve()),
        "files": len(pack["result"]["artifacts"]) + 3,
        "scope": "local-public-work",
        "authority": [],
        "settlement": "NOT_CONNECTED",
    }


def add_commands(commands: Any) -> None:
    """Register one additive command group with machine-readable results."""
    root = commands.add_parser("successor-work", help="Create, run, inspect and retain useful bounded work")
    sub = root.add_subparsers(dest="work_command", required=True)
    sub.add_parser("registry")
    verify = sub.add_parser("verify-receipt")
    verify.add_argument("file", type=Path)
    verify.add_argument("--source-key", required=True)
    example = sub.add_parser("example")
    example.add_argument("family", choices=["reliability", "performance", "documentation", "public-data", "numerical"])
    example.add_argument("--output", type=Path, required=True)
    for name in ("plan", "run", "restore"):
        command = sub.add_parser(name)
        command.add_argument("file", type=Path)
        if name != "plan":
            command.add_argument("--output", type=Path, required=True)
        if name == "run":
            command.add_argument("--run-id", default=None)
            command.add_argument("--resume", action="store_true")
    for name in ("show", "control", "review", "export"):
        command = sub.add_parser(name)
        command.add_argument("run_id")
        if name == "control":
            command.add_argument("--state", choices=["paused", "stopped", "retired"], required=True)
        if name == "review":
            command.add_argument("--result-digest", required=True)
            command.add_argument("--decision", choices=["accepted", "rejected"], required=True)
            command.add_argument("--note", required=True)
        if name == "export":
            command.add_argument("--output", type=Path, required=True)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Dispatch work commands without changing existing journal or export formats."""
    command = args.work_command
    if command == "registry":
        return invoke({"operation": "registry"})
    if command == "verify-receipt":
        envelope = SignedEnvelope.model_validate(read_document(args.file))
        if envelope.domain not in {"workbench-receipt", "computer-receipt"}:
            raise ValueError("Unsupported local receipt domain")
        trust = TrustRegistry({envelope.principal: TrustAnchor(args.source_key, frozenset({"local-source"}))})
        payload = trust.verify(envelope, envelope.domain, "local-source")
        return {
            "authenticated_local_source": envelope.principal,
            "state": payload["state"],
            "independentProof": False,
            "authority": [],
            "freshness": "historical; independently retain journal checkpoint",
        }
    if command == "example":
        spec = invoke({"operation": "example", "family": args.family})
        private_write(args.output, canonical(spec))
        return {"output": str(args.output.resolve())}
    if command == "plan":
        return invoke({"operation": "plan", "spec": read_document(args.file)})
    if command == "restore":
        restored = invoke({"operation": "inspect", "pack": read_document(args.file)})
        private_write(args.output, canonical(restored["spec"]))
        return {
            "output": str(args.output.resolve()),
            "activeAuthority": [],
            "activeProof": [],
            "historical": restored["history"],
            "authentication": restored["authentication"],
        }
    if command == "run":
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError("Choose a new output directory")
        run_id = args.run_id or str(uuid.uuid4())
        result = execute(args.home, read_document(args.file), run_id, resume=args.resume)
        exported = write_artifacts(result["result"], args.output)
        write_receipt(Journal(args.home), result, args.output, "workbench-receipt")
        private_write(args.output / "lifecycle.json", canonical(result["lifecycle"]))
        return {
            **exported,
            "files": exported["files"] + 3,
            "run_id": run_id,
            "state": result["state"],
            "result_digest": result["result_digest"],
        }
    journal = Journal(args.home)
    journal.verify()
    key = _key(args.run_id)
    record = journal.latest(key)
    if command == "show":
        return record
    if command == "control":
        if record["state"] == "retired":
            raise Conflict("Retired work is terminal")
        if record["state"] == "stopped" and args.state == "paused":
            raise Conflict("Stopped work cannot be paused or resumed; create a new run")
        return _change(journal, key, record["revision"], state=args.state)
    if command == "review":
        if record["state"] != "review" or record["result_digest"] != args.result_digest:
            raise Conflict("Review must bind the current result awaiting review")
        if not args.note.strip() or len(args.note) > 2000:
            raise ValueError("A bounded review note is required")
        return _change(
            journal,
            key,
            record["revision"],
            state=args.decision,
            review={"note": args.note, "operator": journal.identity, "independent": False},
            authority=[],
        )
    if command == "export":
        if record.get("result") is None:
            raise Conflict("There is no completed result to export")
        exported = write_artifacts(record["result"], args.output)
        write_receipt(journal, record, args.output, "workbench-receipt")
        private_write(args.output / "lifecycle.json", canonical(record["lifecycle"]))
        return {**exported, "files": exported["files"] + 3}
    raise ValueError("Unknown work command")
