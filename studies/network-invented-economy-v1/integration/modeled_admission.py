# SPDX-License-Identifier: Apache-2.0
"""Replay declared recipient economics through the research skill graph.

This adapter does not run frontier models, customer jobs, ENS, or contracts. Its
capsules contain public modeled-work descriptors, not a newly invented working
algorithm. A graph admission here means that the *declared modeled fixture*
passes the implementation's gates. It is not empirical capability validation.

Run from the package root:
    python3 -m integration.modeled_admission --out evidence/modeled_admission.json
    python3 -m integration.modeled_admission --verify evidence/modeled_admission.json

Use --freeze results/protocol_freeze.json to bind an already frozen core. The
adapter is independently hashed and is outside the core protocol module list.
Existing evidence is never overwritten; use a new output path for a revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable

from src.alpha_assessment import AlphaAssessment, AlphaCosts, BetaBaseline, evaluate_alpha
from src.recipient_ablation import run_recipient_ablation
from src.skill_graph import Dependency, Evidence, GraphError, Session, canonical, fixture_graph, verify_inclusion


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "paid-work-retained-alpha.modeled-admission.v1"
SOURCE_FILES = (
    "src/alpha_assessment.py", "src/skill_graph.py", "src/recipient_ablation.py", "src/simulator.py",
    "tests/test_alpha_assessment.py", "tests/test_skill_graph.py", "tests/test_recipient_ablation.py",
    "sources/calibration.json", "sources/workload_catalog.json",
)
TOOLS = ("python", "declared-workload-cost-model")
FAMILY = "modeled-coordination-bundle"


def json_hash(value: Any) -> str:
    """Match recipient_ablation's canonical Python-JSON digest convention."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, description: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(description)
    return {"check": description, "passed": True}


def blocked(operation: Callable[[], Any], description: str) -> dict[str, Any]:
    try:
        operation()
    except GraphError as error:
        return {"check": description, "blocked": True, "reason": str(error)}
    raise AssertionError("Expected graph refusal: " + description)


def load_assessment(data: dict[str, Any]) -> AlphaAssessment:
    values = dict(data)
    values["costs"] = AlphaCosts(**values["costs"])
    for key in ("scope", "paired_gains", "dependency_hashes", "paired_weights"):
        values[key] = tuple(values.get(key, ()))
    return AlphaAssessment(**values)


