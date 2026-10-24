# SPDX-License-Identifier: Apache-2.0
"""Writer 9 local experiment adapter over unchanged published SUCCESSOR code.

Only RFC 8032 section 7.1 TEST 1 key bytes are reused. This public fixture has
no authentication value, external authority, independent custody, or API token.
The dispatcher executes trusted caller-installed bounded numerical functions;
it is not an operating-system sandbox for arbitrary submitted programs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sqlite3
import sys
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from pathlib import Path
from typing import Any
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ALPHA = HERE / "vendored" / "alpha"
RFC8032_TEST1 = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
RFC8032_PUBLIC = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
RFC8032_URL = "https://www.rfc-editor.org/rfc/rfc8032#section-7.1"
PIN = "dfc79c4ae81ac612cbff9865a0af8389b6ff3de9"
FAMILIES = ("constitution", "evidence", "formation", "challenge", "verification", "admission", "renewal")


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _wire(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Nonfinite measurement")
        return repr(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_wire(v) for v in value]
    return value


def verify_vendored_sources() -> list[dict[str, Any]]:
    manifest = json.loads((HERE / "vendored" / "SOURCES.json").read_text())
    for entry in manifest["files"]:
        path = HERE / entry["vendored_path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("Untrusted vendored source path")
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != entry["git_blob_sha"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Vendored source changed: " + entry["vendored_path"])
    return manifest["files"]


verify_vendored_sources()
sys.path.insert(0, str(ALPHA))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from alpha_factory_v1.core.runtime.models import RuntimeConfig
from alpha_factory_v1.core.runtime.store import Journal, digest as journal_digest
from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher, JobResult
from alpha_factory_v1.core.runtime.successor.protocol import (
    AdmissionDecision, AuthorityEnvelope, BehaviorArtifact, CandidateReleaseManifest,
    ExecutionAuthorization, Institution, JobContract, JobDependency, JobGraph,
    MissionConstitution, PolicyProgram, ProofReceipt, VerifierDisclosure, WorldProgram,
    canonical, digest,
)
from alpha_factory_v1.core.runtime.successor.state import ActionGateway, ActionRequest, SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

for _module in (Journal, JobDispatcher, SuccessorStore, WorldProgram):
    _source = Path(sys.modules[_module.__module__].__file__).resolve()
    if not _source.is_relative_to(ALPHA):
        raise RuntimeError("An unpinned Alpha module was already loaded: " + str(_source))


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _native_decimal(value: Any, rounding: str) -> str:
    with localcontext() as context:
        context.prec = 80
        decimal = Decimal(str(value)).quantize(Decimal("0.000000000000000001"), rounding=rounding)
    result = format(decimal, "f").rstrip("0").rstrip(".") if "." in format(decimal, "f") else format(decimal, "f")
    return result or "0"


def _fixture_journal(root: Path) -> Journal:
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    config = RuntimeConfig(name="writer9-public-fixture")
    (root / "config.json").write_bytes(_json(config.model_dump()))
    descriptor = os.open(root / "identity.key", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(RFC8032_TEST1)
    with sqlite3.connect(root / "journal.sqlite3") as cx:
        cx.execute(
            "CREATE TABLE events(seq INTEGER PRIMARY KEY, mission TEXT NOT NULL, body TEXT NOT NULL, "
            "hash TEXT NOT NULL UNIQUE, signature TEXT NOT NULL)"
        )
        cx.execute("CREATE INDEX events_mission ON events(mission,seq)")
    journal = Journal(root)
    if journal.public != RFC8032_PUBLIC:
        raise ValueError("Public RFC fixture identity mismatch")
    with journal.transaction() as cx:
        journal.append(cx, "@control", {"state": "ready", "config_hash": journal_digest(config.model_dump())})
    return journal


def _fixture_trust() -> tuple[TrustRegistry, Any]:
    key = Ed25519PrivateKey.from_private_bytes(RFC8032_TEST1)
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    if public != RFC8032_PUBLIC:
        raise ValueError("RFC fixture differs from repository TEST 1")
    roles = {
        "local-controller": {"controller", "admission", "authority", "acceptance", "control", "worker"},
        "local-producer": {"producer", "worker"},
        "local-verifier": {"verifier", "acceptance", "worker"},
    }
    return TrustRegistry({p: TrustAnchor(public, frozenset(r)) for p, r in roles.items()}), key


def _file_hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Artifact must be an existing regular file")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_harness(
    output: Path,
    numeric_handler: Callable[[], Mapping[str, Any]],
    independent_check: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    source_files: Mapping[str, Path],
    world: Mapping[str, Any],
    policy: Mapping[str, Any],
    protocol: Mapping[str, Any],
    purpose: str = "Verify a bounded scientific-computing capability",
) -> dict[str, Any]:
    """Execute once, check actual bytes, and retain local native lifecycle evidence.

    numeric_handler is pure and returns artifact_content, or recomputes a result
    while naming an already retained artifact_path and artifact_sha256. The adapter
    persists returned artifact_content only after the native tool completes.
    The checker returns
    artifact_sha256, accepted, max_residual and threshold; numeric thresholds use
    explicit decimal strings. Scientific failure remains a recorded fail result.
    All input functions are trusted installed research code, not imported code.
    """
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources = {name: _file_hash(Path(path)) for name, path in source_files.items()}
    sources["writer9_harness_adapter"] = _file_hash(Path(__file__))
    source_manifest = {"source_files": sources, "vendor": verify_vendored_sources()}
    (output / "source-freeze.json").write_bytes(_json(source_manifest))
    env = {
        "python": platform.python_version(), "system": platform.system(),
        "machine": platform.machine(), "source": sources,
    }
    env_digest = digest("writer9-environment", env)
    world_wire = _wire(world)
    policy_wire = _wire(policy)
    protocol_wire = _wire(protocol)
    world_program = WorldProgram(
        world_id="writer9-world", artifact_digest=digest("writer9-world-source", world_wire),
        uncertainty="Measured numerical outputs and explicitly simulated decision counterfactuals are separate.",
        assumptions=["No external customer adoption or payment is established by this local experiment."],
        falsifiers=["Source mutation, residual failure, or a stronger comparator removes the corresponding claim."],
    )
    policy_program = PolicyProgram(
        policy_id="writer9-policy", artifact_digest=digest("writer9-policy-source", policy_wire),
        objective=purpose, decision_rules=["Use frozen policy inputs; charge declared costs; retain every failure."],
        admissible_actions=["bounded-numerical-experiment", "inspect-retained-artifact"],
        abstention=["Stop on missing current proof or explicit local fixture grant."],
    )
    with patch.object(Ed25519PrivateKey, "generate", side_effect=AssertionError("New keys prohibited")), patch(
        "secrets.token_urlsafe", side_effect=AssertionError("API tokens prohibited")
    ):
        journal = _fixture_journal(output / "fixture-state")
        trust, fixture_key = _fixture_trust()
        store = SuccessorStore(journal, trust)
        institution_id = "writer9-fixture-institution"
        mission_id = "writer9-constructive-foresight"
        store.create_institution(Institution(
            id=institution_id, controller="local-controller",
            constitution=MissionConstitution(
                mission_id=mission_id, owner="local-controller", objective=purpose,
                mission_distribution="Frozen bounded research tasks; no beneficiary or adoption outcome implied",
                scope="Disposable local fixture with one public RFC test identity",
                authority_ceiling="sandbox", proof_requirements=["correctness"],
                prohibited_actions=["network", "financial-action", "deploy", "credential-creation"],
                accounting_rule="Native calls are orchestration records, not model calls or currency.",
            ),
        ), {"calls": 16})
        release = CandidateReleaseManifest(
            release_id="writer9-release-1", institution_id=institution_id, mission_id=mission_id,
            producer="local-producer", environment_digest=env_digest,
            artifacts=[BehaviorArtifact(name=name, role="source", digest=value) for name, value in sources.items()],
            world_digest=digest("world-program", world_program), policy_digest=digest("policy-program", policy_program),
            development_evaluator_digest=digest("writer9-protocol", protocol_wire),
        )
        store.register_release(institution_id, release, request_id="freeze-release")
        release_digest = digest("release", release)
        now = datetime.now(UTC).replace(microsecond=0)
        issued = _iso(now)
        valid = _iso(now + timedelta(hours=4))
        tasks = []
        for index, family in enumerate(FAMILIES):
            worker = (
                "local-verifier" if family in {"challenge", "verification"}
                else "local-controller" if family == "admission" else "local-producer"
            )
            owner = "local-verifier" if worker == "local-controller" else "local-controller"
            tasks.append(JobContract(
                job_id=family, family=family, worker=worker, acceptance_owner=owner,
                release_digest=release_digest, environment_digest=env_digest,
                institution_id=institution_id, mission_id=mission_id,
                inputs={"record": "writer9-phase-v1"} if index else {}, outputs={"record": "writer9-phase-v1"},
                critical_functions=[family], resources={"calls": 1}, valid_until=valid,
                allowed_tools=["fixed-research-function"], effects=[], max_attempts=1,
            ))
        graph = JobGraph(
            jobs=tasks,
            edges=[
                JobDependency(source=FAMILIES[i - 1], target=family, kind="evidence")
                for i, family in enumerate(FAMILIES) if i
            ],
            required_families=list(FAMILIES), required_functions=list(FAMILIES),
        )
        dispatcher = JobDispatcher(store, institution_id)
        dispatcher.seal(graph)
        phase_results: dict[str, Any] = {}
        measured = {"numeric_handler_calls": 0, "checker_calls": 0, "inspection_handler_calls": 0}

        def numerical() -> dict[str, Any]:
            measured["numeric_handler_calls"] += 1
            result = _wire(numeric_handler())
            if isinstance(result, dict) and "artifact_content" in result:
                if "artifact_path" in result or "artifact_sha256" in result:
                    raise ValueError("Content output cannot override the adapter-owned artifact identity")
                artifact_bytes = canonical(result["artifact_content"])
                result["artifact_path"] = str(output / "numerical-artifact.json")
                result["artifact_sha256"] = hashlib.sha256(artifact_bytes).hexdigest()
                return result
            if not isinstance(result, dict) or not {"artifact_path", "artifact_sha256"} <= result.keys():
                raise ValueError("Numeric handler must return the exact artifact path and SHA256")
            if _file_hash(Path(result["artifact_path"])) != result["artifact_sha256"]:
                raise ValueError("Numerical artifact hash differs from actual bytes")
            return result

        def challenge() -> dict[str, Any]:
            measured["checker_calls"] += 1
            report = _wire(independent_check(phase_results["formation"]))
            required = {"artifact_sha256", "accepted", "max_residual", "threshold"}
            if not isinstance(report, dict) or not required <= report.keys():
                raise ValueError("Checker receipt omits artifact binding or numerical acceptance fields")
            if type(report["accepted"]) is not bool:
                raise ValueError("Checker acceptance must be explicit")
            residual, threshold = Decimal(report["max_residual"]), Decimal(report["threshold"])
            if not residual.is_finite() or not threshold.is_finite() or threshold < 0 or residual < 0:
                raise ValueError("Checker threshold/residual must be finite nonnegative decimals")
            if report["accepted"] and residual > threshold:
                raise ValueError("Checker accepted a failed residual threshold")
            if report["artifact_sha256"] != phase_results["formation"]["artifact_sha256"]:
                raise ValueError("Checker examined a different artifact")
            return report

        def verification() -> dict[str, Any]:
            observed = _file_hash(Path(phase_results["formation"]["artifact_path"]))
            if observed != phase_results["formation"]["artifact_sha256"]:
                raise ValueError("Artifact changed after examination")
            for name, path in source_files.items():
                if _file_hash(Path(path)) != sources[name]:
                    raise ValueError("Research source changed during the frozen run")
            if _file_hash(Path(__file__)) != sources["writer9_harness_adapter"]:
                raise ValueError("Harness source changed")
            verify_vendored_sources()
            return {
                "accepted": phase_results["challenge"]["accepted"],
                "artifact_sha256": phase_results["formation"]["artifact_sha256"], "source_unchanged": True,
            }

        handlers = {
            "constitution": lambda: {
                "world": world_program.model_dump(mode="json"),
                "policy": policy_program.model_dump(mode="json"), "protocol": protocol_wire,
            },
            "evidence": lambda: {
                "source_manifest_digest": digest("writer9-source", source_manifest),
                "scope": "Frozen public inputs; no prospective external outcome",
            },
            "formation": numerical, "challenge": challenge, "verification": verification,
            "admission": lambda: {
                "accepted_work": True, "candidate_correctness": phase_results["verification"]["accepted"],
                "external_authority": "none",
            },
            "renewal": lambda: {
                "retained_artifact_sha256": phase_results["formation"]["artifact_sha256"],
                "fresh_successor_proof_required": True,
            },
        }
        for terms in tasks:
            assignment = ExecutionAuthorization(
                authorization_id="writer9-" + terms.job_id, acting_identity=terms.worker,
                job_terms_digest=digest("job-terms", terms), release_digest=release_digest,
                environment_digest=env_digest, capabilities=["fixed-research-function"],
                reservation_id="reservation-" + terms.job_id, expires_at=valid,
            )
            dispatcher.dispatch(terms.job_id, sign_record(fixture_key, "local-controller", "execution", assignment))
            result = dispatcher.execute_tool(
                terms.job_id, tool="fixed-research-function", actor=terms.worker,
                invocation_id="invoke-" + terms.job_id, handler=handlers[terms.job_id], retain_result=True,
            )
            if terms.job_id == "formation" and "artifact_content" in result:
                with Path(result["artifact_path"]).open("xb") as stream:
                    stream.write(canonical(result["artifact_content"]))
                if _file_hash(Path(result["artifact_path"])) != result["artifact_sha256"]:
                    raise ValueError("Persisted numerical artifact differs from the retained pure tool result")
            phase_results[terms.job_id] = result
            acceptance = JobResult(
                job_id=terms.job_id, authorization_id=assignment.authorization_id,
                terms_digest=digest("job-terms", terms), output_digest=digest("job-tool-output", result),
                outputs=terms.outputs, accepted=True, accepted_by=terms.acceptance_owner,
                valid_until=valid, permitted_uses=["dependency"], actual_resources={"calls": 1},
                candidate_verdict=(
                    "pass" if phase_results.get("verification", {}).get("accepted") else "not-established"
                ),
            )
            dispatcher.complete(sign_record(fixture_key, terms.acceptance_owner, "job-acceptance", acceptance))
        result_digest = digest("writer9-result", phase_results["formation"])
        residual_decimal = _native_decimal(phase_results["challenge"]["max_residual"], ROUND_CEILING)
        threshold_decimal = _native_decimal(phase_results["challenge"]["threshold"], ROUND_FLOOR)
        if phase_results["verification"]["accepted"] and Decimal(residual_decimal) > Decimal(threshold_decimal):
            raise ValueError("Native fixed-decimal precision cannot faithfully express this accepted comparison")
        proof = ProofReceipt(
            proof_id="writer9-measured-proof", institution_id=institution_id, mission_id=mission_id,
            release_digest=release_digest, environment_digest=env_digest, verifier="local-verifier",
            issued_at=issued, valid_until=_iso(now + timedelta(hours=1)),
            outcome="pass" if phase_results["verification"]["accepted"] else "fail", claim="correctness",
            comparator_manifest_digest=digest("writer9-comparators", protocol_wire),
            protocol_digest=digest("writer9-protocol", protocol_wire),
            evidence_commitment=digest("writer9-checked-artifact", phase_results["challenge"]), evaluation_units=1,
            disclosure=VerifierDisclosure(
                verifier="local-verifier", organization="same local operator",
                control_separation="none; one public RFC test key shared by local role labels",
                custodian="local-controller", funding_and_conflicts="same research session",
                protocol_controller="local-controller", replication_status="not-replicated",
            ),
            measurements={"max_residual": residual_decimal, "threshold": threshold_decimal},
            uncertainty=(
                "Artifact correctness only. Native 18-place decimals round residual upward and threshold downward; "
                "exact checker values remain in evidence. No independent proof, adoption, payment or economic alpha."
            ),
        )
        store.record_proof(
            institution_id, sign_record(fixture_key, "local-verifier", "proof", proof),
            request_id="record-measured-proof",
        )
        controls: list[dict[str, Any]] = []

        def refused(name: str, operation: Callable[[], Any]) -> None:
            before = dict(measured)
            try:
                operation()
            except (ValueError, KeyError) as error:
                controls.append({
                    "name": name, "rejected": True, "reason": str(error),
                    "handler_counts_unchanged": measured == before,
                })
            else:
                raise AssertionError("Required refusal failed: " + name)

        if proof.outcome == "pass":
            decision = AdmissionDecision(
                decision_id="writer9-local-admission", institution_id=institution_id, release_digest=release_digest,
                principal="local-controller", outcome="admit", proof_ids=[proof.proof_id],
            )
            store.admit(
                institution_id, sign_record(fixture_key, "local-controller", "admission", decision),
                request_id="admit-local",
            )

            def cutover(release_hash: str, operation_id: str) -> Any:
                return store.cutover(
                    institution_id,
                    sign_record(fixture_key, "local-controller", "cutover", {"release_digest": release_hash}),
                    request_id=operation_id, expected_revision=store.read(institution_id)["revision"],
                )

            refused("missing-authority", lambda: cutover(release_digest, "missing-authority"))
            context = digest("writer9-artifact-inspection", {
                "artifact_sha256": phase_results["formation"]["artifact_sha256"], "result_digest": result_digest,
            })

            def grant(name: str, expiry: datetime) -> AuthorityEnvelope:
                value = AuthorityEnvelope(
                    grant_id=name, institution_id=institution_id, mission_id=mission_id, release_digest=release_digest,
                    subject="local-producer", issuer="local-controller", actions=["inspect-retained-artifact"],
                    tools=["fixed-artifact-reader"], targets=["retained-artifact"], resources={"calls": 3},
                    proof_ids=[proof.proof_id], valid_until=_iso(expiry), context_digest=context,
                    approval_required=False,
                )
                store.grant(
                    institution_id, sign_record(fixture_key, "local-controller", "authority", value), request_id=name,
                )
                return value

            grant("writer9-short-fixture-grant", now + timedelta(minutes=30))
            cutover(release_digest, "install-exact-release")

            def action(name: str) -> ActionRequest:
                return ActionRequest(
                    action_id=name, subject="local-producer", release_digest=release_digest,
                    environment_digest=env_digest, action="inspect-retained-artifact", tool="fixed-artifact-reader",
                    target="retained-artifact", context_digest=context, resources={"calls": 1},
                )

            def inspect_artifact(_: Any) -> dict[str, Any]:
                measured["inspection_handler_calls"] += 1
                observed = _file_hash(Path(phase_results["formation"]["artifact_path"]))
                if observed != phase_results["formation"]["artifact_sha256"]:
                    raise ValueError("Retained artifact changed")
                return {"artifact_sha256": observed, "read_only": True}

            gateway = ActionGateway({("fixed-artifact-reader", "inspect-retained-artifact"): inspect_artifact})
            store.dispatch_action(institution_id, action("fresh-inspection"))
            store.execute_action(institution_id, "fresh-inspection", gateway, actual_resources={"calls": 1})
            with patch(
                "alpha_factory_v1.core.runtime.successor.state.utc_now",
                return_value=_iso(now + timedelta(minutes=31)),
            ):
                refused(
                    "stale-authority", lambda: store.dispatch_action(institution_id, action("stale-authority-action")),
                )
            grant("writer9-long-fixture-grant", now + timedelta(hours=2))
            with patch(
                "alpha_factory_v1.core.runtime.successor.state.utc_now",
                return_value=_iso(now + timedelta(minutes=61)),
            ):
                refused("stale-proof", lambda: store.dispatch_action(institution_id, action("stale-proof-action")))
            descendant = release.model_copy(update={
                "release_id": "writer9-release-2", "parent_release_digest": release_digest,
            })
            store.descendant(institution_id, descendant, request_id="shadow-successor")
            refused(
                "successor-without-fresh-proof", lambda: cutover(digest("release", descendant), "successor-cutover"),
            )
        state = store.read(institution_id)
        verified_journal = journal.verify()
        if (output / "fixture-state" / "api.token").exists():
            raise AssertionError("API token must not exist")
        receipt = {
            "schema": "writer9-native-harness-receipt/v1", "alpha_commit": PIN,
            "scope": "Published lifecycle with public common-control test identity; no external authority",
            "fixture": {
                "source": RFC8032_URL,
                "existing_repository_fixture": "tests/runtime/test_successor_signatures.py::PUBLIC",
                "public_key": RFC8032_PUBLIC, "new_identity_generation": False, "api_token_created": False,
                "authentication_value": "none; fixture private bytes are public",
                "organizational_independence": "none",
            },
            "clock_controls": (
                "Expiry probes advance only the disposable fixture's decision clock; "
                "prospective outcomes are not generated."
            ),
            "world": world_program.model_dump(mode="json"), "policy": policy_program.model_dump(mode="json"),
            "release": release.model_dump(mode="json"), "release_digest": release_digest,
            "phases": phase_results, "proof": proof.model_dump(mode="json"), "controls": controls,
            "handler_counts": measured, "resources": state["resources"], "lineage": state["lineage"],
            "journal": verified_journal, "new_candidate_proofs_inherited": False,
            "elapsed_seconds": repr(time.perf_counter() - started_wall),
            "cpu_seconds": repr(time.process_time() - started_cpu),
            "not_claimed": [
                "external beneficiary acceptance", "independent signatures", "Fleet installed execution",
                "mainnet settlement", "economic alpha", "operating-system isolation",
            ],
        }
        (output / "native-receipt.json").write_bytes(canonical(receipt))
        (output / "native-state.json").write_bytes(canonical(state))
        return receipt
