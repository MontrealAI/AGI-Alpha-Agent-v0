// SPDX-License-Identifier: Apache-2.0
// Additive, deterministic simulation of skill admission. No live ENS, signatures,
// transactions, model calls, settlement authority, or economic outcomes are supplied here.
import {createHash} from 'node:crypto';

export const ADMISSION_SCHEMA = 'agialpha-simulated-skill-admission/v1';
export const FIXTURE_AUTHENTICATION = 'SIMULATED_CONTROLLER_BINDING_ONLY';
export const TRUTH_BASIS = 'SIMULATED_WITH_HELD_OUT_TRUTH';
const DIRECT_AGENT = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth$/;
const integer = value => Number.isSafeInteger(value) && value >= 0;
const rate = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
const nonempty = value => typeof value === 'string' && value.length > 0;
const unique = values => new Set(values).size === values.length;
const scopes = value => Array.isArray(value) ? value : [value];
const scopeContains = (allowed, needed) => scopes(needed).every(value => scopes(allowed).includes(value));

export function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonicalJson(value[key])).join(',') + '}';
  throw Error('Only finite JSON values are valid in a simulation evidence binding');
}

export const evidenceHash = value => createHash('sha256').update('AGIALPHA-HUMAN-MARKET-SIMULATION-V1\0' + canonicalJson(value)).digest('hex');
export const policyHashFor = mission => evidenceHash({id:mission.id,scope:mission.scope,policy:mission.policy});
export function sealMission(mission) { return {...mission,policyHash:policyHashFor(mission)}; }
export function candidateHashFor(candidate) { const {attestations,...payload}=candidate; return evidenceHash(payload); }

export function authorityStatus(fixture, week) {
  const reasons=[];
  if (!fixture || !DIRECT_AGENT.test(fixture.name || '')) reasons.push('DIRECT_AGENT_NAME_REQUIRED');
  if (fixture?.authenticationMode !== FIXTURE_AUTHENTICATION) reasons.push('EXPLICIT_SIMULATED_AUTHORITY_REQUIRED');
  if (!nonempty(fixture?.controller)) reasons.push('CONTROLLER_FIXTURE_REQUIRED');
  if (fixture?.eligible !== true) reasons.push('INELIGIBLE_AGENT');
  if (fixture?.revoked === true) reasons.push('AUTHORITY_REVOKED');
  if (!integer(week) || !integer(fixture?.validFromWeek) || !integer(fixture?.expiresWeek) || week < fixture.validFromWeek || week > fixture.expiresWeek) reasons.push('AUTHORITY_NOT_CURRENT');
  return {eligible:reasons.length===0,reasons,authenticationMode:FIXTURE_AUTHENTICATION,liveIdentityAuthenticated:false};
}

// This digest detects altered fixture records. It is NOT a private-key signature,
// and its author is not authenticated on Ethereum or ENS.
export function makeFixtureAttestation({candidate,authority,issuedWeek,expiresWeek,verdict='ADMIT_WITH_SCOPE'}) {
  const payload={authenticationMode:FIXTURE_AUTHENTICATION,signer:authority.name,controller:authority.controller,candidateHash:candidateHashFor(candidate),policyHash:candidate.policyHash,issuedWeek,expiresWeek,verdict};
  return {...payload,fixtureBinding:evidenceHash(payload)};
}

function dependencyReasons(skill, dependencies, week) {
  const reasons=[];
  for (const required of skill.prerequisites || []) {
    const found=dependencies.find(row=>row.skillId===required.id && row.version===required.version);
    let bound=false;
    if(found){const {recordHash,...payload}=found;bound=recordHash===evidenceHash(payload);}
    if (!found || !bound || found.decision!=='ADMIT_WITH_SCOPE' || found.revoked===true || week>found.validUntilWeek || !scopeContains(found.scope,skill.scope)) reasons.push('DEPENDENCY_NOT_CURRENT:'+required.id+'@'+required.version);
  }
  return reasons;
}

/**
 * All validation outcomes below are inputs from the simulator's ground-truth
 * model. Validator agreement is deliberately ignored as a correctness metric.
 * The caller owns costs, keyed random draws, paid maintenance, and cash rules.
 */
