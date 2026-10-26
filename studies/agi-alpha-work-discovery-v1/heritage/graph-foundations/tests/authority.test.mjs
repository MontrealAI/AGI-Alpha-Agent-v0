import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {digest,buildForest,buildGraphEpoch,ZERO_ROOT,validateRootHistory} from '../src/commitments.mjs';
import {authenticateAttestation,authorizeRoot,createFixtureResolver,createFixtureAttestation,createFixtureRoot,fixtureSignature,envelopeDigest,eligibleAgent,ATTESTATION_ACTION,ROOT_ACTION} from '../src/authority.mjs';

const fixture=JSON.parse(readFileSync(new URL('../fixtures/authority.json',import.meta.url)));
const copy=x=>structuredClone(x);
const resolver=createFixtureResolver(fixture);
const h=x=>digest(x,'test');
const skill={id:'lock-root-check',version:'1',implementationDigest:h('implementation'),dependencyDigests:[h('packaging')],scopeDigest:h('scope'),environmentDigest:h('environment'),policyDigest:h('policy'),evidenceDigest:h('evidence'),rightsDigest:h('MIT'),expiresAt:600};
const options={nonce:'attestation-1',graphId:'research-graph',issuedAt:100,expiresAt:500};
const baseContext={mode:'FIXTURE_ONLY',now:150,chainId:31337,registry:'fixture:ens-v1',graphId:'research-graph',policyDigest:skill.policyDigest,scopeDigest:skill.scopeDigest,environmentDigest:skill.environmentDigest,rightsDigest:skill.rightsDigest,currentSnapshotId:'fixture-state-100',evidenceAvailable:true};
const attestation=createFixtureAttestation(skill,options,resolver);
const check=(a=attestation,s=skill,c=baseContext,r=resolver)=>authenticateAttestation(a,s,c,r);

