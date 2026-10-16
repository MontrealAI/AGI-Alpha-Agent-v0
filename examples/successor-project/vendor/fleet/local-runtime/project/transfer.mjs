// Inert project transport. Checksums establish byte integrity, never controller
// identity, runtime trust, reviewer eligibility or payment authority.
import {parseStrict,canonical,sha256,publicOnly,fail,keys} from '../../fleet/successor/vendor/manager/site/assets/successor/safe.mjs';
import {defaultMission,csvRows,validateMission,executeMission} from '../../fleet/successor/vendor/manager/site/assets/successor/missions.mjs';
import {checkArtifacts} from '../../fleet/successor/vendor/manager/site/assets/successor/checker.mjs';
import {validateProject} from './vendor/alpha/examples/successor-project/engine.mjs';

export const PROJECT_BYTES=4_000_000;
export const PROJECT_OBSERVATION_BYTES=16_000;
export const PROJECT_MAPPING='alpha-public-data-to-fleet-rows/v1';
const routes={ 'manager-usdc':{backend:'manager-usdc',asset:'USDC'},'agijobsv0-jobregistry-v2':{backend:'agijobsv0-jobregistry-v2',asset:'AGIALPHA'} };
const bytes=value=>new TextEncoder().encode(value).length;
const identity=p=>({projectId:p.projectId,cycleId:p.cycles.at(-1).cycleId,revision:p.revision,projectDigest:p.projectDigest});
const equal=(a,b)=>canonical(a)===canonical(b);
const HASH='0'.repeat(64),ID='00000000-0000-0000-0000-000000000000';
const receiptExample=result=>canonical({result,observation:null,outputSha256:HASH,inputSha256:HASH,independentReview:false,sourceActor:ID,sourceController:ID,authority:'none',projectRequestSha256:HASH});
async function sealed(body){const raw=canonical({...body,sha256:await sha256(body)});fail(bytes(raw)<=PROJECT_BYTES,'PROJECT_TRANSFER_SIZE');return raw;}
async function opened(raw){fail(typeof raw==='string'&&bytes(raw)<=PROJECT_BYTES,'PROJECT_TRANSFER_SIZE');const value=parseStrict(raw,PROJECT_BYTES);publicOnly(raw);return value;}
async function integrity(value){const {sha256:checksum,...body}=value;fail(checksum===await sha256(body),'PROJECT_TRANSFER_CHANGED');}
async function original(raw,depth=0){
  fail(depth<=2,'PROJECT_NESTING');const v=await opened(raw);
  if(v.schema==='successor-project/v1')return validateProject(raw);
  fail(['agijobmanager/alpha-project-transfer/v1','agijobsv0/alpha-project-transfer/v1'].includes(v.schema),'PROJECT_UPSTREAM_SCHEMA');
  await integrity(v);fail(v.authority==='none'&&v.settlement==='not-connected','PROJECT_UPSTREAM_AUTHORITY');
  keys(v.original,['raw','sha256']);fail(v.original.sha256===await sha256(v.original.raw),'PROJECT_ORIGINAL_CHANGED');
  const p=await original(v.original.raw,depth+1);fail(equal(v.project,identity(p)),'PROJECT_IDENTITY_CHANGED');
  return p;
}
function mappedMission(project,language){
  fail(['en','fr'].includes(language),'PROJECT_LANGUAGE');
  const cycle=project.cycles.at(-1),record=parseStrict(cycle.records.at(-1).bytes,2_000_000);
  fail(record.spec.family==='public-data','PROJECT_MAPPING_UNAVAILABLE');
  const rows=csvRows(record.spec.inputs.csv,2);fail(equal(rows.shift(),['group','amount']),'PROJECT_CSV_HEADER');
  const values=rows.map((row,i)=>{fail(row.length===2&&/^-?(?:0|[1-9]\d*)$/.test(row[1]),'PROJECT_INTEGER_MAPPING');return {id:'alpha-row-'+(i+1),category:row[0],value:row[1]};});
  const mission=defaultMission('analyst',language),fr=language==='fr';
  mission.name=fr?'Projet Alpha — vérification des totaux':'Alpha project — check category totals';
  mission.purpose=fr?'Recalculer les totaux des mêmes lignes sources, sans modifier les unités ni fusionner les doublons.':'Recompute totals from the same source rows, preserving units and every duplicate row.';
  mission.input=canonical(values);
  mission.rights=`${cycle.mapping.choices.dataRights}; ${record.spec.inputs.unit}. `+(fr?'Déclaration fournie, non authentifiée; confirmer les droits avant publication.':'Supplied declaration, unauthenticated; confirm rights before publication.');
  validateMission(mission);return mission;
}
function mapping(language){return {id:PROJECT_MAPPING,language,rowIdentity:'source-row-position',units:'unchanged',duplicates:'every-source-row'};}
async function requestBody(upstreamRaw,{language,route}){
  const upstream=await opened(upstreamRaw),project=await original(upstreamRaw);
  const inferred=upstream.schema==='agijobmanager/alpha-project-transfer/v1'?'manager-usdc':upstream.schema==='agijobsv0/alpha-project-transfer/v1'?'agijobsv0-jobregistry-v2':null;
  fail(route===undefined||!inferred||route===inferred,'PROJECT_ROUTE_CHANGED');
  const selected=routes[inferred||route];fail(selected,'PROJECT_ROUTE_REQUIRED');
  if(inferred==='agijobsv0-jobregistry-v2')fail(equal(upstream.route,selected),'PROJECT_ROUTE_CHANGED');
  return {schema:'agi-fleet/project-request/v1',upstream:{raw:upstreamRaw,sha256:await sha256(upstreamRaw)},project:identity(project),route:selected,mapping:mapping(language),task:{schema:'agi-fleet/local-task/v1',action:'successor-run',workspace:'files',input:{mission:mappedMission(project,language),variant:'baseline'},review:'none',sourceActor:null,sourceController:null},authority:'none',productionQualified:false,settlement:'not-connected'};
}
// Only this fixed deterministic task family is admitted into project returns.
// A provider or arbitrary result cannot enlarge the reserved evidence envelope.
export async function projectTaskResult(task){
  const {mission,variant}=task.input;
  let result;
  if(task.action==='successor-run'){
    result=executeMission(mission,variant);result.checker=checkArtifacts(mission,variant,result.files);
  }else{
    fail(task.action==='successor-check','PROJECT_TASK_SCOPE');
    result={files:[],checker:checkArtifacts(mission,variant,task.input.files),deliverySha256:await sha256(task.input.files)};
  }
  return {...result,authority:'none',provider:null,execution:'bounded-offline',independentReview:false};
}
export async function validateProjectOutcome(task,result,observation){
  fail(equal(result,await projectTaskResult(task)),'PROJECT_OUTPUT_CHANGED');
  fail(bytes(canonical(observation))<=PROJECT_OBSERVATION_BYTES,'PROJECT_OBSERVATION_LIMIT');
  return {receiptUpperBytes:bytes(receiptExample(result))+PROJECT_OBSERVATION_BYTES};
}
export async function projectCapacity(raw,request){
  const executionResult=await projectTaskResult(request.task);
  const reviewTask={schema:'agi-fleet/local-task/v1',action:'successor-check',workspace:'files',input:{...request.task.input,files:executionResult.files},review:'internal',sourceActor:ID,sourceController:ID};
  const reviewResult=await projectTaskResult(reviewTask);
  const entry=result=>({runId:ID,actorId:ID,controllerId:ID,raw:receiptExample(result),sha256:HASH});
  const returned=canonical({schema:'agi-fleet/project-return/v1',request:{raw,sha256:HASH},project:request.project,route:request.route,execution:entry(executionResult),review:entry(reviewResult),reviewClass:'internal',independentReview:false,authority:'none',productionQualified:false,settlement:'not-connected',sha256:HASH});
  // All variable IDs/hashes have fixed ASCII lengths. Result bytes above are
  // exact and enforced at dispatch. Each <=16 KB canonical observation adds at
  // most 2x its bytes when its receipt is quoted in a return, and 4x when that
  // return is quoted in SQLite. The null placeholders make these conservative.
  const returnUpperBytes=bytes(returned)+2*2*PROJECT_OBSERVATION_BYTES;
  const storageUpperBytes=bytes(canonical({schema:'agi-fleet/local-journey/v1',request:raw,project:request.project,route:request.route,returned,reservedBytes:PROJECT_BYTES}))+2*4*PROJECT_OBSERVATION_BYTES;
  return {requestBytes:bytes(raw),executionReceiptUpperBytes:bytes(receiptExample(executionResult))+PROJECT_OBSERVATION_BYTES,reviewReceiptUpperBytes:bytes(receiptExample(reviewResult))+PROJECT_OBSERVATION_BYTES,returnUpperBytes,storageUpperBytes,observationBytes:PROJECT_OBSERVATION_BYTES,returnLimit:PROJECT_BYTES,storageLimit:PROJECT_BYTES};
}
async function reserveCapacity(raw,request){
  const capacity=await projectCapacity(raw,request);
  fail(capacity.returnUpperBytes<=PROJECT_BYTES&&capacity.storageUpperBytes<=PROJECT_BYTES,'PROJECT_RETURN_CAPACITY');return capacity;
}
export async function createProjectRequest(upstreamRaw,options){const raw=await sealed(await requestBody(upstreamRaw,options));await reserveCapacity(raw,await opened(raw));return raw;}
export async function inspectProjectRequest(raw){
  const request=await opened(raw);keys(request,['schema','upstream','project','route','mapping','task','authority','productionQualified','settlement','sha256']);
  await integrity(request);keys(request.upstream,['raw','sha256']);
  fail(request.upstream.sha256===await sha256(request.upstream.raw),'PROJECT_UPSTREAM_CHANGED');
  const expected=await requestBody(request.upstream.raw,{language:request.mapping?.language,route:request.route?.backend});
  const {sha256:_,...body}=request;fail(equal(body,expected),'PROJECT_REQUEST_BINDING');
  const capacity=await reserveCapacity(raw,request);
  return {request,capacity,sourceAuthenticity:'not-established',upstreamClaims:'historical-unverified',nativeValidation:'original Alpha project and exact task mapping',authority:'none',runAuthorized:false};
}
const uuid=v=>typeof v==='string'&&/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(v);
async function receipt(entry){
  keys(entry,['runId','actorId','controllerId','raw','sha256']);
  fail(uuid(entry.runId)&&uuid(entry.actorId)&&uuid(entry.controllerId),'PROJECT_RUN_IDENTITY');
  fail(entry.sha256===await sha256(entry.raw),'PROJECT_RECEIPT_CHANGED');
  const v=await opened(entry.raw);
  keys(v,['result','observation','outputSha256','inputSha256','independentReview','sourceActor','sourceController','authority','projectRequestSha256']);
  fail(entry.raw===canonical(v),'PROJECT_RECEIPT_ENCODING');
  fail(v.authority==='none'&&v.independentReview===false&&v.sourceActor===entry.actorId&&v.sourceController===entry.controllerId,'PROJECT_RECEIPT_AUTHORITY');
  fail(v.outputSha256===await sha256(v.result)&&v.observation?.processGroupGone===true,'PROJECT_RECEIPT_BINDING');
  fail(v.result?.authority==='none'&&v.result.independentReview===false&&v.result.execution==='bounded-offline','PROJECT_RECEIPT_SCOPE');return v;
}
export async function validateProjectReceipt(raw,{task,runId,actorId,controllerId,projectRequestSha256}){
  const value=await receipt({runId,actorId,controllerId,raw,sha256:await sha256(raw)});
  fail(value.projectRequestSha256===projectRequestSha256&&value.inputSha256===await sha256(task),'PROJECT_RECEIPT_PROJECT_BINDING');
  const budget=await validateProjectOutcome(task,value.result,value.observation);
  fail(bytes(raw)<=budget.receiptUpperBytes,'PROJECT_RECEIPT_CAPACITY');return value;
}
export async function sealProjectReturn(body){const raw=await sealed(body);await inspectProjectReturn(raw);return raw;}
export async function inspectProjectReturn(raw){
  const value=await opened(raw);keys(value,['schema','request','project','route','execution','review','reviewClass','independentReview','authority','productionQualified','settlement','sha256']);await integrity(value);
  fail(value.schema==='agi-fleet/project-return/v1'&&value.reviewClass==='internal'&&value.independentReview===false&&value.authority==='none'&&value.productionQualified===false&&value.settlement==='not-connected','PROJECT_RETURN_AUTHORITY');
  keys(value.request,['raw','sha256']);fail(value.request.sha256===await sha256(value.request.raw),'PROJECT_REQUEST_CHANGED');
  const {request}=await inspectProjectRequest(value.request.raw);
  fail(equal(value.project,request.project)&&equal(value.route,request.route),'PROJECT_RETURN_IDENTITY');
  const execution=await receipt(value.execution),review=await receipt(value.review),task=request.task;
  const executionBudget=await validateProjectOutcome(task,execution.result,execution.observation);fail(bytes(value.execution.raw)<=executionBudget.receiptUpperBytes,'PROJECT_RECEIPT_CAPACITY');
  fail(execution.projectRequestSha256===value.request.sha256&&review.projectRequestSha256===value.request.sha256,'PROJECT_RECEIPT_PROJECT_BINDING');
  fail(value.execution.actorId!==value.review.actorId&&value.execution.runId!==value.review.runId,'PROJECT_SEPARATE_REVIEW_REQUIRED');
  fail(execution.inputSha256===await sha256(task),'PROJECT_EXECUTION_CHANGED');
  const reviewTask={schema:'agi-fleet/local-task/v1',action:'successor-check',workspace:'files',input:{...task.input,files:execution.result.files},review:'internal',sourceActor:value.execution.actorId,sourceController:value.execution.controllerId};
  const reviewBudget=await validateProjectOutcome(reviewTask,review.result,review.observation);fail(bytes(value.review.raw)<=reviewBudget.receiptUpperBytes,'PROJECT_RECEIPT_CAPACITY');
  fail(review.inputSha256===await sha256(reviewTask)&&review.result.deliverySha256===await sha256(execution.result.files),'PROJECT_REVIEW_CHANGED');
  const checker=checkArtifacts(task.input.mission,task.input.variant,execution.result.files);
  fail(checker.passed&&equal(checker,review.result.checker)&&equal(checker,execution.result.checker),'PROJECT_RESULT_REJECTED');
  return {returned:value,request,files:execution.result.files,reviewClass:'historical-internal',independentReview:false,sourceAuthenticity:'not-established',authority:'none',runAuthorized:false,productionQualified:false,settlement:'not-connected'};
}
