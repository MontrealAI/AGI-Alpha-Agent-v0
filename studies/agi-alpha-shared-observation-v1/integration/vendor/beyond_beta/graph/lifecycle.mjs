// SPDX-License-Identifier: Apache-2.0
// Research lifecycle. Identity authentication is an explicit fixture simulation.
import {createFixtureResolver,authenticateAttestation,authorizeRoot,eligibleAgent} from '../upstream/graph/authority.mjs';
import {buildForest,buildGraphEpoch,ZERO_ROOT} from '../upstream/graph/commitments.mjs';
import {clone,contentDigest,same,requireInteger,freezeDeep} from './encoding.mjs';
import {encryptCapsule,decryptCapsule} from './crypto_capsule.mjs';

const HEX=/^[a-f0-9]{64}$/;
const TERMINAL=new Set(['REJECTED','REVOKED','RETIRED','SUPERSEDED']);
export const DEFAULT_POLICY=Object.freeze({version:'beyond-beta-alpha-policy-v1',minimumPairedTrials:6,
  validatorQuorum:1,requireIndependentValidator:true,maxAssessmentAge:104});
const keyOf=m=>`${m.id}@${m.version}`;
const ok=()=>({ok:true,reasons:[]});
const fail=(...reasons)=>({ok:false,reasons:[...new Set(reasons.flat())]});
const checkHash=(h,name)=>{if(!HEX.test(h??''))throw Error(`INVALID_${name}`);return h;};
const safeName=x=>typeof x==='string'&&x.length>0&&x.length<=128;
const rightsAllowed=(rule,agent)=>rule==='network'||Array.isArray(rule)&&rule.includes(agent);
function checkedPolicy(input){
  const p={...DEFAULT_POLICY,...clone(input)};
  if(!safeName(p.version)||!Number.isInteger(p.minimumPairedTrials)||p.minimumPairedTrials<6||p.minimumPairedTrials>24||
    !Number.isInteger(p.validatorQuorum)||p.validatorQuorum<1||p.validatorQuorum>16||
    !Number.isSafeInteger(p.maxAssessmentAge)||p.maxAssessmentAge<1||typeof p.requireIndependentValidator!=='boolean')throw Error('INVALID_ADMISSION_POLICY');
  if(p.allowedValidatorAgents&&(!Array.isArray(p.allowedValidatorAgents)||p.allowedValidatorAgents.some(a=>!eligibleAgent(a))))throw Error('INELIGIBLE_POLICY_VALIDATOR');
  return p;
}
export const combineComparisonDigest=(networkInventoryDigest,declaredComparatorDigest=null)=>declaredComparatorDigest===null?
  networkInventoryDigest:contentDigest({networkInventoryDigest,declaredComparatorDigest},'beyond-beta-complete-comparison-universe');

