import {canonicalize,digest,graphEpochRoot} from './commitments.mjs';

export const FIXTURE_MODE='FIXTURE_ONLY';
export const ATTESTATION_ACTION='ISSUE_SKILL_ATTESTATION';
export const ROOT_ACTION='COMMIT_GRAPH_ROOT';
export const FIXTURE_PROTOCOL='AGI_ALPHA_SIMULATED_AUTHORITY_V1';
const HEX=/^[0-9a-f]{64}$/;
const AGENT=/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth$/;
const SKILL_KEYS=['id','version','implementationDigest','dependencyDigests','scopeDigest','environmentDigest','policyDigest','evidenceDigest','rightsDigest','expiresAt'];
const clone=v=>JSON.parse(canonicalize(v));
const equal=(a,b)=>canonicalize(a)===canonicalize(b);
const time=v=>Number.isSafeInteger(v)&&v>=0;
const listed=(xs,x)=>Array.isArray(xs)?xs.includes(x):xs instanceof Set?xs.has(x):false;

function freeze(v) { if(v&&typeof v==='object') {for(const x of Object.values(v)) freeze(x); Object.freeze(v);} return v; }
export function eligibleAgent(name) {return typeof name==='string'&&AGENT.test(name);}
export function fixtureNode(name) {return 'fixture-name-digest:'+digest(name,'fixture-name-not-ens-namehash');}
export function skillBinding(skill) {
  const out=Object.fromEntries(SKILL_KEYS.map(k=>[k,skill?.[k]]));
  if(typeof out.id!=='string'||!out.id||typeof out.version!=='string'||!out.version||!time(out.expiresAt)) throw new TypeError('INVALID_SKILL_BINDING');
  for(const k of ['implementationDigest','scopeDigest','environmentDigest','policyDigest','evidenceDigest','rightsDigest']) if(!HEX.test(out[k]??'')) throw new TypeError('INVALID_SKILL_DIGEST');
  if(!Array.isArray(out.dependencyDigests)||out.dependencyDigests.some(d=>typeof d!=='string'||!HEX.test(d))) throw new TypeError('INVALID_DEPENDENCY_DIGESTS');
  return clone(out);
}
export function envelopeDigest(envelope) {
  const payload=Object.fromEntries(Object.entries(envelope).filter(([k])=>k!=='signature'));
  return digest(payload,'fixture-envelope-not-cryptographic-signature');
}
export function fixtureSignature(payload) {
  return {scheme:'FIXTURE_NOT_CRYPTOGRAPHIC',protocol:FIXTURE_PROTOCOL,signer:payload.signer,payloadDigest:envelopeDigest(payload)};
}
export function createFixtureResolver(fixture) {
  const data=freeze(clone(fixture));
  if(data.schema!=='agi-alpha.authority-fixture.v1'||data.mode!==FIXTURE_MODE||data.protocol!==FIXTURE_PROTOCOL||!Array.isArray(data.snapshots)) throw new TypeError('UNSUPPORTED_AUTHORITY_FIXTURE');
  const ids=new Set();
  for(const snapshot of data.snapshots) {if(ids.has(snapshot.id)) throw new TypeError('DUPLICATE_SNAPSHOT_ID'); ids.add(snapshot.id);}
  return Object.freeze({mode:FIXTURE_MODE,protocol:FIXTURE_PROTOCOL,resolveSnapshot(id){return data.snapshots.find(s=>s.id===id)??null;},verifyFixtureSignature(envelope){
    const signature=envelope?.signature;
    return {mode:FIXTURE_MODE,protocol:FIXTURE_PROTOCOL,cryptographicAuthentication:false,ok:signature?.scheme==='FIXTURE_NOT_CRYPTOGRAPHIC'&&signature?.protocol===FIXTURE_PROTOCOL&&signature?.signer===envelope?.signer&&signature?.payloadDigest===envelopeDigest(envelope)};
  }});
}

export function snapshotBinding(snapshot) {
  if(!snapshot) throw new TypeError('MISSING_AUTHORITY_SNAPSHOT');
  return {authoritySnapshotId:snapshot.id,authorityStateDigest:digest(snapshot,'authority-snapshot'),blockNumber:snapshot.blockNumber,blockHash:snapshot.blockHash,registrySchema:snapshot.registrySchema,registryCodeDigest:snapshot.registryCodeDigest};
}

