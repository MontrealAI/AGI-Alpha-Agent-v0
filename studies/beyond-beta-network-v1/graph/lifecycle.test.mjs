// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash,randomBytes} from 'node:crypto';
import {createSkillNetwork} from './lifecycle.mjs';
import {createModeledAuthority,createModeledNetwork} from './simulation_adapter.mjs';
import {contentDigest,clone} from './encoding.mjs';
import {encryptCapsule,decryptCapsule} from './crypto_capsule.mjs';
import {assessAlpha} from '../model/alpha_gate.mjs';
import {createFixtureResolver,createFixtureAttestation,createFixtureRoot,fixtureSignature,eligibleAgent} from '../upstream/graph/authority.mjs';
import {verifyEpochInclusion,validateRootHistory} from '../upstream/graph/commitments.mjs';

const people=['atlas.agent.agi.eth','lyra.agent.agi.eth','orion.agent.agi.eth'];
const scope=contentDigest('synthetic-scope'),environment=contentDigest('synthetic-environment');
const evidence=id=>({mode:'MODELED',replayAvailable:true,boundaryPass:true,blockedClaimsPresent:false,
  artifactDigest:contentDigest(id),replayDigest:contentDigest([id,'replay']),provenanceDigest:contentDigest([id,'synthetic-provenance'])});
let probeNonce=0;
function assessed(bindings,{delta=2000,cost=1000,alreadyAvailable=false,checks=true,probeTag=`probe-${probeNonce++}`}={}){
  return assessAlpha({bindings,pairedTrials:Array.from({length:6},(_,i)=>({probeId:`${probeTag}:${i}`,clusterId:`mission-${i}`,fresh:true,
    baseline:{netMissionValueCents:1000},candidate:{netMissionValueCents:1000+delta}})),lifecycleCostCents:cost,evaluationCostCents:100,
    forecastEligibleUses:20,alreadyAvailable,correctnessChecksPassed:checks});
}
function harness({fixture=createModeledAuthority(people),policy={},execute=true,baselineEquivalenceKeys=[]}={}){
  const resolver=createFixtureResolver(fixture),networkId='synthetic-graph-controls';let nonce=0;
  const n=createSkillNetwork({networkId,policy,betaVersion:'beta-1',scopeDigest:scope,environmentDigest:environment,
    authorityFixture:fixture,currentSnapshotId:fixture.snapshots[0].id,baselineEquivalenceKeys,
    executionAuthorizer:()=>({allowed:execute,mode:'SYNTHETIC_POLICY_ONLY'})});
  const ownerSigner=agent=>{const name=resolver.resolveSnapshot(n.context().currentSnapshotId).names[agent];return name.wrapped?name.wrappedOwner:name.registryOwner;};
  const mission={scopeDigest:scope,environmentDigest:environment};
  function candidate(id,{owner=people[0],expiresAt=80,prerequisitePins=[],components=[],rights,
    equivalenceKey=id,payload={method:'PRIVATE-CAPSULE-SYNTHETIC-METHOD'},implementationDigest=contentDigest(id)}={},week=0){
    const manifest={id,version:'1',ownerAgent:owner,implementationDigest,equivalenceKey,scopeDigest:scope,environmentDigest:environment,
      expiresAt,prerequisitePins,components,rights:rights??{shareable:true,retrieve:'network',execute:'network',export:false,compose:'network'},
      payloadDigest:payload===null?null:contentDigest(payload,'beyond-beta-private-payload')};
    const result=n.submitCandidate(manifest,{privatePayload:payload,now:week});return {...result,manifest,payload};
  }
  function report(c,week=1,options={}){
    const ctx=n.context();return assessed({candidateId:c.manifest.id,candidateVersion:c.manifest.version,candidateDigest:c.candidateDigest,
      betaVersion:ctx.betaVersion,policyVersion:ctx.policyVersion,scopeDigest:scope,environmentDigest:environment,
      comparisonUniverseDigest:n.inventoryDigest(c.key),evaluatedAt:week,expiresAt:Math.min(c.manifest.expiresAt,week+30),
      prerequisitePins:c.manifest.prerequisitePins},options);
  }
  function attestation(c,week=1,{agent=people[1],signer=ownerSigner(agent),mutate}={}){
    const binding=n.validationBinding(c.key),ctx=n.context();
    const a=clone(createFixtureAttestation(binding,{agent,signer,snapshotId:ctx.currentSnapshotId,issuedAt:week,expiresAt:binding.expiresAt,
      nonce:`validation-${nonce++}`,graphId:`${networkId}:${c.manifest.ownerAgent}`},resolver));
    if(mutate)mutate(a);return a;
  }
  function validated(c,week=1,options={}){
    n.attachEvidence(c.key,evidence(c.manifest.id),week);const a=report(c,week,options);
    assert.equal(n.recordAssessment(c.key,a,week).ok,true);assert.equal(n.validate(c.key,[attestation(c,week)],week).ok,true);return a;
  }
  function signed(proposal,week=1,{agent=proposal.command.actor,signer=ownerSigner(agent),mutate}={}){
    const root=createFixtureRoot(proposal.packet,{agent,signer,snapshotId:n.context().currentSnapshotId,issuedAt:week,expiresAt:week+200,
      nonce:`root-${nonce++}`,graphId:proposal.packet.graphId},resolver);if(mutate)mutate(root);return root;
  }
  function transition(c,action,week=1,options={}){const p=n.prepareTransition(c.key,action,options,week);return n.commitTransition(p,signed(p,week),week);}
  function admitted(id,options={},week=1){const c=candidate(id,options,week);validated(c,week);assert.equal(transition(c,'admit',week).ok,true);return c;}
  function member(agent=people[2],week=1){const binding=n.membershipBinding(agent);return createFixtureAttestation(binding,{agent,signer:ownerSigner(agent),
    snapshotId:n.context().currentSnapshotId,issuedAt:week,expiresAt:week+200,nonce:`member-${nonce++}`,graphId:`${networkId}:membership`},resolver);}
  return {n,fixture,resolver,networkId,mission,candidate,report,attestation,validated,signed,transition,admitted,member};
}

