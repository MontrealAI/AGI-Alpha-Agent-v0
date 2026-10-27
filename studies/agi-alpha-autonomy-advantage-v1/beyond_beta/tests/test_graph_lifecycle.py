# SPDX-License-Identifier: Apache-2.0
"""Adversarial offline controls; all economic evidence is handwritten and fictional."""
from pathlib import Path
from copy import deepcopy
import base64
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "beyond_beta/src"))
from graph_lifecycle import (BeyondBetaGraph, Refusal, OfflinePrincipal, authority_fixture,
                            CapsuleVault, costs, digest)
from fixture_factory import make_fixture_environment, fixture_artifact, matched_evidence, qualify, mission_for, bind_cost_ownership


class GraphControls(unittest.TestCase):
    def setUp(self):
        self.g, self.p = make_fixture_environment()

    def candidate(self, function="solver", name=None, epoch=0, **kwargs):
        return self.g.create(self.p["creator"], self.p["writer"], fixture_artifact(function),
                             skill_id=name, epoch=epoch, **kwargs)

    def admitted(self, function="solver", name=None, epoch=0, prefix="fresh", **kwargs):
        key = self.candidate(function, name, epoch, **kwargs)
        e = matched_evidence(self.g, key, [80, 80], [100, 100], epoch=epoch, case_prefix=prefix)
        self.assertTrue(qualify(self.g, self.p, key, e, epoch)["qualified"])
        self.g.admit(self.p["admitter"], key, epoch)
        return key

    def permit(self, key, function="solver", epoch=0):
        return self.g.authorize_reuse(self.p["executor"], key, mission_for(self.g, function), epoch)

    def test_complete_lifecycle_and_network_availability(self):
        key = self.admitted()
        self.assertEqual(self.g.record(key)["stage"], "ADMITTED")
        for person in self.p.values():
            found = self.g.discover(person, 0)
            self.assertEqual(found[0]["key"], key)
            self.assertTrue(found[0]["availableToEligibleNetwork"])
            self.assertFalse(found[0]["mandatoryUse"])
        result = self.g.resolve_reuse(self.p["executor"], self.permit(key), 0)
        self.assertEqual(result["artifact"], fixture_artifact())

    def test_writer_cannot_promote(self):
        key = self.candidate()
        with self.assertRaisesRegex(Refusal, "ROLE_NOT_AUTHORIZED"):
            self.g.admit(self.p["writer"], key, 0)

    def test_canonical_promotion_cannot_bypass_admission(self):
        key = self.candidate()
        with self.assertRaisesRegex(Refusal, "MANDATORY_CANONICAL_PROMOTION_GATE"):
            self.g.admit(self.p["admitter"], key, 0)
        self.assertEqual(self.g.discover(self.p["reader"], 0), [])

    def test_creator_cannot_impersonate_writer(self):
        with self.assertRaisesRegex(Refusal, "ROLE_NOT_AUTHORIZED"):
            self.g.create(self.p["creator"], self.p["creator"], fixture_artifact())

    def test_validator_is_independent_of_creator_even_if_role_granted(self):
        key = self.candidate()
        self.g.register_evidence(self.p["writer"], key, matched_evidence(self.g, key, [80,80], [100,100]), 0)
        self.g.assess(self.p["assessor"], key, 0)
        self.g.authorities[self.p["creator"].name]["roles"].append("validator")
        with self.assertRaisesRegex(Refusal, "NONINDEPENDENT_VALIDATOR"):
            self.g.validate(self.p["creator"], key, 0)

    def test_complete_qualification_without_alpha_is_not_admission(self):
        key = self.candidate()
        e = matched_evidence(self.g, key, [200,200], [100,100])
        self.assertFalse(qualify(self.g, self.p, key, e)["qualified"])
        with self.assertRaisesRegex(Refusal, "NET_ALPHA_GATE_NOT_PASSED"):
            self.g.admit(self.p["admitter"], key, 0)

    def test_unknown_cost_fails_closed(self):
        key = self.candidate(); e = matched_evidence(self.g, key, [80,80], [100,100])
        e["arms"]["candidate"]["records"][0]["costs"]["verification"] = None
        self.g.register_evidence(self.p["writer"], key, e, 0)
        with self.assertRaisesRegex(Refusal, "UNKNOWN_OR_NEGATIVE_COST"):
            self.g.assess(self.p["assessor"], key, 0)

    def test_omitted_cost_category_fails_closed(self):
        key = self.candidate(); e = matched_evidence(self.g, key, [80,80], [100,100])
        del e["arms"]["candidate"]["records"][0]["costs"]["support"]
        self.g.register_evidence(self.p["writer"], key, e, 0)
        with self.assertRaisesRegex(Refusal, "INCOMPLETE_COST_CATEGORIES"):
            self.g.assess(self.p["assessor"], key, 0)

    def test_all_available_relevant_inventory_must_be_compared(self):
        self.g.advance_inventory(self.p["admitter"], [dict(id="competent-tool", version=1, function="solver", available=True)], 0)
        key = self.candidate(); e = matched_evidence(self.g, key, [80,80], {"beta":[100,100],"inventory:competent-tool@1":[50,50]})
        self.assertFalse(qualify(self.g, self.p, key, e)["qualified"])

    def test_omitted_inventory_comparator_is_rejected(self):
        self.g.advance_inventory(self.p["admitter"], [dict(id="tool", version=1, function="solver")], 0)
        key = self.candidate(); e = matched_evidence(self.g, key, [80,80], [100,100])
        del e["arms"]["inventory:tool@1"]
        self.g.register_evidence(self.p["writer"], key, e, 0)
        with self.assertRaisesRegex(Refusal, "OMITTED_OR_UNDECLARED"):
            self.g.assess(self.p["assessor"], key, 0)

    def test_stale_inventory_blocks_promotion(self):
        key = self.candidate(); qualify(self.g, self.p, key, matched_evidence(self.g, key, [80,80], [100,100]))
        self.g.advance_inventory(self.p["admitter"], [dict(id="tool",version=1,function="solver")], 1)
        with self.assertRaisesRegex(Refusal, "STALE_INVENTORY"):
            self.g.admit(self.p["admitter"], key, 1)

    def test_beta_upgrade_refuses_old_permit_and_historical_clock(self):
        key = self.admitted(); permit = self.permit(key)
        self.g.advance_beta(self.p["admitter"], {**self.g.beta,"version":2}, 1)
        with self.assertRaisesRegex(Refusal, "STALE_BETA_OR_POLICY"):
            self.g.resolve_reuse(self.p["executor"], permit, 1)
        with self.assertRaisesRegex(Refusal, "HISTORICAL_CLOCK"):
            self.g.discover(self.p["reader"], 0)

    def test_live_policy_slider_mutation_is_not_accepted(self):
        key = self.admitted()
        self.g.policy["minimumNetAlphaMicros"] = 1
        with self.assertRaisesRegex(Refusal, "MUTATED_UNCOMMITTED_POLICY"):
            self.g.discover(self.p["reader"], 0)

    def test_policy_version_upgrade_requires_fresh_validation(self):
        key = self.admitted(); permit = self.permit(key)
        self.g.advance_policy(self.p["admitter"], {**self.g.policy,"version":2}, 1)
        with self.assertRaisesRegex(Refusal, "STALE_BETA_OR_POLICY"):
            self.g.resolve_reuse(self.p["executor"], permit, 1)

    def test_new_relevant_admission_stales_older_skill(self):
        old = self.admitted(name="old")
        new = self.admitted(name="new", prefix="second")
        self.assertEqual([x["key"] for x in self.g.discover(self.p["reader"], 0)], [new])
        with self.assertRaisesRegex(Refusal, "NEW_RELEVANT_INVENTORY"):
            self.permit(old)

    def test_irrelevant_inventory_does_not_stale_skill(self):
        old = self.admitted(name="solver")
        self.admitted("verifier", name="verifier", prefix="verify")
        self.assertIn(old, [x["key"] for x in self.g.discover(self.p["reader"], 0)])

    def test_revocation_between_authorization_and_dispatch(self):
        key = self.admitted(); permit = self.permit(key)
        self.g.revoke(self.p["writer"], key, 1)
        with self.assertRaisesRegex(Refusal, "NOT_CURRENT_CANONICAL"):
            self.g.resolve_reuse(self.p["executor"], permit, 1)

    def test_retired_record_never_reactivates_from_history(self):
        key = self.admitted(); self.g.retire(self.p["writer"], key, 1)
        e = matched_evidence(self.g, key, [10,10], [100,100], epoch=1, revalidation=True, case_prefix="new")
        with self.assertRaisesRegex(Refusal, "TERMINAL_RECORD_CANNOT_BE_REACTIVATED"):
            self.g.revalidate(self.p["writer"], key, e, 1)
        self.assertEqual(self.g.discover(self.p["reader"], 1), [])

    def test_repeated_admission_cannot_advance_frontier(self):
        key = self.admitted(); before = self.g.audit_log()["root"]
        with self.assertRaisesRegex(Refusal, "MANDATORY_CANONICAL_PROMOTION_GATE"):
            self.g.admit(self.p["admitter"], key, 0)
        self.assertEqual(self.g.audit_log()["root"], before)

    def test_actual_capsule_encryption_and_aead_tamper_detection(self):
        vault = CapsuleVault(); artifact = fixture_artifact(); d = {"artifactHash":digest("ARTIFACT",artifact)}
        commitment, envelope = vault.seal(artifact, d)
        self.assertEqual(vault.open(commitment, envelope, d), artifact)
        self.assertNotIn("IDENTITY", envelope["ciphertext"])
        altered = deepcopy(envelope); raw=bytearray(base64.b64decode(altered["ciphertext"])); raw[0] ^= 1
        altered["ciphertext"] = base64.b64encode(raw).decode(); bad_commitment=digest("CAPSULE",altered)
        # Exercise AEAD itself after deliberate internal test-only rebinding of its outer hash.
        vault._keys[bad_commitment] = vault._keys[commitment]
        with self.assertRaisesRegex(Refusal, "CAPSULE_AUTHENTICATION_FAILED"):
            vault.open(bad_commitment, altered, d)

    def test_wrong_ephemeral_controller_key_is_rejected(self):
        impostor = OfflinePrincipal(self.p["reader"].name)
        with self.assertRaisesRegex(Refusal, "WRONG_FIXTURE_CONTROLLER_KEY"):
            self.g.discover(impostor, 0)

    def test_deeper_agent_name_does_not_inherit_authority(self):
        actor = OfflinePrincipal("child.reader.agent.agi.eth")
        self.g.authorities[actor.name] = authority_fixture(actor, [])
        with self.assertRaisesRegex(Refusal, "AUTHORITY_NOT_ELIGIBLE"):
            self.g.discover(actor, 0)

    def test_ineligible_network_actor_cannot_discover(self):
        self.admitted(); self.g.authorities[self.p["reader"].name]["eligible"] = False
        with self.assertRaisesRegex(Refusal, "AUTHORITY_NOT_ELIGIBLE"):
            self.g.discover(self.p["reader"], 0)

    def test_duplicate_validator_does_not_satisfy_distinctness(self):
        key = self.candidate(); self.g.register_evidence(self.p["writer"], key, matched_evidence(self.g,key,[80,80],[100,100]),0)
        self.g.assess(self.p["assessor"], key, 0)
        self.g.validate(self.p["validator-a"], key, 0); self.g.validate(self.p["validator-a"], key, 0)
        with self.assertRaisesRegex(Refusal, "INSUFFICIENT_INDEPENDENT_VALIDATORS"):
            self.g.admit(self.p["admitter"], key, 0)

    def test_validator_revocation_blocks_future_influence(self):
        key = self.admitted(); permit=self.permit(key)
        self.g.authorities[self.p["validator-a"].name]["revoked"] = True
        with self.assertRaisesRegex(Refusal, "VALIDATOR_AUTHORITY_EXPIRED_OR_REVOKED"):
            self.g.resolve_reuse(self.p["executor"], permit, 0)

    def test_client_prompt_and_payload_fields_are_refused(self):
        artifact = fixture_artifact(); artifact["clientPrompt"] = "PRIVATE CLIENT CONTENT"
        with self.assertRaisesRegex(Refusal, "CLIENT_CONTENT_REFUSED"):
            self.g.create(self.p["creator"], self.p["writer"], artifact)

    def test_client_constants_and_unapproved_provenance_are_refused(self):
        artifact=fixture_artifact(); artifact["nodes"][0]["parameterKeys"]=["client-account-123"]
        with self.assertRaisesRegex(Refusal, "UNAPPROVED_CONSTANT_OR_CLIENT_DATA"):
            self.g.create(self.p["creator"],self.p["writer"],artifact)
        artifact=fixture_artifact();artifact["publicSourceIds"]=["private-customer-document"]
        with self.assertRaisesRegex(Refusal, "UNAPPROVED_OR_CLIENT_PROVENANCE"):
            self.g.create(self.p["creator"],self.p["writer"],artifact)

    def composition_candidate(self):
        a=self.admitted("solver",name="component-a",prefix="a")
        b=self.admitted("verifier",name="component-b",prefix="b")
        deps=[{"key":k,"artifactHash":self.g.record(k)["descriptor"]["artifactHash"]} for k in (a,b)]
        return self.candidate("composition",name="joint",dependencies=deps),a,b

    def test_composition_requires_its_own_independent_evidence(self):
        key,_,_=self.composition_candidate(); e=matched_evidence(self.g,key,[50,50],[100,100],case_prefix="joint")
        self.assertTrue(qualify(self.g,self.p,key,e)["qualified"])
        self.g.admit(self.p["admitter"],key,0)
        self.g.resolve_reuse(self.p["executor"],self.permit(key,"composition"),0)

    def test_missing_composition_evidence_is_not_inherited(self):
        key,_,_=self.composition_candidate();e=matched_evidence(self.g,key,[50,50],[100,100],case_prefix="joint");e["composition"]=None
        self.g.register_evidence(self.p["writer"],key,e,0)
        with self.assertRaisesRegex(Refusal,"INDEPENDENT_COMPOSITION_EVIDENCE_REQUIRED"):
            self.g.assess(self.p["assessor"],key,0)

    def test_composition_cannot_copy_parent_validation_cases(self):
        key,_,_=self.composition_candidate();e=matched_evidence(self.g,key,[50,50],[100,100],case_prefix="a")
        self.g.register_evidence(self.p["writer"],key,e,0)
        with self.assertRaisesRegex(Refusal,"COMPOSITION_REUSES_COMPONENT_CASES"):
            self.g.assess(self.p["assessor"],key,0)

    def test_dependency_substitution_and_retirement_refuse_reuse(self):
        key,a,_=self.composition_candidate();qualify(self.g,self.p,key,matched_evidence(self.g,key,[50,50],[100,100],case_prefix="joint"));self.g.admit(self.p["admitter"],key,0)
        permit=self.permit(key,"composition")
        self.g.retire(self.p["writer"],a,1)
        with self.assertRaisesRegex(Refusal,"NOT_CURRENT_CANONICAL_ADMISSION"):
            self.g.resolve_reuse(self.p["executor"],permit,1)

    def test_new_component_version_needs_new_composition_validation(self):
        key,a,_=self.composition_candidate();qualify(self.g,self.p,key,matched_evidence(self.g,key,[50,50],[100,100],case_prefix="joint"));self.g.admit(self.p["admitter"],key,0)
        new=self.candidate("solver",name="component-a",version=2,supersedes=a)
        qualify(self.g,self.p,new,matched_evidence(self.g,new,[10,10],[100,100],case_prefix="a2"));self.g.admit(self.p["admitter"],new,0)
        with self.assertRaisesRegex(Refusal,"NOT_CURRENT_CANONICAL_ADMISSION"):
            self.permit(key,"composition")

    def test_construction_cost_can_eliminate_apparent_alpha(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=100)
        self.assertFalse(qualify(self.g,self.p,key,e)["qualified"])

    def test_amortization_is_finitely_bounded_by_policy(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],allocation_uses=11)
        self.g.register_evidence(self.p["writer"],key,e,0)
        with self.assertRaisesRegex(Refusal,"UNBOUNDED_COST_AMORTIZATION"):
            self.g.assess(self.p["assessor"],key,0)

    def test_candidate_cannot_choose_uncertainty_allowance(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100]);e["uncertaintyAllowanceMicros"]=0
        with self.assertRaisesRegex(Refusal,"UNKNOWN_OR_INCOMPLETE_EVIDENCE_FIELDS"):
            self.g.register_evidence(self.p["writer"],key,e,0)

    def test_prospective_revalidation_preserves_historical_construction(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=10)
        qualify(self.g,self.p,key,e);self.g.admit(self.p["admitter"],key,0)
        self.g.advance_beta(self.p["admitter"],{**self.g.beta,"version":2},1)
        new=matched_evidence(self.g,key,[70,70],[100,100],epoch=1,case_prefix="reval",revalidation=True)
        assessment=qualify(self.g,self.p,key,new,1);self.g.admit(self.p["admitter"],key,1)
        self.assertTrue(assessment["prospectiveRevalidation"])
        self.assertEqual(assessment["arms"]["candidate"]["historicalConstructionMicros"],10)
        self.assertEqual(assessment["arms"]["candidate"]["lifecycleCostMicros"],0)

    def test_revalidation_cannot_reuse_old_cases_or_double_charge_construction(self):
        key=self.admitted();e=matched_evidence(self.g,key,[70,70],[100,100],epoch=1,case_prefix="fresh",revalidation=True)
        with self.assertRaisesRegex(Refusal,"REVALIDATION_REUSES_OLD_CASES"):
            self.g.revalidate(self.p["writer"],key,e,1)
        e=matched_evidence(self.g,key,[70,70],[100,100],epoch=1,case_prefix="new",revalidation=True,construction_micros=1)
        self.g.revalidate(self.p["writer"],key,e,1)
        with self.assertRaisesRegex(Refusal,"DOUBLE_CHARGED_HISTORICAL_CONSTRUCTION"):
            self.g.assess(self.p["assessor"],key,1)

    def test_private_storage_only_in_explicit_ablation(self):
        with self.assertRaisesRegex(Refusal,"EXPLICIT_ABLATION_POLICY"):
            self.candidate(shareable=False)
        self.g,self.p=make_fixture_environment(private_ablation=True)
        key=self.admitted(shareable=False)
        self.assertEqual(self.g.discover(self.p["reader"],0),[])
        with self.assertRaisesRegex(Refusal,"PRIVATE_ABLATION_NOT_SHARED"):
            self.permit(key)

    def test_execution_permission_is_distinct_from_network_availability(self):
        key=self.admitted()
        self.assertTrue(self.g.discover(self.p["reader"],0))
        with self.assertRaisesRegex(Refusal,"ROLE_NOT_AUTHORIZED:execution"):
            self.g.authorize_reuse(self.p["reader"],key,mission_for(self.g),0)
        mission=mission_for(self.g);mission["permittedOperators"]=[]
        with self.assertRaisesRegex(Refusal,"EXECUTION_PERMISSION_INSUFFICIENT"):
            self.g.authorize_reuse(self.p["executor"],key,mission,0)

    def test_failed_initial_alpha_cannot_erase_program_cost_as_revalidation(self):
        key=self.candidate();e=matched_evidence(self.g,key,[1,1],[100,100],construction_micros=10000)
        self.assertFalse(qualify(self.g,self.p,key,e)["qualified"])
        fresh=matched_evidence(self.g,key,[1,1],[100,100],epoch=1,case_prefix="new",revalidation=True)
        with self.assertRaisesRegex(Refusal,"INITIAL_EVIDENCE_REQUIRED"):
            self.g.revalidate(self.p["writer"],key,fresh,1)
        fresh["phase"]="initial"
        with self.assertRaisesRegex(Refusal,"UNRECOVERED_INITIAL_PROGRAM_COST_ERASURE"):
            self.g.register_evidence(self.p["writer"],key,fresh,1)
        self.assertNotEqual(self.g.record(key)["stage"],"ADMITTED")

    def test_same_function_composition_can_use_confined_current_parent(self):
        parent=self.admitted(name="parent",prefix="parent")
        dep={"key":parent,"artifactHash":self.g.record(parent)["descriptor"]["artifactHash"]}
        joint=self.candidate(name="joint-same-function",dependencies=[dep])
        qualify(self.g,self.p,joint,matched_evidence(self.g,joint,[10,10],[100,100],case_prefix="joint"))
        self.g.admit(self.p["admitter"],joint,0)
        released=self.g.resolve_reuse(self.p["executor"],self.permit(joint),0)
        self.assertIn(parent,released["confinedComponentArtifacts"])
        with self.assertRaisesRegex(Refusal,"NEW_RELEVANT_INVENTORY"):
            self.permit(parent)

    def support_bundle(self):
        supports=[]
        for name in ("support-a","support-b"):
            key=self.candidate(name=name,support_only=True,support_construction_micros=10)
            supports.append({"key":key,"artifactHash":self.g.record(key)["descriptor"]["artifactHash"]})
        joint=self.candidate("composition",name="support-joint",dependencies=supports)
        return joint,supports

    def test_valuable_bundle_does_not_require_standalone_component_alpha(self):
        joint,supports=self.support_bundle()
        e=matched_evidence(self.g,joint,[1,1],[100,100],case_prefix="bundle",construction_micros=20)
        self.assertTrue(qualify(self.g,self.p,joint,e)["qualified"])
        self.g.admit(self.p["admitter"],joint,0)
        self.assertEqual([r["key"] for r in self.g.discover(self.p["reader"],0)],[joint])
        released=self.g.resolve_reuse(self.p["executor"],self.permit(joint,"composition"),0)
        self.assertEqual(set(released["confinedComponentArtifacts"]),{d["key"] for d in supports})
        with self.assertRaisesRegex(Refusal,"NOT_CURRENT_CANONICAL_ADMISSION"):
            self.permit(supports[0]["key"])

    def test_bundle_cannot_omit_support_construction_cost(self):
        joint,_=self.support_bundle();e=matched_evidence(self.g,joint,[1,1],[100,100],case_prefix="bundle")
        self.g.register_evidence(self.p["writer"],joint,e,0)
        with self.assertRaisesRegex(Refusal,"SUPPORT_BUILD_COST_OMITTED"):
            self.g.assess(self.p["assessor"],joint,0)

    def test_revoked_support_cannot_influence_bundle_from_history(self):
        joint,supports=self.support_bundle();e=matched_evidence(self.g,joint,[1,1],[100,100],case_prefix="bundle",construction_micros=20)
        qualify(self.g,self.p,joint,e);self.g.admit(self.p["admitter"],joint,0)
        permit=self.permit(joint,"composition");self.g.revoke(self.p["writer"],supports[0]["key"],1)
        with self.assertRaisesRegex(Refusal,"RETIRED_OR_REVOKED_SUPPORT_COMPONENT"):
            self.g.resolve_reuse(self.p["executor"],permit,1)

    def test_refused_future_epoch_cannot_poison_clock(self):
        unauthorized=OfflinePrincipal("unregistered.agent.agi.eth")
        with self.assertRaisesRegex(Refusal,"AUTHORITY_NOT_ELIGIBLE"):
            self.g.discover(unauthorized,100000)
        self.assertEqual(self.g.discover(self.p["reader"],0),[])

    def test_plaintext_retrieval_export_and_composition_rights_are_separate(self):
        key=self.admitted()
        with self.assertRaisesRegex(Refusal,"ROLE_NOT_AUTHORIZED:retrieve"):
            self.g.retrieve(self.p["reader"],key,0)
        with self.assertRaisesRegex(Refusal,"ROLE_NOT_AUTHORIZED:export"):
            self.g.export_capsule(self.p["executor"],key,0)
        self.g.authorities[self.p["reader"].name]["roles"].append("retrieve")
        self.assertFalse(self.g.retrieve(self.p["reader"],key,0)["executionAuthorized"])
        self.g.authorities[self.p["creator"].name]["roles"].remove("compose")
        with self.assertRaisesRegex(Refusal,"ROLE_NOT_AUTHORIZED:compose"):
            self.candidate("composition",dependencies=[{"key":key,"artifactHash":self.g.record(key)["descriptor"]["artifactHash"]}])

    def test_nested_component_cases_cannot_be_reused_as_fresh_joint_evidence(self):
        parent=self.admitted(name="deep-parent",prefix="deep")
        dep={"key":parent,"artifactHash":self.g.record(parent)["descriptor"]["artifactHash"]}
        middle=self.candidate("verifier",name="support-middle",dependencies=[dep],support_only=True,support_construction_micros=0)
        outer=self.candidate("composition",name="outer",dependencies=[{"key":middle,"artifactHash":self.g.record(middle)["descriptor"]["artifactHash"]}])
        evidence=matched_evidence(self.g,outer,[1,1],[100,100],case_prefix="deep")
        self.g.register_evidence(self.p["writer"],outer,evidence,0)
        with self.assertRaisesRegex(Refusal,"COMPOSITION_REUSES_COMPONENT_CASES"):
            self.g.assess(self.p["assessor"],outer,0)

    def origin_cost(self,amount=1000000):
        return dict(jobId="completed-job-a",ledgerCommitment=digest("DELIVERY-A-LEDGER",{"job":"a","cost":amount}),
                    costMicros=amount,ownership="DELIVERY_A_ALREADY_CHARGED")

    def test_paid_origin_delivery_cost_is_provenance_not_retention_cost(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=10)
        e=bind_cost_ownership(e,origin_job_costs=[self.origin_cost()])
        assessment=qualify(self.g,self.p,key,e)
        self.assertTrue(assessment["qualified"])
        self.assertEqual(assessment["comparisons"][0]["meanNetAlphaMicros"],"10")
        self.assertEqual(assessment["costOwnership"]["originDeliveryCostMicros"],1000000)
        self.assertEqual(assessment["costOwnership"]["alphaLifecycleCostMicros"],10)
        self.assertFalse(assessment["costOwnership"]["originDeliveryIncludedInAlpha"])

    def test_origin_charge_cannot_also_be_a_retention_charge(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=10)
        e=bind_cost_ownership(e,origin_job_costs=[self.origin_cost()])
        e["costOwnership"]["retentionEntries"][0]["ledgerCommitment"]=self.origin_cost()["ledgerCommitment"]
        with self.assertRaisesRegex(Refusal,"DUPLICATE_ORIGIN_OR_RETENTION_LEDGER_CHARGE"):
            self.g.register_evidence(self.p["writer"],key,e,0)

    def test_origin_cost_cannot_silently_enter_lifecycle_total(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=10)
        e=bind_cost_ownership(e,origin_job_costs=[self.origin_cost()])
        e["arms"]["candidate"]["lifecycleCosts"]["construction"]+=1000000
        with self.assertRaisesRegex(Refusal,"LIFECYCLE_MUST_EQUAL_INCREMENTAL_B_PLUS_C_NOT_ORIGIN_A"):
            self.g.register_evidence(self.p["writer"],key,e,0)

    def test_same_origin_provenance_can_be_referenced_in_revalidation_without_charge(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=10)
        e=bind_cost_ownership(e,origin_job_costs=[self.origin_cost()]);qualify(self.g,self.p,key,e);self.g.admit(self.p["admitter"],key,0)
        fresh=matched_evidence(self.g,key,[70,70],[100,100],epoch=1,case_prefix="reval",revalidation=True)
        fresh=bind_cost_ownership(fresh,origin_job_costs=[self.origin_cost()])
        assessment=qualify(self.g,self.p,key,fresh,1)
        self.assertEqual(assessment["costOwnership"]["alphaLifecycleCostMicros"],0)
        self.assertEqual(assessment["costOwnership"]["originDeliveryCostMicros"],1000000)

    def test_retention_expense_cannot_be_reclassified_as_free_origin_work(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100],construction_micros=10000)
        qualify(self.g,self.p,key,e)
        old=e["costOwnership"]["retentionEntries"][0]
        fresh=matched_evidence(self.g,key,[1,1],[100,100],epoch=1,case_prefix="fresh-b")
        origin=dict(jobId="pretend-origin",ledgerCommitment=old["ledgerCommitment"],costMicros=10000,ownership="DELIVERY_A_ALREADY_CHARGED")
        fresh=bind_cost_ownership(fresh,origin_job_costs=[origin])
        with self.assertRaisesRegex(Refusal,"PAID_COST_OWNERSHIP_OR_AMOUNT_CANNOT_BE_RECLASSIFIED"):
            self.g.register_evidence(self.p["writer"],key,fresh,1)

    def test_optional_research_is_separate_and_still_charged(self):
        key=self.candidate();e=matched_evidence(self.g,key,[80,80],[100,100])
        b=dict(chargeId="retain-b",ledgerCommitment=digest("B",{}),costs=costs(construction=10),ownership="INCREMENTAL_RETENTION_B")
        c=dict(chargeId="research-c",ledgerCommitment=digest("C",{}),costs=costs(search=5),ownership="OPTIONAL_RESEARCH_C")
        e=bind_cost_ownership(e,origin_job_costs=[self.origin_cost()],retention_entries=[b],research_entries=[c])
        assessment=qualify(self.g,self.p,key,e)
        self.assertEqual(assessment["comparisons"][0]["meanNetAlphaMicros"],"5")
        self.assertEqual(assessment["costOwnership"]["incrementalRetentionCostMicros"],10)
        self.assertEqual(assessment["costOwnership"]["optionalResearchCostMicros"],5)

    def test_failure_memory_is_separate_nonexecutable_and_not_positive_graph(self):
        key=self.candidate();e=matched_evidence(self.g,key,[200,200],[100,100])
        self.g.register_evidence(self.p["writer"],key,e,0);self.g.assess(self.p["assessor"],key,0)
        self.g.assess(self.p["assessor"],key,0)
        failed=self.g.failure_memory(self.p["reader"],0)
        self.assertEqual(len(failed),1)
        self.assertFalse(failed[0]["executable"])
        self.assertFalse(failed[0]["positiveGraphAdmission"])
        self.assertFalse(failed[0]["productionAuthority"])
        self.assertNotIn("artifact",failed[0])
        self.assertEqual(self.g.discover(self.p["reader"],0),[])
        with self.assertRaisesRegex(Refusal,"NOT_CURRENT_CANONICAL_ADMISSION"):
            self.permit(key)

    def test_verifier_cannot_also_admit_the_same_candidate(self):
        key=self.candidate();qualify(self.g,self.p,key,matched_evidence(self.g,key,[80,80],[100,100]))
        self.g.authorities[self.p["validator-a"].name]["roles"].append("admission")
        with self.assertRaisesRegex(Refusal,"VERIFIER_AND_ADMITTER_MUST_DIFFER"):
            self.g.admit(self.p["validator-a"],key,0)

    def test_beta_stale_capability_is_not_an_available_inventory_comparator(self):
        old=self.admitted(name="old-beta")
        self.g.advance_beta(self.p["admitter"],{**self.g.beta,"version":2},1)
        candidate=self.candidate(name="current-beta",epoch=1)
        self.assertNotIn("inventory:"+old,self.g.comparison_context(candidate)["requiredArms"])
        self.assertEqual(self.g.discover(self.p["reader"],1),[])

    def test_expired_capability_is_not_an_available_inventory_comparator(self):
        old=self.admitted(name="expired")
        candidate=self.candidate(name="fresh-proof",epoch=9)
        self.assertNotIn("inventory:"+old,self.g.comparison_context(candidate)["requiredArms"])
        self.assertEqual(self.g.discover(self.p["reader"],9),[])

    def test_new_inventory_comparator_replaces_only_stale_standalone_receipt(self):
        old=self.admitted(name="earlier",prefix="earlier")
        current=self.admitted(name="current",prefix="current")
        candidate=self.candidate(name="third")
        arms=self.g.comparison_context(candidate)["requiredArms"]
        self.assertNotIn("inventory:"+old,arms)
        self.assertIn("inventory:"+current,arms)

    def test_foreign_private_capability_is_not_an_available_comparator(self):
        self.g,self.p=make_fixture_environment(private_ablation=True)
        old=self.admitted(name="private-origin",shareable=False)
        foreign=OfflinePrincipal("foreign.agent.agi.eth")
        self.g.authorities[foreign.name]=authority_fixture(foreign,["creator"])
        candidate=self.g.create(foreign,self.p["writer"],fixture_artifact(),skill_id="foreign-candidate",shareable=False)
        self.assertNotIn("inventory:"+old,self.g.comparison_context(candidate)["requiredArms"])

    def test_restored_revalidated_comparator_stales_previous_standalone_receipt(self):
        old=self.admitted(name="returned",prefix="returned-origin")
        current=self.admitted(name="previous-current",prefix="current-origin")
        fresh=matched_evidence(self.g,old,[1,1],[100,100],epoch=1,case_prefix="returned-fresh",revalidation=True)
        self.assertIn("inventory:"+current,fresh["arms"])
        qualify(self.g,self.p,old,fresh,1);self.g.admit(self.p["admitter"],old,1)
        found={r["key"] for r in self.g.discover(self.p["reader"],1)}
        self.assertIn(old,found);self.assertNotIn(current,found)
        with self.assertRaisesRegex(Refusal,"NEW_RELEVANT_INVENTORY_REQUIRES_REVALIDATION"):
            self.permit(current,epoch=1)


if __name__ == "__main__":
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(schema="beyond-beta-adversarial-controls/v1",classification="OFFLINE_EPHEMERAL_CRYPTO_AND_FICTIONAL_ECONOMICS",
                tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
                liveEns=False,livePermissions=False,actualCommercialReceipts=0,calibratedEconomicWorlds=0)
    (ROOT/"beyond_beta/validation/graph-controls.json").write_text(json.dumps(record,indent=2)+"\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
