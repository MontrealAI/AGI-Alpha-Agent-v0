import {createRequire} from 'node:module';
import {validateReceiptBinding} from './receipt.mjs';
import {fail, keys, canonical, parseStrict, sha256} from './vendor/manager/site/assets/successor/safe.mjs';
import {inspectCapsule, freezeCandidate, runCandidate, exportCapsule, compareCandidates, createSystem, recordPlan} from './vendor/manager/site/assets/successor/model.mjs';
import {validateImprovement, prepareImprovement} from './vendor/manager/site/assets/successor/jobs.mjs';
import {checkArtifacts as checkLegacy} from './vendor/manager/site/assets/successor/legacy-checker.mjs';
import {checkArtifacts} from './vendor/manager/site/assets/successor/checker.mjs';
import {compileComputerWork} from './vendor/manager/scripts/successor/adapter.mjs';
const require=createRequire(import.meta.url);
export const computer=require('./vendor/manager/scripts/economics/computer-work.cjs');
export const REQUEST='agi-fleet/successor-request/v1';
const CUSTOM_SCOPE='agi-fleet/custom-sidecar-scope/v1';
const withoutParent=spec=>({...spec,coordination:{...spec.coordination,parentSpecSha256:null}});
function requirePublicCustom(spec){
  fail(spec?.profile==='computer-work/v2'&&spec.dataPolicy==='public'&&['agent','reviewer'].every(role=>spec.authority?.[role]?.scope==='isolated-public'),'FLEET_CUSTOM_PUBLIC_REQUIRED');
}

// Record the complete operator-prepared public Studio specification in the
// immutable mission. This is a new, inert project, never an execution grant.
export async function prepareCustomProject(mission,spec,budget) {
  fail(mission?.kind==='custom','FLEET_CUSTOM_PUBLIC_REQUIRED');requirePublicCustom(spec);
  await createSystem(mission);computer.validateComputerWork(spec);
  const boundMission={...mission,input:canonical({schema:CUSTOM_SCOPE,originalInput:mission.input,originalParentSpecSha256:spec.coordination.parentSpecSha256,specification:withoutParent(spec)})};
  let state=await createSystem(boundMission);const plan=await prepareImprovement(state,{budget});state=await recordPlan(state,plan);
  const specification={...spec,coordination:{...spec.coordination,parentSpecSha256:plan.commitment}};
  computer.validateComputerWork(specification);
  return {capsule:await exportCapsule(state),plan,mission:boundMission,specification,authority:'none'};
}

// Independent validation projection of the pinned Manager compiler. Dispatch
// still uses compileComputerWork above; actual compiler outputs are exercised
// by both end-to-end mission tests to detect upstream contract drift.
function validateLocalScope(plan,kind,spec) {
  fail(['analyst','website'].includes(kind),'FLEET_SIDECAR_PROJECT_SCOPE');
  const delivered=kind==='website'?[['index.html','text/html'],['method.json','application/json']]:[['report.html','text/html'],['result.json','application/json'],['method.json','application/json']];
  const expected={
    outputs:[...delivered.map(([name,mediaType])=>({name,mediaType,maxBytes:plan.outputByteLimit,requirement:'Actual editable artifact; preserve the immutable mission content and document reproduction.'})),{name:'checker-results.json',mediaType:'application/json',maxBytes:100000,requirement:'A separate implementation checks actual delivered bytes, retaining failures and uncertainty.'}],
    criteria:[{id:'exact-result',requirement:plan.draft.fields.acceptance,verification:'Reopen original immutable inputs in a separately controlled environment; recompute exact results and inspect actual delivered artifacts.',evidence:[...delivered.map(([name])=>name),'checker-results.json']}],
    dataPolicy:'public',authority:{agent:{scope:'isolated-public',resources:['job-workspace']},reviewer:{scope:'isolated-public',resources:['job-workspace']}},
    coordination:{parentSpecSha256:plan.commitment,dependencies:[],delegation:'none'}
  };
  for(const [field,value] of Object.entries(expected))fail(canonical(spec[field])===canonical(value),'FLEET_SIDECAR_PROJECT_SCOPE');
  fail(canonical(spec.environment.capabilities)===canonical({agent:['files','code'],reviewer:['files','code','independent-review']}),'FLEET_SIDECAR_PROJECT_SCOPE');
}

export async function inspectRequest(value) {
  const request=typeof value==='string'?parseStrict(value,6000000):value;
  keys(request,['schema','capsule','plan'],'FLEET_REQUEST_FIELDS');
  fail(request.schema===REQUEST&&typeof request.capsule==='string','FLEET_REQUEST');
  const inspected=await inspectCapsule(request.capsule), state=inspected.capsule.payload.state;
  await validateImprovement(request.plan);
  fail(request.plan.missionSha256===await sha256(state.mission),'FLEET_MISSION_CHANGED');
  fail(request.plan.candidateSha256===state.active&&state.active!==null,'FLEET_INCUMBENT_CHANGED');
  return {request,inspected,state,project:await sha256(state.mission),revision:inspected.capsule.sha256,requestSha256:await sha256(request)};
}