const results=[];
function test(name,fn){try{fn();results.push({name,passed:true});}catch(error){results.push({name,passed:false,error:error.stack});}}
test('direct-agent-label-boundary',()=>{assert.equal(eligibleAgent('atlas.agent.agi.eth'),true);
  for(const s of ['x.atlas.agent.agi.eth','atlas.club.agi.eth','atlas.agent.agi.eth.evil','agent.agi.eth'])assert.equal(eligibleAgent(s),false);});
test('candidate-and-evidence-alone-cannot-influence',()=>{const h=harness(),c=h.candidate('draft');
  assert.equal(h.n.discover(h.member(people[1],1),h.mission,1).capabilities.length,0);
  assert.throws(()=>h.n.prepareTransition(c.key,'admit',{},1),/BYPASS/);
  h.n.attachEvidence(c.key,evidence('draft'),1);assert.throws(()=>h.n.prepareTransition(c.key,'admit',{},1),/BYPASS/);});
test('positive-alpha-still-requires-validation',()=>{const h=harness(),c=h.candidate('positive');h.n.attachEvidence(c.key,evidence('positive'),1);
  assert.equal(h.n.recordAssessment(c.key,h.report(c),1).ok,true);assert.throws(()=>h.n.prepareTransition(c.key,'admit',{},1),/BYPASS/);});
test('nonpositive-complete-alpha-rejected',()=>{const h=harness(),c=h.candidate('cost-failure');h.n.attachEvidence(c.key,evidence('cost-failure'),1);
  assert.equal(h.n.recordAssessment(c.key,h.report(c,1,{cost:100000}),1).ok,false);assert.equal(h.n.inspect(c.key,1).status,'REJECTED');});
test('beta-equivalence-rejected-even-with-positive-score',()=>{const h=harness({baselineEquivalenceKeys:['ordinary-tool']}),c=h.candidate('redundant',{equivalenceKey:'ordinary-tool'});
  h.n.attachEvidence(c.key,evidence('redundant'),1);assert.ok(h.n.recordAssessment(c.key,h.report(c),1).reasons.includes('REDUNDANT_WITH_BETA'));});