def freeze_binding(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    path = path.resolve()
    manifest = json.loads(path.read_text())
    if manifest.get("schema") != "paid-work-retained-alpha-protocol/2":
        raise ValueError("This adapter requires the paid-work protocol v2, not the archived v1 protocol")
    for name, expected in manifest["source_hashes"].items():
        require(file_hash(ROOT / name) == expected, "frozen source unchanged: " + name)
    return {"path": str(path.relative_to(ROOT)), "sha256": file_hash(path),
            "schema": manifest["schema"], "frozen_at_utc": manifest["frozen_at_utc"],
            "status": "verified-core-freeze; adapter independently bound"}


def case_replay(
    panel: dict[str, Any], case_name: str, source: dict[str, Any], provenance: dict[str, Any],
) -> dict[str, Any]:
    """Use one predetermined economic case in an independent fixture graph."""
    original = load_assessment(source["assessment"])
    decision = evaluate_alpha(original)
    require(asdict(decision) == source["decision"], "source numeric decision replays exactly")
    graph, actors = fixture_graph()
    scoped_case = "modeled-lifecycle/" + source["input_and_evidence_hash"]
    scope = (scoped_case,)
    # Recipient-local equivalents are part of the bound competent comparator,
    # not silently omitted because this fresh shared catalog begins empty.
    baseline_context = {
        "kind": "declared-modeled-lifecycle-envelope",
        "original_beta_path_id": original.beta_id,
        "original_comparator_hash": original.comparator_capability_set_hash,
        "source_input_evidence_hash": source["input_and_evidence_hash"],
        "recipient_and_world_inputs": panel["protocol"],
        "case": case_name, "case_assessment": asdict(original),
        "runtime": provenance["runtime"], "source_hashes": provenance["source_hashes"],
        "adapter_sha256": provenance["adapter_sha256"],
    }
    beta = BetaBaseline(
        original.beta_id, json_hash(baseline_context),
        "MODELED lifecycle envelope: competent recipient models/tools/prior equivalents, declared moving-Beta "
        "path, exact cost-model sources and local replay environment; not a current production frontier configuration.",
        "simulation",
    )
    graph.set_beta_baseline(actors["admitter"], beta, now=0)
    roles = {actor.name: sorted(graph.directory.require(actor).permissions) for actor in actors.values()}
    role_check = require(
        len({actors[name].name for name in ("inventor", "validator-a", "validator-b", "admitter")}) == 4,
        "producer, two attestors, and admission actor have distinct identities",
    )
    components = []
    component_payloads = {}
    component_evidence = []
    mapping = []
    candidate = panel["protocol"]["candidate"]
    original_component_hashes = []
    replay_hash = json_hash({"adapter": provenance["adapter_sha256"],
                             "sources": provenance["source_hashes"], "case": case_name,
                             "source_evidence": source["input_and_evidence_hash"]})
    for kind in candidate["components"]:
        residual = candidate["residual_work"][kind]
        old_hash = json_hash({"kind": kind, "residual": residual})
        original_component_hashes.append(old_hash)
        skill_id = f"{case_name}/component-{kind}"
        # Neither held-out cases nor scorer internals are in this public fixture.
        payload = canonical({"kind": "public-modeled-work-descriptor", "component": kind,
                             "residual_work_assumption": residual,
                             "source_component_hash": old_hash,
                             "executable_invented_capability": False,
                             "protected_evaluation_contents": False})
        manifest = graph.create_candidate(
            actors["inventor"], skill_id, payload, FAMILY, scope, prerequisites=TOOLS,
            limits="Modeled work parameters only; no capability or independent Alpha claim", now=0,
        )
        # These are eight executed field-validity checks, not eight task trials.
        checks = [require(isinstance(amount, (int, float)) and not isinstance(amount, bool)
                          and math.isfinite(amount) and amount >= 0,
                          "finite nonnegative Work field: " + name)
                  for name, amount in residual.items()]
        evidence = Evidence(manifest.hash, graph.policy.hash, 0, 12, len(checks), 0, 0.0,
                            replay_hash, json_hash(checks), scope, "simulation-fixture", True)
        graph.submit_evidence(actors["inventor"], skill_id, evidence, now=0)
        components.append(Dependency(skill_id, manifest.hash))
        component_payloads[skill_id] = payload
        component_evidence.append({"skill_id": skill_id, "manifest": asdict(manifest),
                                   "evidence": asdict(evidence), "executed_schema_checks": checks,
                                   "independent_alpha_assessment": False})
        mapping.append({"kind": kind, "source_component_hash": old_hash,
                        "graph_manifest_hash": manifest.hash, "graph_evidence_hash": evidence.hash})
    require(sorted(original_component_hashes) == sorted(original.dependency_hashes),
            "every original assessed component maps to one graph-pinned component")

    skill_id = case_name + "/joint-bundle"
    payload = canonical({"kind": "public-modeled-bundle-descriptor", "case": case_name,
                         "components": [asdict(component) for component in components],
                         "source_input_evidence_hash": source["input_and_evidence_hash"],
                         "purpose": "Research replay of declared retained-learning costs",
                         "executable_invented_capability": False, "protected_evaluation_contents": False})
    manifest = graph.create_candidate(
        actors["inventor"], skill_id, payload, FAMILY, scope, prerequisites=TOOLS,
        components=tuple(components),
        limits="Synthetic modeled lifecycle only; public descriptors are not a delivery-ready invention", now=0,
    )
    ledgers = source["ledgers"]
    expected_recommendation = (decision.accepted and source["upfront_affordable_without_future_receipts"]
                               and source["all_modeled_delivery_routes_feasible"])
    checks = [
        role_check,
        require(original.evidence_hash == source["input_and_evidence_hash"], "economic evidence identity preserved"),
        require(original.beta_id == source["baseline_path_id"], "declared moving-Beta path identity preserved"),
        require(original.planned_reuse == source["planned_reuse"], "planned reuse unchanged"),
        require(ledgers["A_job"]["memo"] is None and not ledgers["A_job"]["added_again_to_alpha"],
                "unspecified source-job A memo is not invented or charged again"),
        require(math.isclose(original.costs.total,
                             ledgers["B_additional_retention"]["total_additional_lifecycle"]
                             + ledgers["C_optional_new_rd"]["total"], abs_tol=1e-7),
                "complete incremental costs equal B retention plus optional C R&D"),
        require(ledgers["B_additional_retention"]["receiver_costs_already_in_paired_delivery"],
                "receiving costs remain inside matched delivery comparisons"),
        require(math.isclose(decision.expected_net, source["project_net"], abs_tol=1e-7),
                "economic decision equals reported modeled project net"),
        require(source["project_net"] == source["prospective_net"], "prospective net excludes sunk A costs"),
        require(bool(expected_recommendation) == source["candidate_is_recommended_now"],
                "affordability and delivery constraints remain independent admission prerequisites"),
        require(len(components) == len(original.dependency_hashes), "complete joint component set retained"),
        require(len(source["weekly"]) == len(original.paired_gains), "each paired gain has a declared weekly row"),
    ]
    evidence = Evidence(manifest.hash, graph.policy.hash, 0, 12, len(checks), 0,
                        source["mean_delivery_saving_per_use"], replay_hash, json_hash(checks),
                        scope, "simulation-fixture", True)
    graph.submit_evidence(actors["inventor"], skill_id, evidence, now=0)
    adapted = replace(
        original, comparator_capability_set_hash=graph.comparator_hash(actors["inventor"], skill_id, now=0),
        scope=scope, evidence_hash=evidence.hash,
        dependency_hashes=tuple(sorted(component.manifest_hash for component in components)),
    )
    adapted_decision = evaluate_alpha(adapted)
    numerical_fields = ("accepted", "lower_net", "expected_net", "upper_net", "reason", "beta_id", "source_kind")
    require(all(getattr(adapted_decision, name) == getattr(decision, name) for name in numerical_fields),
            "context rebinding changes no numerical decision input or result")
    graph_decision = graph.assess_alpha(actors["inventor"], skill_id, adapted, now=0)
    require(graph_decision["accepted"] == decision.accepted, "graph gate agrees with the original modeled Alpha gate")
    refusals = [blocked(lambda: graph.promote_canonical(actors["admitter"], skill_id, now=0),
                        "canonical promotion cannot bypass validation and admission")]
    attestations = []
    admitted = bool(expected_recommendation)
    if admitted:
        for name in ("validator-a", "validator-b"):
            attestation = graph.sign_attestation(actors[name], skill_id, "supported", now=0, expires_at=8)
            graph.attach_attestation(actors[name], attestation, now=0)
            attestations.append(asdict(attestation))
        graph.validate(actors["validator-a"], skill_id, now=0)
        refusals.extend([
            blocked(lambda: graph.admit(actors["inventor"], skill_id, now=0), "producer cannot admit"),
            blocked(lambda: graph.admit(actors["validator-a"], skill_id, now=0), "attestor cannot admit"),
        ])
        graph.admit(actors["admitter"], skill_id, now=0)
    else:
        if not decision.accepted:
            refusals.append(blocked(lambda: graph.validate(actors["validator-a"], skill_id, now=0),
                                    "nonpositive or redundant Alpha cannot validate"))
        refusals.append(blocked(lambda: graph.admit(actors["admitter"], skill_id, now=0),
                                "rejected or deferred case has no validated admission"))
        graph.record_failure(
            actors["inventor"], case_name + "/failure-memory", scope,
            "modeled-negative-net" if not decision.accepted else "modeled-admission-deferred",
            "Declared modeled case is not admitted; no empirical capability failure or future value is inferred.",
            original.hash, now=0,
        )

    member_checks = []
    for name, actor in actors.items():
        discovered = tuple(item["skill_id"] for item in graph.discover(actor, now=0))
        selected = graph.select(actor, FAMILY, scoped_case, TOOLS, now=0)
        expected_catalog = (skill_id,) if admitted else ()
        require(discovered == expected_catalog and selected == expected_catalog,
                "equal discoverability and applicable selection for " + name)
        row = {"member": actor.name, "discovered": discovered, "applicable_catalog": selected,
               "action_permissions": roles[actor.name]}
        if admitted:
            require(graph.retrieve(actor, skill_id, now=0) == payload, "identical bundle retrieval for " + name)
            component_hashes = {}
            for component in components:
                retrieved = graph.retrieve_component(actor, skill_id, component.skill_id, now=0)
                require(retrieved == component_payloads[component.skill_id], "component retrieval for " + name)
                component_hashes[component.skill_id] = hashlib.sha256(retrieved).hexdigest()
            row.update({"bundle_payload_sha256": hashlib.sha256(payload).hexdigest(),
                        "component_payload_sha256": component_hashes, "inspect_export_compose_inputs": True})
        else:
            row["retrieval_refusal"] = blocked(lambda actor=actor: graph.retrieve(actor, skill_id, now=0),
                                                "unadmitted capsule cannot be retrieved")
        memories = graph.read_failures(actor, now=0)
        require(len(memories) == (0 if admitted else 1), "separate failure-memory availability for " + name)
        require(all(not item["positive_alpha"] and not item["eligible_for_skill_selection"] for item in memories),
                "failure memory cannot become a positive skill")
        row["failure_memory"] = list(memories)
        member_checks.append(row)

    reuse_receipt = None
    if admitted:
        refusals.append(blocked(
            lambda: graph.authorize_reuse(actors["recipient-b"], skill_id, scoped_case, TOOLS, now=0),
            "full capsule access does not grant execution action permission"))
        permit = graph.authorize_reuse(actors["recipient-a"], skill_id, scoped_case, TOOLS, now=0)
        reuse_receipt = graph.consume_reuse(actors["recipient-a"], permit, now=0)
        require(reuse_receipt["code_executed"] is False, "graph authorization does not claim capability execution")
    else:
        refusals.append(blocked(
            lambda: graph.authorize_reuse(actors["recipient-a"], skill_id, scoped_case, TOOLS, now=0),
            "execution permission cannot override rejected admission"))
    forged_session = Session(actors["recipient-a"].name, actors["recipient-a"].fixture_wallet, 0)
    refusals.extend([
        blocked(lambda: graph.directory.open_session("nested.recipient-a.agent.agi.eth", "fixture-wallet:recipient-a"),
                "nested agent name has no direct-label membership authority"),
        blocked(lambda: graph.discover(forged_session, now=0),
                "copied identity fields do not create an authenticated fixture session"),
    ])
    inclusion = graph.inclusion(actors["recipient-a"], skill_id)
    require(verify_inclusion(inclusion["leaf"], inclusion["proof"], inclusion["root"]),
            "public-root inclusion verifies without granting capability truth or authority")
    checkpoint = graph.public_commitment()
    checkpoint_events = list(graph.history(actors["recipient-a"]))
    # A later model/tool/environment context is a changed fixture, not a claim
    # that an actual provider has changed. Old history cannot license its use.
    changed_beta = BetaBaseline(
        beta.beta_id + "/changed-runtime-fixture",
        json_hash({"prior": beta.hash, "runtime_change": "declared synthetic change"}),
        "Synthetic model/tool/environment change; no new Alpha assessment supplied", "simulation",
    )
    graph.set_beta_baseline(actors["admitter"], changed_beta, now=1)
    after_change = []
    for name, actor in actors.items():
        require(not graph.discover(actor, now=1), "old admission unavailable after baseline change for " + name)
        after_change.append({"member": actor.name, "discovered": [],
                             "retrieval_refusal": blocked(lambda actor=actor: graph.retrieve(actor, skill_id, now=1),
                                                          "changed Beta requires fresh admission")})
    return {
        "case": case_name, "graph_is_independent_of_other_case": True,
        "source_economic_result": source, "original_alpha_assessment": asdict(original),
        "original_alpha_decision": asdict(decision), "graph_alpha_result": graph_decision,
        "context_mapping": {
            "numeric_inputs_and_decision_unchanged": True,
            "source_scope": original.scope, "graph_scope": scope,
            "source_comparator_hash": original.comparator_capability_set_hash,
            "graph_comparator_hash": adapted.comparator_capability_set_hash,
            "source_evidence_hash": original.evidence_hash, "graph_evidence_hash": adapted.evidence_hash,
            "component_mapping": mapping, "baseline_configuration_hash": beta.configuration_hash,
            "initial_shared_catalog": [], "prior_recipient_equivalents_preserved_in_beta_context": True,
            "limitation": ("The Beta record binds a projected lifecycle envelope, not live competence "
                           "or future successful revalidation."),
        },
        "graph_manifest": asdict(manifest), "graph_evidence": asdict(evidence),
        "evidence_interpretation": ("Executed schema/accounting checks plus declared modeled benefit; "
                                    "no task-quality trials."),
        "executed_accounting_checks": checks, "component_evidence": component_evidence,
        "roles": roles, "fixture_attestations": attestations,
        "admission_checkpoint": {"admitted": admitted, "complete_numeric_gate_passes": decision.accepted,
                                 "affordable_before_spending": source["upfront_affordable_without_future_receipts"],
                                 "delivery_constraints_pass": source["all_modeled_delivery_routes_feasible"],
                                 "member_access_checks": member_checks, "public_commitment": checkpoint,
                                 "inclusion": inclusion, "events": checkpoint_events,
                                 "reuse_receipt": reuse_receipt, "refusals": refusals},
        "after_synthetic_baseline_change": {
            "beta": asdict(changed_beta), "all_members_blocked": after_change,
            "public_commitment": graph.public_commitment(),
            "old_assessment_history_retained": list(graph.assessment_history(actors["recipient-a"])),
        },
    }


def replay(freeze_path: Path | None = None) -> dict[str, Any]:
    before = {name: file_hash(ROOT / name) for name in SOURCE_FILES}
    freeze = freeze_binding(freeze_path)
    source_status = "verified-frozen-v2-core" if freeze else "independently-snapshotted-core; no freeze claimed"
    provenance = {"source_hashes": before, "adapter_sha256": file_hash(Path(__file__)),
                  "runtime": {"python": platform.python_version(), "cryptography": version("cryptography")},
                  "core_freeze": freeze,
                  "source_status": source_status}
    panel = run_recipient_ablation()
    cases = [case_replay(panel, "primary-retention", panel["lifecycle"], provenance),
             case_replay(panel, "optional-new-rd", panel["optional_new_rd_comparison"], provenance)]
    require(before == {name: file_hash(ROOT / name) for name in SOURCE_FILES}, "source files unchanged during replay")
    require(freeze_binding(freeze_path) == freeze, "optional frozen protocol unchanged during replay")
    return {"schema": SCHEMA, "evidence_kind": "actual-local-integration-of-declared-modeled-assessments",
            "provenance": provenance, "source_protocol": panel["protocol_id"],
            "source_panel_sha256": json_hash(panel), "source_protocol_inputs": panel["protocol"],
            "predeclared_cases": ["primary-retention", "optional-new-rd"], "cases": cases,
            "actual_activity": {"frontier_role_model_calls": 0, "customer_jobs": 0, "collections_usd": 0,
                                "ens_queries": 0, "contract_transactions": 0, "production_deployments": 0,
                                "production_authentication": False, "production_capsule_secrecy": False,
                                "protected_evaluation_material_shared": False},
            "interpretation": [
                "Admissions and refusals are actual local API results under simulated identities "
                "and declared economic inputs.",
                "Signed fixture attestations confirm recorded statements, not independent capability truth "
                "or correct market forecasts.",
                "Public deterministic encryption/signing keys provide no production privacy or identity assurance.",
                "The source-job A cost remains unspecified; the fixed recipient panel charges only "
                "incremental B and optional C.",
                "The zero declared uncertainty margin is not a confidence guarantee; successful future "
                "revalidation is an assumption.",
                "Every direct-label fixture member can retrieve an admitted bundle, even without "
                "execution action permissions.",
                "Members may copy exported public fixture capsules; access control is not demonstrated defensibility.",
                "The two cases use separate graphs and represent alternative modeled decisions, "
                "not two actual invention campaigns.",
                "The recipient candidate's admitted label is only a cost-model eligibility assumption; "
                "this replay starts graph candidates and cannot import that label as admission.",
                "No full customer outcome, executable invention, cash payment, or realized "
                "reinvestment loop is established here.",
            ]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--out", type=Path)
    group.add_argument("--verify", type=Path)
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args()
    expected = None
    freeze_path = args.freeze
    if args.verify:
        expected = json.loads(args.verify.read_text())
        saved_freeze = expected["provenance"]["core_freeze"]
        if freeze_path is None and saved_freeze is not None:
            freeze_path = ROOT / saved_freeze["path"]
    result = replay(freeze_path)
    if expected is not None:
        require(canonical(result) == canonical(expected),
                "retained integration evidence replays byte-for-byte canonically")
        output = args.verify
    else:
        output = args.out or ROOT / "evidence/modeled_admission.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    print(json.dumps({"output": str(output), "verified": expected is not None,
                      "evidence_kind": result["evidence_kind"], "cases": [
                          {"case": case["case"],
                           "admitted_at_fixture_checkpoint": case["admission_checkpoint"]["admitted"],
                           "modeled_lower_net_usd": case["original_alpha_decision"]["lower_net"],
                           "member_access_checks": len(case["admission_checkpoint"]["member_access_checks"])}
                          for case in result["cases"]]}))


if __name__ == "__main__":
    main()
