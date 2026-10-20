#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Produce a source-exact reading card through the existing bounded TI runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.store import Journal, private_write
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor.transformation import (
    DiscoveryLoop,
    DiscoveryRequest,
    IntentCharter,
    SourceDocument,
    assert_public_content,
    validate_envelope,
)
from alpha_factory_v1.core.runtime.successor.transformation_model import (
    LocalModelConfig,
    ModelDiscovery,
    validate_model_envelope,
)

FIXTURES = Path(__file__).resolve().parents[1] / "examples/transformational-intelligence/public-preparation"
INPUT_SHA256 = "ee1de0992ad4c820438e4d21ac8d5adaf075b3ac296184b328eeda798aa539f9"
MANAGER_COMMIT = "8b0cf7fbc09e48ffe55d8ed35df8cd40920231d2"
SOURCE_HASHES = {
    "ubuntu-ephemeral-creator.md": "0c802dee7adcb60c8c52618ba5703f642635e8a8488a6dacca05eab66376485b",
    "direct-origination-profile.md": "8ed6da2e8733c672b21035e2936c7954fc8ffcbf9caf8248b2e71d4656a1bf24",
}


class PilotFailure(ValueError):
    """Retain sanitized evidence of a consumed, unsuccessful real proposal call."""

    def __init__(self, evidence: dict[str, Any]) -> None:
        super().__init__("local model pilot did not complete; retained failure evidence has no approval")
        self.evidence = evidence