export function assessCandidate({candidate,mission,authorityFixtures,week,dependencyAdmissions=[]}) {
  const reasons=[];
  let decision='ADMIT_WITH_SCOPE';
  const fail=(level,reason)=>{reasons.push(reason);const rank={ADMIT_WITH_SCOPE:0,REPAIR:1,REJECT:2,QUARANTINE:3};if(rank[level]>rank[decision])decision=level;};
  if (!candidate || !mission || !Array.isArray(authorityFixtures) || !integer(week)) return {decision:'REJECT',reasons:['MALFORMED_ADMISSION_INPUT'],admission:null};
  const skill=candidate.skill || {}, policy=mission.policy || {}, validation=candidate.validation || {};
  if (!nonempty(skill.id) || !nonempty(skill.version) || !Array.isArray(skill.scope) || !skill.scope.length || !skill.scope.every(nonempty)) fail('REJECT','MALFORMED_SKILL');
  if (!integer(policy.minimumValidationCases) || policy.minimumValidationCases<1 || !rate(policy.minPassRate) || !integer(policy.maxCriticalEscapes) || !integer(policy.minDistinctValidators) || policy.minDistinctValidators<1 || !integer(policy.maxEvidenceAgeWeeks) || !integer(policy.maxSkillAgeWeeks) || policy.requireFreshCases!==true || policy.minimumProofLevel!=='SIMULATED_L3_SCOPED') fail('REJECT','MALFORMED_OR_UNSUPPORTED_MISSION_POLICY');
  if (mission.policyHash!==policyHashFor(mission) || candidate.policyHash!==mission.policyHash || candidate.missionId!==mission.id) fail('QUARANTINE','IMMUTABLE_MISSION_POLICY_BINDING_FAILED');
  if (!scopeContains(mission.scope || [],skill.scope || [])) fail('REJECT','SKILL_OUTSIDE_MISSION_SCOPE');
  const creator=authorityFixtures.find(row=>row.name===skill.creator);
  if (!authorityStatus(creator,week).eligible) fail('QUARANTINE','CREATOR_NOT_ELIGIBLE_DIRECT_AGENT_FIXTURE');
  if (candidate.paidBuild!==true) fail('REPAIR','CONSTRUCTION_NOT_PAID');
  if (!integer(candidate.builtWeek) || candidate.builtWeek>week) fail('REPAIR','BUILD_NOT_COMPLETE');
  if (!integer(skill.requiredDemandingAcceptedJobsSincePrevious) || skill.requiredDemandingAcceptedJobsSincePrevious<1) fail('REJECT','DEMANDING_ORIGIN_REQUIREMENT_MISSING');
  for (const reason of dependencyReasons(skill,dependencyAdmissions,week)) fail('REPAIR',reason);
  const applicableDependencies=dependencyAdmissions.filter(row=>(skill.prerequisites || []).some(required=>required.id===row.skillId && required.version===row.version));
  const previousAdmissionWeek=applicableDependencies.length ? Math.max(...applicableDependencies.map(row=>row.admittedWeek)) : -1;
  const origins=(candidate.originJobs || []).filter(row=>row.accepted===true && row.demanding===true && integer(row.week) && row.week>previousAdmissionWeek && row.week<=candidate.builtWeek && nonempty(row.id));
  const originIds=[...new Set(origins.map(row=>row.id))];
  if (originIds.length<skill.requiredDemandingAcceptedJobsSincePrevious) fail('REPAIR','INSUFFICIENT_NEW_DEMANDING_ACCEPTED_WORK');
  const caseIds=validation.caseIds || [];
  if (!Array.isArray(caseIds) || !caseIds.every(nonempty) || !unique(caseIds) || !integer(validation.cases) || validation.cases!==caseIds.length || validation.cases<policy.minimumValidationCases) fail('REPAIR','INSUFFICIENT_DISTINCT_VALIDATION_CASES');
  if (!integer(validation.passes) || validation.passes>validation.cases || validation.cases===0 || validation.passes/validation.cases<policy.minPassRate) fail('REPAIR','VALIDATION_PASS_THRESHOLD_NOT_MET');
  if (!integer(validation.criticalEscapes) || validation.criticalEscapes>validation.cases || validation.criticalEscapes>policy.maxCriticalEscapes) fail('REJECT','CRITICAL_ESCAPE_THRESHOLD_EXCEEDED');
  if (validation.truthBasis!==TRUTH_BASIS || validation.scoredAgainstGroundTruth!==true) fail('REJECT','VALIDATOR_AGREEMENT_IS_NOT_GROUND_TRUTH');
  if (validation.replayReady!==true || !nonempty(validation.caseSetId)) fail('REPAIR','REPLAYABLE_VALIDATION_RECORD_MISSING');
  if (!integer(validation.week) || validation.week<candidate.builtWeek || validation.week>week || week-validation.week>policy.maxEvidenceAgeWeeks) fail('REPAIR','VALIDATION_NOT_CURRENT');
  if (week-candidate.builtWeek>policy.maxSkillAgeWeeks) fail('REPAIR','SKILL_EXPIRED');
  const training=new Set([...(candidate.trainingJobIds || []),...(candidate.originJobs || []).map(row=>row.id)]);
  if (caseIds.some(id=>training.has(id))) fail('QUARANTINE','VALIDATION_TRAINING_OVERLAP');
  if ((skill.prerequisites || []).length && validation.compositionValidated!==true) fail('REPAIR','NEW_COMPOSITION_REQUIRES_SEPARATE_VALIDATION');
  const counted=new Set();
  const candidateHash=candidateHashFor(candidate);
  for (const attestation of candidate.attestations || []) {
    const {fixtureBinding,...payload}=attestation;
    const authority=authorityFixtures.find(row=>row.name===attestation.signer);
    if (fixtureBinding!==evidenceHash(payload) || attestation.candidateHash!==candidateHash || attestation.policyHash!==mission.policyHash) {fail('QUARANTINE','ATTESTATION_BINDING_FAILED');continue;}
    if (!authorityStatus(authority,week).eligible || attestation.authenticationMode!==FIXTURE_AUTHENTICATION || attestation.controller!==authority.controller) {fail('QUARANTINE','INELIGIBLE_OR_UNBOUND_VALIDATOR');continue;}
    if (!integer(attestation.issuedWeek) || !integer(attestation.expiresWeek) || attestation.issuedWeek<validation.week || attestation.issuedWeek>week || week>attestation.expiresWeek) {fail('REPAIR','ATTESTATION_NOT_CURRENT');continue;}
    if (attestation.verdict==='QUARANTINE') fail('QUARANTINE','VALIDATOR_QUARANTINE');
    else if (attestation.verdict==='REJECT') fail('REJECT','VALIDATOR_REJECT');
    else if (attestation.verdict==='REPAIR') fail('REPAIR','VALIDATOR_REPAIR');
    else if (attestation.verdict!=='ADMIT_WITH_SCOPE') fail('REJECT','INVALID_VALIDATOR_VERDICT');
    else if (attestation.signer!==skill.creator) counted.add(attestation.signer);
  }
  if (counted.size<policy.minDistinctValidators) fail('REPAIR','INSUFFICIENT_DISTINCT_NONSELF_ELIGIBLE_ATTESTATIONS');
  if (decision!=='ADMIT_WITH_SCOPE') return {decision,reasons:[...new Set(reasons)],admission:null,candidateHash,authenticationMode:FIXTURE_AUTHENTICATION};
  const admission={schema:ADMISSION_SCHEMA,decision,skillId:skill.id,version:skill.version,skillHash:evidenceHash(skill),scope:[...skill.scope],candidateHash,policyHash:mission.policyHash,admittedWeek:week,validUntilWeek:Math.min(validation.week+policy.maxEvidenceAgeWeeks,candidate.builtWeek+policy.maxSkillAgeWeeks,integer(skill.usefulLifetimeWeeks)?candidate.builtWeek+skill.usefulLifetimeWeeks:Number.MAX_SAFE_INTEGER),prerequisites:skill.prerequisites || [],validatorNames:[...counted].sort(),originJobIds:originIds,validationCaseSetId:validation.caseSetId,truthBasis:TRUTH_BASIS,revoked:false,authenticationMode:FIXTURE_AUTHENTICATION,liveIdentityAuthenticated:false,liveTransaction:false};
  return {decision,reasons:[],admission:{...admission,recordHash:evidenceHash(admission)},candidateHash,authenticationMode:FIXTURE_AUTHENTICATION};
}