test('fixture verifies scoped historical and current admission without a live-auth claim',()=>{
  const r=check(); assert.equal(r.ok,true); assert.equal(r.historyValid,true); assert.equal(r.currentReuseAllowed,true); assert.equal(r.mode,'FIXTURE_ONLY'); assert.equal(r.liveIdentityEnforcement,'NOT_RUN'); assert.equal(r.cryptographicAuthentication,false);
});
test('no live mode accepts fixture authority',()=>{const r=check(attestation,skill,{...baseContext,mode:'LIVE'});assert.equal(r.ok,false);assert.equal(r.historyValid,false);assert.ok(r.reasons.includes('LIVE_IDENTITY_ENFORCEMENT_NOT_RUN'));});
test('name policy supports only exact direct normalized ASCII agents',()=>{
  for(const name of ['research.agent.agi.eth','a-1.agent.agi.eth']) assert.equal(eligibleAgent(name),true);
  for(const name of ['research.club.agi.eth','child.research.agent.agi.eth','agent.agi.eth','research.agent.agi.eth.evil','Research.agent.agi.eth','-bad.agent.agi.eth','é.agent.agi.eth']) assert.equal(eligibleAgent(name),false);
});
for(const agent of ['research.club.agi.eth','child.research.agent.agi.eth']) test('eligible spelling cannot be inherited: '+agent,()=>{
  const a=createFixtureAttestation(skill,{...options,agent},resolver);const r=check(a);assert.equal(r.ok,false);assert.ok(r.reasons.includes('INELIGIBLE_DIRECT_AGENT'));
});
for(const field of ['implementationDigest','scopeDigest','environmentDigest','policyDigest','evidenceDigest','rightsDigest']) test('attestation binds exact '+field,()=>{
  const changed={...skill,[field]:h('changed')};assert.equal(check(attestation,changed).ok,false);
});
test('attestation binds skill ID, version, dependencies and lifetime',()=>{
  for(const change of [{id:'other'},{version:'2'},{dependencyDigests:[h('new')]},{expiresAt:601}]) assert.equal(check(attestation,{...skill,...change}).ok,false);
});
for(const change of [{chainId:1},{registry:'fixture:other-registry'},{graphId:'other-graph'},{policyDigest:h('other-policy')}]) test('cross-context replay rejected '+JSON.stringify(change),()=>{assert.ok(check(attestation,skill,{...baseContext,...change}).reasons.includes('CONTEXT_REPLAY'));});
test('copied payload mutation cannot retain a valid fixture integrity check',()=>{
  const a=copy(attestation);a.skill.evidenceDigest=h('forged');const r=check(a);assert.equal(r.ok,false);assert.ok(r.reasons.includes('INVALID_FIXTURE_SIGNATURE'));assert.equal(attestation.skill.evidenceDigest,skill.evidenceDigest);
});
test('signature tampering is rejected even when every bound object matches',()=>{const a=copy(attestation);a.signature.payloadDigest=h('forged');assert.ok(check(a).reasons.includes('INVALID_FIXTURE_SIGNATURE'));});
test('caller supplied boolean is not simulated signature protocol',()=>{const a=copy(attestation);a.signature={signature_valid:true};assert.equal(check(a).ok,false);});
test('signer must have actual fixture controller or operator/delegation authority',()=>{
  const a=createFixtureAttestation(skill,{...options,signer:'fixture:unrelated'},resolver);assert.ok(check(a).reasons.includes('HISTORICAL_SIGNER_NOT_CONTROLLER_OR_DELEGATE'));
});
test('full-control operators can receive an operation-specific policy grant',()=>{
  const a=createFixtureAttestation(skill,{...options,signer:'fixture:full-operator'},resolver);assert.equal(check(a).ok,true);
});
test('wrapper holder replaces registry wrapper contract as controller',()=>{
  const good=createFixtureAttestation(skill,{...options,agent:'wrapped.agent.agi.eth',signer:'fixture:wrapped-owner'},resolver);assert.equal(check(good).ok,true);
  const bad=createFixtureAttestation(skill,{...options,agent:'wrapped.agent.agi.eth',signer:'fixture:name-wrapper'},resolver);assert.equal(check(bad).ok,false);
});
test('renewal-only approval cannot gain authority even with a policy grant',()=>{
  const a=createFixtureAttestation(skill,{...options,signer:'fixture:renewal-only'},resolver);const r=check(a);assert.equal(r.ok,false);assert.ok(r.reasons.includes('HISTORICAL_SIGNER_NOT_CONTROLLER_OR_DELEGATE'));
});
test('attestation and root delegations are separate permissions',()=>{
  const a=createFixtureAttestation(skill,{...options,signer:'fixture:attestation-delegate'},resolver);assert.equal(check(a).ok,true);
  const b=createFixtureAttestation(skill,{...options,signer:'fixture:root-delegate'},resolver);assert.equal(check(b).ok,false);assert.ok(check(b).reasons.includes('HISTORICAL_OPERATION_NOT_GRANTED'));
});
test('state hash/block identity are signed and exactly matched',()=>{
  for(const change of [{authorityStateDigest:h('other-state')},{blockHash:h('other-block')},{blockNumber:101}]) {const a={...attestation,...change};a.signature=fixtureSignature(a);assert.ok(check(a).reasons.includes('HISTORICAL_STATE_BINDING_MISMATCH'));}
});
test('unknown registry and attestation schemas fail closed',()=>{
  const f=copy(fixture);f.snapshots[0].registrySchema='ENS_V2_UNVERIFIED';const r=createFixtureResolver(f),a=createFixtureAttestation(skill,options,r);assert.equal(check(a,skill,baseContext,r).ok,false);
  const b={...attestation,schema:'unknown'};b.signature=fixtureSignature(b);assert.ok(check(b).reasons.includes('UNSUPPORTED_ATTESTATION_SCHEMA'));
});
test('expiry preserves historical truth while removing current reuse',()=>{
  const r=check(attestation,skill,{...baseContext,now:501});assert.equal(r.historyValid,true);assert.equal(r.currentReuseAllowed,false);assert.ok(r.reasons.includes('ATTESTATION_EXPIRED'));
});
test('a later policy refuses reuse without rewriting the historical authority result',()=>{
  const r=check(attestation,skill,{...baseContext,policyDigest:h('later-policy')});assert.equal(r.historyValid,true);assert.equal(r.ok,false);assert.ok(r.reasons.includes('CONTEXT_REPLAY'));
});
test('authority transfer preserves historical validity but requires fresh authorization',()=>{
  const r=check(attestation,skill,{...baseContext,now:250,currentSnapshotId:'fixture-state-200'});assert.equal(r.historyValid,true);assert.equal(r.currentReuseAllowed,false);assert.ok(r.reasons.includes('AUTHORITY_CHANGED_REVALIDATION_REQUIRED'));
});
test('retired identity cannot authorize current reuse',()=>{
  const f=copy(fixture);f.snapshots[1]=copy(f.snapshots[0]);f.snapshots[1].id='fixture-retired';f.snapshots[1].names['research.agent.agi.eth'].retired=true;
  const r=check(attestation,skill,{...baseContext,currentSnapshotId:'fixture-retired'},createFixtureResolver(f));assert.equal(r.historyValid,true);assert.equal(r.ok,false);assert.ok(r.reasons.includes('CURRENT_IDENTITY_INACTIVE'));
});
test('wrapper expiration blocks admission',()=>{
  const f=copy(fixture);f.snapshots[0].names['wrapped.agent.agi.eth'].wrapperExpiry=99;const r=createFixtureResolver(f),a=createFixtureAttestation(skill,{...options,agent:'wrapped.agent.agi.eth',signer:'fixture:wrapped-owner'},r);assert.equal(check(a,skill,baseContext,r).historyValid,false);
});
test('revoked delegate cannot issue an attestation',()=>{
  const f=copy(fixture);f.snapshots[0].names['research.agent.agi.eth'].delegations[0].revoked=true;const r=createFixtureResolver(f),a=createFixtureAttestation(skill,{...options,signer:'fixture:attestation-delegate'},r);assert.equal(check(a,skill,baseContext,r).historyValid,false);
});
test('delegation is bound to authority epoch and operation',()=>{
  const f=copy(fixture);f.snapshots[0].names['research.agent.agi.eth'].delegations[0].authorityEpoch=2;const r=createFixtureResolver(f),a=createFixtureAttestation(skill,{...options,signer:'fixture:attestation-delegate'},r);assert.equal(check(a,skill,baseContext,r).ok,false);
});
test('nonce reuse blocks repeat admission but not read-only inspection',()=>{
  const key=check().nonceKey;assert.ok(check(attestation,skill,{...baseContext,seenNonces:[key]}).reasons.includes('NONCE_REPLAY'));
  assert.equal(check(attestation,skill,{...baseContext,intent:'reuse',seenNonces:[key]}).ok,true);
});
for(const patch of [{revokedAttestations:[envelopeDigest(attestation)]},{revokedSkills:['lock-root-check@1']},{supersededSkills:['lock-root-check@1']},{evidenceAvailable:false},{scopeDigest:h('different-scope')},{environmentDigest:h('different-environment')},{rightsDigest:h('different-rights')}]) test('current reuse fails while historical validity remains '+JSON.stringify(patch),()=>{
  const r=check(attestation,skill,{...baseContext,...patch});assert.equal(r.historyValid,true);assert.equal(r.ok,false);
});
test('missing current scope or evidence is not permissive',()=>{const c={...baseContext};delete c.scopeDigest;assert.equal(check(attestation,skill,c).ok,false);delete c.evidenceAvailable;assert.equal(check(attestation,skill,c).ok,false);});
test('resolver snapshot is detached from caller mutations and frozen',()=>{
  const f=copy(fixture),r=createFixtureResolver(f);f.snapshots[0].names['research.agent.agi.eth'].registryOwner='fixture:evil';assert.equal(check(attestation,skill,baseContext,r).ok,true);assert.throws(()=>{r.resolveSnapshot('fixture-state-100').names['research.agent.agi.eth'].registryOwner='fixture:evil';},TypeError);
});