def load_input(folder: Path = FIXTURES) -> dict[str, Any]:
    """Bind captured public bytes before using annotations or constructing output."""
    raw_input = (folder / "input.json").read_bytes()
    if hashlib.sha256(raw_input).hexdigest() != INPUT_SHA256:
        raise ValueError("pilot annotation manifest checksum mismatch")
    inputs: dict[str, Any] = json.loads(raw_input)
    if inputs["manager_commit"] != MANAGER_COMMIT or inputs["selection_limit"] != 3:
        raise ValueError("pilot source identity or fixed artifact limit changed")
    if {item["file"]: item["sha256"] for item in inputs["sources"]} != SOURCE_HASHES:
        raise ValueError("pilot requires the published source-byte pins")
    sources = {}
    for item in inputs["sources"]:
        raw = (folder / item["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != SOURCE_HASHES[item["file"]]:
            raise ValueError("public source-byte checksum mismatch")
        expected_url = f"https://github.com/MontrealAI/AGIJobManager/blob/{MANAGER_COMMIT}/{item['repository_path']}"
        if item["source_url"] != expected_url:
            raise ValueError("public source URL differs from its immutable commit")
        sources[item["source_url"]] = " ".join(raw.decode("utf-8").split())
    for partition in ("development", "confirmation"):
        document = SourceDocument.model_validate(inputs["documents"][partition])
        for claim in document.claims:
            if sources[document.source_url].count(claim.text) != 1:
                raise ValueError("annotated clause is not a unique whitespace-normalized source quotation")
    assert_public_content(inputs)
    return inputs


def check_summary(document: dict[str, Any], result: dict[str, Any], limit: int) -> dict[str, Any]:
    """Recompute fidelity and prerequisite coverage without using the runtime scorer."""
    claims = {item["id"]: item for item in document["claims"]}
    selected = result["selected"]
    if len(selected) > limit or len(set(selected)) != len(selected) or not set(selected) <= claims.keys():
        raise ValueError("artifact violates the fixed source-clause limit")
    chosen = set(selected)
    ordered = [item for item in document["claims"] if item["id"] in chosen]
    if result["text"] != "\n".join(item["text"] for item in ordered):
        raise ValueError("artifact text differs from the pinned source clauses")
    expected_references = [{"id": item["id"], "provenance": item["provenance"]} for item in ordered]
    if result["references"] != expected_references:
        raise ValueError("artifact provenance differs from the pinned source clauses")
    supported = []
    for item in ordered:
        pending, closure = [item["id"]], set()
        while pending:
            name = pending.pop()
            if name not in closure:
                closure.add(name)
                pending.extend(claims[name]["depends_on"])
        if closure <= chosen:
            supported.append(item["id"])
    covered = sum(claims[name]["weight"] for name in supported)
    total = sum(item["weight"] for item in claims.values())
    score = covered * 1_000_000 // total
    expected = {
        "score_millionths": score,
        "covered_weight": covered,
        "total_weight": total,
        "supported_claims": supported,
        "unsupported_claims": sorted(chosen - set(supported)),
    }
    if any(result.get(key) != value for key, value in expected.items()):
        raise ValueError("producer coverage differs from independent recomputation")
    return {**expected, "source_exact": True, "all_selected_prerequisites_present": len(supported) == len(selected)}


def run_pilot(state: Path, *, model_config: Path | None = None, fixtures: Path = FIXTURES) -> dict[str, Any]:
    """Execute one disposable actual native campaign; source text is never code."""
    started, cpu_started = time.perf_counter(), time.process_time()
    inputs = load_input(fixtures)
    if state.exists():
        raise FileExistsError("choose a new disposable pilot runtime directory")
    try:
        configuration = (
            None if model_config is None else LocalModelConfig.model_validate_json(model_config.read_bytes())
        )
    except ValueError:
        raise ValueError("invalid local model configuration; use a credential-free numeric loopback endpoint") from None
    request = DiscoveryRequest(
        campaign_id=str(uuid.uuid4()),
        charter=IntentCharter(
            purpose="Prepare a three-clause source-exact reading card for reviewing the Manager operator guidance.",
            population="Two preselected public documentation excerpts; no statistical population claim",
            outcomes=["at most three exact source clauses", "retain the selected guidance's declared prerequisites"],
            constraints=[
                "documentation reading aid only; read the complete linked guide before any operation",
                "public non-personal inputs only; zero paid calls and no payment or chain operation",
                "retain source identities, annotations, failed comparisons and incomplete outcome evidence",
            ],
            permitted_actions=["read-public-source", "construct-bounded", "evaluate-local", "write-artifact"],
        ),
        development=[SourceDocument.model_validate(inputs["documents"]["development"])],
        operator_ids=["local-model-proposals"] if configuration else ["representation", "production", "complementary"],
    )
    timing = {}
    journal = Journal.initialize(state)
    model = None
    proposal_started = time.perf_counter()
    if configuration:
        model = ModelDiscovery(journal)
        record = model.create(request, configuration)
        model.approve(request.campaign_id, record["binding_digest"])
        try:
            proposed = model.propose(request.campaign_id)
            if proposed["state"] != "proposed":
                raise PermissionError("model response was revoked by pause or cancellation")
        except (ValueError, PermissionError) as exc:
            retained = model.show(request.campaign_id)
            evidence = {
                "schema": "public-preparation-pilot-failure/v1",
                "source_input_sha256": INPUT_SHA256,
                "source_pins": inputs["sources"],
                "campaign_id": request.campaign_id,
                "model_config": configuration.model_dump(),
                "retained_state": retained["state"],
                "failure": retained["failure"],
                "call_permit_consumed": retained["state"] not in {"queued", "paused"},
                "retry_allowed": False,
                "authority": "none",
                "wall_microseconds": int((time.perf_counter() - started) * 1_000_000),
                "outcome": "failed or inconclusive; no native candidate execution or promotion claimed",
            }
            assert_public_content(evidence)
            raise PilotFailure(evidence) from exc
        loop, request = model.native(request.campaign_id)
    else:
        loop = DiscoveryLoop(journal)
        loop.create(request)
    timing["model_proposal_wall_microseconds"] = (
        int((time.perf_counter() - proposal_started) * 1_000_000) if model else None
    )
    loop.approve(request.campaign_id, loop.show(request.campaign_id)["binding_digest"])
    for phase in ("diagnose", "develop", "freeze"):
        phase_started = time.perf_counter()
        frozen = loop.step(request.campaign_id, operation_id=phase)
        timing[phase + "_wall_microseconds"] = int((time.perf_counter() - phase_started) * 1_000_000)
    phase_started = time.perf_counter()
    fresh = SourceDocument.model_validate(inputs["documents"]["confirmation"])
    if model:
        model.compare(request.campaign_id, [fresh], frozen["freeze"]["digest"])
        model_evidence = validate_model_envelope(model.envelope(request.campaign_id))
        envelope = model_evidence["native_envelope"]
    else:
        loop.confirm(request.campaign_id, [fresh], frozen["freeze"]["digest"])
        model_evidence = None
        envelope = loop.envelope(request.campaign_id)
    timing["terminal_execution_and_controls_wall_microseconds"] = int((time.perf_counter() - phase_started) * 1_000_000)
    validate_envelope(envelope)
    phase_started = time.perf_counter()
    checks = {
        name: check_summary(inputs["documents"]["confirmation"], values[0], inputs["selection_limit"])
        for name, values in envelope["result"]["results"].items()
    }
    timing["independent_check_wall_microseconds"] = int((time.perf_counter() - phase_started) * 1_000_000)
    journal_count = journal.verify()
    reopened = DiscoveryLoop(Journal(state), loop.registry)
    if reopened.envelope(request.campaign_id) != envelope:
        raise AssertionError("portable native reopen differs from retained evidence")
    independent = Journal.initialize(state.parent / (state.name + "-independent-import"))
    imported = DiscoveryLoop(independent).import_history(envelope)
    if imported["status"] != "historical-only" or imported["envelope"] != envelope:
        raise AssertionError("reverse import did not actually retain complete validated history")
    timing["total_wall_microseconds"] = int((time.perf_counter() - started) * 1_000_000)
    timing["process_cpu_microseconds"] = int((time.process_time() - cpu_started) * 1_000_000)
    report = {
        "schema": "public-preparation-pilot/v1",
        "source_input_sha256": INPUT_SHA256,
        "pilot_driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_pins": inputs["sources"],
        "annotation_basis": inputs["annotation_basis"],
        "sampling": inputs["sampling"],
        "native": envelope,
        "development_attempts": loop.show(request.campaign_id)["attempts"],
        "model": model_evidence,
        "independent_checks": checks,
        "recovery": {
            "reopened_identically": True,
            "verified_journal_events": journal_count,
            "history_imported": True,
            "imported_digest": digest("ti-public-pilot-import", imported["envelope"]),
            "imported_authority": imported["active_permission"],
        },
        "costs": {
            "logical_native": envelope["result"]["costs"],
            "timing": timing,
            "construction": "included in develop phase; every attempted candidate retained in development_attempts",
            "migration": (
                "fresh disposable runtime plus actual independent historical " "import; timings included in total"
            ),
            "execution_and_verification": (
                "terminal candidate and all credible controls executed and in" "dependently recomputed"
            ),
            "money_minor": 0,
            "paid_model_calls": 0,
            "maintenance": None,
            "human_effort_seconds": None,
            "device_energy_joules": None,
            "hardware_amortization": None,
            "economic_claim": "unsupported; whole-lifecycle categories with unknown values remain explicit",
        },
        "limitations": [
            "A documentation reading card, not deployment instructions or authority to sign or transact.",
            "Local annotations and exact text checking do not establish semantic truth or reader comprehension.",
            "No calibrated outcome, fresh-campaign statistical test or general Level 3/4 superiority is established.",
            "The unrestricted exact-search comparator remains visible, including ties and negative outcomes.",
            "The deterministic mode makes no model calls; HTTP fixture tests do not count as real-model evidence.",
            (
                "Model mode is experimental, uses the operator-attested local"
                " no-charge provider and retains actual provenance."
            ),
        ],
    }
    assert_public_content(report)
    return report


def main() -> None:
    """Write inert public evidence only after source and output screening succeed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-config", type=Path)
    parser.add_argument("--approve-free-local-pilot", action="store_true", required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("choose a new public evidence output")
    try:
        report = run_pilot(args.state, model_config=args.model_config)
    except PilotFailure as exc:
        private_write(args.output, canonical(exc.evidence))
        raise ValueError("model pilot failed; inspect sanitized public failure evidence") from None
    private_write(args.output, canonical(report))
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "phase": report["native"]["phase"],
                "model_calls": 0 if report["model"] is None else 1,
                "decision": report["native"]["result"]["decision"],
            }
        )
    )


if __name__ == "__main__":
    main()