function makeEnvelope(payload,options,resolver) {
  const ownedPayload=freeze(clone(payload)),ownedOptions=freeze(clone(options));
  const {agent='research.agent.agi.eth',signer='fixture:owner-1',snapshotId='fixture-state-100',issuedAt=100,expiresAt=500,nonce,graphId}=ownedOptions;
  const snapshot=freeze(clone(resolver.resolveSnapshot(snapshotId)));
  const envelope={...ownedPayload,mode:FIXTURE_MODE,agent,signer,...snapshotBinding(snapshot),issuedAt,expiresAt,nonce,chainId:snapshot.chainId,registry:snapshot.registry,graphId};
  return {...envelope,signature:fixtureSignature(envelope)};
}
export function createFixtureAttestation(skill,options,resolver) {
  return makeEnvelope({schema:'agi-alpha.skill-attestation.v1',action:ATTESTATION_ACTION,skill:skillBinding(skill),verdict:'PASS_WITH_SCOPE'},options,resolver);
}
export function createFixtureRoot(packet,options,resolver) {
  const record=makeEnvelope({...packet,action:ROOT_ACTION},options,resolver);
  if(record.graphRoot!==graphEpochRoot(record)) throw new TypeError('ROOT_OPTIONS_CHANGED_COMMITMENT');
  return record;
}

function assessSnapshot(snapshot,envelope,at,reasons,prefix) {
  if(!snapshot) {reasons.push(prefix+'MISSING_SNAPSHOT'); return null;}
  if(snapshot.mode!==FIXTURE_MODE||snapshot.registrySchema!=='ENS_V1_FIXTURE'||snapshot.chainId!==envelope.chainId||snapshot.registry!==envelope.registry||!HEX.test(snapshot.registryCodeDigest??'')||!HEX.test(snapshot.blockHash??'')) reasons.push(prefix+'UNSUPPORTED_REGISTRY_STATE');
  if(!time(snapshot.blockNumber)||!time(snapshot.observedAt)||!time(snapshot.validUntil)||snapshot.observedAt>at||at>=snapshot.validUntil) reasons.push(prefix+'STATE_TIME_INVALID');
  const name=snapshot.names?.[envelope.agent];
  if(!name) {reasons.push(prefix+'IDENTITY_NOT_FOUND'); return null;}
  if(name.node!==fixtureNode(envelope.agent)||name.normalizedName!==envelope.agent||!Number.isSafeInteger(name.authorityEpoch)||name.authorityEpoch<1) reasons.push(prefix+'IDENTITY_BINDING_INVALID');
  if(!time(name.validFrom)||!time(name.expiresAt)||at<name.validFrom||at>=name.expiresAt||name.revoked===true||name.retired===true) reasons.push(prefix+'IDENTITY_INACTIVE');
  if(name.wrapped===true) {
    if(name.registryOwner!==name.wrapper||typeof name.wrappedOwner!=='string'||!name.wrappedOwner||!time(name.wrapperExpiry)||at>=name.wrapperExpiry) reasons.push(prefix+'WRAPPER_AUTHORITY_INVALID');
  } else if(name.wrapped!==false||typeof name.registryOwner!=='string'||!name.registryOwner||name.registryOwner===name.wrapper) reasons.push(prefix+'OWNER_AUTHORITY_INVALID');
  return name;
}

function operationAuthority(name,envelope,at,policyDigest,reasons,prefix) {
  if(!name) return;
  const owner=name.wrapped?name.wrappedOwner:name.registryOwner;
  let controlled=envelope.signer===owner||listed(name.operatorsForAll,envelope.signer);
  const delegation=(name.delegations??[]).find(d=>d.signer===envelope.signer&&d.delegator===owner&&d.authorityEpoch===name.authorityEpoch&&listed(d.actions,envelope.action)&&time(d.notBefore)&&time(d.expiresAt)&&d.notBefore<=at&&at<d.expiresAt&&d.revoked!==true&&(d.graphId===null||d.graphId===envelope.graphId)&&(d.policyDigest===null||d.policyDigest===policyDigest));
  controlled=controlled||Boolean(delegation);
  if(!controlled) reasons.push(prefix+'SIGNER_NOT_CONTROLLER_OR_DELEGATE');
  if(!listed(name.grants?.[envelope.action],envelope.signer)) reasons.push(prefix+'OPERATION_NOT_GRANTED');
}