export function createSkillNetwork({networkId='beyond-beta-research-network-v1',policy={},betaVersion,
  scopeDigest,environmentDigest,authorityFixture,currentSnapshotId,baselineEquivalenceKeys=[],executionAuthorizer=()=>({allowed:false})}={}){
  let currentPolicy=checkedPolicy(policy),currentBeta=String(betaVersion),clock=0,revision=0;
  if(!safeName(currentBeta)||currentBeta==='undefined')throw Error('BETA_VERSION_REQUIRED');
  checkHash(scopeDigest,'SCOPE');checkHash(environmentDigest,'ENVIRONMENT');
  const resolver=createFixtureResolver(authorityFixture),snapshots=clone(authorityFixture.snapshots);
  let snapshotId=currentSnapshotId??snapshots[0]?.id;
  const records=new Map(),vault=new Map(),heads=new Map(),rootHistory=[],rootArtifacts=[],events=[],canonical=new Map(),seenNonces=new Set();
  const usedProbeDigests=new Set(),usedPairDigests=new Set(),failureMemory=[],protectedStrings=new Set(),protectedDigests=new Set();
  const forbiddenFields=new Set(['heldoutseeds','protectedcases','evaluationcases','scorercode','scorer','referenceanswers','privateevaluationdata','evaluationtargets','testanswers']);
  const betaVersions=new Set([currentBeta]),policyVersions=new Set([currentPolicy.version]);
  let baselineKeys=new Set(baselineEquivalenceKeys);
  const policyDigest=()=>contentDigest(currentPolicy,'beyond-beta-admission-policy');
  const tick=now=>{requireInteger(now,'TIME');if(now<clock)throw Error('HISTORICAL_TIME_CANNOT_RESTORE_AUTHORITY');clock=now;};
  const get=key=>{const r=records.get(key);if(!r)throw Error('UNKNOWN_CANDIDATE');return r;};
  const graphId=owner=>`${networkId}:${owner}`;
  const entry=(type,key,detail={})=>{events.push({sequence:events.length,week:clock,type,key,...clone(detail)});revision++;};
  function protectedMaterial(value){
    const walk=x=>{
      if(protectedDigests.has(contentDigest(x,'protected-evaluation-material')))return true;
      if(typeof x==='string')return [...protectedStrings].some(s=>s.length>0&&x.includes(s));
      if(x&&typeof x==='object')return Object.entries(x).some(([k,v])=>forbiddenFields.has(k.toLowerCase().replace(/[^a-z0-9]/g,''))||walk(v));
      return false;
    };return walk(value);
  }
  const context=(owner,binding,now,intent='reuse')=>({mode:'FIXTURE_ONLY',chainId:snapshots[0].chainId,
    registry:snapshots[0].registry,graphId:graphId(owner),policyDigest:policyDigest(),currentSnapshotId:snapshotId,
    now,intent,seenNonces:[...seenNonces],revokedAttestations:[],revokedSkills:[],supersededSkills:[],
    evidenceAvailable:true,scopeDigest:binding.scopeDigest,environmentDigest:binding.environmentDigest,rightsDigest:binding.rightsDigest});
  function validationBinding(key){
    const r=get(key);if(!r.evidence||!r.assessment)throw Error('EVIDENCE_AND_ALPHA_ASSESSMENT_REQUIRED');
    return {id:r.manifest.id,version:r.manifest.version,implementationDigest:r.manifest.implementationDigest,
      dependencyDigests:r.manifest.prerequisitePins.map(p=>p.digest),scopeDigest:r.manifest.scopeDigest,
      environmentDigest:r.manifest.environmentDigest,policyDigest:policyDigest(),
      evidenceDigest:contentDigest({candidate:r.candidateDigest,evidence:r.evidenceDigest,assessment:r.assessmentDigest},'beyond-beta-validation-dossier'),
      rightsDigest:contentDigest(r.manifest.rights,'beyond-beta-rights'),expiresAt:Math.min(r.manifest.expiresAt,r.assessment.expiresAt)};
  }
  function inventoryDigest(excludeKey=null){
    return contentDigest({betaVersion:currentBeta,baselineEquivalenceKeys:[...baselineKeys].sort(),
      capabilities:[...records.values()].filter(r=>r.key!==excludeKey&&r.status==='ADMITTED'&&r.manifest.expiresAt>clock&&
        r.assessment?.betaVersion===currentBeta&&r.assessment?.policyVersion===currentPolicy.version)
        .map(r=>({key:r.key,digest:r.candidateDigest,equivalenceKey:r.manifest.equivalenceKey})).sort((a,b)=>a.key.localeCompare(b.key))},'beyond-beta-comparison-universe');
  }
  function reportReasons(r,now,{checkUniverse=false}={}){
    const a=r.assessment,m=r.manifest,reasons=[];
    if(!r.evidence||!r.evidenceAvailable)reasons.push('EVIDENCE_UNAVAILABLE');
    if(!a)return [...reasons,'ALPHA_ASSESSMENT_MISSING'];
    const expected={candidateId:m.id,candidateVersion:m.version,candidateDigest:r.candidateDigest,betaVersion:currentBeta,
      policyVersion:currentPolicy.version,scopeDigest:m.scopeDigest,environmentDigest:m.environmentDigest};
    for(const [k,v]of Object.entries(expected))if(a[k]!==v)reasons.push(`ASSESSMENT_${k.toUpperCase()}_MISMATCH`);
    if(!Array.isArray(a.prerequisitePins)||!same(a.prerequisitePins,m.prerequisitePins))reasons.push('PREREQUISITE_ASSESSMENT_MISMATCH');
    if(checkUniverse&&a.comparisonUniverseDigest!==combineComparisonDigest(inventoryDigest(r.key),r.declaredComparatorDigest??null))reasons.push('COMPARISON_UNIVERSE_CHANGED');
    if(a.verdict!=='admit'||!Number.isSafeInteger(a.assessedLowerBoundNetCents)||a.assessedLowerBoundNetCents<=0)reasons.push('NO_POSITIVE_NET_ALPHA');
    if(a.alreadyAvailable===true||baselineKeys.has(m.equivalenceKey))reasons.push('REDUNDANT_WITH_BETA');
    if([...records.values()].some(x=>x.key!==r.key&&x.status==='ADMITTED'&&x.manifest.expiresAt>now&&
      x.assessment?.betaVersion===currentBeta&&(x.manifest.implementationDigest===m.implementationDigest||x.manifest.equivalenceKey===m.equivalenceKey)))reasons.push('REDUNDANT_WITH_AVAILABLE_CAPABILITY');
    if(a.freshTests!==true||a.correctnessChecksPassed!==true)reasons.push('FRESH_PAIRED_CHECKS_REQUIRED');
    if(!Number.isInteger(a.pairedTrials)||a.pairedTrials<currentPolicy.minimumPairedTrials||a.pairedTrials>24||
       !Number.isInteger(a.independentClusters)||a.independentClusters<currentPolicy.minimumPairedTrials)reasons.push('INSUFFICIENT_INDEPENDENT_EVIDENCE');
    for(const k of ['probeIdsDigest','observedPairsDigest','comparisonUniverseDigest'])if(!HEX.test(a[k]??''))reasons.push('INVALID_EVIDENCE_BINDING');
    for(const k of ['lifecycleCostCents','evaluationCostCents'])if(!Number.isSafeInteger(a[k])||a[k]<0)reasons.push('INCOMPLETE_COST_ACCOUNTING');
    if(a.completeLifecycleCostCents!==a.lifecycleCostCents+a.evaluationCostCents)reasons.push('COST_ACCOUNTING_MISMATCH');
    if(!Number.isSafeInteger(a.evaluatedAt)||!Number.isSafeInteger(a.expiresAt)||a.evaluatedAt>now||now>=a.expiresAt||
      now-a.evaluatedAt>currentPolicy.maxAssessmentAge||now>=m.expiresAt)reasons.push('STALE_ALPHA_ASSESSMENT');
    return reasons;
  }
  function attestationReasons(r,now){
    if(!r.attestations.length)return ['VALIDATOR_ATTESTATIONS_REQUIRED'];
    const bound=validationBinding(r.key),identities=new Set(),reasons=[];
    for(const a of r.attestations){
      const verdict=authenticateAttestation(a,bound,context(r.manifest.ownerAgent,bound,now),resolver);
      if(!verdict.ok)reasons.push(...verdict.reasons);
      if(currentPolicy.requireIndependentValidator&&a.agent===r.manifest.ownerAgent)reasons.push('CREATOR_CANNOT_SELF_VALIDATE');
      if(currentPolicy.allowedValidatorAgents&&!currentPolicy.allowedValidatorAgents.includes(a.agent))reasons.push('VALIDATOR_NOT_ELIGIBLE_UNDER_POLICY');
      identities.add(a.agent);
    }
    if(identities.size<currentPolicy.validatorQuorum)reasons.push('VALIDATOR_QUORUM_NOT_MET');
    return reasons;
  }
  function eligible(key,now,stack=new Set(),requireAdmitted=true){
    const r=records.get(key);if(!r)return fail('DEPENDENCY_OR_SKILL_MISSING');
    if(stack.has(key))return fail('COMPOSITION_CYCLE');
    const reasons=[];if(requireAdmitted&&r.status!=='ADMITTED')reasons.push(`NOT_ADMITTED:${r.status}`);
    if(TERMINAL.has(r.status))reasons.push('TERMINAL_LIFECYCLE_STATE');
    reasons.push(...reportReasons(r,now),...attestationReasons(r,now));
    if(requireAdmitted&&r.status==='ADMITTED'){
      if(!r.admissionRoot)reasons.push('ADMISSION_ROOT_MISSING');
      else{const bound=validationBinding(key),root=r.admissionRoot;
        const rootGate=authorizeRoot(root,{...context(r.manifest.ownerAgent,bound,now,'inspect'),expectedPreviousRoot:root.previousRoot,
          expectedEpoch:root.epoch,expectedGraphRoot:root.graphRoot,admissionsVerified:true,lifecycleEvidenceVerified:true},resolver);
        if(!rootGate.ok)reasons.push('CURRENT_CREATOR_WRITE_AUTHORITY_INVALID',...rootGate.reasons);
      }
    }
    stack.add(key);
    for(const pin of r.manifest.prerequisitePins){const dep=records.get(`${pin.id}@${pin.version}`);
      if(!dep||dep.candidateDigest!==pin.digest)reasons.push('DEPENDENCY_VERSION_OR_DIGEST_MISMATCH');
      else{const v=eligible(dep.key,now,stack,true);if(!v.ok)reasons.push('DEPENDENCY_NOT_CURRENT',...v.reasons);}
    }
    stack.delete(key);return reasons.length?fail(reasons):ok();
  }
  function submitCandidate(manifest,{privatePayload=null,now=clock}={}){
    tick(now);const m=clone(manifest);if(protectedMaterial(m))throw Error('PROTECTED_MATERIAL_IN_PUBLIC_MANIFEST');
    if(!safeName(m.id)||!safeName(m.version)||!eligibleAgent(m.ownerAgent)||!safeName(m.equivalenceKey))throw Error('INVALID_CANDIDATE_IDENTITY');
    for(const k of ['implementationDigest','scopeDigest','environmentDigest'])checkHash(m[k],k);
    if(m.scopeDigest!==scopeDigest||m.environmentDigest!==environmentDigest)throw Error('CANDIDATE_OUTSIDE_NETWORK_SCOPE');
    requireInteger(m.expiresAt,'EXPIRY');if(m.expiresAt<=now)throw Error('CANDIDATE_ALREADY_EXPIRED');
    if(!Array.isArray(m.prerequisitePins)||m.prerequisitePins.some(p=>!safeName(p.id)||!safeName(p.version)||!HEX.test(p.digest??'')))throw Error('INVALID_PREREQUISITES');
    if(!Array.isArray(m.components)||m.components.some(x=>!safeName(x.id)||!HEX.test(x.implementationDigest??'')))throw Error('INVALID_BUNDLE_COMPONENTS');
    const rights=m.rights;if(!rights||typeof rights.shareable!=='boolean')throw Error('RIGHTS_REQUIRED');
    for(const name of ['retrieve','execute','export','compose'])if(rights[name]!=='network'&&rights[name]!==false&&(!Array.isArray(rights[name])||rights[name].some(a=>!eligibleAgent(a))))throw Error('INVALID_RIGHTS');
    if(rights.shareable&&['retrieve','execute','compose'].some(k=>rights[k]!=='network'))throw Error('SHAREABLE_REQUIRES_NETWORK_AVAILABILITY');
    if(privatePayload!==null&&m.payloadDigest!==contentDigest(privatePayload,'beyond-beta-private-payload'))throw Error('PRIVATE_CAPSULE_COMMITMENT_MISMATCH');
    if(privatePayload!==null&&protectedMaterial(privatePayload))throw Error('PROTECTED_EVALUATION_MATERIAL_CANNOT_ENTER_CAPSULE');
    const key=keyOf(m);if(records.has(key))throw Error('VERSION_ALREADY_EXISTS_HISTORY_CANNOT_OVERWRITE');
    const candidateDigest=contentDigest(m,'beyond-beta-candidate');
    records.set(key,{key,manifest:freezeDeep(m),candidateDigest,status:'CANDIDATE',evidence:null,evidenceDigest:null,
      evidenceAvailable:false,assessment:null,assessmentDigest:null,attestations:[],evaluationHistory:[],validationHistory:[],
      createdAt:now,admittedAt:null,terminalAt:null});
    if(privatePayload!==null){const binding={key,candidateDigest};vault.set(key,{...encryptCapsule(privatePayload,binding),binding});}
    entry('candidate',key,{candidateDigest});return {key,candidateDigest};
  }
  function attachEvidence(key,evidence,now=clock){
    tick(now);const r=get(key);if(!['CANDIDATE','EVIDENCED'].includes(r.status))throw Error('EVIDENCE_TRANSITION_NOT_ALLOWED');
    const e=clone(evidence);if(protectedMaterial(e))throw Error('PROTECTED_MATERIAL_IN_PUBLIC_EVIDENCE');
    if(e.replayAvailable!==true||e.boundaryPass!==true||e.blockedClaimsPresent!==false)throw Error('EVIDENCE_GATE_FAILED');
    if(!['MODELED','OBSERVED_LOCAL_TESTS'].includes(e.mode))throw Error('EVIDENCE_CATEGORY_REQUIRED');
    for(const k of ['artifactDigest','replayDigest','provenanceDigest'])checkHash(e[k],k);
    r.evidence=freezeDeep(e);r.evidenceDigest=contentDigest(e,'beyond-beta-evidence');r.evidenceAvailable=true;r.status='EVIDENCED';
    entry('evidence',key,{evidenceDigest:r.evidenceDigest,mode:e.mode});return r.evidenceDigest;
  }
  function recordAssessment(key,assessment,now=clock,{declaredComparatorDigest=null}={}){
    tick(now);const r=get(key);if(r.status!=='EVIDENCED')throw Error('ASSESSMENT_REQUIRES_EVIDENCE');
    if(protectedMaterial(assessment))throw Error('PROTECTED_MATERIAL_IN_PUBLIC_ASSESSMENT');
    if(declaredComparatorDigest!==null)checkHash(declaredComparatorDigest,'COMPARATOR_CONTEXT');r.declaredComparatorDigest=declaredComparatorDigest;
    r.assessment=freezeDeep(clone(assessment));r.assessmentDigest=contentDigest(assessment,'beyond-beta-alpha-assessment');
    r.evaluationHistory.push({week:now,assessment:clone(assessment),assessmentDigest:r.assessmentDigest,evidenceDigest:r.evidenceDigest});
    const reasons=reportReasons(r,now,{checkUniverse:true});
    if(usedProbeDigests.has(assessment.probeIdsDigest)||usedPairDigests.has(assessment.observedPairsDigest))reasons.push('PREVIOUS_EVALUATION_CANNOT_BE_RELABELED_FRESH');
    if(HEX.test(assessment.probeIdsDigest??''))usedProbeDigests.add(assessment.probeIdsDigest);
    if(HEX.test(assessment.observedPairsDigest??''))usedPairDigests.add(assessment.observedPairsDigest);
    r.status=reasons.length?'REJECTED':'ASSESSED';
    if(reasons.length)r.terminalAt=now;
    entry('alpha-assessment',key,{assessmentDigest:r.assessmentDigest,verdict:r.status,reasons});return reasons.length?fail(reasons):ok();
  }
  function validate(key,attestations,now=clock){
    tick(now);const r=get(key);if(r.status!=='ASSESSED')return fail('VALIDATION_REQUIRES_POSITIVE_ASSESSMENT');
    const supplied=clone(attestations);if(!Array.isArray(supplied))throw Error('ATTESTATION_ARRAY_REQUIRED');
    const bound=validationBinding(key),reasons=[];r.attestations=supplied;
    for(const a of supplied){const v=authenticateAttestation(a,bound,context(r.manifest.ownerAgent,bound,now,'admit'),resolver);if(!v.ok)reasons.push(...v.reasons);}
    reasons.push(...attestationReasons(r,now),...reportReasons(r,now,{checkUniverse:true}));
    if(reasons.length){r.attestations=[];entry('validation-rejected',key,{reasons});return fail(reasons);}
    for(const a of supplied){const v=authenticateAttestation(a,bound,context(r.manifest.ownerAgent,bound,now,'reuse'),resolver);seenNonces.add(v.nonceKey);}
    r.validationHistory.push({week:now,attestations:clone(supplied),assessmentDigest:r.assessmentDigest});
    r.status='VALIDATED';entry('validation',key,{validators:supplied.map(a=>a.agent),cryptographicAuthentication:false});return ok();
  }
  function proposalFor(command,now){
    const c=clone(command),r=get(c.key);if(c.actor!==r.manifest.ownerAgent)throw Error('CREATOR_WRITE_AUTHORITY_REQUIRED');
    if(c.action==='admit'){
      if(r.status!=='VALIDATED')throw Error('ADMISSION_CANNOT_BYPASS_VALIDATION');
      const v=eligible(c.key,now,new Set(),false),reasons=[...v.reasons,...reportReasons(r,now,{checkUniverse:true})];
      if(reasons.length)throw Error(reasons.join('|'));
    }else if(c.action==='promote'){
      if(!eligible(c.key,now).ok)throw Error('CANONICAL_PROMOTION_REQUIRES_CURRENT_ADMISSION');
      if(!safeName(c.alias))throw Error('CANONICAL_ALIAS_REQUIRED');
    }else if(['revoke','retire','supersede'].includes(c.action)){
      if(TERMINAL.has(r.status))throw Error('TERMINAL_STATE_CANNOT_BE_REWRITTEN');
      if(!safeName(c.reason))throw Error('LIFECYCLE_REASON_REQUIRED');
      if(c.action==='supersede'){
        const next=get(c.replacementKey);if(next.manifest.ownerAgent!==c.actor||next.manifest.scopeDigest!==r.manifest.scopeDigest||!eligible(next.key,now).ok)throw Error('REPLACEMENT_REQUIRES_SEPARATE_CURRENT_ADMISSION');
      }
    }else throw Error('UNSUPPORTED_LIFECYCLE_TRANSITION');
    const projected=c.action==='admit'?'ADMITTED':c.action==='promote'?r.status:{revoke:'REVOKED',retire:'RETIRED',supersede:'SUPERSEDED'}[c.action];
    const ownerRows=[...records.values()].filter(x=>x.manifest.ownerAgent===c.actor);
    const states=ownerRows.map(x=>({key:x.key,status:x.key===c.key?projected:x.status,candidateDigest:x.candidateDigest,
      evidenceDigest:x.evidenceDigest,assessmentDigest:x.assessmentDigest}));
    const skills=ownerRows.filter(x=>x.key===c.key?projected==='ADMITTED':eligible(x.key,now).ok).map(x=>validationBinding(x.key));
    const forest=buildForest({skill:skills,policy:[{version:currentPolicy.version,digest:policyDigest()}],
      metadata:[{networkId,revision,command:c,states,betaVersion:currentBeta,preparedAt:now}],
      evidence:ownerRows.filter(x=>x.evidenceDigest).map(x=>({key:x.key,digest:x.evidenceDigest})),
      attestation:ownerRows.flatMap(x=>x.attestations),
      revocation:events.filter(e=>e.type==='revoke'||e.type==='retire').map(e=>({sequence:e.sequence,key:e.key,week:e.week,type:e.type})),
      supersession:events.filter(e=>e.type==='supersede').map(e=>({sequence:e.sequence,key:e.key,week:e.week,replacementKey:e.replacementKey}))});
    const head=heads.get(c.actor),snapshot=resolver.resolveSnapshot(snapshotId);
    const packet=buildGraphEpoch({forest,graphId:graphId(c.actor),agent:c.actor,chainId:snapshot.chainId,registry:snapshot.registry,
      epoch:(head?.epoch??0)+1,previousRoot:head?.graphRoot??ZERO_ROOT,policyDigest:policyDigest(),
      snapshotDigest:contentDigest({revision,states,command:c},'beyond-beta-lifecycle-snapshot'),proofLevel:'MODELED_ALPHA_RESEARCH_ADMISSION'});
    return {schema:'beyond-beta.transition-proposal/v1',command:c,preparedAt:now,revision,projected,forest,packet};
  }
  function prepareTransition(key,action,options={},now=clock){tick(now);return clone(proposalFor({key,action,actor:get(key).manifest.ownerAgent,...options},now));}
  function commitTransition(proposal,signedRoot,now=clock){
    tick(now);if(proposal.preparedAt!==now||proposal.revision!==revision)return fail('STALE_TRANSITION_PROPOSAL');
    let expected;try{expected=proposalFor(proposal.command,now);}catch(e){return fail(String(e.message));}
    if(!same(proposal,expected)||signedRoot.graphRoot!==expected.packet.graphRoot)return fail('TRANSITION_COMMITMENT_MISMATCH');
    const p=expected.packet,r=get(expected.command.key),bound={scopeDigest:r.manifest.scopeDigest,environmentDigest:r.manifest.environmentDigest,rightsDigest:contentDigest(r.manifest.rights,'beyond-beta-rights')};
    if(signedRoot.agent!==r.manifest.ownerAgent)return fail('WRITER_NOT_CREATOR');
    const v=authorizeRoot(signedRoot,{...context(r.manifest.ownerAgent,bound,now,'publish'),expectedPreviousRoot:p.previousRoot,
      expectedEpoch:p.epoch,expectedGraphRoot:p.graphRoot,admissionsVerified:true,lifecycleEvidenceVerified:true},resolver);
    if(!v.ok)return v;
    seenNonces.add(v.nonceKey);heads.set(r.manifest.ownerAgent,clone(signedRoot));rootHistory.push(clone(signedRoot));
    rootArtifacts.push({graphRoot:p.graphRoot,forest:clone(expected.forest)});
    r.status=expected.projected;if(expected.command.action==='admit'){r.admittedAt=now;r.admissionRoot=clone(signedRoot);}
    if(TERMINAL.has(r.status))r.terminalAt=now;
    if(expected.command.action==='promote')canonical.set(expected.command.alias,r.key);
    entry(expected.command.action,r.key,{graphRoot:p.graphRoot,...(expected.command.replacementKey?{replacementKey:expected.command.replacementKey}:{}),reason:expected.command.reason??null});
    return {ok:true,key:r.key,status:r.status,graphRoot:p.graphRoot,simulatedAuthority:true,cryptographicAuthentication:false};
  }
  function membershipBinding(agent){
    if(!eligibleAgent(agent))throw Error('DIRECT_AGENT_REQUIRED');
    return {id:`network-member:${agent}`,version:currentPolicy.version,implementationDigest:contentDigest({agent,networkId},'fixture-membership-not-execution'),
      dependencyDigests:[],scopeDigest,environmentDigest,policyDigest:policyDigest(),evidenceDigest:contentDigest({networkId,agent,policyVersion:currentPolicy.version},'fixture-membership'),
      rightsDigest:contentDigest({membership:true,executionAuthority:false},'fixture-membership-rights'),expiresAt:1000000};
  }
  function memberCheck(proof,now){
    if(!proof||!eligibleAgent(proof.agent))return fail('INELIGIBLE_NETWORK_MEMBER');
    const b=membershipBinding(proof.agent);return authenticateAttestation(proof,b,{...context('membership',b,now),graphId:`${networkId}:membership`},resolver);
  }
  function missionReasons(r,mission){
    const out=[];if(mission?.scopeDigest!==r.manifest.scopeDigest)out.push('MISSION_SCOPE_MISMATCH');
    if(mission?.environmentDigest!==r.manifest.environmentDigest)out.push('MISSION_ENVIRONMENT_MISMATCH');
    if(r.manifest.components.length&&mission?.requestedComponents&&
       !same([...mission.requestedComponents].sort(),r.manifest.components.map(x=>x.id).sort()))out.push('BUNDLE_MUST_RETAIN_VALIDATED_COMPONENTS');
    if(mission?.betaVersion&&mission.betaVersion!==currentBeta)out.push('HISTORICAL_BETA_NOT_CURRENT');return out;
  }
  function discover(memberProof,mission,now=clock){
    tick(now);const auth=memberCheck(memberProof,now);if(!auth.ok)return {ok:false,reasons:auth.reasons,capabilities:[]};
    return {ok:true,capabilities:[...records.values()].filter(r=>eligible(r.key,now).ok&&missionReasons(r,mission).length===0&&
      rightsAllowed(r.manifest.rights.retrieve,memberProof.agent)).map(r=>({key:r.key,id:r.manifest.id,version:r.manifest.version,
      candidateDigest:r.candidateDigest,ownerAgent:r.manifest.ownerAgent,shareable:r.manifest.rights.shareable,
      scopeDigest:r.manifest.scopeDigest,environmentDigest:r.manifest.environmentDigest,prerequisitePins:clone(r.manifest.prerequisitePins),
      status:'ADMITTED',betaVersion:currentBeta,policyVersion:currentPolicy.version,expiresAt:Math.min(r.manifest.expiresAt,r.assessment.expiresAt),
      executionAuthority:false,optionalUse:true})),cryptographicAuthentication:false};
  }
  function requestReuse(key,memberProof,mission,{right='retrieve',dryRun=false}={},now=clock){
    tick(now);const auth=memberCheck(memberProof,now);if(!auth.ok)return auth;
    const r=get(key),gate=eligible(key,now),reasons=[...gate.reasons,...missionReasons(r,mission)];
    if(!['retrieve','execute','export','compose'].includes(right)||!rightsAllowed(r.manifest.rights[right],memberProof.agent))reasons.push('RIGHT_NOT_GRANTED');
    if(right==='execute'){
      const action=executionAuthorizer({member:memberProof.agent,mission:clone(mission),capabilityKey:key,week:now});
      if(action?.allowed!==true)reasons.push('SEPARATE_MISSION_EXECUTION_AUTHORITY_REQUIRED');
    }
    if(reasons.length)return fail(reasons);
    const capsule=vault.get(key),payload=capsule&&!dryRun?decryptCapsule(capsule.envelope,capsule.key,capsule.binding):null;
    if(!dryRun)entry('authorized-reuse',key,{member:memberProof.agent,right,optional:true});
    return {ok:true,key,right,member:memberProof.agent,payload,authorizedCapabilityAccess:true,
      executionAuthority:right==='execute'?'SEPARATE_SUPPLIED_POLICY_CHECKED':'NOT_GRANTED',
      actualExecution:false,dryRun,exportCopyingLimit:right==='export'?'Authorized plaintext export can be copied; no revocation of an existing copy is promised.':null};
  }
  function beginRevalidation(key,evidence,now=clock){
    tick(now);const r=get(key);if(TERMINAL.has(r.status))return fail('TERMINAL_HISTORY_CANNOT_RESURRECT');
    r.status='CANDIDATE';r.attestations=[];r.assessment=null;r.assessmentDigest=null;r.evidence=null;r.evidenceDigest=null;r.evidenceAvailable=false;
    entry('revalidation-started',key);attachEvidence(key,evidence,now);return ok();
  }
  function advanceBeta(version,now,keys=[]){tick(now);if(betaVersions.has(version))throw Error('BETA_VERSION_CANNOT_ROLL_BACK');
    if(!safeName(version))throw Error('BETA_VERSION_REQUIRED');betaVersions.add(version);currentBeta=version;baselineKeys=new Set(keys);entry('beta-version',null,{version});}
  function advancePolicy(next,now){tick(now);const p=checkedPolicy(next);if(policyVersions.has(p.version))throw Error('POLICY_VERSION_CANNOT_ROLL_BACK');
    policyVersions.add(p.version);currentPolicy=p;entry('policy-version',null,{version:p.version});}
  function advanceAuthoritySnapshot(id,now){tick(now);const previous=resolver.resolveSnapshot(snapshotId),next=resolver.resolveSnapshot(id);
    if(!next||next.observedAt>now||next.blockNumber<previous.blockNumber)throw Error('AUTHORITY_STATE_CANNOT_ROLL_BACK');snapshotId=id;entry('authority-snapshot',null,{id});}
  function capsuleProjection(key,includeCiphertext){
    if(!vault.has(key))return null;const e=vault.get(key).envelope;
    if(includeCiphertext)return clone(e);
    return {schema:e.schema,algorithm:e.algorithm,bindingDigest:e.bindingDigest,scope:e.scope,
      ciphertextIncluded:false,ciphertextBytes:Buffer.from(e.ciphertext,'base64').length,
      nonceBytes:Buffer.from(e.nonce,'base64').length,authenticationTagBytes:Buffer.from(e.tag,'base64').length,
      qualification:'Randomized encryption remains local; this reproducible projection omits random bytes and their digest.'};
  }
  function snapshot({includeCiphertext=true}={}){return {schema:'beyond-beta.lifecycle-snapshot/v1',networkId,betaVersion:currentBeta,policy:clone(currentPolicy),week:clock,
    scopeDigest,environmentDigest,revision,records:[...records.values()].map(r=>({key:r.key,manifest:clone(r.manifest),candidateDigest:r.candidateDigest,
      status:r.status,effective:eligible(r.key,clock),evidenceDigest:r.evidenceDigest,assessmentDigest:r.assessmentDigest,
      assessment:r.assessment?clone(r.assessment):null,evaluationHistory:clone(r.evaluationHistory),validationHistory:clone(r.validationHistory),
      createdAt:r.createdAt,admittedAt:r.admittedAt,terminalAt:r.terminalAt,
      encryptedCapsule:capsuleProjection(r.key,includeCiphertext)})),events:clone(events),rootHistory:clone(rootHistory),rootArtifacts:clone(rootArtifacts),
    canonical:[...canonical.entries()],failureMemory:clone(failureMemory),protectedEvaluationCommitments:[...protectedDigests],
    authorityMode:'FIXTURE_ONLY',cryptographicAuthentication:false,liveIdentityEnforcement:'NOT_RUN',
    localEncryption:'AES-256-GCM',zeroKnowledgeProofs:'NOT_IMPLEMENTED',productionExecution:'NOT_CONNECTED',jobsClubRoles:'UNCHANGED',
    historyImportSupported:false};}
  return Object.freeze({submitCandidate,attachEvidence,recordAssessment,validationBinding,validate,prepareTransition,commitTransition,
    membershipBinding,discover,requestReuse,beginRevalidation,advanceBeta,advancePolicy,advanceAuthoritySnapshot,
    inventoryDigest,snapshot,context:()=>({networkId,betaVersion:currentBeta,policyVersion:currentPolicy.version,policyDigest:policyDigest(),scopeDigest,environmentDigest,currentSnapshotId:snapshotId,week:clock}),
    protectEvaluationMaterial:values=>{for(const value of clone(values)){protectedDigests.add(contentDigest(value,'protected-evaluation-material'));if(typeof value==='string'&&value.length)protectedStrings.add(value);}},
    recordFailure:(failure,now=clock)=>{tick(now);const f=clone(failure);if(!safeName(f.id)||!safeName(f.reason)||!HEX.test(f.evidenceDigest??'')||protectedMaterial(f))throw Error('INVALID_OR_PROTECTED_FAILURE_MEMORY');
      const record={id:f.id,reason:f.reason,evidenceDigest:f.evidenceDigest,week:now,classification:'FAILURE_MEMORY_NOT_ALPHA',
        admissionAuthority:false,executionAuthority:false,positiveCapability:false};failureMemory.push(record);entry('failure-memory',null,{id:f.id});return clone(record);},
    inspect:(key,now=clock)=>{tick(now);const r=get(key);return {key,status:r.status,candidateDigest:r.candidateDigest,eligibility:eligible(key,now)};},
    resolveCanonical:(alias,now=clock)=>{tick(now);const key=canonical.get(alias);return key&&eligible(key,now).ok?key:null;},
    setEvidenceAvailable:(key,available,now=clock)=>{tick(now);if(available!==false)throw Error('RESTORATION_REQUIRES_FRESH_REVALIDATION');get(key).evidenceAvailable=false;entry('evidence-unavailable',key);}});
}
