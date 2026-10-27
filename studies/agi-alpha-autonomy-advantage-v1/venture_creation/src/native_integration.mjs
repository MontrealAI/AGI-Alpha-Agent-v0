// SPDX-License-Identifier: Apache-2.0
// Thin supplied-evidence adapter. No credential, signing, settlement or ENS API.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {planMission} from '../../native_snapshot/canonical/shadow-ledger.mjs';
import {sealMission,makeFixtureAttestation,assessCandidate,mayInfluence,assessTransfer,authorityStatus,evidenceHash,candidateHashFor,
  FIXTURE_AUTHENTICATION,TRUTH_BASIS} from '../../human_market/validation/skill_admission.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const requireCondition=(value,message)=>{if(!value)throw Error(message);};
export const SCHEMA='agialpha-venture-native-batch/v1';
export function sourceIdentities(){
  return ['venture_creation/src/native_integration.mjs','native_snapshot/canonical/shadow-ledger.mjs','human_market/validation/skill_admission.mjs'].map(relative=>{
    const bytes=fs.readFileSync(path.join(ROOT,relative));return {path:relative,bytes:bytes.length,sha256:sha(bytes)};
  });
}

/** Bind explicitly supplied simulated evidence; this does not create correctness evidence. */
export function fixtureEnvelope({mission,candidate,authorityFixtures,week,validatorNames,dependencyAdmissions=[]}){
  requireCondition(Array.isArray(validatorNames),'Explicit fixture validator names are required');
  const sealed=sealMission(mission),bound={...candidate,missionId:sealed.id,policyHash:sealed.policyHash,attestations:[]};
  for(const name of validatorNames){
    const authority=authorityFixtures.find(row=>row.name===name);
    requireCondition(authority,'Missing explicit authority fixture '+name);
    bound.attestations.push(makeFixtureAttestation({candidate:bound,authority,issuedWeek:week,expiresWeek:authority.expiresWeek}));
  }
  return {mission:sealed,candidate:bound,authorityFixtures,week,dependencyAdmissions};
}

// Fresh venture authority check; deliberately excludes the historical study's
// sequential-origin rule. All cryptographic operations remain fixture bindings.
export function checkVentureAttestations({candidate,fixtures,week,attestations,minimumValidators=2}){
  requireCondition(Number.isSafeInteger(minimumValidators)&&minimumValidators>0,'Positive validator threshold required');
  const reasons=[],creator=candidate?.skill?.creator,byName=new Map(fixtures.map(f=>[f.name,f])),counted=new Set();
  if(byName.size!==fixtures.length)reasons.push('DUPLICATE_AUTHORITY_FIXTURE');
  if(!authorityStatus(byName.get(creator),week).eligible)reasons.push('CREATOR_NOT_ELIGIBLE_DIRECT_AGENT_FIXTURE');
  if(typeof candidate.policyHash!=='string'||!candidate.policyHash)reasons.push('POLICY_BINDING_REQUIRED');
  const bound=candidateHashFor(candidate);
  for(const a of attestations){
    const {fixtureBinding,...payload}=a,f=byName.get(a.signer);
    if(fixtureBinding!==evidenceHash(payload)||a.candidateHash!==bound||a.policyHash!==candidate.policyHash){reasons.push('ATTESTATION_BINDING_FAILED');continue;}
    if(!authorityStatus(f,week).eligible||a.authenticationMode!==FIXTURE_AUTHENTICATION||a.controller!==f.controller){reasons.push('INELIGIBLE_OR_UNBOUND_VALIDATOR');continue;}
    if(!Number.isSafeInteger(a.issuedWeek)||a.issuedWeek<0||!Number.isSafeInteger(a.expiresWeek)||a.expiresWeek<0||a.issuedWeek>week||week>a.expiresWeek){reasons.push('ATTESTATION_NOT_CURRENT');continue;}
    if(a.verdict!=='ADMIT_WITH_SCOPE'){reasons.push('VALIDATOR_DID_NOT_ADMIT');continue;}
    if(a.signer!==creator)counted.add(a.signer);
  }
  if(counted.size<minimumValidators)reasons.push('INSUFFICIENT_DISTINCT_NONSELF_ELIGIBLE_ATTESTATIONS');
  return {allowed:reasons.length===0,reasons:[...new Set(reasons)],validatorNames:[...counted].sort(),candidateHash:bound,
    authenticationMode:FIXTURE_AUTHENTICATION,liveIdentityAuthenticated:false,liveSignatureVerified:false,
    correctnessEstablished:false,existingClubRoles:'UNCHANGED',scope:'Simulated authority/integrity only; separate venture proof contract required'};
}