function authenticateEnvelope(envelope,context,resolver,action,policyDigest) {
  const historyReasons=[], currentReasons=[];
  if(context?.mode!=='FIXTURE_ONLY'||envelope?.mode!=='FIXTURE_ONLY'||resolver?.mode!=='FIXTURE_ONLY'||resolver?.protocol!==FIXTURE_PROTOCOL) return {historyReasons:['LIVE_IDENTITY_ENFORCEMENT_NOT_RUN'],currentReasons:['LIVE_IDENTITY_ENFORCEMENT_NOT_RUN'],historical:null,current:null,mode:context?.mode??'UNKNOWN'};
  if(!eligibleAgent(envelope.agent)) historyReasons.push('INELIGIBLE_DIRECT_AGENT');
  if(envelope.action!==action) historyReasons.push('WRONG_OPERATION_DOMAIN');
  if(typeof envelope.signer!=='string'||!envelope.signer.startsWith('fixture:')) historyReasons.push('NONFIXTURE_SIGNER');
  if(envelope.chainId!==context.chainId||envelope.registry!==context.registry||envelope.graphId!==context.graphId||policyDigest!==context.policyDigest) currentReasons.push('CONTEXT_REPLAY');
  if(!time(envelope.issuedAt)||!time(envelope.expiresAt)||envelope.expiresAt<=envelope.issuedAt||typeof envelope.nonce!=='string'||!envelope.nonce) historyReasons.push('INVALID_ENVELOPE_TIME_OR_NONCE');
  if(!time(context.now)||context.now<envelope.issuedAt) currentReasons.push('CURRENT_TIME_INVALID');
  const historicalSnapshot=resolver.resolveSnapshot(envelope.authoritySnapshotId);
  let historical=null;
  if(historicalSnapshot) {
    if(!equal(snapshotBinding(historicalSnapshot),Object.fromEntries(Object.keys(snapshotBinding(historicalSnapshot)).map(k=>[k,envelope[k]])))) historyReasons.push('HISTORICAL_STATE_BINDING_MISMATCH');
    historical=assessSnapshot(historicalSnapshot,envelope,envelope.issuedAt,historyReasons,'HISTORICAL_');
    operationAuthority(historical,envelope,envelope.issuedAt,policyDigest,historyReasons,'HISTORICAL_');
  } else historyReasons.push('HISTORICAL_MISSING_SNAPSHOT');
  const signature=resolver.verifyFixtureSignature(envelope);
  if(signature?.ok!==true||signature?.mode!==FIXTURE_MODE||signature?.protocol!==FIXTURE_PROTOCOL||signature?.cryptographicAuthentication!==false) historyReasons.push('INVALID_FIXTURE_SIGNATURE');
  const currentSnapshot=resolver.resolveSnapshot(context.currentSnapshotId);
  const current=assessSnapshot(currentSnapshot,envelope,context.now,currentReasons,'CURRENT_');
  if(currentSnapshot&&(currentSnapshot.registryCodeDigest!==envelope.registryCodeDigest||currentSnapshot.registrySchema!==envelope.registrySchema)) currentReasons.push('REGISTRY_CHANGED_REVALIDATION_REQUIRED');
  if(currentSnapshot&&currentSnapshot.blockNumber<envelope.blockNumber) currentReasons.push('CURRENT_STATE_PREDATES_ATTESTATION');
  operationAuthority(current,envelope,context.now,policyDigest,currentReasons,'CURRENT_');
  if(historical&&current&&(current.authorityEpoch!==historical.authorityEpoch||(current.wrapped?current.wrappedOwner:current.registryOwner)!==(historical.wrapped?historical.wrappedOwner:historical.registryOwner))) currentReasons.push('AUTHORITY_CHANGED_REVALIDATION_REQUIRED');
  if(context.now>=envelope.expiresAt) currentReasons.push('ATTESTATION_EXPIRED');
  const nonceKey=[envelope.graphId,envelope.action,envelope.agent,envelope.nonce].join('|');
  if(context.intent!=='reuse'&&context.intent!=='inspect'&&(listed(context.seenNonces,nonceKey)||listed(context.seenNonces,envelope.nonce))) currentReasons.push('NONCE_REPLAY');
  if(listed(context.revokedAttestations,envelopeDigest(envelope))||listed(context.revokedAttestations,envelope.nonce)) currentReasons.push('ATTESTATION_REVOKED');
  return {historyReasons,currentReasons,historical,current,mode:FIXTURE_MODE,nonceKey};
}

