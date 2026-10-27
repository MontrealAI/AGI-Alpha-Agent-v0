# SPDX-License-Identifier: Apache-2.0
"""Adversarial lifecycle tests; fixture verdicts are not empirical invention evidence."""

from __future__ import annotations

import dataclasses
import json
import unittest

from src.skill_graph import (
    AlphaCosts, Dependency, Evidence, FixtureDirectory, GraphError, Policy, Principal, Session,
    direct_agent, digest, fixture_alpha, fixture_beta, fixture_evidence, fixture_graph, merkle_proof, merkle_root,
    run_graph_demo, verify_inclusion,
)


class LifecycleTests(unittest.TestCase):
    """Check public API refusals and freshness at the eventual use boundary."""

    def setUp(self) -> None:
        self.graph, self.actors = fixture_graph()
        self.scope = "finite-quasilinear-types"
        self.tools = ("python-3.12",)

    def candidate(self, skill_id: str = "s1", **kwargs):
        return self.graph.create_candidate(
            self.actors["inventor"], skill_id, ("private synthetic " + skill_id).encode(),
            "mechanism", (self.scope,), prerequisites=self.tools, **kwargs,
        )

    def evidence(self, manifest, now: int = 1, assess: bool = True, **changes) -> Evidence:
        evidence = dataclasses.replace(fixture_evidence(manifest, self.graph.policy, now), **changes)
        self.graph.submit_evidence(self.actors["inventor"], manifest.skill_id, evidence, now)
        if assess:
            self.graph.assess_alpha(self.actors["inventor"], manifest.skill_id,
                                    fixture_alpha(self.graph, self.actors["inventor"], manifest, now), now)
        return evidence

    def attest(self, manifest, now: int = 1, verdict: str = "supported") -> None:
        for name in ("validator-a", "validator-b"):
            attestation = self.graph.sign_attestation(self.actors[name], manifest.skill_id, verdict, now, now + 8)
            self.graph.attach_attestation(self.actors[name], attestation, now)

    def admitted(self, skill_id: str = "s1", now: int = 1, **kwargs):
        manifest = self.candidate(skill_id, now=now, **kwargs)
        self.evidence(manifest, now)
        self.attest(manifest, now)
        self.graph.validate(self.actors["validator-a"], skill_id, now)
        self.graph.admit(self.actors["admitter"], skill_id, now)
        return manifest

    def test_direct_child_and_exact_owner_are_both_required(self) -> None:
        for invalid in ("x.y.agent.agi.eth", "agent.agi.eth", "foo.club.agi.eth", "FOO.agent.agi.eth",
                        "foo.agent.agi.eth.evil", "foo.agent.agi.eth\n", "-foo.agent.agi.eth"):
            with self.subTest(invalid=invalid):
                self.assertFalse(direct_agent(invalid))
                with self.assertRaises(GraphError):
                    FixtureDirectory((Principal(invalid, "fixture:one"),))
        self.assertTrue(direct_agent("legitimate.agent.agi.eth"))
        with self.assertRaises(GraphError):
            self.graph.directory.open_session("inventor.agent.agi.eth", "wrong-owner")
        with self.assertRaises(GraphError):
            self.graph.directory.open_session("unknown.agent.agi.eth", "fixture-wallet:inventor")

    def test_forged_session_does_not_authenticate(self) -> None:
        genuine = self.actors["inventor"]
        forged = Session(genuine.name, genuine.fixture_wallet, genuine.issued_at)
        with self.assertRaises(GraphError):
            self.graph.discover(forged, 999999)
        self.assertEqual(self.graph.discover(genuine, 0), ())
        with self.assertRaises(GraphError):
            self.graph.create_candidate(forged, "s1", b"x", "mechanism", (self.scope,))

    def test_roles_cannot_write_or_admit_each_others_records(self) -> None:
        manifest = self.candidate()
        with self.assertRaises(GraphError):
            self.graph.create_candidate(self.actors["validator-a"], "s2", b"x", "mechanism", (self.scope,))
        with self.assertRaises(GraphError):
            self.graph.submit_evidence(self.actors["admitter"], "s1", fixture_evidence(manifest, self.graph.policy), 1)
        self.evidence(manifest)
        self.attest(manifest)
        self.graph.validate(self.actors["validator-a"], "s1", 1)
        with self.assertRaises(GraphError):
            self.graph.admit(self.actors["validator-a"], "s1", 1)

    def test_candidate_and_validated_are_not_admitted(self) -> None:
        manifest = self.candidate()
        with self.assertRaises(GraphError):
            self.graph.admit(self.actors["admitter"], "s1", 0)
        with self.assertRaises(GraphError):
            self.graph.promote_canonical(self.actors["admitter"], "s1", 0)
        self.evidence(manifest)
        self.attest(manifest)
        self.graph.validate(self.actors["validator-a"], "s1", 1)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 1), ())
        with self.assertRaises(GraphError):
            self.graph.promote_canonical(self.actors["admitter"], "s1", 1)
        self.graph.admit(self.actors["admitter"], "s1", 1)
        self.graph.promote_canonical(self.actors["admitter"], "s1", 1)
        self.assertTrue(self.graph.discover(self.actors["recipient-a"], 1)[0]["canonical"])

    def test_bad_evidence_or_adverse_attestation_is_refused(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest, failed_cases=1)
        self.attest(manifest)
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 1)
        self.evidence(manifest, now=2)
        self.attest(manifest, now=2, verdict="blocked")
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 2)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())

    def test_no_measured_benefit_never_becomes_capability_evidence(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest, benefit=0.0)
        self.attest(manifest)
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 1)

    def test_attestations_bind_content_policy_scope_and_evidence(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest)
        attestation = self.graph.sign_attestation(self.actors["validator-a"], "s1", "supported", 1, 9)
        for changes in ({"signature": "00" * 64}, {"evidence_hash": "0" * 64},
                        {"policy_hash": "0" * 64}, {"verdict": "blocked"}, {"manifest_hash": "0" * 64},
                        {"alpha_hash": "0" * 64}):
            with self.subTest(changes=changes), self.assertRaises(GraphError):
                self.graph.attach_attestation(
                    self.actors["validator-a"], dataclasses.replace(attestation, **changes), 1,
                )
        with self.assertRaises(GraphError):
            self.graph.attach_attestation(self.actors["validator-b"], attestation, 1)

    def test_duplicate_validator_does_not_make_quorum(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest)
        attestation = self.graph.sign_attestation(self.actors["validator-a"], "s1", "supported", 1, 9)
        self.graph.attach_attestation(self.actors["validator-a"], attestation, 1)
        self.graph.attach_attestation(self.actors["validator-a"], attestation, 1)
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 1)

    def test_self_validation_rejected_even_if_creator_has_validator_role(self) -> None:
        directory = FixtureDirectory((Principal("a.agent.agi.eth", "fixture:a",
                                                frozenset({"record.write", "graph.validate"})),))
        graph = type(self.graph)(directory)
        actor = directory.open_session("a.agent.agi.eth", "fixture:a")
        manifest = graph.create_candidate(actor, "s1", b"x", "mechanism", (self.scope,))
        graph.submit_evidence(actor, "s1", fixture_evidence(manifest, graph.policy), 1)
        graph.assess_alpha(actor, "s1", fixture_alpha(graph, actor, manifest, 1), 1)
        with self.assertRaises(GraphError):
            graph.sign_attestation(actor, "s1", "supported", 1, 9)

    def test_every_member_can_discover_inspect_and_export(self) -> None:
        manifest = self.admitted()
        for actor in self.actors.values():
            found = self.graph.discover(actor, 2)
            self.assertEqual([row["skill_id"] for row in found], [manifest.skill_id])
            self.assertEqual(self.graph.retrieve(actor, "s1", 2), b"private synthetic s1")
        with self.assertRaises(GraphError):
            self.graph.authorize_reuse(self.actors["recipient-b"], "s1", self.scope, self.tools, 2)
        selected = self.graph.select(self.actors["recipient-b"], "mechanism", self.scope, self.tools, 2)
        self.assertEqual(selected, ("s1",))

    def test_scope_and_prerequisites_are_required_at_reuse(self) -> None:
        self.admitted()
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", "wrong", self.tools, 2), ())
        with self.assertRaises(GraphError):
            self.graph.authorize_reuse(self.actors["recipient-a"], "s1", self.scope, (), 2)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ("s1",))

    def test_network_restriction_and_shareability_not_narrowed(self) -> None:
        manifest = self.candidate(reuse_rights="preferred-subgroup")
        self.evidence(manifest)
        self.attest(manifest)
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 1)
        self.graph.directory.disable_fixture(self.actors["recipient-a"].name)
        with self.assertRaises(GraphError):
            self.graph.discover(self.actors["recipient-a"], 1)

    def test_unsanitized_material_cannot_be_admitted(self) -> None:
        manifest = self.candidate(sanitized=False)
        self.evidence(manifest)
        self.attest(manifest)
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 1)

    def test_revoked_and_retired_versions_cannot_return(self) -> None:
        for status in ("revoked", "retired"):
            with self.subTest(status=status):
                self.setUp()
                manifest = self.admitted()
                self.graph.terminate(self.actors["inventor"], "s1", status, "test counterexample", 2)
                self.assertEqual(
                    self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), (),
                )
                with self.assertRaises(GraphError):
                    self.graph.promote_canonical(self.actors["admitter"], "s1", 2)
                with self.assertRaises(GraphError):
                    self.evidence(manifest, now=2)
                with self.assertRaises(GraphError):
                    self.graph.retrieve(self.actors["recipient-a"], "s1", 2)
                with self.assertRaises(GraphError):
                    self.candidate(now=2)

    def test_stale_evidence_and_attestations_stop_future_selection(self) -> None:
        self.admitted()
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 10), ())
        with self.assertRaises(GraphError):
            self.graph.retrieve(self.actors["recipient-a"], "s1", 10)
        with self.assertRaises(GraphError):
            self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2)

    def test_policy_change_requires_fresh_validation(self) -> None:
        manifest = self.admitted()
        self.graph.set_policy(self.actors["admitter"], Policy(version="v2", min_cases=12), 2)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())
        with self.assertRaises(GraphError):
            self.graph.promote_canonical(self.actors["admitter"], "s1", 2)
        self.evidence(manifest, now=2)
        self.attest(manifest, now=2)
        self.graph.validate(self.actors["validator-a"], "s1", 2)
        self.graph.admit(self.actors["admitter"], "s1", 2)
        self.assertEqual(len(self.graph.discover(self.actors["recipient-a"], 2)), 1)
        with self.assertRaises(GraphError):
            self.graph.set_policy(self.actors["admitter"], Policy(), 3)

    def test_evidence_revision_invalidates_prior_attestations_and_admission(self) -> None:
        manifest = self.admitted()
        self.evidence(manifest, now=2)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 2)

    def test_revoked_dependency_invalidates_composed_skill(self) -> None:
        base = self.admitted()
        self.admitted("bundle", dependencies=(Dependency("s1", base.hash),))
        permit = self.graph.authorize_reuse(self.actors["recipient-a"], "bundle", self.scope, self.tools, 2)
        self.graph.terminate(self.actors["inventor"], "s1", "revoked", "dependency defect", 2)
        with self.assertRaises(GraphError):
            self.graph.consume_reuse(self.actors["recipient-a"], permit, 2)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ())

    def test_dependency_pin_mismatch_fails_before_creation(self) -> None:
        self.admitted()
        with self.assertRaises(GraphError):
            self.candidate("bundle", dependencies=(Dependency("s1", "0" * 64),), now=1)

    def test_supersession_requires_admitted_independent_new_version(self) -> None:
        self.admitted()
        newer = self.candidate("s2", version=2, now=1)
        with self.assertRaises(GraphError):
            self.graph.supersede(self.actors["inventor"], "s1", "s2", 1)
        self.evidence(newer)
        self.attest(newer)
        self.graph.validate(self.actors["validator-a"], "s2", 1)
        self.graph.admit(self.actors["admitter"], "s2", 1)
        self.graph.supersede(self.actors["inventor"], "s1", "s2", 2)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ("s2",))

    def test_supersession_cannot_break_replacement_dependency(self) -> None:
        base = self.admitted()
        self.admitted("s2", version=2, dependencies=(Dependency("s1", base.hash),))
        with self.assertRaises(GraphError):
            self.graph.supersede(self.actors["inventor"], "s1", "s2", 2)

    def test_permit_is_one_use_and_checked_after_membership_change(self) -> None:
        self.admitted()
        permit = self.graph.authorize_reuse(self.actors["recipient-a"], "s1", self.scope, self.tools, 2)
        receipt = self.graph.consume_reuse(self.actors["recipient-a"], permit, 2)
        self.assertFalse(receipt["code_executed"])
        with self.assertRaises(GraphError):
            self.graph.consume_reuse(self.actors["recipient-a"], permit, 2)
        permit = self.graph.authorize_reuse(self.actors["recipient-a"], "s1", self.scope, self.tools, 2)
        self.graph.directory.disable_fixture(self.actors["recipient-a"].name)
        with self.assertRaises(GraphError):
            self.graph.consume_reuse(self.actors["recipient-a"], permit, 2)

    def test_lost_validator_eligibility_invalidates_reuse(self) -> None:
        self.admitted()
        self.graph.directory.disable_fixture(self.actors["validator-a"].name)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())

    def test_capsule_tamper_is_detected(self) -> None:
        self.admitted()
        self.graph._records["s1"].ciphertext += b"bad"
        with self.assertRaises(GraphError):
            self.graph.retrieve(self.actors["recipient-a"], "s1", 2)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ())

    def test_public_roots_do_not_export_private_content_and_snapshots_are_copies(self) -> None:
        self.admitted()
        public = self.graph.public_commitment()
        self.assertNotIn("private synthetic", json.dumps(public))
        public["roots"]["skills"] = "bad"
        self.assertNotEqual(self.graph.public_commitment()["roots"]["skills"], "bad")
        found = self.graph.discover(self.actors["recipient-a"], 2)
        found[0]["status"] = "revoked"
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2)[0]["status"], "admitted")

    def test_inclusion_is_not_admission_or_truth(self) -> None:
        self.candidate()
        proof = self.graph.inclusion(self.actors["recipient-a"], "s1")
        self.assertTrue(verify_inclusion(proof["leaf"], proof["proof"], proof["root"]))
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 0), ())
        self.assertNotEqual(digest("evidence", {"a": 1}), digest("manifest", {"a": 1}))
        leaves = [digest("leaf", i) for i in range(5)]
        root = merkle_root(leaves)
        for leaf in leaves:
            self.assertTrue(verify_inclusion(leaf, merkle_proof(leaves, leaf), root))
            self.assertFalse(verify_inclusion("0" * 64, merkle_proof(leaves, leaf), root))

    def test_malformed_evidence_cannot_smuggle_unbounded_or_nonfinite_claims(self) -> None:
        manifest = self.candidate()
        evidence = fixture_evidence(manifest, self.graph.policy)
        for changes in ({"benefit": float("nan")}, {"cases": -1}, {"replay_hash": "replay://available"},
                        {"expires_at": 0}, {"observed_at": True}):
            with self.subTest(changes=changes), self.assertRaises(GraphError):
                dataclasses.replace(evidence, **changes)

    def test_alpha_stage_cannot_be_bypassed_by_valid_evidence_or_crypto(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest, assess=False)
        proof = self.graph.inclusion(self.actors["recipient-a"], "s1")
        self.assertTrue(verify_inclusion(proof["leaf"], proof["proof"], proof["root"]))
        with self.assertRaises(GraphError):
            self.attest(manifest)
        with self.assertRaises(GraphError):
            self.graph.validate(self.actors["validator-a"], "s1", 1)
        with self.assertRaises(GraphError):
            self.graph.admit(self.actors["admitter"], "s1", 1)

    def test_full_cost_and_redundancy_alpha_rejections(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest, assess=False)
        base = fixture_alpha(self.graph, self.actors["inventor"], manifest, 1)
        for changes in ({"costs": AlphaCosts(construction=1001)}, {"redundant": True}):
            with self.subTest(changes=changes):
                outcome = self.graph.assess_alpha(self.actors["inventor"], "s1",
                                                  dataclasses.replace(base, **changes), 1)
                self.assertFalse(outcome["accepted"])
                with self.assertRaises(GraphError):
                    self.attest(manifest)
                self.assertEqual(self.graph.discover(self.actors["recipient-a"], 1), ())

    def test_alpha_binds_current_beta_scope_comparator_and_evidence(self) -> None:
        manifest = self.candidate()
        self.evidence(manifest, assess=False)
        base = fixture_alpha(self.graph, self.actors["inventor"], manifest, 1)
        for changes in ({"beta_id": "older-beta-v0"}, {"scope": ("different-scope",)},
                        {"evidence_hash": "0" * 64}, {"comparator_capability_set_hash": "0" * 64},
                        {"dependency_hashes": ("1" * 64,)}):
            with self.subTest(changes=changes), self.assertRaises(GraphError):
                self.graph.assess_alpha(self.actors["inventor"], "s1", dataclasses.replace(base, **changes), 1)

    def test_comparator_includes_newly_available_capability_before_admission(self) -> None:
        first = self.candidate()
        self.evidence(first)
        self.attest(first)
        self.graph.validate(self.actors["validator-a"], "s1", 1)
        second = self.admitted("s2")
        self.assertNotEqual(self.graph.comparator_hash(self.actors["inventor"], "s1", 1),
                            self.graph._records["s1"].alpha.comparator_capability_set_hash)
        with self.assertRaises(GraphError):
            self.graph.admit(self.actors["admitter"], "s1", 1)
        self.evidence(first)
        self.attest(first)
        self.graph.validate(self.actors["validator-a"], "s1", 1)
        self.graph.admit(self.actors["admitter"], "s1", 1)
        self.assertEqual(len(self.graph.discover(self.actors["recipient-a"], 1)), 2)
        self.assertIn(second.hash, self.graph._records["s1"].comparator_snapshot)

    def test_duplicate_current_payload_is_rejected_even_with_positive_claim(self) -> None:
        self.admitted()
        copy = self.graph.create_candidate(self.actors["inventor"], "copy", b"private synthetic s1",
                                          "mechanism", (self.scope,), prerequisites=self.tools, now=1)
        self.evidence(copy, assess=False)
        outcome = self.graph.assess_alpha(self.actors["inventor"], "copy",
                                          fixture_alpha(self.graph, self.actors["inventor"], copy, 1), 1)
        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason"], "duplicate-current-capsule")

    def test_beta_upgrade_invalidates_old_history_permits_and_canonical_status(self) -> None:
        manifest = self.admitted()
        self.graph.promote_canonical(self.actors["admitter"], "s1", 1)
        permit = self.graph.authorize_reuse(self.actors["recipient-a"], "s1", self.scope, self.tools, 2)
        prior = self.graph.assessment_history(self.actors["recipient-a"])
        self.graph.set_beta_baseline(self.actors["admitter"], fixture_beta("competent-beta-fixture-v2"), 2)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ())
        self.assertEqual(self.graph.assessment_history(self.actors["recipient-a"]), prior)
        for operation in (
            lambda: self.graph.consume_reuse(self.actors["recipient-a"], permit, 2),
            lambda: self.graph.promote_canonical(self.actors["admitter"], "s1", 2),
            lambda: self.graph.admit(self.actors["admitter"], "s1", 2),
            lambda: self.graph.set_beta_baseline(self.actors["admitter"], fixture_beta(), 2),
        ):
            with self.assertRaises(GraphError):
                operation()
        self.evidence(manifest, now=2)
        self.attest(manifest, now=2)
        self.graph.validate(self.actors["validator-a"], "s1", 2)
        self.graph.admit(self.actors["admitter"], "s1", 2)
        self.assertEqual(len(self.graph.discover(self.actors["recipient-a"], 2)), 1)
        self.assertEqual(len(self.graph.assessment_history(self.actors["recipient-a"])), 2)

    def test_beta_catches_up_owner_can_retire_without_old_assessment_reentry(self) -> None:
        manifest = self.admitted()
        self.graph.set_beta_baseline(self.actors["admitter"], fixture_beta("competent-beta-fixture-v2"), 2)
        negative = dataclasses.replace(fixture_alpha(self.graph, self.actors["inventor"], manifest, 2),
                                       paired_gains=(1.0, 1.0))
        self.assertFalse(self.graph.assess_alpha(self.actors["inventor"], "s1", negative, 2)["accepted"])
        self.graph.terminate(self.actors["inventor"], "s1", "retired", "Beta makes this redundant", 2)
        with self.assertRaises(GraphError):
            self.evidence(manifest, now=2)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ())

    def test_bundle_components_need_no_individual_positive_alpha(self) -> None:
        first, second = self.candidate("component-a"), self.candidate("component-b")
        for component in (first, second):
            self.evidence(component, benefit=0, assess=False)
        bundle = self.admitted("bundle", components=(Dependency(first.skill_id, first.hash),
                                                    Dependency(second.skill_id, second.hash)))
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2),
                         (bundle.skill_id,))
        for actor in self.actors.values():
            self.assertEqual(self.graph.retrieve_component(actor, "bundle", "component-a", 2),
                             b"private synthetic component-a")
        with self.assertRaises(GraphError):
            self.graph.retrieve(self.actors["recipient-a"], "component-a", 2)
        permit = self.graph.authorize_reuse(self.actors["recipient-a"], "bundle", self.scope, self.tools, 2)
        self.assertFalse(self.graph.consume_reuse(self.actors["recipient-a"], permit, 2)["code_executed"])
        self.graph.terminate(self.actors["inventor"], "component-a", "revoked", "counterexample", 2)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ())

    def test_component_evidence_revision_invalidates_bundle_assessment(self) -> None:
        component = self.candidate("component")
        self.evidence(component, benefit=0, assess=False)
        self.admitted("bundle", components=(Dependency(component.skill_id, component.hash),))
        self.evidence(component, now=2, benefit=0, assess=False)
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 2), ())

    def failure(self, failure_id: str = "failed-campaign", now: int = 1, **changes):
        return self.graph.record_failure(
            self.actors["inventor"], failure_id, (self.scope,), "construction-failure",
            "Sanitized synthetic summary: declared constraints were not satisfied.",
            digest("failed-attempt", failure_id), now, **changes,
        )

    def test_failure_memory_is_available_to_all_but_never_a_positive_skill(self) -> None:
        failure = self.failure()
        for actor in self.actors.values():
            memories = self.graph.read_failures(actor, 1)
            self.assertEqual([x["failure_id"] for x in memories], [failure.failure_id])
            self.assertFalse(memories[0]["positive_alpha"])
            self.assertFalse(memories[0]["eligible_for_skill_selection"])
            self.assertTrue(memories[0]["context_current"])
            self.assertEqual(self.graph.discover(actor, 1), ())
        self.assertEqual(self.graph.select(self.actors["recipient-a"], "mechanism", self.scope, self.tools, 1), ())
        for operation in (
            lambda: self.graph.admit(self.actors["admitter"], failure.failure_id, 1),
            lambda: self.graph.promote_canonical(self.actors["admitter"], failure.failure_id, 1),
            lambda: self.graph.retrieve(self.actors["recipient-a"], failure.failure_id, 1),
            lambda: self.graph.authorize_reuse(self.actors["recipient-a"], failure.failure_id, self.scope, self.tools, 1),
            lambda: self.candidate(failure.failure_id, now=1),
        ):
            with self.assertRaises(GraphError):
                operation()
        self.assertNotIn("Sanitized synthetic summary", json.dumps(self.graph.public_commitment()))

    def test_failure_memory_rechecks_membership_and_distinct_write_authority(self) -> None:
        self.failure()
        self.graph.directory.disable_fixture(self.actors["recipient-a"].name)
        with self.assertRaises(GraphError):
            self.graph.read_failures(self.actors["recipient-a"], 1)
        with self.assertRaises(GraphError):
            self.graph.record_failure(self.actors["validator-a"], "new-failure", (self.scope,), "failed",
                                      "synthetic summary", "1" * 64, 1)
        with self.assertRaises(GraphError):
            self.graph.withdraw_failure(self.actors["admitter"], "failed-campaign", "not owner", 1)

    def test_failure_memory_becomes_historical_after_baseline_change(self) -> None:
        failure = self.failure()
        self.graph.set_beta_baseline(self.actors["admitter"], fixture_beta("new-environment-v2"), 2)
        memory = self.graph.read_failures(self.actors["recipient-a"], 2)[0]
        self.assertFalse(memory["context_current"])
        self.assertFalse(memory["positive_alpha"])
        self.assertEqual(memory["record_hash"], failure.hash)
        self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())
        self.graph.withdraw_failure(self.actors["inventor"], failure.failure_id, "corrected interpretation", 2)
        self.assertEqual(self.graph.read_failures(self.actors["recipient-a"], 2), ())
        with self.assertRaises(GraphError):
            self.failure(now=2)

    def test_protected_evaluation_material_never_enters_shared_capsules_or_failure_memory(self) -> None:
        with self.assertRaises(GraphError):
            self.candidate(protected_evaluation_material=True)
        for changes in ({"protected_evaluation_material": True}, {"sanitized": False}, {"rights_check": False}):
            with self.subTest(changes=changes), self.assertRaises(GraphError):
                self.failure(**changes)
        self.assertEqual(self.graph.read_failures(self.actors["recipient-a"], 1), ())

    def test_failure_and_skill_identifiers_cannot_be_reinterpreted(self) -> None:
        self.candidate("same-id")
        with self.assertRaises(GraphError):
            self.failure("same-id")
        self.failure("failure-only")
        with self.assertRaises(GraphError):
            self.candidate("failure-only", now=1)

    def test_model_tool_and_environment_updates_invalidate_old_admission(self) -> None:
        for changed in ("model", "tools", "environment"):
            with self.subTest(changed=changed):
                self.setUp()
                self.admitted()
                prior = self.graph.beta
                changed_config = dataclasses.replace(
                    prior, beta_id=changed + "-configuration-v2",
                    configuration_hash=digest("changed-beta-configuration", {"prior": prior.hash, changed: "v2"}),
                )
                with self.assertRaises(GraphError):
                    self.graph.set_beta_baseline(self.actors["admitter"],
                                                 dataclasses.replace(changed_config, beta_id=prior.beta_id), 2)
                self.graph.set_beta_baseline(self.actors["admitter"], changed_config, 2)
                self.assertEqual(self.graph.discover(self.actors["recipient-a"], 2), ())
                with self.assertRaises(GraphError):
                    self.graph.authorize_reuse(self.actors["recipient-a"], "s1", self.scope, self.tools, 2)

    def test_overlapping_role_permissions_cannot_make_a_claimant_its_own_admitter(self) -> None:
        roles = {
            "producer": {"record.write", "graph.admit"},
            "v1": {"graph.validate", "graph.admit"},
            "v2": {"graph.validate"},
            "admission": {"graph.admit"},
        }
        directory = FixtureDirectory(tuple(Principal(name + ".agent.agi.eth", "fixture:" + name, frozenset(perms))
                                           for name, perms in roles.items()))
        graph = type(self.graph)(directory)
        actors = {name: directory.open_session(name + ".agent.agi.eth", "fixture:" + name) for name in roles}
        manifest = graph.create_candidate(actors["producer"], "role-separation", b"synthetic capsule", "mechanism",
                                          (self.scope,))
        graph.submit_evidence(actors["producer"], manifest.skill_id, fixture_evidence(manifest, graph.policy), 1)
        graph.assess_alpha(actors["producer"], manifest.skill_id, fixture_alpha(graph, actors["producer"], manifest), 1)
        for name in ("v1", "v2"):
            attestation = graph.sign_attestation(actors[name], manifest.skill_id, "supported", 1, 9)
            graph.attach_attestation(actors[name], attestation, 1)
        graph.validate(actors["v1"], manifest.skill_id, 1)
        for name in ("producer", "v1"):
            with self.subTest(name=name), self.assertRaises(GraphError):
                graph.admit(actors[name], manifest.skill_id, 1)
        graph.admit(actors["admission"], manifest.skill_id, 1)
        self.assertEqual(len(graph.discover(actors["producer"], 1)), 1)

    def test_demo_claim_boundaries_and_full_network_availability(self) -> None:
        demo = run_graph_demo()
        self.assertFalse(demo["production_confidentiality"])
        self.assertFalse(demo["zk_proofs"])
        self.assertFalse(demo["authorized_recipient_copying_prevented"])
        self.assertEqual(demo["onchain_transactions"], 0)
        self.assertEqual(len(demo["network_availability_before_revocation"]), 6)
        self.assertTrue(all(value == ["deviation-witness-v1"]
                            for value in demo["network_availability_before_revocation"].values()))
        self.assertEqual(demo["selected_after_revocation"], ())
        self.assertFalse(demo["failure_memory"]["eligible_for_positive_selection"])
        self.assertFalse(demo["protected_evaluation_policy"]["testcases_and_scorer_internals_allowed"])


if __name__ == "__main__":
    unittest.main()