export async function compileRequest(value,context,now=Math.floor(Date.now()/1000)) {
  const inspected=await inspectRequest(value);
  const compiled=await compileComputerWork(inspected.request.plan,context,now);
  return {...inspected,compiled};
}

export async function validateSidecarProject(capsule,handoff,files) {
  const inspected=await inspectCapsule(capsule),state=inspected.capsule.payload.state,spec=handoff.specification;
  fail(spec.profile==='computer-work/v2','FLEET_SIDECAR_PROJECT_PROFILE');
  computer.validateComputerWork(spec);
  const plan=state.plans.find(p=>p.commitment===spec.coordination.parentSpecSha256);
  fail(plan&&plan.missionSha256===await sha256(state.mission),'FLEET_SIDECAR_PROJECT_PLAN');
  fail(plan.candidateSha256===null?state.mission.kind==='custom':state.candidates.some(c=>c.id===plan.candidateSha256),'FLEET_SIDECAR_PROJECT_INCUMBENT');
  // A custom plan's prose alone cannot bind arbitrary Studio deliverables.
  // Its immutable input must retain the complete specification selected when
  // this project was prepared, including inputs, requirements and criteria.
  if(state.mission.kind==='custom'){
    requirePublicCustom(spec);
    let scope;try{scope=parseStrict(state.mission.input);}catch{fail(false,'FLEET_SIDECAR_CUSTOM_SCOPE');}
    keys(scope,['schema','originalInput','originalParentSpecSha256','specification'],'FLEET_SIDECAR_CUSTOM_SCOPE');
    fail(scope.schema===CUSTOM_SCOPE&&canonical(scope.specification)===canonical(withoutParent(spec)),'FLEET_SIDECAR_CUSTOM_SCOPE');
    return; // Historical evidence only; no candidate or operating authority.
  }
  fail(spec.title===plan.draft.fields.title.slice(0,160)&&spec.prompt===plan.goal&&spec.inputs.length===plan.immutableInputs.length,'FLEET_SIDECAR_PROJECT_SCOPE');
  for(let i=0;i<spec.inputs.length;i++){const input=spec.inputs[i],expected=plan.immutableInputs[i];fail(input.name===expected.name&&input.sha256===expected.sha256&&input.maxBytes===Buffer.byteLength(expected.content)&&input.mediaType==='application/json','FLEET_SIDECAR_PROJECT_INPUT');}
  validateLocalScope(plan,state.mission.kind,spec);
  const source=inspected.capsule.payload.sourceManifest;fail(source?.engineSha256,'FLEET_SOURCE_REQUIRED');
  const matches=c=>c&&files.size===c.files.length+1&&files.has('checker-results.json')&&c.files.every(f=>files.get(f.name)?.equals(Buffer.from(f.content)));
  if(matches(state.candidates.find(c=>c.id===plan.candidateSha256)))return;
  const improved=await freezeCandidate(state.mission,'improved',source.engineSha256,state.engine);
  fail(matches(improved),'FLEET_SIDECAR_PROJECT_ARTIFACTS');
}

export async function checkReturnedWork(request,handoff,receipt,studioAPI) {
  const {state,inspected}=await inspectRequest(request);
  studioAPI.validateHandoff(handoff);
  fail(handoff.specification.coordination.parentSpecSha256===request.plan.commitment,'FLEET_PLAN_CHANGED');
  await validateReceiptBinding(handoff,receipt,'node');
  const verdict=studioAPI.computerVerdict(handoff.specification,{safeToReview:receipt.review?.safeToReview,checks:receipt.review?.checks});
  const {files}=studioAPI.validateBundle(handoff.specification,Buffer.from(handoff.delivery));
  const source=inspected.capsule.payload.sourceManifest;
  fail(source?.engineSha256,'FLEET_SOURCE_REQUIRED');
  const proposed=await runCandidate(state,'improved',source.engineSha256);
  const delivered=proposed.candidate.files.map(expected=>{
    const actual=files.get(expected.name);fail(actual,'FLEET_MISSING_ARTIFACT');
    return {...expected,content:actual.toString('utf8')};
  });
  const checks=(state.engine==='successor-local/1'?checkLegacy:checkArtifacts)(state.mission,'improved',delivered);
  const exact=proposed.candidate.files.every(expected=>files.get(expected.name)?.equals(Buffer.from(expected.content)));
  const accepted=verdict.verdict==='consistent'&&checks.passed&&exact;
  const before=state.candidates.find(c=>c.id===state.active);
  const result={schema:'agi-fleet/successor-checked-result/v1',project:await sha256(state.mission),requestSha256:await sha256(request),
    specificationSha256:handoff.specHash,deliverySha256:handoff.deliveryHash,reviewSha256:await sha256(receipt),
    outcome:accepted?'accepted':'rejected',checks,exactReusableMethod:exact,
    comparison:accepted?compareCandidates(before,proposed.candidate):{outcome:'regression',recommendation:'retain'},
    selected:state.active,proposed:accepted?proposed.candidate.id:null,independentController:'UNVERIFIED',
    qualification:'NOT_RUN',authority:'none',payment:'unfunded',providerParticipation:'See separate compute observations; receipt is not provider attestation',
    capsule:await exportCapsule(accepted?proposed.state:state,source)};
  return {...result,sha256:await sha256(result)};
}