test('existing-capability-redundancy-rejected',()=>{const h=harness();h.admitted('existing',{equivalenceKey:'shared-method'});
  const c=h.candidate('duplicate',{equivalenceKey:'shared-method'},1);h.n.attachEvidence(c.key,evidence('duplicate'),1);
  assert.ok(h.n.recordAssessment(c.key,h.report(c),1).reasons.includes('REDUNDANT_WITH_AVAILABLE_CAPABILITY'));});
test('all-members-discover-shareable-admission-without-use',()=>{const h=harness(),c=h.admitted('available');
  for(const person of people)assert.equal(h.n.discover(h.member(person,1),h.mission,1).capabilities[0].key,c.key);
  assert.equal(h.n.snapshot().events.filter(e=>e.type==='authorized-reuse').length,0);});
test('shareable-rights-cannot-be-restricted-to-selected-recipients',()=>{const h=harness();
  assert.throws(()=>h.candidate('unfair-share',{rights:{shareable:true,retrieve:[people[0]],execute:'network',compose:'network',export:false}}),/NETWORK_AVAILABILITY/);});
test('creator-cannot-self-validate',()=>{const h=harness(),c=h.candidate('self');h.n.attachEvidence(c.key,evidence('self'),1);h.n.recordAssessment(c.key,h.report(c),1);
  assert.ok(h.n.validate(c.key,[h.attestation(c,1,{agent:people[0]})],1).reasons.includes('CREATOR_CANNOT_SELF_VALIDATE'));});
test('club-validator-cannot-enter-additional-agent-layer',()=>{const h=harness(),c=h.candidate('club');h.n.attachEvidence(c.key,evidence('club'),1);h.n.recordAssessment(c.key,h.report(c),1);
  assert.ok(h.n.validate(c.key,[h.attestation(c,1,{agent:'research.club.agi.eth'})],1).reasons.includes('INELIGIBLE_DIRECT_AGENT'));});
test('nested-validator-cannot-inherit-direct-authority',()=>{const h=harness(),c=h.candidate('nested');h.n.attachEvidence(c.key,evidence('nested'),1);h.n.recordAssessment(c.key,h.report(c),1);
  assert.ok(h.n.validate(c.key,[h.attestation(c,1,{agent:'child.research.agent.agi.eth'})],1).reasons.includes('INELIGIBLE_DIRECT_AGENT'));});
test('wrong-validator-controller-denied',()=>{const h=harness(),c=h.candidate('wrong-controller');h.n.attachEvidence(c.key,evidence('wrong-controller'),1);h.n.recordAssessment(c.key,h.report(c),1);
  assert.equal(h.n.validate(c.key,[h.attestation(c,1,{signer:'fixture:unrelated'})],1).ok,false);});
test('validation-signature-tamper-denied',()=>{const h=harness(),c=h.candidate('tamper');h.n.attachEvidence(c.key,evidence('tamper'),1);h.n.recordAssessment(c.key,h.report(c),1);
  assert.equal(h.n.validate(c.key,[h.attestation(c,1,{mutate:a=>{a.skill.implementationDigest=contentDigest('changed');}})],1).ok,false);});
test('root-publication-needs-creator-control',()=>{const h=harness(),c=h.candidate('writer');h.validated(c);const p=h.n.prepareTransition(c.key,'admit',{},1);
  assert.equal(h.n.commitTransition(p,h.signed(p,1,{signer:'fixture:unrelated'}),1).ok,false);});
test('attester-and-root-operation-domains-are-separate',()=>{const h=harness(),c=h.candidate('operation');h.validated(c);const p=h.n.prepareTransition(c.key,'admit',{},1);
  const r=h.signed(p,1,{mutate:x=>{x.action='ISSUE_SKILL_ATTESTATION';x.signature=fixtureSignature(x);}});assert.equal(h.n.commitTransition(p,r,1).ok,false);});