export function mayInfluence({admission,skill,jobScope,week,revokedIds=[],activeDependencies=[],maintenanceCurrent}) {
  const reasons=[];
  if (!admission || admission.decision!=='ADMIT_WITH_SCOPE') return {allowed:false,reasons:['NO_ADMITTED_SKILL']};
  const {recordHash,...payload}=admission;
  if (recordHash!==evidenceHash(payload)) reasons.push('ADMISSION_RECORD_BINDING_FAILED');
  if (!skill || admission.skillId!==skill.id || admission.version!==skill.version) reasons.push('WRONG_SKILL_VERSION');
  if (skill && admission.skillHash!==evidenceHash(skill)) reasons.push('SKILL_DEFINITION_CHANGED_AFTER_ADMISSION');
  if (!integer(week) || week<admission.admittedWeek || week>admission.validUntilWeek) reasons.push('SKILL_OR_EVIDENCE_NOT_CURRENT');
  if (admission.revoked===true || revokedIds.includes(admission.skillId) || revokedIds.includes(admission.skillId+'@'+admission.version)) reasons.push('SKILL_REVOKED');
  if (!jobScope || !scopeContains(admission.scope,jobScope)) reasons.push('SCOPE_MISMATCH');
  if (maintenanceCurrent!==true) reasons.push('MAINTENANCE_OR_REVALIDATION_NOT_CURRENT');
  if (skill) reasons.push(...dependencyReasons(skill,activeDependencies,week));
  return {allowed:reasons.length===0,reasons};
}

