# SPDX-License-Identifier: Apache-2.0
"""Run packaged fixed work adapters through the existing signed operator journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
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


def _environment() -> dict[str, str]:
    """Pass only execution paths, never inherited Node preloads or credential settings."""
    return {key: value for key, value in os.environ.items() if key in {"PATH", "SYSTEMROOT", "WINDIR", "TMPDIR"}}


def _worker_source() -> dict[str, Any]:
    """Bind the installed module manifest to the exact generated executable bytes."""
    source = json.loads(WORKER.with_name("workbench_sources.json").read_text(encoding="utf-8"))
    if not isinstance(source, dict) or any(
        not isinstance(source.get(field), str) or re.fullmatch(r"[0-9a-f]{64}", source[field]) is None
        for field in ("sourceHash", "workerSHA256")
    ):
        raise ValueError("Work adapter lacks a complete executable identity; restore matching software")
    if source["workerSHA256"] != hashlib.sha256(WORKER.read_bytes()).hexdigest():
        raise ValueError("Work adapter executable differs from its source manifest")
    return source


def freeze(journal: Journal, spec: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Register this work method in the existing lifecycle without granting proof or operation."""
    trust, _ = retained_local_principals(journal.root / "workbench-principals")
    store = SuccessorStore(journal, trust)
    institution_id = "work-" + run_id
    spec_digest = digest("workbench-request", spec)
    source = _worker_source()
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
                    [shutil.which("node") or "node", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                    env=_environment(),
                ).stdout.strip(),
                "platform": platform.system(),
                "architecture": platform.machine(),
                "family": spec["family"],
            },
        ),
        artifacts=[
            BehaviorArtifact(name="input", role="other", digest=spec_digest),
            BehaviorArtifact(name="adapter-sources", role="source", digest=source["sourceHash"]),
            BehaviorArtifact(name="adapter-worker", role="source", digest=source["workerSHA256"]),
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
    environment = _environment()
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
    identity = digest("workbench-request", spec)
    journal: Journal | None = None
    retained: dict[str, Any] | None = None
    if home.exists():
        journal = Journal(home)
        journal.verify()
        with journal.transaction() as connection:
            try:
                retained = journal.latest(key, connection)
            except KeyError:
                pass
            if retained is not None:
                if retained["request_digest"] != identity:
                    raise Conflict("Run ID already belongs to a different request")
                if retained["state"] in {"review", "accepted", "rejected"}:
                    # Return verified history even if the current worker removed its family or schema.
                    # This grants no new review, qualification, authority, or execution.
                    return retained
    source = _worker_source()
    if retained is not None:
        frozen_sources = [
            artifact["digest"]
            for artifact in retained["lifecycle"]["candidate"]["artifacts"]
            if artifact["name"] == "adapter-sources"
        ]
        frozen_workers = [
            artifact["digest"]
            for artifact in retained["lifecycle"]["candidate"]["artifacts"]
            if artifact["name"] == "adapter-worker"
        ]
        if frozen_sources != [source["sourceHash"]] or frozen_workers != [source["workerSHA256"]]:
            raise Conflict(
                "Work adapter source changed; unfinished work cannot resume. "
                "Restore the previous software or create a new run; retained history is unchanged. "
                "Legacy unfinished records without a complete worker identity cannot be requalified by inference"
            )
    # Validate new/unfinished work before creating an identity, freezing source or consuming an attempt.
    invoke({"operation": "plan", "spec": spec})
    if journal is None:
        journal = Journal.initialize(home)
        journal.verify()
    lifecycle = freeze(journal, spec, run_id)
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


def _artifact_files(pack: dict[str, Any]) -> list[tuple[str, bytes]]:
    """Check the retained v1 storage envelope without reinterpreting its adapter inputs."""
    canonical(pack)  # Bound the entire document before preparing any filesystem side effect.
    if pack.get("schema") != "successor-workbench/v1" or not isinstance(pack.get("spec"), dict):
        raise ValueError("Unsupported retained work artifact format")
    body = {key: value for key, value in pack.items() if key != "integrityDigest"}
    if pack.get("integrityDigest") != digest("workbench-pack", body):
        raise ValueError("Retained work pack integrity mismatch")
    result = pack.get("result")
    artifacts = result.get("artifacts") if isinstance(result, dict) else None
    if not isinstance(artifacts, list) or len(artifacts) > 12:
        raise ValueError("Retained work artifact count exceeds its limit")
    names = {"mission.json", "evidence.json", "read_me.txt", "lifecycle.json", "signed-receipt.json", "source-key.txt"}
    files: list[tuple[str, bytes]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"name", "type", "content", "digest"}:
            raise ValueError("Invalid retained work artifact envelope")
        name, content = artifact["name"], artifact["content"]
        if (
            not isinstance(name, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name) is None
            or name.endswith(".")
            or re.match(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\.|$)", name, re.I)
            or name.casefold() in names
        ):
            raise ValueError("Unsafe or duplicate retained work artifact name")
        if (
            artifact["type"]
            not in ("text/javascript", "text/plain", "text/csv", "text/html", "text/markdown", "application/json")
            or not isinstance(content, str)
            or len(content.encode("utf-16-le")) // 2 > 200_000
        ):
            raise ValueError("Retained work artifact content exceeds its policy")
        if artifact["digest"] != digest(
            "workbench-artifact", {key: value for key, value in artifact.items() if key != "digest"}
        ):
            raise ValueError("Retained work artifact integrity mismatch")
        names.add(name.casefold())
        files.append((name, content.encode()))
    return files


def _write_artifacts(pack: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Write only validated inert names and bytes; never execute an exported artifact."""
    files = _artifact_files(pack)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Choose a new output directory; existing files are preserved")
    destination.mkdir(parents=True, mode=0o700)
    private_write(destination / "mission.json", canonical(pack["spec"]))
    private_write(destination / "evidence.json", canonical(pack))
    for name, content in files:
        private_write(destination / name, content)
    private_write(
        destination / "READ_ME.txt",
        (
            "SUCCESSOR Ω local work artifacts\n\nReview the files before use. "
            "No live permission or settlement is included.\n"
            "Reproduce: alpha-agent successor-work run mission.json --output NEW_DIRECTORY\n"
            "mission.json binds the original inputs; evidence.json retains all local results and limitations.\n"
            "A signed retained-history export authenticates the saved observation, not current-worker compatibility.\n"
            "It does not repeat execution or establish independent acceptance, current eligibility, or physical validity.\n"
        ).encode(),
    )
    return {
        "output": str(destination.resolve()),
        "files": len(files) + 3,
        "scope": "local-public-work",
        "authority": [],
        "settlement": "NOT_CONNECTED",
    }


def write_artifacts(pack: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Inspect an untrusted pack with the current adapter before exporting its inert files."""
    invoke({"operation": "inspect", "pack": pack})
    return _write_artifacts(pack, destination)


def write_retained_artifacts(journal: Journal, record: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Export exact authenticated history without requiring its original worker to remain installed."""
    journal.verify()
    retained = journal.latest(_key(record["run_id"]))
    if retained != record:
        raise Conflict("Work changed before export; inspect its current state")
    pack = retained.get("result")
    if not isinstance(pack, dict):
        raise Conflict("There is no completed result to export")
    if retained.get("result_digest") != digest("workbench-result", pack):
        raise ValueError("Retained work result binding mismatch")
    if (
        retained.get("request_digest") != digest("workbench-request", retained["request"])
        or digest("workbench-request", pack.get("spec")) != retained["request_digest"]
    ):
        raise ValueError("Retained work request binding mismatch")
    exported = _write_artifacts(pack, destination)
    write_receipt(journal, retained, destination, "workbench-receipt")
    private_write(destination / "lifecycle.json", canonical(retained["lifecycle"]))
    return {**exported, "files": exported["files"] + 3, "validation": "authenticated-retained-history"}


def add_commands(commands: Any) -> None:
    """Register one additive command group with machine-readable results."""
    root = commands.add_parser("successor-work", help="Create, run, inspect and retain useful bounded work")
    sub = root.add_subparsers(dest="work_command", required=True)
    sub.add_parser("registry")
    verify = sub.add_parser("verify-receipt")
    verify.add_argument("file", type=Path)
    verify.add_argument("--source-key", required=True)
    example = sub.add_parser("example")
    example.add_argument(
        "family", choices=["reliability", "performance", "documentation", "public-data", "numerical", "thermal-witness"]
    )
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
        exported = write_retained_artifacts(Journal(args.home), result, args.output)
        return {
            **exported,
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
        return write_retained_artifacts(journal, record, args.output)
    raise ValueError("Unknown work command")