test('stale-proposal-cannot-overwrite-current-graph',()=>{const h=harness(),c=h.candidate('stale-proposal');h.validated(c);const p=h.n.prepareTransition(c.key,'admit',{},1),r=h.signed(p);
  h.n.recordFailure({id:'separate-failure',reason:'failed search',evidenceDigest:contentDigest('failed')},1);
  assert.equal(h.n.commitTransition(p,r,1).ok,false);});
test('root-replay-cannot-duplicate-admission',()=>{const h=harness(),c=h.candidate('replay');h.validated(c);const p=h.n.prepareTransition(c.key,'admit',{},1),r=h.signed(p);
  assert.equal(h.n.commitTransition(p,r,1).ok,true);assert.equal(h.n.commitTransition(p,r,1).ok,false);});
test('typed-inclusion-and-per-creator-root-chain-replay',()=>{const h=harness(),c=h.admitted('roots');h.transition(c,'promote',1,{alias:'canonical'});
  const s=h.n.snapshot(),root=s.rootHistory[0],artifact=s.rootArtifacts[0],leaf=artifact.forest.classes.skill.records[0];
  assert.equal(verifyEpochInclusion(root,'skill',leaf.record,leaf.proof),true);
  assert.equal(verifyEpochInclusion(root,'policy',leaf.record,leaf.proof),false);
  assert.equal(validateRootHistory(s.rootHistory).integrityOk,true);assert.equal(validateRootHistory(s.rootHistory).ok,false,'Integrity alone is not authority');});
test('canonical-promotion-cannot-bypass-admission',()=>{const h=harness(),c=h.candidate('unproven-canonical');assert.throws(()=>h.n.prepareTransition(c.key,'promote',{alias:'global'},1),/CURRENT_ADMISSION/);});
test('revocation-blocks-ordinary-and-canonical-history-reuse',()=>{const h=harness(),c=h.admitted('revoked');h.transition(c,'promote',1,{alias:'canonical'});const saved=h.n.snapshot();
  assert.equal(h.transition(c,'revoke',2,{reason:'adverse result'}).ok,true);assert.equal(h.n.resolveCanonical('canonical',2),null);
  assert.equal(h.n.requestReuse(c.key,h.member(people[1],2),h.mission,{},2).ok,false);
  assert.equal(h.n.beginRevalidation(c.key,evidence('attempted resurrection'),2).ok,false);
  saved.records[0].status='ADMITTED';assert.equal(h.n.inspect(c.key,2).status,'REVOKED');assert.equal(h.n.snapshot().historyImportSupported,false);});
test('retired-record-cannot-be-overwritten-or-revalidated',()=>{const h=harness(),c=h.admitted('retired');h.transition(c,'retire',2,{reason:'obsolete'});
  assert.throws(()=>h.n.submitCandidate(c.manifest,{privatePayload:c.payload,now:2}),/HISTORY_CANNOT_OVERWRITE/);
  assert.equal(h.n.beginRevalidation(c.key,evidence('old'),2).ok,false);});
test('replacement-must-first-earn-its-own-admission',()=>{const h=harness(),old=h.admitted('old'),next=h.candidate('replacement',{},2);
  assert.throws(()=>h.n.prepareTransition(old.key,'supersede',{replacementKey:next.key,reason:'new edition'},2),/SEPARATE_CURRENT_ADMISSION/);
  h.validated(next,2);h.transition(next,'admit',2);h.transition(old,'supersede',2,{replacementKey:next.key,reason:'new edition'});
  assert.equal(h.n.inspect(old.key,2).eligibility.ok,false);assert.equal(h.n.inspect(next.key,2).eligibility.ok,true);});
test('moving-beta-blocks-old-alpha-until-fresh-revalidation',()=>{const h=harness(),c=h.admitted('moving');h.n.advanceBeta('beta-2',2);
  assert.equal(h.n.inspect(c.key,2).eligibility.ok,false);assert.throws(()=>h.n.advanceBeta('beta-1',3),/ROLL_BACK/);
  assert.equal(h.n.beginRevalidation(c.key,evidence('fresh-beta2'),3).ok,true);assert.equal(h.n.recordAssessment(c.key,h.report(c,3),3).ok,true);
  h.n.validate(c.key,[h.attestation(c,3)],3);assert.equal(h.transition(c,'admit',3).ok,true);assert.equal(h.n.inspect(c.key,3).eligibility.ok,true);});
