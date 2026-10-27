# SPDX-License-Identifier: Apache-2.0
"""Executed adversarial lifecycle checks; all identities/economic observations synthetic."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

from graph_lifecycle_v3 import (BASIS, REMAINING_COSTS, CapsuleVault, LifecycleGraph,
    create_assessed_record, default_policy, digest, open_capsule, reassess_record,
    seal_capsule, simulated_authorities)

ROOT = Path(__file__).resolve().parents[1]
CREATOR = "constructor.agent.agi.eth"
MEMBER = "recipient.agent.agi.eth"
SCOPE = "digital-batch-assignment"
TRACES = []


def fixture(policy=None):
    registry, actors = simulated_authorities(CREATOR, [MEMBER], "local-test")
    return LifecycleGraph(policy or default_policy(), registry, "beta-1"), actors


def inputs(graph, cid="method-1", month=0, components=None, dependencies=None, gains=None,
           shareable=True, capsule_commitment=None):
    candidate = {"id": cid, "version": "1", "creator": CREATOR, "scope": [SCOPE],
                 "components": components or ["typed-compiler"], "dependencies": dependencies or [],
                 "shareable": shareable, "sanitized": True, "valid_until": 18,
                 "capsule_commitment": capsule_commitment or digest({"synthetic_payload": cid}),
                 "model_config": {"reasoner": "gpt-6-astra", "executor": "gpt-6.1-terra",
                                  "basis": "SIMULATED_USAGE_NO_MODEL_CALL"},
                 "origin": {"kind": "separate_research", "campaign_id": "synthetic-research-" + cid,
                            "ledger_receipt_id": "sim-research-paid-" + cid,
                            "construction_cost_already_charged": 40.0, "basis": "SIMULATED_LEDGER_RECEIPT"},
                 "knowledge_boundary": {"client_data_removed": True, "restricted_third_party_removed": True,
                                        "evaluation_cases_removed": True, "scorer_internals_removed": True,
                                        "heldout_overlap_check_passed": True}}
    observations = [{"case_id": f"{cid}-heldout-{i}", "scope": SCOPE,
                      "beta_version": graph.beta_version, "candidate_net_value": 100 + gain,
                      "beta_net_value": 100.0, "equivalent_net_values": [98.0],
                      "component_test_passed": True, "acceptance_unit": "component_test",
                      "project_value_basis": "MODEL_EXTRAPOLATION_FROM_COMPONENT_TESTS",
                      "evidence_basis": "SIMULATED_PAIRED_ASSESSMENT"}
                     for i, gain in enumerate(gains if gains is not None else [20.0, 16.0, 12.0, 28.0])]
    evidence = {"evidence_hash": digest(observations), "observed_month": month,
                "paid_receipt_id": f"sim-paid-assessment-{cid}-{month}", "paid_amount": 40.0,
                "payment_basis": "SIMULATED_LEDGER_RECEIPT", "beta_qualified": True,
                "equivalents_checked": True, "independent_checks_passed": True,
                "evidence_basis": "SIMULATED_PAIRED_ASSESSMENT",
                "sanitization_receipt_id": "sim-sanitization-" + cid,
                "sanitization_basis": "SIMULATED_SANITIZATION_CHECK"}
    if len(candidate["components"]) > 1 or candidate["dependencies"]:
        evidence.update(composition_checks_passed=True,
                        composition_receipt_id=f"sim-composition-{cid}-{month}",
                        dependency_manifest_hash=digest(candidate["dependencies"]))
    costs = {"sunk_construction": 40.0, "sunk_assessment": 40.0, "job_delivery_excluded": 0.0,
             **{key: 3.0 for key in REMAINING_COSTS}}
    forecast = {"expected_uses": 50.0, "recipients_missing_equivalent": 2,
                "basis": "ASSUMED_FROM_OBSERVED_STATE", "forecast_id": f"forecast-{cid}-{month}"}
    return candidate, evidence, observations, costs, forecast


def build(graph, actors, **kwargs):
    candidate, evidence, obs, costs, forecast = inputs(graph, **kwargs)
    result = create_assessed_record(graph, candidate, evidence, obs, costs, forecast, actors, kwargs.get("month", 0))
    return result


def capture(case_id, name, graph, assertions, extra_steps=None):
    TRACES.append({"id": case_id, "name": name, "passed": True,
                   "steps": graph.events + (extra_steps or []), "assertions": assertions,
                   "limitations": ["Synthetic agent names are local authentication/role fixtures, not real reviewers or ENS ownership.",
                                   "Paired values and reuse forecasts are simulation inputs, not frontier or sales measurements."]})


class GraphLifecycleTests(unittest.TestCase):
    def test_01_positive_lifecycle_and_network_reuse(self):
        graph, actors = fixture()
        result = build(graph, actors)
        self.assertTrue(result["admitted"])
        self.assertEqual([e["after"] for e in result["stages"]],
                         ["CANDIDATE", "EVIDENCED", "ALPHA_ASSESSED", "VALIDATED", "ADMITTED"])
        self.assertTrue(graph.use("method-1", MEMBER, SCOPE, 1, "acquire", {"compatible": True, "already_equivalent": False})["allowed"])
        self.assertTrue(graph.use("method-1", MEMBER, SCOPE, 1)["allowed"])
        self.assertEqual(len(graph.discover(MEMBER, SCOPE, 1)), 1)
        assessment = result["record"]["assessment"]
        self.assertGreater(assessment["expected_prospective_net_alpha"], 0)
        self.assertGreater(assessment["full_cycle_expected_net_alpha"], 0)
        c, e, o, costs, f = inputs(graph, month=1)
        costs["sunk_construction"] = 2000.0
        retained = reassess_record(graph, "method-1", e, o, costs, f, actors, 1)
        self.assertTrue(retained["admitted"])
        self.assertLess(retained["record"]["assessment"]["full_cycle_expected_net_alpha"], 0)
        self.assertEqual(retained["record"]["assessment"]["gate_context"], "retention_reassessment")
        capture("positive-residual-alpha", "Positive incremental Alpha admission and retention preserve separate historical cost", graph,
                ["All five lifecycle stages executed.", "A different authenticated member discovered and used the shareable capability.",
                 "Remaining incremental costs determine admission.", "Construction-inclusive residual forecast may remain negative; actual historical recovery requires the separate cash ledger."])

    def test_02_redundant_candidate_and_nonpositive_economics(self):
        graph, actors = fixture()
        c, e, o, costs, f = inputs(graph)
        for obs in o:
            obs["equivalent_net_values"] = [obs["candidate_net_value"]]
        result = create_assessed_record(graph, c, e, o, costs, f, actors, 0)
        self.assertFalse(result["admitted"])
        self.assertIn("no_evidence_conditioned_incremental_advantage", result["record"]["assessment"]["reasons"])
        c, e, o, costs, f = inputs(graph, cid="costly")
        costs["remaining_maintenance"] = 100000
        self.assertFalse(create_assessed_record(graph, c, e, o, costs, f, actors, 0)["admitted"])
        c, e, o, costs, f = inputs(graph, cid="unrecovered-initial")
        costs["sunk_construction"] = 2000.0
        r = create_assessed_record(graph, c, e, o, costs, f, actors, 0)
        self.assertGreater(r["record"]["assessment"]["expected_prospective_net_alpha"], 0)
        self.assertTrue(r["admitted"])
        self.assertLess(r["record"]["assessment"]["construction_inclusive_residual_forecast"], 0)
        self.assertTrue(reassess_record(graph, c["id"], e, o, costs, f, actors, 0)["admitted"])
        c, e, o, costs, f = inputs(graph, cid="no-recipient")
        f["recipients_missing_equivalent"] = 0
        self.assertFalse(create_assessed_record(graph, c, e, o, costs, f, actors, 0)["admitted"])
        capture("redundancy-and-net-cost", "Best competent equivalent, remaining costs and absent eligible recipients can reject Alpha", graph,
                ["Equal available equivalent produces zero incremental advantage.", "Remaining costs can eliminate positive gross benefit.",
                 "No unserved recipient means no reusable Alpha admission.",
                 "Already charged construction is separately visible and is not charged again by the residual admission gate."])

    def test_03_uncertainty_reported_not_extra_hurdle(self):
        graph, actors = fixture()
        c, e, o, costs, f = inputs(graph, gains=[-100.0, 104.0])
        f["expected_uses"] = 100.0
        costs["sunk_construction"] = 5.0
        costs["sunk_assessment"] = 5.0
        result = create_assessed_record(graph, c, e, o, costs, f, actors, 0)
        a = result["record"]["assessment"]
        self.assertTrue(result["admitted"])
        self.assertLess(a["descriptive_net_interval_95"][0], 0)
        self.assertEqual(a["raw_paired_cases"], 2)
        self.assertEqual(a["prior_effective_cases"], 8)
        self.assertAlmostEqual(a["posterior_expected_gain_per_use"], 0.4)
        capture("uncertain-positive-expectation", "Positive posterior expectation with explicit unresolved downside", graph,
                ["Two performed synthetic observations remain two; eight prior pseudo-cases are not counted as tests.",
                 "Negative interval endpoint remains visible; it is not an unapproved admission hurdle."])

    def test_04_exact_direct_names_and_authentication(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors)["admitted"])
        spoofed = ["x.recipient.agent.agi.eth", "recipient.agent.agi.eth.attacker", "recipient.club.agi.eth",
                   "recipient.agent.agi.eth\n", "Recipient.agent.agi.eth", "unknown.agent.agi.eth"]
        for name in spoofed:
            self.assertFalse(graph.use("method-1", name, SCOPE, 1)["allowed"])
        capture("direct-name-access", "Nested names, lookalikes, unrelated roles and missing authentication rejected", graph,
                ["Exact direct ASCII name syntax is required.", "A syntactically valid name still needs a simulated authenticated registry receipt.",
                 "No substring or nested-label authority inheritance."])

    def test_05_roles_and_canonical_no_bypass(self):
        graph, actors = fixture(); c, e, o, costs, f = inputs(graph)
        self.assertFalse(graph.propose(c, CREATOR, 0)["allowed"])
        self.assertTrue(graph.propose(c, actors["writer"], 0)["allowed"])
        self.assertFalse(graph.promote_canonical(c["id"], actors["admission"], 0)["allowed"])
        self.assertFalse(graph.admit(c["id"], actors["admission"], 0)["allowed"])
        e.update(candidate_commitment=graph.snapshot(c["id"])["commitment"], observations_hash=digest(o),
                 beta_version=graph.beta_version, policy_hash=graph.policy_hash,
                 origin_receipt_hash=digest(c["origin"]))
        self.assertFalse(graph.attach_evidence(c["id"], e, MEMBER, 0)["allowed"])
        self.assertTrue(graph.attach_evidence(c["id"], e, actors["writer"], 0)["allowed"])
        self.assertFalse(graph.assess(c["id"], o, costs, f, actors["writer"], 0)["allowed"])
        self.assertTrue(graph.assess(c["id"], o, costs, f, actors["assessor"], 0)["allowed"])
        att = graph.make_attestation(c["id"], actors["validator"], 0)
        self.assertTrue(graph.validate(c["id"], [att], actors["validator"], 0)["allowed"])
        self.assertFalse(graph.admit(c["id"], actors["writer"], 0)["allowed"])
        self.assertTrue(graph.admit(c["id"], actors["admission"], 0)["allowed"])
        capture("authority-separation", "Creation, writing, assessment, validation, admission and execution are distinct", graph,
                ["Creator identity does not grant record-writing authority.", "Writer does not automatically assess, validate or admit.",
                 "Canonical promotion and direct admission cannot skip the validated lifecycle."])

    def test_06_stale_evidence_and_paid_reassessment(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors)["admitted"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 6)["allowed"])
        c, e, o, costs, f = inputs(graph, month=6)
        commitment = graph.snapshot("method-1")["commitment"]
        r = reassess_record(graph, "method-1", e, o, costs, f, actors, 6)
        self.assertTrue(r["admitted"])
        self.assertEqual(r["record"]["commitment"], commitment)
        self.assertEqual(r["record"]["generation"], 2)
        self.assertTrue(graph.use("method-1", MEMBER, SCOPE, 6)["allowed"])
        e["observed_month"] = 0
        self.assertFalse(reassess_record(graph, "method-1", e, o, costs, f, actors, 7)["admitted"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 7)["allowed"])
        capture("freshness-and-reassessment", "Expired evidence requires a new paid assessment and validation generation", graph,
                ["Record lifetime alone cannot keep stale evidence usable.", "Fresh paid evidence restores the same immutable payload only through all gates.",
                 "A failed refresh withdraws current influence."])

    def test_07_moving_beta_and_no_history_resurrection(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors)["admitted"])
        self.assertTrue(graph.promote_canonical("method-1", actors["admission"], 0)["allowed"])
        old_snapshot = graph.snapshot("method-1"); old_history = graph.events
        self.assertTrue(graph.beta_update("beta-2", actors["governance"], 2)["allowed"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 2)["allowed"])
        self.assertIsNone(graph.canonical_for(MEMBER, SCOPE, 2))
        old_snapshot["status"] = "ADMITTED"; old_history[-1]["after"] = "ADMITTED"
        self.assertEqual(graph.snapshot("method-1")["status"], "STALE")
        c, e, o, costs, f = inputs(graph, month=2, gains=[0.0] * 4)
        r = reassess_record(graph, "method-1", e, o, costs, f, actors, 2)
        self.assertFalse(r["admitted"])
        self.assertFalse(graph.promote_canonical("method-1", actors["admission"], 2)["allowed"])
        capture("moving-beta", "An improved Beta can erase Alpha; old admitted history cannot restore it", graph,
                ["Beta update immediately makes previous assessments stale.", "Fresh equivalent-Beta outcomes yield rejection.",
                 "Snapshots, canonical pointers and old event entries are never executable authority."])

    def test_08_policy_version_binding(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors)["admitted"])
        old_policy_hash = graph.policy_hash
        graph.policy["validator_quorum"] = 0
        graph.registry[MEMBER]["roles"].append("admission")
        self.assertEqual(graph.policy["validator_quorum"], 1)
        self.assertNotIn("admission", graph.registry[MEMBER]["roles"])
        with self.assertRaises(AttributeError):
            graph.policy_hash = "0" * 64
        with self.assertRaises(AttributeError):
            graph.beta_version = "unversioned-override"
        policy = copy.deepcopy(graph.policy); policy["version"] = "policy-2"
        self.assertFalse(graph.update_policy(policy, MEMBER, 2)["allowed"])
        self.assertEqual(graph.policy_hash, old_policy_hash)
        self.assertTrue(graph.update_policy(policy, actors["governance"], 2)["allowed"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 2)["allowed"])
        self.assertFalse(graph.promote_canonical("method-1", actors["admission"], 2)["allowed"])
        c, e, o, costs, f = inputs(graph, month=2)
        self.assertTrue(reassess_record(graph, "method-1", e, o, costs, f, actors, 2)["admitted"])
        self.assertNotEqual(graph.snapshot("method-1")["policy_hash"], old_policy_hash)
        capture("policy-version", "Policy revisions invalidate old admission until fresh bound evidence is assessed", graph,
                ["An authenticated ordinary member cannot revise policy.", "A version update invalidates old current influence.",
                 "Fresh revalidation binds the new policy hash.",
                 "Public policy/registry snapshots cannot mutate current authority; version identifiers are read-only."])

    def test_09_revocation_retirement_and_clock(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors)["admitted"])
        self.assertTrue(graph.promote_canonical("method-1", actors["admission"], 0)["allowed"])
        self.assertTrue(graph.use("method-1", MEMBER, SCOPE, 3)["allowed"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 2)["allowed"])
        self.assertTrue(graph.revoke("method-1", actors["governance"], 3, "observed failure")["allowed"])
        c, e, o, costs, f = inputs(graph, month=3)
        self.assertFalse(reassess_record(graph, "method-1", e, o, costs, f, actors, 3)["admitted"])
        self.assertFalse(graph.promote_canonical("method-1", actors["admission"], 3)["allowed"])
        self.assertIsNone(graph.canonical_for(MEMBER, SCOPE, 3))
        self.assertEqual(graph.discover(MEMBER, SCOPE, 3), [])
        self.assertTrue(build(graph, actors, cid="retirement", month=3)["admitted"])
        self.assertTrue(graph.revoke("retirement", actors["writer"], 3, "end of useful scope", retire=True)["allowed"])
        self.assertFalse(graph.use("retirement", MEMBER, SCOPE, 3)["allowed"])
        capture("terminal-history", "Revocation and retirement permanently remove current influence while preserving history", graph,
                ["Earlier timestamps cannot recover old permissions.", "Terminal records cannot re-enter through reassessment or canonical promotion.",
                 "Authorized writers can retire owned records; history remains readable as evidence only."])

    def test_10_composition_and_transitive_dependency_revocation(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors, cid="base")["admitted"])
        parent = graph.snapshot("base")
        dep = {k: parent[k] for k in ("id", "version", "commitment")}
        c, e, o, costs, f = inputs(graph, cid="composite", components=["compiler", "certificate"], dependencies=[dep])
        e.pop("composition_receipt_id")
        self.assertFalse(create_assessed_record(graph, c, e, o, costs, f, actors, 0)["admitted"])
        c, e, o, costs, f = inputs(graph, cid="composite", components=["compiler", "certificate"], dependencies=[dep])
        self.assertTrue(reassess_record(graph, "composite", e, o, costs, f, actors, 0)["admitted"])
        mid = graph.snapshot("composite")
        dep2 = {k: mid[k] for k in ("id", "version", "commitment")}
        self.assertTrue(build(graph, actors, cid="grandchild", dependencies=[dep2])["admitted"])
        self.assertTrue(graph.use("grandchild", MEMBER, SCOPE, 1, "compose")["allowed"])
        self.assertTrue(graph.revoke("base", actors["governance"], 1, "dependency invalidated")["allowed"])
        self.assertFalse(graph.use("composite", MEMBER, SCOPE, 1)["allowed"])
        self.assertFalse(graph.use("grandchild", MEMBER, SCOPE, 1)["allowed"])
        capture("paid-composition-and-transitive-revocation", "Composition needs its own bound evidence and follows every dependency", graph,
                ["Component validity alone cannot admit a composition without paid composition evidence.",
                 "The third-level composition checks transitive current dependency state.",
                 "Revoking a base dependency blocks downstream use immediately."])

    def test_11_supersession_does_not_silently_rebind_dependencies(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors, cid="old")["admitted"])
        dep = {k: graph.snapshot("old")[k] for k in ("id", "version", "commitment")}
        self.assertTrue(build(graph, actors, cid="dependent", dependencies=[dep])["admitted"])
        self.assertTrue(graph.promote_canonical("old", actors["admission"], 0)["allowed"])
        self.assertTrue(build(graph, actors, cid="replacement")["admitted"])
        self.assertTrue(graph.supersede("old", "replacement", actors["writer"], 1)["allowed"])
        self.assertFalse(graph.use("old", MEMBER, SCOPE, 1)["allowed"])
        self.assertFalse(graph.use("dependent", MEMBER, SCOPE, 1)["allowed"])
        self.assertEqual(graph.canonical_for(MEMBER, SCOPE, 1)["id"], "replacement")
        capture("supersession", "Replacement is admitted first; dependent records must be rebuilt or revalidated explicitly", graph,
                ["Canonical pointer can move only to a currently admitted replacement.",
                 "Existing dependency commitments do not silently resolve to new versions.", "Superseded old records stay unusable."])

    def test_12_private_retention_and_recipient_compatibility(self):
        graph, actors = fixture(); self.assertTrue(build(graph, actors, shareable=False)["admitted"])
        self.assertTrue(graph.use("method-1", CREATOR, SCOPE, 1)["allowed"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 1)["allowed"])
        self.assertEqual(graph.discover(MEMBER, SCOPE, 1), [])
        self.assertTrue(build(graph, actors, cid="shared", month=1)["admitted"])
        self.assertFalse(graph.use("shared", MEMBER, "medical", 1)["allowed"])
        self.assertFalse(graph.use("shared", MEMBER, SCOPE, 1, "acquire", {"compatible": False})["allowed"])
        self.assertFalse(graph.use("shared", MEMBER, SCOPE, 1, "acquire", {"compatible": True, "already_equivalent": True})["allowed"])
        parent = graph.snapshot("method-1")
        dep = {k: parent[k] for k in ("id", "version", "commitment")}
        self.assertFalse(build(graph, actors, cid="private-laundering", month=1, dependencies=[dep])["admitted"])
        capture("private-and-compatible", "Private retention stays creator-only; network reuse respects compatibility and equivalence", graph,
                ["Authenticated network membership does not export private retained skills.",
                 "Out-of-scope, incompatible and already-equivalent acquisitions fail.",
                 "A shareable composition cannot launder a private dependency into network access."])

    def test_13_attestation_tampering_and_quorum(self):
        graph, actors = fixture(default_policy(validator_quorum=2))
        second = "local-test-validator-two.agent.agi.eth"
        registry = graph.registry
        registry[second] = copy.deepcopy(registry[actors["validator"]])
        graph = LifecycleGraph(graph.policy, registry, graph.beta_version)
        result = build(graph, actors)
        self.assertFalse(result["admitted"])
        self.assertEqual(result["record"]["status"], "ALPHA_ASSESSED")
        att = graph.make_attestation("method-1", actors["validator"], 0)
        self.assertFalse(graph.validate("method-1", [att, att], actors["validator"], 0)["allowed"])
        att2 = graph.make_attestation("method-1", second, 0)
        tampered = copy.deepcopy(att2); tampered["binding_hash"] = "0" * 64
        self.assertFalse(graph.validate("method-1", [att, tampered], actors["validator"], 0)["allowed"])
        self.assertTrue(graph.validate("method-1", [att, att2], actors["validator"], 0)["allowed"])
        self.assertTrue(graph.admit("method-1", actors["admission"], 0)["allowed"])
        changed = graph.registry[second]; changed["authenticated_simulated"] = False
        self.assertTrue(graph.update_authority(second, changed, actors["governance"], 1)["allowed"])
        self.assertFalse(graph.use("method-1", MEMBER, SCOPE, 1)["allowed"])
        capture("attestation-binding", "Distinct eligible attestations bind exact evidence, Beta and policy versions", graph,
                ["Duplicating one attestation does not create quorum.", "A mismatched attestation hash is rejected.",
                 "Loss of validator eligibility blocks subsequent reuse.", "Multiple fixture identities do not prove statistical independence or truth."])

    def test_14_local_capsule_crypto_and_action_permission(self):
        graph, actors = fixture()
        vault = CapsuleVault({"check_schema": lambda p: {"valid_recipe_schema": "sanitized_recipe" in json.loads(p)}})
        payload = b'{"sanitized_recipe":"typed assignment schema plus certificate checks"}'
        context = {"candidate_id": "method-1", "version": "1", "purpose": "LOCAL_SYNTHETIC_TEST"}
        capsule = vault.put("method-1", payload, context)
        self.assertNotIn("sanitized_recipe", json.dumps(capsule))
        self.assertTrue(build(graph, actors, capsule_commitment=capsule["content_commitment"])["admitted"])
        retrieved = vault.retrieve(graph, "method-1", MEMBER, SCOPE, 1)
        self.assertNotIn("key", retrieved)
        with self.assertRaises(PermissionError):
            vault.execute(graph, "method-1", MEMBER, SCOPE, 1, "check_schema")
        with self.assertRaises(PermissionError):
            vault.execute(graph, "method-1", MEMBER, SCOPE, 1, lambda p: p, True)
        executed = vault.execute(graph, "method-1", MEMBER, SCOPE, 1, "check_schema", True)
        self.assertEqual(executed, {"valid_recipe_schema": True})
        with self.assertRaises(PermissionError):
            vault.export(graph, "method-1", MEMBER, SCOPE, 1)
        direct_capsule, key = seal_capsule(payload, context)
        self.assertEqual(open_capsule(direct_capsule, key, context), payload)
        corrupted = copy.deepcopy(direct_capsule)
        cipher = bytearray(base64.b64decode(corrupted["ciphertext"])); cipher[0] ^= 1
        corrupted["ciphertext"] = base64.b64encode(cipher).decode()
        corrupted["ciphertext_sha256"] = hashlib.sha256(cipher).hexdigest()
        with self.assertRaises(Exception):
            open_capsule(corrupted, key, context)
        with self.assertRaises(Exception):
            open_capsule(direct_capsule, b"x" * 32, context)
        with self.assertRaises(ValueError):
            open_capsule(direct_capsule, key, {**context, "version": "2"})
        capture("local-encrypted-capsule", "Local authenticated encryption, encrypted retrieval and bounded execution", graph,
                ["Actual AES-GCM round trip executed on synthetic bytes.", "Ciphertext tampering remains rejected even after an attacker recomputes its ordinary hash.",
                 "Wrong key and mismatched context fail.", "Member retrieval returns ciphertext without a key; export is denied by default.",
                 "Capability access alone cannot authorize the requested action.",
                 "An arbitrary caller-supplied plaintext-returning callback is rejected; only preinstalled trusted executor IDs are accepted."],
                [{"event": "local_crypto_checks", "allowed": True, "outcome": {"round_trip": True, "tamper_rejected": True,
                  "wrong_key_rejected": True, "wrong_context_rejected": True},
                  "crypto_basis": "ACTUAL_LOCAL_CRYPTOGRAPHY_SYNTHETIC_PAYLOAD_AND_KEY"}])

    def test_15_authorized_export_cannot_be_uncopied(self):
        policy = default_policy(default_export_allowed=True)
        graph, actors = fixture(policy)
        registry = graph.registry; registry[MEMBER]["member_operations"].append("export")
        graph = LifecycleGraph(policy, registry, graph.beta_version)
        vault = CapsuleVault(); payload = b"sanitized reusable method"
        capsule = vault.put("method-1", payload, {"id": "method-1", "version": "1"})
        self.assertTrue(build(graph, actors, capsule_commitment=capsule["content_commitment"])["admitted"])
        exported = vault.export(graph, "method-1", MEMBER, SCOPE, 1)
        self.assertTrue(graph.revoke("method-1", actors["governance"], 1, "retire after export")["allowed"])
        with self.assertRaises(PermissionError):
            vault.export(graph, "method-1", MEMBER, SCOPE, 1)
        self.assertEqual(exported, payload)
        capture("export-copying-limit", "Revocation blocks later access but cannot erase an authorized plaintext export", graph,
                ["Plaintext export required both a policy grant and member-specific permission.",
                 "New export is blocked after revocation.", "The previously authorized copy still exists; authentication cannot prevent copying after release."])


    def test_16_paid_job_cost_not_charged_twice(self):
        graph, actors = fixture(); c, e, o, costs, f = inputs(graph)
        c["origin"] = {"kind": "paid_job", "job_id": "source-job-17",
                       "ledger_receipt_id": "sim-source-job-17-cost", "delivery_cost_already_charged": 5000.0,
                       "outcome_observed": "validated_pass", "basis": "SIMULATED_LEDGER_RECEIPT"}
        costs.update(sunk_construction=0.0, sunk_assessment=40.0, job_delivery_excluded=5000.0)
        result = create_assessed_record(graph, c, e, o, costs, f, actors, 0)
        self.assertTrue(result["admitted"])
        a = result["record"]["assessment"]
        self.assertEqual(a["job_delivery_cost_excluded_from_incremental_gate"], 5000)
        self.assertEqual(a["expected_net_alpha_for_gate"], a["expected_prospective_net_alpha"])
        self.assertLess(a["expected_prospective_net_alpha"] - 5000, 0)
        c2, e2, o2, cost2, f2 = inputs(graph, cid="mismatched-cost-origin")
        c2["origin"] = copy.deepcopy(c["origin"])
        self.assertFalse(create_assessed_record(graph, c2, e2, o2, cost2, f2, actors, 0)["admitted"])
        c3, e3, o3, cost3, f3 = inputs(graph, cid="latent-source-trigger")
        c3["origin"] = {**c["origin"], "outcome_observed": "true_accepted"}
        self.assertFalse(create_assessed_record(graph, c3, e3, o3, cost3, f3, actors, 0)["admitted"])
        capture("job-cost-once", "Paid job provenance is bound while already charged delivery is excluded from the incremental gate", graph,
                ["The source job has a simulated ledger receipt and an observable validated-pass status, not latent truth.",
                 "The $5,000 already charged source-job cost is disclosed and excluded, not charged again.",
                 "A mismatched exclusion or an oracle-labelled true-accepted trigger is rejected."])

    def test_17_protected_proof_plane_not_shared(self):
        graph, actors = fixture(); c, e, o, costs, f = inputs(graph)
        c["knowledge_boundary"]["evaluation_cases_removed"] = False
        self.assertFalse(create_assessed_record(graph, c, e, o, costs, f, actors, 0)["admitted"])
        c["knowledge_boundary"]["evaluation_cases_removed"] = True
        c["knowledge_boundary"]["scorer_internals_removed"] = False
        self.assertFalse(create_assessed_record(graph, c, e, o, costs, f, actors, 0)["admitted"])
        protected = (b"SYNTHETIC-HOLDOUT-CASE-SECRET", b"SYNTHETIC-SCORER-SEED-PRIVATE")
        vault = CapsuleVault(protected_material=protected)
        attempts = 0
        for marker in protected:
            for representation in (marker, base64.b64encode(marker), marker.hex().encode()):
                with self.assertRaises(ValueError):
                    vault.put("leak-" + str(attempts), b"prefix:" + representation, {"synthetic": True})
                attempts += 1
        safe = vault.put("sanitized", b"General method without proof cases or scorer source", {"synthetic": True})
        self.assertTrue(safe["content_commitment"])
        capture("protected-proof-plane", "Shared methods exclude protected test cases and scorer internals", graph,
                ["Explicitly unsanitized proof cases or scorer internals block candidate creation.",
                 "Actual local vault rejected six known protected-marker/encoding leaks before encryption.",
                 "Known-marker checks are bounded; this is not proof of general semantic sanitization or production data-loss prevention."],
                [{"event": "local_protected_material_checks", "allowed": True,
                  "outcome": {"known_leaks_rejected": attempts, "sanitized_payload_sealed": True},
                  "basis": "ACTUAL_LOCAL_BYTE_CHECK_SYNTHETIC_PROTECTED_FIXTURES"}])

    def test_18_failed_approach_memory_is_not_positive_alpha(self):
        graph, actors = fixture(); c, e, o, costs, f = inputs(graph)
        failure = {"id": "failed-route-1", "creator": CREATOR, "scope": [SCOPE], "shareable": True,
                   "valid_until": 10, "origin": c["origin"], "observed_failure_kind": "test_rejection",
                   "description_commitment": digest({"failed_approach": "synthetic wrong constraint"}),
                   "evidence_hash": digest({"observed": "rejected"}), "knowledge_boundary": c["knowledge_boundary"]}
        self.assertFalse(graph.record_failure(failure, MEMBER, 0)["allowed"])
        self.assertTrue(graph.record_failure(failure, actors["writer"], 0)["allowed"])
        self.assertEqual(graph.discover(MEMBER, SCOPE, 0), [])
        self.assertFalse(graph.promote_canonical(failure["id"], actors["admission"], 0)["allowed"])
        self.assertFalse(graph.use(failure["id"], MEMBER, SCOPE, 0)["allowed"])
        self.assertFalse(graph.consult_failures(MEMBER, SCOPE, 1, {})["allowed"])
        receipt = {"basis": "SIMULATED_LEDGER_RECEIPT", "ledger_receipt_id": "sim-retrieval-1", "paid_amount": 2.5}
        review = graph.consult_failures(MEMBER, SCOPE, 1, receipt)
        self.assertTrue(review["allowed"]); self.assertEqual(len(review["failures"]), 1)
        self.assertFalse(review["failures"][0]["positive_alpha"])
        self.assertEqual(graph.consult_failures(MEMBER, "unrelated-scope", 1, receipt)["failures"], [])
        c["id"] = failure["id"]
        self.assertFalse(graph.propose(c, actors["writer"], 1)["allowed"])
        graph.beta_update("beta-2", actors["governance"], 2)
        self.assertEqual(graph.consult_failures(MEMBER, SCOPE, 2, receipt)["failures"], [])
        self.assertEqual(len(graph.failure_memory), 1)
        capture("failure-memory-separation", "Failed approaches remain scoped paid advisory memory, never admitted positive capability", graph,
                ["Failure records cannot enter positive discovery, canonical promotion or execution.",
                 "Consulting them requires an explicit paid retrieval receipt; no automatic performance bonus exists.",
                 "Scope and current Beta still gate consultation; stale history remains auditable but has no influence."])


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GraphLifecycleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    source = ROOT / "sim" / "graph_lifecycle_v3.py"
    report = {"schema": "paid-job-alpha-lifecycle-audit/v3", "passed": result.wasSuccessful(),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "basis": "LOCAL_EXECUTED_POLICY_TESTS_WITH_SYNTHETIC_IDENTITIES_AND_ASSESSMENTS",
              "actual_crypto": "AES-256-GCM and SHA-256 on synthetic local bytes; no keys are exported.",
              "not_tested": ["Real ENS ownership", "wallet signatures", "Ethereum or ZK proofs", "production key custody",
                             "frontier model performance", "real commercial Alpha", "production isolation"],
              "failure_details": [{"test": str(t), "traceback": tb} for t, tb in result.failures + result.errors]}
    (ROOT / "qa").mkdir(exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "qa" / "graph_lifecycle_v3_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "results" / "graph_lifecycle_v3_cases.json").write_text(json.dumps({
        "schema": "paid-job-alpha-lifecycle-traces/v3", "basis": report["basis"],
        "source_sha256": report["source_sha256"], "audit": report, "cases": TRACES}, indent=2) + "\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
