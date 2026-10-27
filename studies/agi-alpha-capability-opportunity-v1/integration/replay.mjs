// SPDX-License-Identifier: Apache-2.0
// Adapter derived from immutable thermal study lifecycle_bridge.py at 71d1054dd56a9ef25f19ec5f19e941b1957b02ce.
// The imported lifecycle implementation remains unchanged.

import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const q=JSON.parse(readFileSync(0,'utf8'));
const load=p=>import(pathToFileURL(`${q.module_root}/${p}`).href);
const {createSkillNetwork,combineComparisonDigest}=await load('graph/lifecycle.mjs');
const {createModeledAuthority}=await load('graph/simulation_adapter.mjs');
const {createFixtureResolver,createFixtureAttestation,createFixtureRoot}=await load('upstream/graph/authority.mjs');
const {contentDigest}=await load('graph/encoding.mjs');
const {assessAlpha}=await load('model/alpha_gate.mjs');
const members=['atlas.agent.agi.eth','lyra.agent.agi.eth','orion.agent.agi.eth','validator.agent.agi.eth'];
const fixture=createModeledAuthority(members), resolver=createFixtureResolver(fixture);
const scope=contentDigest('capability-opportunity-scientific-research/v1');
const environment=contentDigest('local-computation-synthetic-network-monetary-assumptions/v1');
const networkId='capability-opportunity-relay-research/v1';
const network=createSkillNetwork({networkId,betaVersion:q.beta_version,
  scopeDigest:scope,environmentDigest:environment,authorityFixture:fixture,
  currentSnapshotId:fixture.snapshots[0].id,
  executionAuthorizer:()=>({allowed:q.execution_authorized===true,mode:'SIMULATED_MISSION_AUTHORITY',actualExecution:false})});
