// SPDX-License-Identifier: Apache-2.0
// A finite experiment adapter over the released AGI ALPHA workbench seam.
// This is not a new installed runtime, daemon, production service, or authority.
import {inspectTask,inspectStrategy,SPECIALISTS} from './core.mjs';
import {runMission,localCheck,checkerReserve} from './adapter.mjs';
import {discover,qualify,admission,clone,strategyIdentity,equivalentRecipe} from './learning.mjs';
import {digest} from './vendor/docs/assets/successor/engine.mjs';
import {SOURCE_HASH,SOURCE_STATUS} from './binding.mjs';

export const MODES=['flywheel','learner','portfolio','workflow','no_discovery','no_admission','no_retention','no_succession','diagnostic'];
const stages=['dispatch','lookahead','repair'];
const scopeOf=task=>task.scope??(task.kind==='repair'?'repair':'ordinary');
const stageScope=stage=>({dispatch:'ordinary',lookahead:'tight',repair:'repair'})[stage];
const now=()=>new Date().toISOString();
// Telemetry values use a fixed accounting field; timing-number formatting must
// not turn identical strategies into different metered algorithms.
const workBytes=value=>Math.ceil(new TextEncoder().encode(JSON.stringify(value,(key,value)=>key.endsWith('_ms')||key==='storage_bytes'?0:value)).length/64);
async function identity(value){return digest('release-stream',JSON.stringify(value));}
function stripPack(row){const {pack,...small}=row;return small;}