/** A recipient needs a functional/cost probe; missing an inventory identifier is insufficient. */
export function assessTransfer({skill,recipient,probe,week}) {
  const reasons=[];
  if (!recipient || !nonempty(recipient.name) || !skill || !probe || probe.truthBasis!==TRUTH_BASIS || probe.scoredAgainstGroundTruth!==true) return {eligible:false,equivalent:null,reasons:['EXPLICIT_GROUND_TRUTH_RECIPIENT_PROBE_REQUIRED']};
  if (!integer(probe.week) || !integer(week) || probe.week>week || week-probe.week>1) reasons.push('RECIPIENT_PROBE_STALE');
  if (!integer(probe.cases) || probe.cases<1 || !integer(probe.passes) || probe.passes>probe.cases || !rate(probe.equivalenceMinPassRate) || !Number.isFinite(probe.costUsdPerCase) || probe.costUsdPerCase<0 || !Number.isFinite(probe.equivalenceMaxCostUsdPerCase) || probe.equivalenceMaxCostUsdPerCase<0) reasons.push('INVALID_RECIPIENT_PROBE');
  if (!Array.isArray(skill.requiredFunctions) || !skill.requiredFunctions.length || !Array.isArray(probe.passedFunctions) || !Array.isArray(probe.testedFunctions) || !scopeContains(probe.testedFunctions,skill.requiredFunctions)) reasons.push('RECIPIENT_PROBE_DID_NOT_COVER_FUNCTIONAL_ENVELOPE');
  if (reasons.length) return {eligible:false,equivalent:null,reasons};
  const equivalent=scopeContains(probe.passedFunctions,skill.requiredFunctions) && probe.passes/probe.cases>=probe.equivalenceMinPassRate && probe.costUsdPerCase<=probe.equivalenceMaxCostUsdPerCase;
  return {eligible:!equivalent,equivalent,reasons:equivalent?['RECIPIENT_ALREADY_HAS_FUNCTIONALLY_EQUIVALENT_CAPABILITY']:[],probeBasis:TRUTH_BASIS,requiresPaidAdaptationAndFreshValidation:!equivalent};
}