network.protectEvaluationMaterial(q.protected_material);
let nonce=0;
const rows=[], checks=[], owners=new Map();
const signTransition=(key,action,options,week)=>{
  const p=network.prepareTransition(key,action,options,week), agent=p.command.actor;
  const root=createFixtureRoot(p.packet,{agent,signer:`fixture:${agent}`,
    snapshotId:network.context().currentSnapshotId,issuedAt:week,expiresAt:week+1000,
    nonce:`root:${nonce++}`,graphId:p.packet.graphId},resolver);
  return network.commitTransition(p,root,week);
};
const memberProof=(agent,week)=>{
  const binding=network.membershipBinding(agent);
  return createFixtureAttestation(binding,{agent,signer:`fixture:${agent}`,
    snapshotId:network.context().currentSnapshotId,issuedAt:week,expiresAt:week+1000,
    nonce:`member:${nonce++}`,graphId:`${networkId}:membership`},resolver);
};
const mission=()=>({scopeDigest:scope,environmentDigest:environment,betaVersion:network.context().betaVersion});
for(const c of q.candidates){
  let key=null;
  try{
    const week=c.week??0, expiry=c.expiry??100, owner=c.owner??members[0];
    const rights=c.rights??(c.shared?{shareable:true,retrieve:'network',execute:'network',compose:'network',export:false}:
      {shareable:false,retrieve:[owner],execute:[owner],compose:[owner],export:false});
    const payload={schema:'local-scientific-artifact/v1',artifactSha256:c.artifact_sha256,
      contentEncoding:c.content_encoding,content:c.artifact_content,
      provenance:'researcher-constructed learning code; local numerical learning; simulated network authority'};
    const manifest={id:c.id,version:String(c.version),ownerAgent:owner,
      implementationDigest:c.artifact_sha256,equivalenceKey:c.equivalence_key??`${c.id}-v${c.version}`,
      scopeDigest:scope,environmentDigest:environment,expiresAt:expiry,
      prerequisitePins:c.prerequisite_pins??[],components:c.components??[],rights,
      payloadDigest:contentDigest(payload,'beyond-beta-private-payload')};
    const submitted=network.submitCandidate(manifest,{privatePayload:payload,now:week});
    key=submitted.key;owners.set(key,owner);
    const context=network.context(), comparator=contentDigest(c.comparison_id??q.beta_version);
    const bindings={candidateId:c.id,candidateVersion:String(c.version),candidateDigest:submitted.candidateDigest,
      betaVersion:context.betaVersion,policyVersion:context.policyVersion,scopeDigest:scope,
      environmentDigest:environment,comparisonUniverseDigest:combineComparisonDigest(network.inventoryDigest(key),comparator),
      evaluatedAt:week,expiresAt:expiry,prerequisitePins:manifest.prerequisitePins};
    const assessment=assessAlpha({bindings,pairedTrials:c.paired_trials??[],
      lifecycleCostCents:c.lifecycle_cost_cents??0,evaluationCostCents:c.evaluation_cost_cents??0,
      forecastEligibleUses:c.forecast_uses??0,correctnessChecksPassed:c.correctness_passed===true,
      alreadyAvailable:c.already_available===true});
    network.attachEvidence(key,{mode:'OBSERVED_LOCAL_TESTS',replayAvailable:c.replay_available===true,boundaryPass:c.boundary_passed===true,
      blockedClaimsPresent:false,artifactDigest:c.artifact_sha256,replayDigest:assessment.observedPairsDigest,
      provenanceDigest:contentDigest({artifact:c.artifact_sha256,assay:c.provenance_digest??'local-test-observations',
        money:'ASSUMED_RESOURCE_VALUE',frontierComparison:false})},week);
    const assessed=network.recordAssessment(key,assessment,week,{declaredComparatorDigest:comparator});
    let admission=null;
    if(assessed.ok){
      const b=network.validationBinding(key),validator='validator.agent.agi.eth';
      const attestation=createFixtureAttestation(b,{agent:validator,signer:`fixture:${validator}`,
        snapshotId:context.currentSnapshotId,issuedAt:week,expiresAt:b.expiresAt,
        nonce:`validation:${nonce++}`,graphId:`${networkId}:${owner}`},resolver);
      const validated=network.validate(key,[attestation],week);
      if(validated.ok)admission=signTransition(key,'admit',{},week);
    }
    rows.push({id:c.id,key,assessment,assessed,admission,state:network.inspect(key,week),
      researchAuthority:'FIXTURE_ONLY',productionAdmission:'NOT_QUALIFIED',frontierAlpha:'UNMEASURED'});
  }catch(error){rows.push({id:c.id,key,error:error.message,productionAdmission:'NOT_QUALIFIED'});}
}
for(const op of q.operations){
  try{
    let result;
    const week=op.week??1, member=op.member??members[1];
    if(op.action==='discover')result=network.discover(memberProof(member,week),mission(),week);
    else if(op.action==='retrieve'||op.action==='execute'||op.action==='compose'||op.action==='export'){
      result=network.requestReuse(op.key,memberProof(member,week),{...mission(),...(op.mission??{})},
        {right:op.action,dryRun:op.dry_run??false},week);
      if(result.payload){
        const p=result.payload;
        result.transferredArtifact={sha256:p.artifactSha256,contentEncoding:p.contentEncoding,content:p.content};
        delete result.payload;
      }
    }else if(op.action==='revoke'||op.action==='retire')
      result=signTransition(op.key,op.action,{reason:op.reason??'declared research lifecycle control'},week);
    else if(op.action==='beta-update'){
      network.advanceBeta(op.beta_version,week,op.baseline_keys??[]);result={ok:true};
    }else if(op.action==='inspect')result=network.inspect(op.key,week);
    else throw Error('UNKNOWN_RESEARCH_OPERATION');
    checks.push({operation:op,result});
  }catch(error){checks.push({operation:op,result:{ok:false,reasons:[error.message]}});}
}
process.stdout.write(JSON.stringify({schema:'capability-opportunity-lifecycle-replay/v1',candidates:rows,
  operations:checks,snapshot:network.snapshot({includeCiphertext:false}),
  liveCapsuleAdmission:'NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE',
  actualFrontierCalls:0,actualReceiptsMicroUSD:0,
  distinction:'Research fixture access replays local artifact bytes; it neither deploys a protected service nor runs the artifact.'}));