function projectionResult(projection){
  requireCondition(projection&&projection.accrual&&projection.liquidity,'Both native projection inputs are required');
  for(const input of [projection.accrual,projection.liquidity]){
    requireCondition(input.totalCollectedCents===0&&input.costBasis==='assumed','Simulation must preserve zero observed revenue and assumed costs');
    requireCondition(input.operatingCostsComplete===true,'Explicit full scenario cost completeness is required');
  }
  const accrual=planMission(projection.accrual),liquidity=planMission(projection.liquidity);
  for(const output of [accrual,liquidity])requireCondition(output.summary.observed.revenue===0&&output.summary.observed.fullCost===null,'Native observed basis contaminated by simulation');
  requireCondition(Number.isSafeInteger(projection.expectedEarnedMicros)&&Number.isSafeInteger(projection.expectedLiquidExcludingSeedMicros),'Expected micro-USD accounting totals required');
  const accrualErrorCents=accrual.summary.scenario.afterReserves-projection.expectedEarnedMicros/10000;
  const liquidityErrorCents=liquidity.summary.scenario.afterReserves-projection.expectedLiquidExcludingSeedMicros/10000;
  requireCondition(Math.abs(accrualErrorCents)<=2.01&&Math.abs(liquidityErrorCents)<=2.01,'Native accounting reconciliation failed');
  return {nativePlanMissionCalls:2,inputSha256:sha(canonical(projection)),accrual:accrual.summary,liquidity:liquidity.summary,
    reconciliation:{passed:true,accrualErrorCents,liquidityErrorCents,toleranceCents:2.01},
    actualCollectionsUsd:0,actualCompleteCostUsd:null};
}

export function projectBatch(batch){
  requireCondition(batch?.schema===SCHEMA&&Array.isArray(batch.worlds),'Invalid native batch schema');
  const started=performance.now(),cpu=process.cpuUsage(),identities=sourceIdentities(),seen=new Set();
  const worlds=batch.worlds.map(world=>{
    requireCondition(typeof world.id==='string'&&world.id.length&&!seen.has(world.id),'Unique world identity required');seen.add(world.id);
    const accounting=projectionResult(world.projection);
    const admissions=(world.admissions||[]).map(raw=>{
      const envelope=raw.fixtureInput?fixtureEnvelope(raw.fixtureInput):raw;
      const output=assessCandidate(envelope);
      return {inputSha256:sha(canonical(envelope)),candidateId:envelope.candidate?.skill?.id,result:output};
    });
    const influence=(world.influenceChecks||[]).map(input=>({inputSha256:sha(canonical(input)),result:mayInfluence(input)}));
    const transfers=(world.transferChecks||[]).map(input=>({inputSha256:sha(canonical(input)),result:assessTransfer(input)}));
    const authorities=(world.authorityChecks||[]).map(input=>({inputSha256:sha(canonical(input)),name:input.fixture?.name,result:authorityStatus(input.fixture,input.week)}));
    const authorityAttestations=(world.authorityAttestationChecks||[]).map(input=>({inputSha256:sha(canonical(input)),candidateId:input.candidate?.skill?.id,result:checkVentureAttestations(input)}));
    return {id:world.id,inputSha256:sha(canonical(world)),accounting,admissions,influence,transfers,authorities,authorityAttestations};
  });
  requireCondition(canonical(sourceIdentities())===canonical(identities),'Native source changed during batch');
  const used=process.cpuUsage(cpu);
  return {schema:'agialpha-venture-native-results/v1',inputSha256:sha(canonical(batch)),sources:identities,worlds,
    measuredExecution:{nativePlanMissionCalls:2*worlds.length,admissionCalls:worlds.reduce((n,x)=>n+x.admissions.length,0),
      influenceCalls:worlds.reduce((n,x)=>n+x.influence.length,0),transferCalls:worlds.reduce((n,x)=>n+x.transfers.length,0),
      authorityCalls:worlds.reduce((n,x)=>n+x.authorities.length,0),
      ventureAttestationChecks:worlds.reduce((n,x)=>n+x.authorityAttestations.length,0),
      elapsedSeconds:(performance.now()-started)/1000,cpuSeconds:(used.user+used.system)/1e6},
    boundaries:{actualCollectionsUsd:0,actualCompleteCostUsd:null,liveIdentityAuthenticated:false,liveSignaturesVerified:false,
      authenticationMode:FIXTURE_AUTHENTICATION,validationTruthBasis:TRUTH_BASIS,
      existingClubValidation:'UNCHANGED; this adapter neither invokes nor changes AGI Jobs club settlement authority',
      identityCorrectness:'Eligibility authorizes fixture attestation only; independent supplied ground-truth qualification remains required',
      historicalAdmissionNamespace:'The unchanged foundation retains its original human-market simulation domain separator; reuse adds no live enforcement',
      role:'Actual execution of inert native accounting and simulated evidence predicates; not an actual commercial or model-performance trial'}};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [inputFile,outputFile]=process.argv.slice(2);
  requireCondition(inputFile&&outputFile&&process.argv.length===4,'Usage: node native_integration.mjs INPUT.json NEW_OUTPUT.json');
  requireCondition(!fs.existsSync(outputFile),'Refuse to overwrite native batch evidence');
  const inputBytes=fs.readFileSync(inputFile),output=projectBatch(JSON.parse(inputBytes));
  output.inputFileSha256=sha(inputBytes);
  fs.writeFileSync(outputFile,JSON.stringify(output,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({worlds:output.worlds.length,outputFile,...output.measuredExecution}));
}
