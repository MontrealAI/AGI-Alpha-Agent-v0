// SPDX-License-Identifier: Apache-2.0
/** Inert continuity, never a common authority envelope. Native bytes stay unchanged. */
import {canonical, digest, parseBounded} from '../../docs/assets/successor/engine.mjs';
import * as discoveryNative from '../alpha-discovery/engine.mjs';
import {JOB_TEMPLATES} from '../build-successor/vendor/agijobs/templates.mjs';
import {validateRecord, interruptRun} from '../successor-workbench/mission-record.mjs';

export const SCHEMA = 'successor-project/v1';
export const LIMIT = 2_000_000;
export const GATES = Object.freeze(['candidate-manifest','incumbent-manifest','alternative-manifest',
  'protected-task-set-and-custodian','formation-set','protocol-and-resource-policy',
  'seven-metric-methods-and-uncertainty','constraint-requirements','reviewer-organization-and-custody','expiry']);
const HASH=/^[a-f0-9]{64}$/, ID=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
function fail(ok, code){if(!ok)throw Error(`PROJECT_${code}`);}
function keys(v,k){fail(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join('|')===[...k].sort().join('|'),'SCHEMA');}
function id(v){fail(typeof v==='string'&&ID.test(v),'ID');}
function hash(v){fail(typeof v==='string'&&HASH.test(v),'HASH');}
function clone(v){return parseBounded(canonical(v));}
function bounded(v){fail(typeof v==='string'&&new TextEncoder().encode(v).length<=LIMIT,'BYTES');return parseBounded(v);}
export async function exactDigest(bytes){fail(typeof bytes==='string','BYTES');return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(bytes))),n=>n.toString(16).padStart(2,'0')).join('');}
async function seal(v){return {...v,projectDigest:await digest('successor-project',v)};}
async function cycleDigest(v){return digest('successor-project-cycle',v);}
function source(v){keys(v,['repository','commit','path','sha256']);fail(v.repository==='MontrealAI/AGI-Alpha-Agent-v0'&&/^[a-f0-9]{40}$/.test(v.commit),'SOURCE');fail(['examples/alpha-discovery/engine.mjs','examples/successor-workbench/mission-record.mjs'].includes(v.path),'SOURCE_PATH');hash(v.sha256);}
async function link(role,bytes,sourceIdentity,identity){const native=bounded(bytes);return {role,identity,nativeSchema:native.schema,source:clone(sourceIdentity),algorithm:'sha256-utf8',artifactDigest:await exactDigest(bytes),bytes};}
async function checkLink(a,role){
  keys(a,['role','identity','nativeSchema','source','algorithm','artifactDigest','bytes']);
  fail(a.role===role&&a.algorithm==='sha256-utf8','LINK');id(a.identity);source(a.source);hash(a.artifactDigest);
  fail(await exactDigest(a.bytes)===a.artifactDigest,'ARTIFACT_BYTES');const v=bounded(a.bytes);
  fail(v.schema===a.nativeSchema,'NATIVE_SCHEMA');
  if(role==='discovery'){
    fail(a.source.path==='examples/alpha-discovery/engine.mjs','SOURCE_PATH');
    const rebuilt=await discoveryNative.createBrief(v.input,v.sourceHash);
    fail(canonical(rebuilt)===canonical(v),'DISCOVERY_BINDING');
  }else{
    fail(a.source.path==='examples/successor-workbench/mission-record.mjs','SOURCE_PATH');
    await validateRecord(v);fail(v.missionId===a.identity,'NATIVE_IDENTITY');
  }
  return v;
}
function choices(v){keys(v,['family','selection','duplicatePolicy','unitPolicy','dataRights']);fail(v.family==='public-data'&&v.selection==='explicit-user-selection'&&v.duplicatePolicy==='sum-all-rows-no-deduplication'&&v.unitPolicy==='unchanged-integer-units'&&['public','synthetic','licensed-nonpersonal'].includes(v.dataRights),'UNSUPPORTED_MAPPING');}
async function mapping(discovery,record,selected,sourceHash){choices(selected);return {schema:'successor-project-mapping/v1',adapter:'alpha-public-data-explicit/v1',sourceHash,discoveryDigest:discovery.artifactDigest,specDigest:record.specDigest,inputDigest:await exactDigest(record.spec.inputs.csv),choices:clone(selected),unresolved:['No discovery claim or metric is established by CSV totals.','No Manager decimal/identity adapter.','No Fleet execution envelope.'],authority:'none'};}
function stageWork(cycle){return JOB_TEMPLATES.map(t=>({templateId:t.id,title:t.title,status:'unfunded-proposal',dependencyDigests:[cycle.discovery.artifactDigest,cycle.records.at(-1).artifactDigest],principal:null,reviewer:null,budget:null,expiry:null,protocol:null,authority:'none'}));}
function evaluation(cycle){return {schema:'successor-project-evaluation-draft/v1',status:'incomplete-uncommissioned',basis:cycle.records.at(-1).artifactDigest,proposalDigest:cycle.discovery.artifactDigest,unresolved:[...GATES],commitments:null,metricsMapping:'unresolved-no-automatic-five-to-seven-dimension-mapping',authority:'none'};}
export function publicDataOpportunity(){const v=discoveryNative.example();v.mission='Reconcile permitted public or synthetic integer CSV totals into an inspectable report';v.baseline='Retain manual checking of the same rows';v.alternative='Use an existing spreadsheet with separately checked formulas';v.candidate='Try the existing bounded Alpha public-data aggregator';v.changed='An inspectable local report may reduce repetitive reconciliation; no comparative measurements supplied.';v.constraints=[{name:'Use only permitted nonpersonal CSV with unchanged integer units',status:'unknown',reference:'Operator must explicitly select the input and confirm its rights.'}];v.evidence=[{kind:'change',claim:'Illustrative public-data reporting opportunity; no measured advantage.',reference:'Local planning example only.',basis:'illustrative',supports:['candidate','change']}];v.metrics=v.metrics.map((m,i)=>({...m,name:['Reconciliation quality','Cost','Proof effort','Data handling risk','Human review burden'][i],unit:['correct outputs','same currency','person-hours','defined risk measure','person-hours'][i],minimumGain:0,baseline:{value:null,basis:'unknown',reference:'Not measured.'},alternative:{value:null,basis:'unknown',reference:'Not measured.'},candidate:{value:null,basis:'unknown',reference:'Not measured.'}}));return v;}
export async function validateProject(raw){
  const p=typeof raw==='string'?bounded(raw):bounded(canonical(raw));
  keys(p,['schema','projectId','revision','sourceHash','cycles','history','authority','projectDigest']);
  fail(p.schema===SCHEMA&&p.authority==='none','VERSION_AUTHORITY');id(p.projectId);hash(p.sourceHash);
  fail(Number.isSafeInteger(p.revision)&&p.revision>=0,'REVISION');
  fail(Array.isArray(p.cycles)&&p.cycles.length>0&&p.cycles.length<=8,'CYCLES');
  fail(Array.isArray(p.history)&&p.history.length>0&&p.history.length<=64,'HISTORY');
  fail(new Set(p.cycles.map(c=>c.cycleId)).size===p.cycles.length,'DUPLICATE_CYCLE');
  const seenRecords=new Set(),missionIds=new Set();
  for(let i=0;i<p.cycles.length;i++){
    const c=p.cycles[i];keys(c,['cycleId','projectId','parentCycleDigest','discovery','mapping','records','evaluationDraft','stageWork']);id(c.cycleId);fail(c.projectId===p.projectId,'CROSS_PROJECT');
    fail(c.parentCycleDigest===(i===0?null:await cycleDigest(p.cycles[i-1])),'CYCLE_LINEAGE');
    await checkLink(c.discovery,'discovery');
    fail(Array.isArray(c.records)&&c.records.length>0&&c.records.length<=24,'RECORDS');
    let prior=null;
    for(const a of c.records){const r=await checkLink(a,'mission');fail(!seenRecords.has(a.artifactDigest),'REUSED_ARTIFACT');seenRecords.add(a.artifactDigest);if(prior)fail(r.missionId===prior.missionId&&r.revision===prior.revision+1&&r.specDigest===prior.specDigest&&r.sourceHash===prior.sourceHash,'RECORD_LINEAGE');prior=r;}
    const first=bounded(c.records[0].bytes);fail(first.state==='draft'&&first.revision===0&&first.review===null&&first.result===null,'CYCLE_DRAFT');fail(!missionIds.has(first.missionId),'REUSED_MISSION');missionIds.add(first.missionId);
    fail(c.mapping.choices.dataRights===first.spec.rights.dataClass,'RIGHTS');
    fail(canonical(c.mapping)===canonical(await mapping(c.discovery,first,c.mapping.choices,c.mapping.sourceHash)),'MAPPING_BINDING');hash(c.mapping.sourceHash);fail(first.sourceHash===c.mapping.sourceHash,'NATIVE_SOURCE_BINDING');if(i===p.cycles.length-1)fail(c.mapping.sourceHash===p.sourceHash,'PROJECT_SOURCE_BINDING');
    fail(canonical(c.stageWork)===canonical(stageWork(c)),'STAGE_WORK');
    if(c.evaluationDraft!==null){fail(prior.result!==null,'EVALUATION_BASIS');fail(canonical(c.evaluationDraft)===canonical(evaluation(c)),'EVALUATION_DRAFT');}
  }
  p.history.forEach((h,i)=>{keys(h,['revision','cycleId','action','artifactDigest']);fail(h.revision===i,'HISTORY_REVISION');fail(p.cycles.some(c=>c.cycleId===h.cycleId),'HISTORY_CYCLE');fail(['created','native-transition','new-cycle','recovered-cycle'].includes(h.action),'HISTORY_ACTION');hash(h.artifactDigest);fail(p.cycles.some(c=>c.cycleId===h.cycleId&&c.records.some(a=>a.artifactDigest===h.artifactDigest)),'HISTORY_LINK');});
  fail(p.history.length===p.revision+1,'HISTORY_LENGTH');
  const {projectDigest,...body}=p;fail(projectDigest===await digest('successor-project',body),'INTEGRITY');return p;
}
export async function inspectDiscovery(bytes){
  const native=bounded(bytes);const rebuilt=await discoveryNative.createBrief(native.input,native.sourceHash);fail(canonical(native)===canonical(rebuilt),'DISCOVERY_BINDING');return native;
}
export async function createProject({projectId,cycleId,sourceHash,discoveryBytes,record,choices:selected,sources}){
  id(projectId);id(cycleId);hash(sourceHash);await validateRecord(record);
  const discovery=await link('discovery',discoveryBytes,sources.discovery,'discovery');
  const mission=await link('mission',canonical(record),sources.mission,record.missionId);
  const cycle={cycleId,projectId,parentCycleDigest:null,discovery,mapping:await mapping(discovery,record,selected,sourceHash),records:[mission],evaluationDraft:null,stageWork:[]};cycle.stageWork=stageWork(cycle);
  return validateProject(await seal({schema:SCHEMA,projectId,revision:0,sourceHash,cycles:[cycle],history:[{revision:0,cycleId,action:'created',artifactDigest:mission.artifactDigest}],authority:'none'}));
}
export async function appendRecord(raw,record,{expectedRevision,sourceHash,sources}){
  const p=await validateProject(raw);fail(p.revision===expectedRevision,'REVISION_CONFLICT');fail(p.sourceHash===sourceHash,'SOURCE_DRIFT');
  const c=p.cycles.at(-1);fail(canonical(c.records.at(-1).source)===canonical(sources.mission),'SOURCE_DRIFT');
  const a=await link('mission',canonical(await validateRecord(record)),sources.mission,record.missionId);c.records.push(a);c.stageWork=stageWork(c);
  c.evaluationDraft=record.result?evaluation(c):null;p.revision++;p.history.push({revision:p.revision,cycleId:c.cycleId,action:'native-transition',artifactDigest:a.artifactDigest});delete p.projectDigest;const checked=await validateProject(await seal(p));
  if(record.state==='running'){
    // Reserve an exact worst-reason interruption snapshot before committing a start.
    // A too-large result may fail, but its stopped history can still be persisted.
    const stopped=await interruptRun(record,{expectedRevision:record.revision,runId:record.run.runId,reason:'\u0000'.repeat(512)});
    await appendRecord(checked,stopped,{expectedRevision:checked.revision,sourceHash,sources});
  }
  return checked;
}
export async function nextCycle(raw,{cycleId,record,choices:selected,sourceHash,sources,recovered=false,expectedRevision}){
  const p=await validateProject(raw);fail(p.revision===expectedRevision,'REVISION_CONFLICT');id(cycleId);hash(sourceHash);
  const prior=p.cycles.at(-1);await validateRecord(record);fail(record.missionId!==bounded(prior.records.at(-1).bytes).missionId,'NEW_MISSION_ID_REQUIRED');
  const a=await link('mission',canonical(record),sources.mission,record.missionId);
  const renewedDiscovery=await link('discovery',canonical(await discoveryNative.createBrief(bounded(prior.discovery.bytes).input,sourceHash)),sources.discovery,'discovery');
  const c={cycleId,projectId:p.projectId,parentCycleDigest:await cycleDigest(prior),discovery:renewedDiscovery,mapping:await mapping(renewedDiscovery,record,selected,sourceHash),records:[a],evaluationDraft:null,stageWork:[]};c.stageWork=stageWork(c);
  p.sourceHash=sourceHash;p.cycles.push(c);p.revision++;p.history.push({revision:p.revision,cycleId,action:recovered?'recovered-cycle':'new-cycle',artifactDigest:a.artifactDigest});delete p.projectDigest;return validateProject(await seal(p));
}
export async function projectView(raw,{sourceHash,sources,restored=false}){
  const p=await validateProject(raw),c=p.cycles.at(-1),record=bounded(c.records.at(-1).bytes);
  const sourceCurrent=p.sourceHash===sourceHash&&record.sourceHash===sourceHash&&c.mapping.sourceHash===sourceHash&&canonical(c.records.at(-1).source)===canonical(sources.mission)&&canonical(c.discovery.source)===canonical(sources.discovery);
  return {projectId:p.projectId,cycleId:c.cycleId,revision:p.revision,authority:'none',restored,sourceCurrent,
    sourceAuthenticity:'not-established',currentReview:restored||!sourceCurrent?null:record.review,
    evaluation:p.cycles.map((item,index)=>({cycleId:item.cycleId,status:index<p.cycles.length-1?'stale-dependent-evaluation':restored?'historical-incomplete':item.evaluationDraft?.status||'not-prepared',draft:item.evaluationDraft})),
    nextAction:restored||!sourceCurrent?'Start a fresh cycle with explicit input selection.':record.result?'Inspect the actual result; evaluation commitments remain unresolved.':'Explicitly run the permitted local CSV task.',
    protocols:{ManagerUSDC:'unavailable-no-native-adapter',JobRegistryAGIALPHA:'unfunded-no-assignment',Fleet:'unavailable-no-accepted-envelope'},record};
}