export function createMissionStream({tasks,qualification={},policy={},storage=null,onEvent=()=>{},signal,check,sourceHash=SOURCE_HASH,onPack=async()=>{},onRecord=async()=>{}}){
 const cfg={mode:'flywheel',totalWork:1000000,perMissionWork:100000,qualificationWork:50000,discoveryWork:500000,stageAt:[1,25,49],maxAssets:3,wallTimeMs:120000,actor:'experiment-driver',
  authority:{scope:'LOCAL_SYNTHETIC_RELEASE_PLANNING',expires:'2099-01-01T00:00:00Z'},...clone(policy)};
 if(!MODES.includes(cfg.mode)||!Array.isArray(tasks)||tasks.length<1||tasks.length>216)throw Error('STREAM_SCOPE');
 // The equally enabled conventional learner executes literally the same
 // mechanism. Its experimental label lives in the outer trial record, so a
 // one-character label difference cannot change metered checkpoint bytes.
 if(cfg.mode==='learner')cfg.mode='flywheel';
 if(!Number.isSafeInteger(cfg.totalWork)||cfg.totalWork<0||cfg.totalWork>5000000||!Number.isSafeInteger(cfg.perMissionWork)||cfg.perMissionWork<18000||cfg.perMissionWork>1000000||!Number.isSafeInteger(cfg.discoveryWork)||cfg.discoveryWork<0||cfg.discoveryWork>1500000)throw Error('STREAM_BUDGET_SCOPE');
 if(!Number.isSafeInteger(cfg.wallTimeMs)||cfg.wallTimeMs<1||cfg.wallTimeMs>300000)throw Error('STREAM_WALL_SCOPE');
 const seen=new Set();for(const task of tasks){inspectTask(task);if(seen.has(task.id))throw Error('DUPLICATE_MISSION_ID');seen.add(task.id);}
 let state={schema:'release-stream/v1',source_hash:sourceHash,source_status:SOURCE_STATUS,config_digest:null,policy:cfg,
  cursor:0,status:'READY',reason:null,work:0,sequence:0,events:[],ledger:[],missions:[],assets:[],rejected:[],discoveries:[],
  completed_stages:[],requests:{},interventions:[],research_evaluations:[],replacements:[],storage_bytes:0,pending:null,ready_result:null,inflight_discovery:null,proof:[],authority:[]};
 let running=false,requestedStop=false,activeSignal=signal,startedAt=0;
 const configuration={tasks,qualification,policy:cfg,source_hash:sourceHash};
 const remaining=()=>Math.max(0,cfg.totalWork-state.work);
 const book=(kind,work,detail={})=>{if(!Number.isSafeInteger(work)||work<0)throw Error('ACCOUNTING_CHARGE');state.work+=work;state.ledger.push({entry:state.ledger.length,kind,work,total:state.work,mission_index:Math.min(state.cursor,tasks.length-1),...detail});if(state.work>cfg.totalWork){state.status='STOPPED';state.reason='ACCOUNTING_OVERRUN';throw Error('ACCOUNTING_OVERRUN');}};
 const controlReserve=()=>3*(workBytes(state)+512)+4096;
 const brief=row=>({task_id:row.task_id,valid:row.valid,qualified:row.qualified,work:row.work,error:row.error,truncated:row.truncated,allocated_budget:row.allocated_budget,
  makespan:row.result?.makespan??null,movement:row.result?.movement??null,counts:row.counts,wall_ms:row.wall_ms});
 async function event(kind,detail={}){const row={sequence:state.sequence++,kind,at:now(),work_total:state.work,...detail};state.events.push(row);onEvent(clone(row));return row;}
 async function snapshot(){const body=clone(state);body.proof=[];body.authority=[];return {...body,integrity:await identity(body)};}
 async function persist(){
  state.storage_bytes=new TextEncoder().encode(JSON.stringify(state)).length;
  // Charge actual checkpoint serialization only when a durable backend is
  // installed. The in-memory browser option is explicitly not persistent.
  if(storage){const cost=workBytes(state)+4;if(remaining()<cost)throw Error('CHECKPOINT_BUDGET_UNFUNDED');book('checkpoint-write-block64',cost);}
  if(storage?.saveGuard){const old=storage.loadGuard?await storage.loadGuard():null;await storage.saveGuard({source_hash:sourceHash,high_water:Math.max(state.cursor,old?.high_water??0),
   work:Math.max(state.work,old?.work??0),reserved_upper:Math.max(state.work+(state.pending?.reserved_work??0),old?.reserved_upper??0),
   sequence:Math.max(state.sequence,old?.sequence??0),rejected:[...new Set([...(old?.rejected??[]),...state.rejected.map(r=>r.digest)])],
   completed_stages:[...new Set([...(old?.completed_stages??[]),...state.completed_stages])]});}
  if(storage)await storage.save(await snapshot());
 }
 async function checkpoint(){
  await new Promise(resolve=>setTimeout(resolve,0));
  if(requestedStop||activeSignal?.aborted){state.status='STOPPED';state.reason='USER_STOP';await event('STOP',{reason:'USER_STOP',resumable:true});await persist();throw Error('USER_STOP');}
  if(cfg.authority.scope!=='LOCAL_SYNTHETIC_RELEASE_PLANNING'||!Number.isFinite(Date.parse(cfg.authority.expires))||Date.now()>=Date.parse(cfg.authority.expires)){state.status='STOPPED';state.reason='EXPIRED_AUTHORITY';await event('STOP',{reason:state.reason,resumable:false});await persist();throw Error(state.reason);}
  if(startedAt&&performance.now()-startedAt>cfg.wallTimeMs){state.status='STOPPED';state.reason='WALL_DEADLINE';await event('STOP',{reason:state.reason,resumable:false});await persist();throw Error(state.reason);}
  if(remaining()<18000+controlReserve()){state.status='STOPPED';state.reason='BUDGET_EXHAUSTED';await event('STOP',{reason:state.reason,resumable:false});await persist();throw Error(state.reason);}
 }
 async function evaluate(task,strategy,phase,cap=cfg.perMissionWork){
  await checkpoint();
  const before=state.work,overhead=controlReserve(),budget=Math.min(cap,remaining())-overhead;
  if(budget<18000)return {task_id:task.id,result:null,valid:false,qualified:false,work:0,counts:{},wall_ms:0,error:'CHECK_RESERVE',truncated:true,allocated_budget:0};
  state.pending={task_id:task.id,phase,reserved_work:budget,started:now()};await persist();
  const row=await runMission(task,{strategy,sourceHash,check,budget,signal:activeSignal});
  book(phase,row.work,{task_id:task.id,valid:row.valid,qualified:row.qualified,error:row.error,counts:row.counts,wall_ms:row.wall_ms});
  state.pending=null;
  book('raw-evidence-block64',workBytes({task,strategy,row:stripPack(row)}),{task_id:task.id,phase});
  if(row.pack)await onPack(row.pack,{phase,task_id:task.id});
  if(phase!=='mission')state.research_evaluations.push({phase,...brief(row)});
  else state.ready_result=stripPack(row);
  await persist();
  const complete={...stripPack(row),execution_work:row.work,work:state.work-before,allocated_budget:cap,execution_budget:budget,counts:{...row.counts,'stream:bookkeeping':state.work-before-row.work}};
  await onRecord({phase,task:clone(task),strategy:clone(strategy),row:clone(complete)});
  if(phase==='mission')state.ready_result=complete;
  return complete;
 }
 function incumbent(stage){
  const scope=stageScope(stage),asset=[...state.assets].reverse().find(a=>a.active&&a.scope===scope);
  return asset?.strategy??'portfolio';
 }
 function parent(stage){
  const wanted=stage==='lookahead'?'dispatch':stage==='repair'?'lookahead':null;
  return wanted?[...state.assets].reverse().find(a=>a.active&&a.stage===wanted):null;
 }
 async function acquire(stage,{rebuilding=false}={}){
  if(state.completed_stages.includes(stage))return;
  state.completed_stages.push(stage);
  if(['portfolio','no_discovery'].includes(cfg.mode)){await event('OUT_EVOLVE',{stage,decision:'DISCOVERY_DISABLED'});return;}
  const corpus=qualification[stage],conventional=cfg.mode==='workflow';let ancestor=parent(stage);
  if(cfg.mode==='diagnostic'&&stage!=='dispatch'&&cfg.parentTreatment==='removed'){
   book('parent-removal-probe',1,{stage});await event('OUT_EVOLVE',{stage,decision:'DEFER_PARENT_REMOVED',removed_digest:ancestor?.digest??null});return;
  }
  if(cfg.mode==='diagnostic'&&stage!=='dispatch'&&cfg.parentTreatment==='rebuild'&&!rebuilding){
   const needed=stage==='repair'?['dispatch','lookahead']:['dispatch'];
   for(const neededStage of needed){const previous=state.assets.filter(a=>a.active&&a.stage===neededStage);for(const a of previous){a.active=false;a.retirement_reason='DIAGNOSTIC_ANCESTRY_REMOVAL';}
    state.completed_stages=state.completed_stages.filter(s=>s!==neededStage);await acquire(neededStage,{rebuilding:true});
    const rebuilt=state.assets.findLast(a=>a.active&&a.stage===neededStage);await event('RECONSTRUCTION',{stage:neededStage,previous:previous.map(a=>a.digest),rebuilt:rebuilt?.digest??null,
     exact_contents_recovered:Boolean(rebuilt&&previous.some(a=>a.digest===rebuilt.digest)),source:'Same registered training/search/qualification; no copied answer or parent AST.'});}
   ancestor=parent(stage);
  }
  if(cfg.mode==='diagnostic'&&stage!=='dispatch'&&cfg.parentTreatment==='equivalent'&&ancestor){
   const recipe=equivalentRecipe(ancestor.strategy),replacement={digest:await strategyIdentity(recipe),strategy:recipe,replaces:ancestor.digest,
    equivalence:'Remove semantically ignored names; divide all priority coefficients by their positive common factor. No precomputed answer.',proof:[],authority:[]};
   book('equivalent-method-reconstruction',1+workBytes(replacement),{stage});state.replacements.push(replacement);ancestor={...ancestor,strategy:recipe,digest:replacement.digest};
   await event('REPLACEMENT',{stage,original:replacement.replaces,equivalent:replacement.digest});
  }
  if(!corpus?.training?.length||!corpus?.validation?.length){await event('OUT_EVOLVE',{stage,decision:'DEFER_NO_FRESH_QUALIFICATION'});return;}
  if(stage!=='dispatch'&&!ancestor&&!conventional&&cfg.mode!=='no_succession'){await event('OUT_EVOLVE',{stage,decision:'DEFER_NO_ACCEPTED_PARENT'});return;}
  const acquisitionStart=state.work,limit=Math.min(cfg.discoveryWork,remaining()-18000);
  if(limit<18000){await event('OUT_EVOLVE',{stage,decision:'DEFER_BUDGET'});return;}
  await event('OUT_LEARN',{stage,training_tasks:corpus.training.length,qualification_tasks:corpus.validation.length});
  await event('OUT_THINK',{stage,parent_digest:ancestor?.digest??null,source:'Closed declared grammar; no evaluator or authority mutation'});
  state.inflight_discovery={stage,starting_work:acquisitionStart,stage_limit:limit};await persist();
  const options={conventional,noSuccession:cfg.mode==='no_succession'};
  const qualificationAllocation=cfg.mode==='diagnostic'?100000:cfg.qualificationWork;
  const qualificationReserve=corpus.validation.length*2*qualificationAllocation+1024;
  const search=await discover({stage,parent:ancestor?.strategy,training:corpus.training,options,
   remaining:()=>limit-(state.work-acquisitionStart)-qualificationReserve,
   evaluate:(task,strategy,phase)=>evaluate(task,strategy,phase,Math.min(cfg.perMissionWork,Math.max(0,limit-(state.work-acquisitionStart)-qualificationReserve-1024)))});
  await event('OUT_DESIGN',{stage,candidate_digest:search.candidate?.digest??null,tried:search.trials.length,search_stop:search.stop});
  const searchRecord={...search,trials:search.trials.map(t=>({...t,rows:t.rows.map(brief)}))};state.inflight_discovery.search=searchRecord;await persist();
  if(!search.candidate){state.discoveries.push({stage,search:searchRecord,qualification:null,gate:null,acquisition:state.work-acquisitionStart});state.inflight_discovery=null;await event('OUT_EVOLVE',{stage,decision:'REJECT_NO_COMPLETE_CANDIDATE'});return;}
  // Candidate is immutable and identity-bound before any qualification input is
  // sent to the executor. Its grammar cannot access the checker or corpus.
  const frozenDigest=search.candidate.digest;
  const q=await qualify({candidate:search.candidate,tasks:corpus.validation,incumbent:incumbent(stage),allocation:qualificationAllocation,
   canFundPair:()=>limit-(state.work-acquisitionStart)>=2*qualificationAllocation+controlReserve()&&remaining()>=2*qualificationAllocation+controlReserve(),
   evaluate:(task,strategy,phase,allocation)=>evaluate(task,strategy,phase,allocation)});
  if(frozenDigest!==await strategyIdentity(search.candidate.strategy))throw Error('CANDIDATE_CHANGED_AFTER_FREEZE');
  const qRecord={...q,rows:q.rows.map(brief),reference:q.reference.map(brief)};
  book('admission-decision',1+workBytes(qRecord)+workBytes(search.candidate),{stage});
  const acquisition=state.work-acquisitionStart,scope=stageScope(stage),remainingMissions=tasks.slice(state.cursor).filter(t=>scopeOf(t)===scope).length;
  const gate=admission({qualification:q,acquisition,remainingMissions,remainingBudget:remaining(),maintenance:workBytes(search.candidate)*remainingMissions,
   force:['no_admission','diagnostic'].includes(cfg.mode)});
  const discovery={stage,search:searchRecord,qualification:qRecord,gate,acquisition};state.discoveries.push(discovery);state.inflight_discovery=null;
  await event('OUT_STRATEGISE',{stage,decision:gate.decision,forecast_remaining_missions:remainingMissions,break_even_missions:gate.break_even_missions});
  if(gate.accepted&&cfg.mode!=='no_retention'){
   for(const old of state.assets)if(old.active&&old.scope===scope){old.active=false;old.retirement_reason='REPLACED_WITH_CURRENT_QUALIFIED_ASSET';await event('RETIRE',{digest:old.digest,reason:old.retirement_reason});}
   const asset={id:`strategy-${state.assets.length+1}`,digest:frozenDigest,strategy:clone(search.candidate.strategy),stage,scope,parent_digest:ancestor?.digest??null,
    source_hash:sourceHash,created_after_mission:state.cursor,active:true,last_used:null,qualification:q.candidate,gate:clone(gate),proof:[],authority:[]};
   state.assets.push(asset);book('retention-write',workBytes(asset),{digest:asset.digest});
   while(state.assets.filter(a=>a.active).length>cfg.maxAssets){const old=state.assets.find(a=>a.active);old.active=false;old.retirement_reason='CATALOG_CAP';await event('RETIRE',{digest:old.digest,reason:old.retirement_reason});}
   await event('ADMISSION',{stage,digest:frozenDigest,parent_digest:asset.parent_digest,decision:gate.decision,production_authority:[],current_proof:[]});
  }else{
   state.rejected.push({digest:frozenDigest,stage,decision:cfg.mode==='no_retention'?'DISCARD_RETENTION_ABLATION':gate.decision});
   await event('ADMISSION',{stage,digest:frozenDigest,decision:cfg.mode==='no_retention'?'DISCARD_RETENTION_ABLATION':gate.decision});
  }
  await persist();
 }
 async function select(task){
  const scope=scopeOf(task);book('catalog-lookup',1+state.assets.length,{task_id:task.id});
  const choices=[...state.assets].reverse();
  for(const asset of choices){
   if(!asset.active||asset.scope!==scope)continue;
   book('retention-maintenance',workBytes(asset.strategy)+1,{task_id:task.id,digest:asset.digest});
   if(asset.source_hash!==sourceHash||state.rejected.some(x=>x.digest===asset.digest)){
    asset.active=false;asset.retirement_reason='SOURCE_OR_REJECTION_MISMATCH';await event('RETIRE',{digest:asset.digest,reason:asset.retirement_reason});continue;
   }
   inspectStrategy(asset.strategy);asset.last_used=state.cursor;return {strategy:asset.strategy,asset};
  }
  return {strategy:'portfolio',asset:null};
 }
 async function start({resume=false,requestId='start'}={}){
  if(running)throw Error('ALREADY_RUNNING');
  if(state.requests[requestId]?.complete)return snapshot();
  if(state.status==='COMPLETE')return snapshot();
  if(state.status==='STOPPED'&&(!resume||state.reason!=='USER_STOP'))throw Error('EXPLICIT_NEW_BOUNDED_RUN_REQUIRED');
  running=true;requestedStop=false;state.status='RUNNING';state.reason=null;startedAt=performance.now();
  try{
   if(!state.config_digest)state.config_digest=await identity(configuration);
   state.requests[requestId]={complete:false,started:now()};
   state.interventions.push({kind:resume?'EXPLICIT_RESUME':'EXPLICIT_START',actor:cfg.actor,at:now(),human_minutes:null,automatic:cfg.actor==='experiment-driver'});
   await event(resume?'RECOVER':'START',{request_id:requestId,missions:tasks.length,source_hash:sourceHash});
   await persist();
   while(state.cursor<tasks.length){
    await checkpoint();
    for(let i=0;i<stages.length;i++)if(state.cursor>=cfg.stageAt[i])await acquire(stages[i]);
    await checkpoint();const task=tasks[state.cursor];
    // A durable accepted record is the idempotency key, not an acknowledgement.
    if(state.missions.some(m=>m.task_id===task.id)){state.cursor++;continue;}
    await event('IDENTIFY',{mission_id:task.id,index:state.cursor,scope:scopeOf(task),deadline:task.deadline});
    const selected=await select(task);await event('OUT_EXECUTE',{mission_id:task.id,asset_digest:selected.asset?.digest??null});
    const row=state.ready_result?.task_id===task.id?state.ready_result:await evaluate(task,selected.strategy,'mission');
    const record={...row,index:state.cursor,scope:scopeOf(task),asset_digest:selected.asset?.digest??null,source_hash:sourceHash,
     receipt_digest:await identity({task_id:task.id,result:row.result,checker:row.checker,source_hash:sourceHash}),proof:[],authority:[]};
    book('receipt-write',workBytes(record),{task_id:task.id});state.missions.push(record);state.cursor++;state.ready_result=null;
    await event('RESULT',{mission_id:task.id,index:record.index,valid:row.valid,qualified:row.qualified,makespan:row.result?.makespan??null,
     deadline:task.deadline,work:row.work,asset_digest:record.asset_digest,error:row.error});
    await persist();
    // Discovery is skipped at the end: no remaining useful work can amortize it.
   }
   state.status='COMPLETE';state.requests[requestId].complete=true;await event('WAIT',{reason:'FINITE_AUTHORIZED_MISSION_STREAM_EXHAUSTED'});await event('COMPLETE',{qualified:state.missions.filter(x=>x.qualified).length});await persist();
  }catch(error){
   if(!['USER_STOP','BUDGET_EXHAUSTED','EXPIRED_AUTHORITY','WALL_DEADLINE'].includes(error.message)){state.status='STOPPED';state.reason=error.message;await event('ERROR',{reason:error.message});await persist();}
  }finally{running=false;}
  return snapshot();
 }
 async function restore(saved){
  if(running)throw Error('RESTORE_WHILE_RUNNING');
  if(!saved||saved.schema!=='release-stream/v1')throw Error('SNAPSHOT_SCHEMA');
  const {integrity,...body}=clone(saved);
  if(integrity!==await identity(body))throw Error('SNAPSHOT_INTEGRITY');
  if(body.source_hash!==sourceHash||body.config_digest!==await identity(configuration))throw Error('SOURCE_OR_CONFIGURATION_CHANGED');
  const guard=storage?.loadGuard?await storage.loadGuard():null;
  if(guard&&(guard.source_hash!==sourceHash||body.cursor<guard.high_water||body.work<guard.work||body.sequence<guard.sequence||
   guard.completed_stages?.some(s=>!body.completed_stages.includes(s))||guard.rejected.some(d=>!body.rejected.some(r=>r.digest===d)||body.assets.some(a=>a.active&&a.digest===d))))throw Error('STALE_OR_REJECTED_SNAPSHOT');
  if(body.proof?.length||body.authority?.length)throw Error('INHERITED_AUTHORITY_OR_PROOF');
  const ids=new Set();
  for(const m of body.missions){
   if(ids.has(m.task_id)||!tasks.some(t=>t.id===m.task_id)||m.proof?.length||m.authority?.length)throw Error('INVALID_RECEIPT');ids.add(m.task_id);
   if(m.receipt_digest!==await identity({task_id:m.task_id,result:m.result,checker:m.checker,source_hash:sourceHash}))throw Error('INVALID_RECEIPT');
  }
  const rejected=new Set(body.rejected.map(r=>r.digest));for(const asset of body.assets){inspectStrategy(asset.strategy);if(asset.digest!==await strategyIdentity(asset.strategy)||asset.source_hash!==sourceHash||asset.proof?.length||asset.authority?.length||asset.active&&rejected.has(asset.digest))throw Error('INVALID_RETAINED_ASSET');}
  if(body.work!==body.ledger.reduce((sum,row)=>sum+row.work,0)||body.cursor!==body.missions.length||body.missions.some((m,i)=>m.task_id!==tasks[i].id))throw Error('INVALID_LEDGER_OR_CURSOR');
  state=body;state.proof=[];state.authority=[];if(state.status==='RUNNING'){state.status='STOPPED';state.reason='USER_STOP';}
  if(state.pending){const uncertain=clone(state.pending);book('uncertain-interrupted-execution',uncertain.reserved_work,{task_id:uncertain.task_id,phase:uncertain.phase,
   reason:'Process died after durable intent but before durable measured completion; ceiling charged, CPU exactly-once not asserted.'});state.pending=null;}
  if(state.inflight_discovery){state.discoveries.push({stage:state.inflight_discovery.stage,interrupted:true,search:state.inflight_discovery.search??null,
   acquisition:state.work-state.inflight_discovery.starting_work,decision:'REJECT_INTERRUPTED_SEARCH'});state.inflight_discovery=null;}
  book('restore-inspection',1+workBytes(body),{restored_missions:ids.size});
  for(const m of [...state.missions,...(state.ready_result?[state.ready_result]:[])])if(m.valid&&m.result){const task=tasks.find(t=>t.id===m.task_id);
   const reserve=checkerReserve(task,m.result);if(remaining()<controlReserve()+reserve+1024)throw Error('RESTORE_BUDGET_EXHAUSTED');
   book('restore-check-transport',1+workBytes({task,result:m.result}),{task_id:m.task_id});let checkAgain;
   try{checkAgain=await (check??localCheck)(task,m.result);}catch(error){book('restore-current-check-timeout',reserve,{task_id:m.task_id});throw error;}
   const checkedWork=checkAgain.counts?.total??0;if(!Number.isSafeInteger(checkedWork)||checkedWork<0||checkedWork>reserve){book('restore-check-accounting-refusal',reserve,{task_id:m.task_id});throw Error('CHECKER_ACCOUNTING_BOUND');}
   book('restore-current-check',checkedWork,{task_id:m.task_id});
   if(!checkAgain.valid||Boolean(checkAgain.qualified)!==Boolean(m.qualified))throw Error('INVALID_RECEIPT_CURRENT_CHECK');}
  state.interventions.push({kind:'RESTART',at:now(),human_minutes:null,measured_by:'caller',automatic:false});
  await event('RECOVER',{restored_missions:ids.size,active_proof:[],active_authority:[],authentication:'UNAUTHENTICATED_LOCAL_HISTORY'});await persist();return snapshot();
 }
 async function rollback(digestToRemove,reason='USER_ROLLBACK'){
  if(running)throw Error('ROLLBACK_WHILE_RUNNING');const asset=state.assets.find(a=>a.digest===digestToRemove&&a.active);if(!asset)throw Error('UNKNOWN_ACTIVE_ASSET');
  asset.active=false;asset.retirement_reason=reason;state.rejected.push({digest:asset.digest,stage:asset.stage,decision:'ROLLED_BACK'});
  state.interventions.push({kind:'ROLLBACK',actor:cfg.actor,at:now(),human_minutes:null,automatic:cfg.actor==='experiment-driver',digest:asset.digest});
  const previous=[...state.assets].reverse().find(a=>a.scope===asset.scope&&a.digest!==asset.digest&&!state.rejected.some(r=>r.digest===a.digest)&&a.source_hash===sourceHash);
  if(previous)previous.active=true;book('rollback',1+workBytes(asset));await event('ROLLBACK',{removed:asset.digest,incumbent:previous?.digest??'portfolio',proof:[],authority:[]});await persist();return snapshot();
 }
 return Object.freeze({start,rollback,stop(reason='USER_STOP'){requestedStop=true;state.interventions.push({kind:reason,at:now(),human_minutes:null,automatic:false});},
  snapshot,restore,async load(){if(!storage)throw Error('NO_STORAGE');const saved=await storage.load();return saved?restore(saved):null;},getState:()=>clone(state),
  get running(){return running;},setSignal(value){activeSignal=value;}});
}