test('old-tests-cannot-be-relabeled-as-fresh-revalidation',()=>{const h=harness(),c=h.candidate('stale-probes');const old=h.validated(c);h.transition(c,'admit',1);h.n.advanceBeta('beta-2',2);
  h.n.beginRevalidation(c.key,evidence('replay-old'),2);const next=h.report(c,2);next.probeIdsDigest=old.probeIdsDigest;next.observedPairsDigest=old.observedPairsDigest;
  assert.ok(h.n.recordAssessment(c.key,next,2).reasons.includes('PREVIOUS_EVALUATION_CANNOT_BE_RELABELED_FRESH'));});
test('policy-version-change-blocks-prior-validation',()=>{const h=harness(),c=h.admitted('policy');h.n.advancePolicy({version:'alpha-policy-v2'},2);
  assert.equal(h.n.inspect(c.key,2).eligibility.ok,false);assert.throws(()=>h.n.advancePolicy({version:'beyond-beta-alpha-policy-v1'},2),/ROLL_BACK/);});
test('expired-evidence-blocks-reuse-despite-longer-asset-life',()=>{const h=harness(),c=h.admitted('stale-evidence',{expiresAt:80});
  assert.equal(h.n.inspect(c.key,32).eligibility.ok,false);assert.equal(h.n.discover(h.member(people[1],32),h.mission,32).capabilities.length,0);});
test('scope-environment-and-execution-authority-remain-separate',()=>{const h=harness({execute:false}),c=h.admitted('scope');
  assert.equal(h.n.requestReuse(c.key,h.member(),{...h.mission,scopeDigest:contentDigest('other')},{},1).ok,false);
  assert.equal(h.n.requestReuse(c.key,h.member(),h.mission,{right:'retrieve'},1).ok,true);
  assert.ok(h.n.requestReuse(c.key,h.member(),h.mission,{right:'execute'},1).reasons.includes('SEPARATE_MISSION_EXECUTION_AUTHORITY_REQUIRED'));});
test('composition-rechecks-current-dependency-state',()=>{const h=harness(),a=h.admitted('dependency'),b=h.admitted('composition',{
  prerequisitePins:[{id:a.manifest.id,version:a.manifest.version,digest:a.candidateDigest}]},2);
  assert.equal(h.n.requestReuse(b.key,h.member(people[2],2),h.mission,{right:'compose'},2).ok,true);h.transition(a,'revoke',3,{reason:'dependency invalid'});
  assert.ok(h.n.requestReuse(b.key,h.member(people[2],3),h.mission,{right:'compose'},3).reasons.includes('DEPENDENCY_NOT_CURRENT'));});
test('dependency-version-cannot-be-substituted',()=>{const h=harness(),a=h.admitted('pinned');const b=h.candidate('bad-pin',{
  prerequisitePins:[{id:a.manifest.id,version:'99',digest:a.candidateDigest}]},2);h.validated(b,2);
  assert.throws(()=>h.n.prepareTransition(b.key,'admit',{},2),/DEPENDENCY/);});
test('complementary-bundle-does-not-admit-standalone-components',()=>{const h=harness(),c=h.admitted('bundle',{components:[{id:'A',implementationDigest:contentDigest('A')},{id:'B',implementationDigest:contentDigest('B')}]});
  assert.equal(h.n.discover(h.member(),h.mission,1).capabilities.length,1);
  assert.ok(h.n.requestReuse(c.key,h.member(),{...h.mission,requestedComponents:['A']},{right:'compose'},1).reasons.includes('BUNDLE_MUST_RETAIN_VALIDATED_COMPONENTS'));});
test('evidence-loss-fails-closed-and-cannot-be-toggled-back',()=>{const h=harness(),c=h.admitted('lost-evidence');h.n.setEvidenceAvailable(c.key,false,2);
  assert.equal(h.n.inspect(c.key,2).eligibility.ok,false);assert.throws(()=>h.n.setEvidenceAvailable(c.key,true,2),/FRESH_REVALIDATION/);});