function result(state,extra={}) {
  const historyValid=state.historyReasons.length===0;
  const currentReuseAllowed=historyValid&&state.currentReasons.length===0;
  return {ok:currentReuseAllowed,reasons:[...new Set([...state.historyReasons,...state.currentReasons])],historyValid,currentReuseAllowed,mode:state.mode,liveIdentityEnforcement:'NOT_RUN',cryptographicAuthentication:false,nonceKey:state.nonceKey??null,...extra};
}

export function authenticateAttestation(attestation,skill,context,fixtureResolver) {
  let mode='UNKNOWN';
  try {
    const a=freeze(clone(attestation)), bound=freeze(skillBinding(skill)), c=freeze(clone(context));
    mode=c.mode??'UNKNOWN';
    const state=authenticateEnvelope(a,c,fixtureResolver,ATTESTATION_ACTION,bound.policyDigest);
    if(a.schema!=='agi-alpha.skill-attestation.v1') state.historyReasons.push('UNSUPPORTED_ATTESTATION_SCHEMA');
    if(!equal(a.skill,bound)) state.historyReasons.push('SKILL_OR_EVIDENCE_CONTEXT_MISMATCH');
    if(a.verdict!=='PASS_WITH_SCOPE') state.historyReasons.push('TECHNICAL_VERDICT_NOT_ADMITTED');
    if(a.issuedAt>=bound.expiresAt) state.historyReasons.push('SKILL_EXPIRED_AT_ISSUANCE');
    if(c.now>=bound.expiresAt) state.currentReasons.push('SKILL_EXPIRED');
    if(c.evidenceAvailable!==true) state.currentReasons.push('EVIDENCE_UNAVAILABLE');
    const skillKey=bound.id+'@'+bound.version;
    if(listed(c.revokedSkills,skillKey)||listed(c.revokedSkills,bound.id)) state.currentReasons.push('SKILL_REVOKED');
    if(listed(c.supersededSkills,skillKey)||listed(c.supersededSkills,bound.id)) state.currentReasons.push('SKILL_SUPERSEDED');
    for(const [contextKey,skillKey2] of [['scopeDigest','scopeDigest'],['environmentDigest','environmentDigest'],['rightsDigest','rightsDigest']]) if(c[contextKey]!==bound[skillKey2]) state.currentReasons.push('CURRENT_'+contextKey.toUpperCase()+'_MISMATCH');
    return result(state,{skillId:bound.id,skillVersion:bound.version});
  } catch(error) {return {ok:false,reasons:['MALFORMED_ATTESTATION',String(error.message)],historyValid:false,currentReuseAllowed:false,mode,liveIdentityEnforcement:'NOT_RUN',cryptographicAuthentication:false,nonceKey:null};}
}

export function authorizeRoot(rootRecord,context,fixtureResolver) {
  let mode='UNKNOWN';
  try {
    const r=freeze(clone(rootRecord)), c=freeze(clone(context));
    mode=c.mode??'UNKNOWN';
    const state=authenticateEnvelope(r,c,fixtureResolver,ROOT_ACTION,r.policyDigest);
    if(r.schema!=='agi-alpha.graph-epoch.v1'||graphEpochRoot(r)!==r.graphRoot) state.historyReasons.push('GRAPH_ROOT_BINDING_MISMATCH');
    if(r.previousRoot!==c.expectedPreviousRoot||r.epoch!==c.expectedEpoch) state.currentReasons.push('ROOT_COMPARE_AND_SWAP_MISMATCH');
    if(c.expectedGraphRoot!==undefined&&r.graphRoot!==c.expectedGraphRoot) state.currentReasons.push('UNEXPECTED_GRAPH_ROOT');
    if(listed(c.revokedRoots,r.graphRoot)) state.currentReasons.push('GRAPH_ROOT_REVOKED');
    if(c.admissionsVerified!==true) state.currentReasons.push('SKILL_ADMISSIONS_NOT_VERIFIED');
    if(c.lifecycleEvidenceVerified!==true) state.currentReasons.push('LIFECYCLE_EVIDENCE_NOT_VERIFIED');
    return result(state,{authorizedOperation:ROOT_ACTION});
  } catch(error) {return {ok:false,reasons:['MALFORMED_ROOT',String(error.message)],historyValid:false,currentReuseAllowed:false,mode,liveIdentityEnforcement:'NOT_RUN',cryptographicAuthentication:false,nonceKey:null};}
}