const forest=buildForest({skill:[skill],attestation:[attestation],policy:[{policyDigest:skill.policyDigest}]});
const packet=buildGraphEpoch({forest,graphId:'research-graph',agent:'research.agent.agi.eth',chainId:31337,registry:'fixture:ens-v1',epoch:1,policyDigest:skill.policyDigest,snapshotDigest:h('snapshot')});
const root=createFixtureRoot(packet,{...options,nonce:'root-1'},resolver);
const rootContext={...baseContext,expectedPreviousRoot:ZERO_ROOT,expectedEpoch:1,admissionsVerified:true,lifecycleEvidenceVerified:true};
test('root has separate signed authorization and expected predecessor',()=>{assert.equal(authorizeRoot(root,rootContext,resolver).ok,true);assert.equal(authorizeRoot(root,{...rootContext,expectedPreviousRoot:h('stale')},resolver).ok,false);assert.equal(authorizeRoot(root,{...rootContext,expectedEpoch:2},resolver).ok,false);});
test('attestation grant cannot commit root; root grant can',()=>{
  const no=createFixtureRoot(packet,{...options,nonce:'root-no',signer:'fixture:attestation-delegate'},resolver);assert.equal(authorizeRoot(no,rootContext,resolver).ok,false);
  const yes=createFixtureRoot(packet,{...options,nonce:'root-yes',signer:'fixture:root-delegate'},resolver);assert.equal(authorizeRoot(yes,rootContext,resolver).ok,true);
});
test('root writer cannot bypass skill admission or lifecycle evidence',()=>{
  assert.equal(authorizeRoot(root,{...rootContext,admissionsVerified:false},resolver).ok,false);assert.equal(authorizeRoot(root,{...rootContext,lifecycleEvidenceVerified:false},resolver).ok,false);
});
test('revoked root keeps its former historical authorization but cannot currently commit',()=>{const r=authorizeRoot(root,{...rootContext,revokedRoots:[root.graphRoot]},resolver);assert.equal(r.historyValid,true);assert.equal(r.ok,false);});
test('root tamper and wrong operation fail',()=>{
  const r={...root,graphRoot:h('tamper')};r.signature=fixtureSignature(r);assert.equal(authorizeRoot(r,rootContext,resolver).ok,false);
  const a={...root,action:ATTESTATION_ACTION};a.signature=fixtureSignature(a);assert.equal(authorizeRoot(a,rootContext,resolver).ok,false);
});
test('authorized append-only root history checks every operation at its state',()=>{
  const packet2=buildGraphEpoch({...packet,forest,epoch:2,previousRoot:root.graphRoot});
  const root2=createFixtureRoot(packet2,{...options,nonce:'root-2'},resolver);
  const checked=validateRootHistory([root,root2],{authorizer:(record,expected)=>authorizeRoot(record,{...rootContext,...expected},resolver)});assert.equal(checked.ok,true);
  assert.equal(validateRootHistory([root2,root],{authorizer:(record,expected)=>authorizeRoot(record,{...rootContext,...expected},resolver)}).ok,false);
});
test('resolver callback cannot clear caller revocations after context capture',()=>{
  const c={...baseContext,revokedSkills:['lock-root-check@1']};
  const hostile={...resolver,resolveSnapshot(id){c.revokedSkills.length=0;return resolver.resolveSnapshot(id);}};
  const r=check(attestation,skill,c,hostile);assert.equal(r.ok,false);assert.ok(r.reasons.includes('SKILL_REVOKED'));
});
test('resolver callback cannot repair a wrong caller root epoch after capture',()=>{
  const c={...rootContext,expectedEpoch:999};
  const hostile={...resolver,resolveSnapshot(id){c.expectedEpoch=root.epoch;return resolver.resolveSnapshot(id);}};
  const r=authorizeRoot(root,c,hostile);assert.equal(r.ok,false);assert.ok(r.reasons.includes('ROOT_COMPARE_AND_SWAP_MISMATCH'));
});
test('signature resolver cannot mutate the owned root or attestation envelope',()=>{
  const hostile={...resolver,verifyFixtureSignature(value){value.action=ROOT_ACTION;return resolver.verifyFixtureSignature(value);}};
  assert.equal(check(attestation,skill,baseContext,hostile).ok,false);
  const rootHostile={...resolver,verifyFixtureSignature(value){value.epoch=999;return resolver.verifyFixtureSignature(value);}};
  assert.equal(authorizeRoot(root,rootContext,rootHostile).ok,false);
});
test('accessor contexts are rejected before resolver callbacks',()=>{
  let calls=0;const hostile={...resolver,resolveSnapshot(id){calls++;return resolver.resolveSnapshot(id);}};
  const c={...baseContext};Object.defineProperty(c,'now',{enumerable:true,get(){return 150;}});
  assert.equal(check(attestation,skill,c,hostile).ok,false);assert.equal(calls,0);
});
test('fixture-envelope builder owns nested packet data before resolver callbacks',()=>{
  const copied=copy(packet),opts={...options,nonce:'owned-builder'};
  const hostile={...resolver,resolveSnapshot(id){copied.roots.skill=h('late-change');opts.graphId='late-change';return resolver.resolveSnapshot(id);}};
  const built=createFixtureRoot(copied,opts,hostile);assert.equal(built.graphRoot,packet.graphRoot);assert.equal(built.graphId,packet.graphId);assert.equal(built.roots.skill,packet.roots.skill);
});