test('local-capsule-authentication-context-and-key-controls',()=>{const payload={method:'private synthetic method'},binding={id:'capsule'};
  const a=encryptCapsule(payload,binding),b=encryptCapsule(payload,binding);assert.notEqual(a.envelope.ciphertext,b.envelope.ciphertext);
  assert.deepEqual(decryptCapsule(a.envelope,a.key,binding),payload);
  assert.throws(()=>decryptCapsule(a.envelope,randomBytes(32),binding));assert.throws(()=>decryptCapsule(a.envelope,a.key,{id:'other'}));
  const tampered=clone(a.envelope);tampered.ciphertext='AAAA';assert.throws(()=>decryptCapsule(tampered,a.key,binding));});
test('capsule-private-content-and-keys-absent-from-public-snapshot',()=>{const h=harness();h.admitted('private');const s=JSON.stringify(h.n.snapshot());
  assert.equal(s.includes('PRIVATE-CAPSULE-SYNTHETIC-METHOD'),false);assert.equal(s.includes('"key":{"type":"Buffer"'),false);
  assert.ok(s.includes('AES-256-GCM'));});
test('export-right-distinct-and-copying-limit-explicit',()=>{const h=harness(),privateSkill=h.admitted('no-export');
  assert.equal(h.n.requestReuse(privateSkill.key,h.member(),h.mission,{right:'export'},1).ok,false);
  const c=h.admitted('exportable',{rights:{shareable:true,retrieve:'network',execute:'network',compose:'network',export:'network'}},2);
  const exported=h.n.requestReuse(c.key,h.member(people[2],2),h.mission,{right:'export'},2);assert.equal(exported.ok,true);assert.ok(exported.exportCopyingLimit.includes('can be copied'));
  h.transition(c,'revoke',3,{reason:'later failure'});assert.equal(exported.payload.method,'PRIVATE-CAPSULE-SYNTHETIC-METHOD','Revocation cannot erase previously exported plaintext');});
test('failure-memory-is-separate-from-positive-alpha',()=>{const h=harness();h.n.recordFailure({id:'failure-only',reason:'candidate disproven',evidenceDigest:contentDigest('negative')},1);
  assert.equal(h.n.snapshot().failureMemory[0].positiveCapability,false);assert.equal(h.n.discover(h.member(),h.mission,1).capabilities.length,0);
  assert.throws(()=>h.n.prepareTransition('failure-only','admit',{},1),/UNKNOWN_CANDIDATE/);});
test('protected-evaluation-material-never-enters-shared-capsule',()=>{const h=harness();h.n.protectEvaluationMaterial(['SECRET-HELDOUT-TARGET']);
  assert.throws(()=>h.candidate('leak',{payload:{method:'include SECRET-HELDOUT-TARGET here'}}),/PROTECTED/);
  assert.throws(()=>h.candidate('scorer-leak',{payload:{scorerCode:'synthetic hidden scorer'}}),/PROTECTED/);
  assert.throws(()=>h.candidate('cases-leak',{payload:{evaluationCases:[1,2,3]}}),/PROTECTED/);});
test('identity-rotation-invalidates-prior-creator-authority',()=>{
  const fixture=createModeledAuthority(people),next=clone(fixture.snapshots[0]);next.id='rotated';next.blockNumber=10;next.blockHash=contentDigest('rotated-block');next.observedAt=10;
  next.names[people[0]].authorityEpoch=2;next.names[people[0]].registryOwner='fixture:new-owner';next.names[people[0]].grants={ISSUE_SKILL_ATTESTATION:['fixture:new-owner'],COMMIT_GRAPH_ROOT:['fixture:new-owner']};
  fixture.snapshots.push(next);const h=harness({fixture}),c=h.admitted('identity-rotation');h.n.advanceAuthoritySnapshot('rotated',10);
  assert.equal(h.n.inspect(c.key,10).eligibility.ok,false);assert.throws(()=>h.n.advanceAuthoritySnapshot('network-fixture-state-0',10),/ROLL_BACK/);
});
test('adapter-pure-future-binding-does-not-advance-current-time',()=>{const n=createModeledNetwork({members:people});
  n.assessmentBindings({id:'future',keys:['A'],owner:people[0],week:10,expiryWeek:30,comparisonUniverse:[]});assert.equal(n.context().week,0);});
test('adapter-completion-rechecks-recipient-beta-universe',()=>{const n=createModeledNetwork({members:people}),d={id:'context-change',keys:['A'],owner:people[0],week:4,expiryWeek:30,comparisonUniverse:[]};
  const report=assessed(n.assessmentBindings(d));assert.equal(n.admit({...d,assessment:report,readyWeek:4,comparisonUniverse:['newly-copied-capability']}),false);
  assert.equal(n.available({id:d.id,member:people[1],week:4}),false);});
test('adapter-evidence-expiry-separate-from-asset-lifetime',()=>{const n=createModeledNetwork({members:people}),d={id:'renewable',keys:['A'],owner:people[0],comparisonUniverse:[],week:4,expiryWeek:10,assetExpiryWeek:40};
  assert.ok(n.admit({...d,assessment:assessed(n.assessmentBindings(d)),readyWeek:4,expiryWeek:40}));assert.equal(n.available({id:d.id,member:people[1],week:10}),false);
  const r={...d,week:10,expiryWeek:20};assert.equal(n.revalidate({...r,assessment:assessed(n.assessmentBindings(r)),readyWeek:10,expiryWeek:40}),true);
  assert.equal(n.available({id:d.id,member:people[2],week:10}),true);assert.equal(n.snapshot().records[0].evaluationHistory.length,2);});
test('economic-snapshot-is-reproducible-with-random-capsules-redacted',()=>{
  const a=createModeledNetwork({members:people}),b=createModeledNetwork({members:people});
  const d={id:'reproducible',keys:['A'],owner:people[0],comparisonUniverse:[],week:4,expiryWeek:10,assetExpiryWeek:40};
  const report=assessed(a.assessmentBindings(d));assert.deepEqual(b.assessmentBindings(d),a.assessmentBindings(d));
  assert.ok(a.admit({...d,assessment:report,readyWeek:4}));assert.ok(b.admit({...d,assessment:report,readyWeek:4}));
  assert.deepEqual(a.snapshot({includeCiphertext:false}),b.snapshot({includeCiphertext:false}));
  assert.equal(a.snapshot().records[0].encryptedCapsule.ciphertextIncluded,false);
  assert.notEqual(a.snapshot({includeCiphertext:true}).records[0].encryptedCapsule.ciphertext,
    b.snapshot({includeCiphertext:true}).records[0].encryptedCapsule.ciphertext);
});

const paths=['graph/lifecycle.mjs','graph/simulation_adapter.mjs','graph/encoding.mjs','graph/crypto_capsule.mjs','graph/lifecycle.test.mjs','model/alpha_gate.mjs','upstream/graph/authority.mjs','upstream/graph/commitments.mjs'];
const sourceHashes=Object.fromEntries(paths.map(p=>[p,createHash('sha256').update(readFileSync(new URL(`../${p}`,import.meta.url))).digest('hex')]));
const failed=results.filter(r=>!r.passed);
console.log(JSON.stringify({schema:'beyond-beta-graph-controls/v1',evidence:'OBSERVED_LOCAL_SOFTWARE_CONTROLS',createdAt:new Date().toISOString(),
  controls:results.length,passed:results.length-failed.length,failed:failed.length,results,sourceHashes,
  identityAuthentication:'FIXTURE_ONLY_NOT_CRYPTOGRAPHIC',localEncryption:'REAL_AES_256_GCM_EPHEMERAL_KEYS',
  zeroKnowledgeProofs:'NOT_IMPLEMENTED',liveENS:'NOT_RUN',onchain:'NOT_DEPLOYED',empiricalFrontierAlpha:'NOT_ESTABLISHED',
  jobsClubRoles:'UNCHANGED',actualCustomerJobs:0,actualCollectionsUSD:0},null,2));
if(failed.length)process.exitCode=1;
