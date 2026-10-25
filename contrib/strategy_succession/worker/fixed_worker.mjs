// SPDX-License-Identifier: Apache-2.0
// Engineering adapter over unchanged frozen scientific modules; no research freeze or daemon.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import readline from 'node:readline';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {runMission,checkerReserve,ADAPTER_MANIFEST} from './scientific/companion/adapter.mjs';
import {Meter,inspectTask,inspectStrategy,SPECIALISTS,lowerBound} from './scientific/companion/core.mjs';
import {discover,qualify,admission,strategyIdentity,equivalentRecipe,clone} from './scientific/companion/learning.mjs';
import {createWorkbench} from './scientific/companion/vendor/examples/successor-workbench/engine.mjs';
import {SOURCE_HASH as SCIENTIFIC_SOURCE_HASH} from './scientific/companion/binding.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const startedWall=performance.now(),startedCPU=process.cpuUsage();let activeAccount='service_work';
const canonical=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const hash=x=>crypto.createHash('sha256').update(typeof x==='string'||Buffer.isBuffer(x)?x:canonical(x)).digest('hex');
const blocks=x=>1+Math.ceil(Buffer.byteLength(JSON.stringify(x,(k,v)=>k.endsWith('_ms')||k.endsWith('_seconds')?0:v))/64);
const counters=['service_work','improvement_work','native_calls','native_solve_seconds'];
const lines=readline.createInterface({input:process.stdin});const iterator=lines[Symbol.asyncIterator]();
let request,limits,costs={service_work:0,improvement_work:0,native_calls:0,native_solve_seconds:0,unknown_costs:['Node orchestration/source hashing/IPC CPU is not converted to declared JavaScript units.','Human effort and hardware/monetary costs are unmeasured.','Opaque native solver work is not converted to JavaScript work units.']},seq=0,events=[],pythonTelemetry=[],nativeReservedSeconds=0,workLedger=[];
function require(ok,code){if(!ok)throw Error(code);}
function integer(n,low,high){return Number.isSafeInteger(n)&&n>=low&&n<=high;}
function keys(x,allowed,code){require(x&&typeof x==='object'&&!Array.isArray(x),code);require(Object.keys(x).every(k=>allowed.includes(k)),code);}
function verifySources(){
 const raw=fs.readFileSync(path.join(ROOT,'SOURCE_FILES.json'));const manifest=JSON.parse(raw);
 for(const file of manifest.files){require(typeof file.path==='string'&&!path.isAbsolute(file.path)&&!file.path.split('/').includes('..'),'SOURCE_PATH');let full=ROOT;for(const part of file.path.split('/')){full=path.join(full,part);require(!fs.lstatSync(full).isSymbolicLink(),'SOURCE_SYMLINK');}require(fs.statSync(full).isFile()&&hash(fs.readFileSync(full))===file.sha256,'SOURCE_CHANGED');}
 require(manifest.scientific_source_hash===SCIENTIFIC_SOURCE_HASH,'SCIENTIFIC_SOURCE_CHANGED');return hash(raw);
}
let workerManifest;
async function checkpoint(phase,increments={},receipt=null){
 for(const [k,v]of Object.entries(increments)){require(counters.includes(k)&&Number.isFinite(v)&&v>=0&&(k==='native_solve_seconds'||Number.isSafeInteger(v)),'COST_INCREMENT');require(costs[k]+v<=limits[k]+1e-9,'PROTECTED_BUDGET_EXHAUSTED:'+k);}
 const id=seq++;process.stdout.write(JSON.stringify({type:'checkpoint',seq:id,phase,increments,...(receipt?{receipt,source_hash:limits.source_hash}:{})})+'\n');
 const line=await iterator.next();require(!line.done&&Buffer.byteLength(line.value)<4096,'CHECKPOINT_ACK_REQUIRED');const ack=JSON.parse(line.value);require(ack.ack===id,'CHECKPOINT_ACK_MISMATCH');
 for(const [k,v]of Object.entries(increments))costs[k]+=v;events.push({phase,costs:{...costs},sequence:id,account:activeAccount});for(const [account,work]of Object.entries(increments))if(account.endsWith('_work'))workLedger.push({sequence:id,phase,account,work});
}
async function charge(account,n,phase){await checkpoint(phase,{[account]:n});}
function task(input){
 keys(input,['schema','id','kind','jobs','capacity','release','locked','deadline','baseline','movement_limit','public_or_synthetic','planning_only','project_id','input_license','horizon','disruption'],'TASK_FIELDS');require(Buffer.byteLength(JSON.stringify(input))<=65536,'TASK_BYTES');
 const t=clone(input);require(typeof t.id==='string'&&t.id.length>0&&t.id.length<=128,'TASK_ID');require(!t.proof?.length&&!t.authority?.length,'IMPORTED_AUTHORITY');
 for(const field of ['release','locked','baseline'])if(t[field]!==undefined)require(t[field]&&typeof t[field]==='object'&&!Array.isArray(t[field]),'TASK_MAPPING');
 for(const j of t.jobs??[]){keys(j,['id','duration','crew','deps'],'JOB_FIELDS');require(Array.isArray(j.deps)&&j.deps.length<=17,'TASK_DEPENDENCIES');}
 for(const field of ['project_id','input_license'])if(t[field]!==undefined)require(typeof t[field]==='string'&&t[field].length<=128,'TASK_TEXT');
 if(t.disruption!==undefined){keys(t.disruption,['observed_at','completed_jobs','in_progress_jobs'],'DISRUPTION_FIELDS');require(integer(t.disruption.observed_at,0,127)&&[t.disruption.completed_jobs,t.disruption.in_progress_jobs].every(a=>Array.isArray(a)&&a.every(x=>typeof x==='string')),'DISRUPTION_SCOPE');}
 const meter=new Meter();inspectTask(t,meter);return {task:t,validation:meter.spent+blocks(t)};
}
function bridge(role,payload){
 require(['checker','specialist'].includes(role),'FIXED_ROLE');require(path.isAbsolute(process.env.FIXED_PYTHON??''),'CONFIGURED_PYTHON_REQUIRED');
 const start=performance.now();const run=spawnSync(process.env.FIXED_PYTHON,[path.join(ROOT,'python_bridge.py'),role],{input:JSON.stringify(payload),encoding:'utf8',timeout:role==='specialist'?8000:3000,maxBuffer:1048576,env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONDONTWRITEBYTECODE:'1'}});
 const record={role,process_wall_seconds:(performance.now()-start)/1000,status:run.status,signal:run.signal,error:run.error?.code??null};
 if(run.error||run.status!==0){pythonTelemetry.push(record);throw Error('PYTHON_'+role.toUpperCase()+'_FAILED');}
 let out;try{out=JSON.parse(run.stdout);}catch{pythonTelemetry.push(record);throw Error('PYTHON_PROTOCOL');}
 pythonTelemetry.push({...record,...out});require(out.ok,'PYTHON_REFUSED:'+out.error);return out;
}
async function check(t,result,account,{alreadyCharged=false}={}){
 await checkpoint('independent-check');let output;
 try{output=bridge('checker',{task:t,result}).result;}catch(e){if(!alreadyCharged)await charge(account,checkerReserve(t,result),'failed-check-reservation');throw e;}
 require(integer(output?.counts?.total,0,checkerReserve(t,result)),'CHECK_ACCOUNTING');
 if(!alreadyCharged)await charge(account,output.counts.total,'independent-check-cost');return output;
}
function nativeResult(t,r){const m=inspectTask(t),bound=lowerBound(m);return {schema:'release-plan-result/v1',task_id:t.id,schedule:r.schedule,makespan:r.makespan,movement:r.movement,lower_bound:bound,optimal_by_lower_bound:r.makespan===bound.value,dispatch_order:r.schedule.filter(j=>!(j.id in(t.locked??{}))).map(j=>j.id),lookahead_steps:0,proof:[],authority:[]};}
function quality(t,a,b){if(a.qualified!==b.qualified)return a.qualified?-1:1;if(t.kind==='repair'&&a.qualified)return a.result.movement-b.result.movement||a.result.makespan-b.result.makespan;return a.result.makespan-b.result.makespan||a.result.movement-b.result.movement;}
async function evaluate(t,strategy,account,allocation=100000){
 const previousAccount=activeAccount;activeAccount=account;
 const remaining=limits[account]-costs[account];const budget=Math.min(allocation,remaining-2048);
 if(budget<18000){activeAccount=previousAccount;return {task_id:t.id,result:null,valid:false,qualified:false,error:'CHECK_RESERVE',truncated:true,work:0,allocated_budget:0};}
 await checkpoint('bounded-'+account+'-evaluation');
 const row=await runMission(t,{strategy,sourceHash:limits.source_hash,budget,check:(input,result)=>check(input,result,account,{alreadyCharged:true})});
 require(integer(row.work,0,limits[account]-costs[account]),'EVALUATION_COST_EXCEEDS_RESERVATION');await charge(account,row.work,'evaluation-and-check-cost');
 const evidenceBlocks=blocks({...row,pack:undefined});await charge(account,evidenceBlocks,'evaluation-evidence');
 const {pack,...small}=row;activeAccount=previousAccount;return {...small,pack_digest:pack?hash(pack):null,work:row.work+evidenceBlocks,allocated_budget:allocation,execution_budget:budget};
}
async function deliver(t,{strategy=null,label='Mission',baselineSource=null,phaseIndex=0}={}){
 const start={...costs};await checkpoint('start:'+label);const input=task(t);await charge('service_work',input.validation,'service-input-validation');t=input.task;
 const inputCheck=await check(t,null,'service_work');require(inputCheck.errors.length===1&&inputCheck.errors[0].code==='RESULT_TYPE','INDEPENDENT_INPUT_REFUSED');
 const attempts=[];let selected=null;const portfolio=await evaluate(t,'portfolio','service_work');attempts.push({method:'ordinary-portfolio',...portfolio});if(portfolio.valid)selected=attempts.at(-1);
 if(strategy){inspectStrategy(strategy);const candidate=await evaluate(t,strategy,'improvement_work');attempts.push({method:'retained-qualified-trial',...candidate});if(candidate.valid&&(!selected||quality(t,candidate,selected)<0))selected=attempts.at(-1);}
 if(limits.allow_native){for(const mode of (t.kind==='repair'?['repair','makespan']:['deadline','makespan'])){
  if(costs.native_calls>=limits.native_calls||limits.native_solve_seconds-nativeReservedSeconds<2){attempts.push({method:'native-'+mode,error:'DEFER_NATIVE_ALLOWANCE',allocated_solver_seconds:0});continue;}
  await checkpoint('approved-native-'+mode,{native_calls:1,native_solve_seconds:2});nativeReservedSeconds+=2;let native;
  try{
   const response=bridge('specialist',{task:t,mode,upper_bound:mode==='makespan'&&portfolio.valid?portfolio.result.makespan:null});native=response.result;
   const solverSeconds=Number(native.model_solve_ms??0)/1000;
   require(Number.isFinite(solverSeconds)&&solverSeconds>=0,'NATIVE_COST');await checkpoint('observed-native-solve-telemetry');
   const entry={method:'native-'+mode,native,allocated_solver_seconds:2,valid:false,qualified:false,result:null};
   if(native.schedule){entry.result=nativeResult(t,native);entry.checker=await check(t,entry.result,'service_work');entry.valid=entry.checker.valid;entry.qualified=entry.checker.qualified;}
   attempts.push(entry);if(entry.valid&&(!selected||quality(t,entry,selected)<0))selected=entry;
  }catch(e){if(e.message.startsWith('PROTECTED_'))throw e;attempts.push({method:'native-'+mode,error:e.message,native:native??null,allocated_solver_seconds:2});costs.unknown_costs.push('One native/check attempt failed; its CPU/opaque work may be unknown.');}
 }}else attempts.push({method:'native-specialist',decision:'UNAVAILABLE_NOT_OPERATOR_APPROVED'});
 const verified=Boolean(selected?.valid);const result=selected?.result??null;const receipt={source_hash:limits.source_hash,scientific_source_hash:SCIENTIFIC_SOURCE_HASH,task:t,result,checker:selected?.checker??null,method:selected?.method??null,proof:[],authority:[]};
 const receiptHash=hash(receipt);let pack=null;
 if(verified){
  const adapter={manifest:ADAPTER_MANIFEST,validate(x){inspectTask(x.task);require(hash(x.receipt)===receiptHash,'RECEIPT_BINDING');},async execute(x,cp){await cp('Out-Execute');return {decision:selected.qualified?'QUALIFIED_LOCAL_RESULT':'FEASIBLE_TARGET_NOT_MET',summary:{qualified:selected.qualified,makespan:result.makespan},evidence:{receipt_hash:receiptHash,proof:[],authority:[]},artifacts:[{name:'release-plan.json',type:'application/json',content:JSON.stringify(x.receipt,null,2)+'\n'}],limits:['Planning artifacts only; no physical action or inherited authority.']};}};
  pack=await createWorkbench([adapter]).run({schema:'successor-workbench/v1',family:'release-strategy',name:label,language:'en',owner:'approved-local-operator',rights:{dataClass:t.public_or_synthetic==='public'?'public':'synthetic',source:'Explicitly supplied project plan',license:t.input_license??'Apache-2.0'},reviewMinutes:10,inputs:{task:t,receipt}},{sourceHash:limits.source_hash});
 }
 await charge('service_work',blocks({task:t,result,attempts,pack}),'delivery-pack-and-receipt');
 if(verified)await checkpoint('verified-phase-receipt',{}, {phase_index:phaseIndex,receipt_hash:receiptHash,task:t,result,checker:selected.checker,selectedmethod:selected.method});
 return {label,task_id:t.id,task:t,result,selected_method:selected?.method??null,verified,qualified:Boolean(selected?.qualified),costs:Object.fromEntries(counters.map(k=>[k,costs[k]-start[k]])),receipt_hash:receiptHash,receipt,attempts,pack,baseline_source:baselineSource};
}
function changedPlan(initial,changes){
 keys(changes,['durations','crew','capacity','release','deadline'],'CHANGES_SCHEMA');const next=clone(initial);require(next.kind==='plan','INITIAL_PLAN_REQUIRED');
 next.id=(next.id.slice(0,110)+'-changed');
 for(const [field,target]of [['durations','duration'],['crew','crew']])if(changes[field]!==undefined){keys(changes[field],next.jobs.map(j=>j.id),'CHANGE_JOB');for(const [id,v]of Object.entries(changes[field]))next.jobs.find(j=>j.id===id)[target]=v;}
 for(const field of ['capacity','release','deadline'])if(changes[field]!==undefined)next[field]=clone(changes[field]);
 const validated=task(next).task;require(semanticHash(initial)!==semanticHash(validated),'CHANGED_REQUIREMENTS_REQUIRED');return validated;
}
function repairPlan(previous,repair){
 keys(repair,['observed_at','capacity','deadline','movement_limit'],'REPAIR_SCHEMA');require(previous.verified&&previous.qualified&&previous.result,'VERIFIED_PREVIOUS_PLAN_REQUIRED');
 const t=clone(previous.task);require(integer(repair.observed_at,0,t.capacity.length-1),'OBSERVATION_TIME');
 t.kind='repair';t.id=t.id.slice(0,110)+'-repair';t.baseline=Object.fromEntries(previous.result.schedule.map(j=>[j.id,j.start]));
 t.locked=Object.fromEntries(previous.result.schedule.filter(j=>j.start<repair.observed_at).map(j=>[j.id,j.start]));
 t.release=Object.fromEntries(t.jobs.map(j=>[j.id,j.id in t.locked?(t.release?.[j.id]??0):Math.max(t.release?.[j.id]??0,repair.observed_at)]));
 for(const field of ['capacity','deadline','movement_limit'])if(repair[field]!==undefined)t[field]=clone(repair[field]);
 require(t.capacity.length===previous.task.capacity.length,'REPAIR_HORIZON_CHANGED');
 require(JSON.stringify(t.capacity.slice(0,repair.observed_at))===JSON.stringify(previous.task.capacity.slice(0,repair.observed_at)),'CANNOT_CHANGE_OBSERVED_PAST');
 t.disruption={observed_at:repair.observed_at,completed_jobs:previous.result.schedule.filter(j=>j.end<=repair.observed_at).map(j=>j.id),in_progress_jobs:previous.result.schedule.filter(j=>j.start<repair.observed_at&&j.end>repair.observed_at).map(j=>j.id)};
 return task(t).task;
}
async function construct(payload,{ceiling=250000}={}){
 const previousAccount=activeAccount;activeAccount='improvement_work';
 keys(payload,['stage','parent','training','validation','remaining_missions'],'CONSTRUCTION_SCHEMA');
 require(['dispatch','lookahead','repair'].includes(payload.stage),'CONSTRUCTION_STAGE');
 require(integer(payload.remaining_missions??1,1,3),'FORECAST_MISSIONS_SCOPE');
 require(Array.isArray(payload.training)&&payload.training.length>=1&&payload.training.length<=4&&Array.isArray(payload.validation)&&payload.validation.length>=1&&payload.validation.length<=4,'CONSTRUCTION_CORPUS');
 const inspectedTraining=payload.training.map(task),inspectedValidation=payload.validation.map(task),training=inspectedTraining.map(x=>x.task),validation=inspectedValidation.map(x=>x.task);let parent=payload.parent??null;if(parent)inspectStrategy(parent);
 const trainingHashes=new Set(training.map(semanticHash));require(validation.every(t=>!trainingHashes.has(semanticHash(t))),'TRAINING_QUALIFICATION_NOT_DISJOINT');
 const inherited=payload.stage!=='dispatch';require(!inherited||parent,'PARENT_REQUIRED');
 await checkpoint('construct:'+payload.stage);const beginning=costs.improvement_work,ledgerStart=workLedger.length,end=Math.min(limits.improvement_work-8192,beginning+ceiling),available=()=>Math.max(0,end-costs.improvement_work);
 if(available()<100000){activeAccount=previousAccount;return {stage:payload.stage,decision:'DEFER_PROTECTED_IMPROVEMENT_ALLOWANCE',asset:null,allocated_child_work:ceiling};}
 await charge('improvement_work',inspectedTraining.reduce((n,x)=>n+x.validation,0)+inspectedValidation.reduce((n,x)=>n+x.validation,0)+blocks(payload)+1+(parent?blocks(parent):0),'construction-input-validation-parent-read');
 const reserve=validation.length*2*30000+16384;
 const search=await discover({stage:payload.stage,parent,training,remaining:()=>available()-reserve,evaluate:(t,s)=>evaluate(t,s,'improvement_work',Math.min(60000,Math.max(0,available()-reserve-2048)))});
 const lineage={parent_digest:parent?await strategyIdentity(parent):null,parent_read:parent?1:0,parent_calls:search.trials.reduce((n,t)=>n+t.rows.reduce((n,r)=>n+(r.counts?.['strategy:inherited-dispatch-rollout']??0)+(r.counts?.['strategy:inherited-lookahead-decision']??0),0),0),candidate_digest:search.candidate?.digest??null,output_digest:hash(search),authority:[],proof:[]};
 if(!search.candidate){await charge('improvement_work',blocks({search,lineage}),'failed-construction-evidence');activeAccount=previousAccount;return {stage:payload.stage,decision:'DEFER_NO_COMPLETE_CANDIDATE',search,lineage,asset:null,construction_work:costs.improvement_work-beginning,allocated_child_work:ceiling};}
 const frozen=search.candidate.digest;
 const incumbent=payload.stage==='repair'?{kind:'repair',mode:'quality',stability:0,base:clone(SPECIALISTS[0])}:clone(SPECIALISTS[0]);
 const q=await qualify({candidate:search.candidate,tasks:validation,incumbent,allocation:30000,canFundPair:()=>available()>=64096,evaluate:(t,s,phase,allocation)=>evaluate(t,s,'improvement_work',allocation)});
 require(frozen===await strategyIdentity(search.candidate.strategy),'CANDIDATE_CHANGED');
 const maintenance=blocks(search.candidate)*Math.max(1,payload.remaining_missions??1);
 const provisional=admission({qualification:q,acquisition:costs.improvement_work-beginning,maintenance,remainingMissions:payload.remaining_missions??1,remainingBudget:Math.max(0,limits.service_work-costs.service_work)});
 const gate={...provisional,accepted:false,decision:q.correctness?'HOLD_FULL_COST_UNKNOWN':'REJECT_CURRENT_QUALIFICATION',provisional_model_only:true,native_human_hardware_monetary_costs:'UNKNOWN_OR_SEPARATE',note:'No economic promotion is based on a pre-finalization forecast. Whole action construction/diagnostic/integration/export debits are retained in the authoritative protected improvement ledger.'};
 const corpusBinding={training:training.map(t=>({id:t.id,semantic_hash:semanticHash(t)})),qualification:validation.map(t=>({id:t.id,semantic_hash:semanticHash(t)})),protected_research:false};
 const asset={schema:'engineering-strategy-capability/v1',version:1,stage:payload.stage,strategy:search.candidate.strategy,digest:frozen,frozen_before_service_inputs:true,source_hash:limits.source_hash,scientific_source_hash:SCIENTIFIC_SOURCE_HASH,parent_digest:lineage.parent_digest,executable_interface:'Fixed release-plan/v1 strategy AST, no host code',dependencies:['fixed core.mjs grammar','independent Python checker'],applicability:{kind:payload.stage==='repair'?'repair':'plan',jobs:18,horizon:128},qualification:q,admission:gate,active:false,trial_only:true,production_authority:false,authority:[],proof:[],lifecycle_costs:[],corpus:corpusBinding};
 await charge('improvement_work',blocks({search,q,gate,asset,lineage,corpusBinding}),'construction-retention-integration-evidence');
 const acquisition=costs.improvement_work-beginning;require(acquisition<=ceiling,'CONSTRUCTION_CHILD_ALLOCATION_EXCEEDED');gate.acquisition=acquisition;gate.finalization_included_in_stage_work=true;gate.action_export_accounting='See action-level improvement ledger; no economic promotion before full costs.';
 asset.lifecycle_costs=[{kind:'stage-construction-failed-candidates-checks-retention-integration',improvement_work:acquisition,ledger_start:ledgerStart,ledger_end:workLedger.length},{kind:'forecast-maintenance',work:maintenance,assumption:'Declared remaining missions only; not yet incurred.'},{kind:'action-level-diagnostics-and-export',account:'improvement_work',authoritative_action_ledger:true}];
 activeAccount=previousAccount;
 return {stage:payload.stage,decision:gate.decision,search,qualification:q,gate,lineage,asset,construction_work:acquisition,allocated_child_work:ceiling,corpus:corpusBinding,scope:'Disjoint authored development tasks; candidates freeze before any actual served changed/repair inputs are exposed to them. Not protected research evaluation.'};
}
function semanticHash(t){const jobs=t.jobs.map(j=>({...j,deps:[...j.deps].sort()})).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);return hash({kind:t.kind,jobs,capacity:t.capacity,release:Object.fromEntries(jobs.map(j=>[j.id,t.release?.[j.id]??0])),locked:t.locked??{},baseline:t.baseline??null,deadline:t.deadline??t.capacity.length,movement_limit:t.kind==='repair'?(t.movement_limit??2304):null});}
function developmentPlans(initial){
 const variants=[1,2].map((offset,index)=>{const t=clone(initial);t.id=t.id.slice(0,95)+(index?'-dev-qualification':'-dev-training');t.jobs[0].duration=1+(t.jobs[0].duration-1+offset)%12;t.deadline=t.capacity.length;return task(t).task;});
 require(semanticHash(variants[0])!==semanticHash(variants[1]),'DEVELOPMENT_CORPUS_COLLISION');return {training:[variants[0]],validation:[variants[1]]};
}
async function developmentRepairs(corpus){
 const rows=[],baselineAttempts=[];
 for(const planTask of [corpus.training[0],corpus.validation[0]]){
  const row=await evaluate(planTask,'portfolio','improvement_work',60000);baselineAttempts.push(row);if(!row.valid||!row.qualified){await charge('improvement_work',blocks(baselineAttempts),'development-baseline-deferral-evidence');return {deferred:true,reason:'DEVELOPMENT_BASELINE_NOT_QUALIFIED',baseline_attempts:baselineAttempts,training:[],validation:[]};}
  const planReceipt={verified:true,qualified:true,task:planTask,result:row.result,receipt_hash:hash({task:planTask,result:row.result,checker:row.checker})};
  const observation=1,capacity=clone(planTask.capacity);for(let i=8;i<Math.min(11,capacity.length);i++)capacity[i]=Math.max(0,capacity[i]-1);
  let repaired;try{repaired=repairPlan(planReceipt,{observed_at:observation,capacity,deadline:capacity.length});}catch(error){const failure={deferred:true,reason:'DEVELOPMENT_REPAIR_INFEASIBLE_OR_INVALID',error:error.message,baseline_attempts:baselineAttempts,training:[],validation:[]};await charge('improvement_work',blocks(failure),'development-repair-deferral-evidence');return failure;}repaired.id=planTask.id+'-repair';
  await charge('improvement_work',blocks({planReceipt,repaired}),'development-repair-baseline-lock-provenance');rows.push(repaired);
 }
 return {training:[rows[0]],validation:[rows[1]]};
}
async function parentDiagnostics({stage,parent,corpus,rebuild,rebuildStages=1}){
 const childAllowance=250000,reconstructionAllowance=rebuildStages*250000,armTotalAllocation=childAllowance+reconstructionAllowance+1024,required=3*armTotalAllocation+32768;
 if(limits.improvement_work-costs.improvement_work<required)return {stage,decision:'DEFER_UNFUNDED_MATCHED_PARENT_DIAGNOSTICS',required_allowance:required,arms:[],parent_benefit:'UNQUALIFIED_UNEXECUTED'};
 const start=costs.improvement_work,arms=[];
 for(const treatment of ['inherited','rebuilt','equivalent']){
  await checkpoint('parent-diagnostic:'+stage+':'+treatment);const before=costs.improvement_work;let selectedParent=parent,reconstructed=[];
  if(treatment==='rebuilt'){
   const restored=await rebuild();selectedParent=restored.asset?.strategy??null;reconstructed=restored.reconstruction??[restored];
  }else if(treatment==='equivalent'){
   selectedParent=equivalentRecipe(parent);inspectStrategy(selectedParent);await charge('improvement_work',1+blocks({parent,selectedParent}),'equivalent-parent-normalization');
  }else await charge('improvement_work',1+blocks(parent),'retained-parent-retrieval');
  const reconstructionWork=costs.improvement_work-before;require(reconstructionWork<=reconstructionAllowance+1024,'PARENT_RECONSTRUCTION_ALLOCATION_EXCEEDED');const childStart=costs.improvement_work;
  const child=selectedParent?await construct({stage,parent:selectedParent,...corpus,remaining_missions:1},{ceiling:childAllowance}):null;
  require(costs.improvement_work-before<=armTotalAllocation,'PARENT_DIAGNOSTIC_TOTAL_ALLOCATION_EXCEEDED');arms.push({treatment,parent_digest:selectedParent?await strategyIdentity(selectedParent):null,parent_reconstruction_work:reconstructionWork,parent_reconstruction:reconstructed,child_work:costs.improvement_work-childStart,total_work:costs.improvement_work-before,child_allocation:childAllowance,reconstruction_allocation:reconstructionAllowance,total_allocation:armTotalAllocation,unused_total_allowance:armTotalAllocation-(costs.improvement_work-before),child,decision:child?.qualification?.correctness?'CURRENT_QUALIFICATION_PASSED':'DEFER_OR_REJECT'});
 }
 const [inherited,rebuilt,equivalent]=arms,allQualified=arms.every(a=>a.child?.qualification?.correctness),outputs=a=>a.child?.qualification?.rows.map(r=>r.result)??[];
 const equalFreshOutputs=allQualified&&hash(outputs(inherited))===hash(outputs(rebuilt))&&hash(outputs(inherited))===hash(outputs(equivalent));
 const costRelation=allQualified?(inherited.total_work<rebuilt.total_work?'LESS_RECONSTRUCTION_WORK':inherited.total_work===rebuilt.total_work?'TIE':'MORE_WORK'):'UNQUALIFIED';
 const diagnostic={stage,decision:allQualified?'MATCHED_CHILD_COMPARISONS_EXECUTED':'INCOMPLETE_DIAGNOSTIC',arms,all_currently_qualified:allQualified,equal_fresh_outputs:equalFreshOutputs,parent_construction_consequence:costRelation,parent_benefit:allQualified?'MEASURED_LOCAL_CONSTRUCTION_COSTS_ONLY':'NOT_ESTABLISHED',scope:'Identical per-arm total allowance and child cap with the same child grammar/tools/corpora. All arms reserve the same parent-reconstruction allowance; inherited/equivalent arms leave unused allowance unused, without extra child search. Actual lookup/reconstruction/checking/child/retention costs are recorded. Original parent acquisition is paid once in the full action ledger; experimental rebuilding is separately charged. Local costs/quality do not establish economic promotion or general superiority.',total_work:costs.improvement_work-start};
 await charge('improvement_work',blocks(diagnostic),'parent-diagnostic-retention-export');return diagnostic;
}
async function journey(payload){
 keys(payload,['initial','changes','repair','construction'],'JOURNEY_SCHEMA');const initial=task(payload.initial).task;require(initial.kind==='plan','INITIAL_PLAN_REQUIRED');
 keys(payload.changes,['durations','crew','capacity','release','deadline'],'CHANGES_SCHEMA');keys(payload.repair,['observed_at','capacity','deadline','movement_limit'],'REPAIR_SCHEMA');keys(payload.construction??{},['enabled'],'CONSTRUCTION_OPTIONS');
 const phases=[],capabilities=[],diagnostics=[];const requested=payload.construction?.enabled===true;let enabled=requested&&limits.improvement_work>=3000000;let dispatch=null,repairAsset=null;let corpus=null,repairCorpus=null;
 if(requested&&!enabled)capabilities.push({decision:'DEFER_PROTECTED_IMPROVEMENT_DIAGNOSTIC_ALLOWANCE',required_allowance:3000000,construction_executed:false});
 phases.push(await deliver(initial,{label:'Initial plan'}));if(!phases[0].verified)return {phases,capabilities,inheritance:{parent_benefit:'NOT_ESTABLISHED'},decision:'HOLD_INITIAL_NOT_VERIFIED'};
 if(enabled){
  activeAccount='improvement_work';await checkpoint('fixed-disjoint-development-corpus');try{corpus=developmentPlans(initial);}catch(error){await charge('improvement_work',1+blocks({initial,error:error.message}),'development-corpus-deferral-evidence');capabilities.push({decision:'DEFER_INVALID_DEVELOPMENT_CORPUS',reason:error.message,construction_executed:false});enabled=false;}const actualChangedForCollision=changedPlan(initial,payload.changes);
  if(corpus){
  const forbidden=[semanticHash(initial),semanticHash(actualChangedForCollision)];
  await charge('improvement_work',blocks(corpus)+corpus.training.map(task).concat(corpus.validation.map(task)).reduce((n,x)=>n+x.validation,0),'fixed-disjoint-development-corpus-validation');
  if([...corpus.training,...corpus.validation].some(t=>forbidden.includes(semanticHash(t)))){enabled=false;capabilities.push({decision:'DEFER_DEVELOPMENT_CORPUS_COLLISION',construction_executed:false});}
  else{
   dispatch=await construct({stage:'dispatch',...corpus,remaining_missions:2});capabilities.push(dispatch);
   if(dispatch.asset?.qualification?.correctness){
    const look=await parentDiagnostics({stage:'lookahead',parent:dispatch.asset.strategy,corpus,rebuildStages:1,rebuild:()=>construct({stage:'dispatch',...corpus,remaining_missions:1})});diagnostics.push(look);
    const inheritedLook=look.arms?.[0]?.child;
    if(inheritedLook?.asset?.qualification?.correctness){
     capabilities.push(inheritedLook);repairCorpus=await developmentRepairs(corpus);
     if(repairCorpus.deferred){capabilities.push({decision:'DEFER_DEVELOPMENT_REPAIR_CORPUS',...repairCorpus,asset:null});repairCorpus=null;}else{
     const repair=await parentDiagnostics({stage:'repair',parent:inheritedLook.asset.strategy,corpus:repairCorpus,rebuildStages:2,rebuild:async()=>{
      const rebuiltDispatch=await construct({stage:'dispatch',...corpus,remaining_missions:1});
      if(!rebuiltDispatch.asset?.qualification?.correctness)return {...rebuiltDispatch,asset:null,reconstruction:[rebuiltDispatch]};
      const rebuiltLook=await construct({stage:'lookahead',parent:rebuiltDispatch.asset.strategy,...corpus,remaining_missions:1});return {...rebuiltLook,reconstruction:[rebuiltDispatch,rebuiltLook]};
     }});diagnostics.push(repair);const inheritedRepair=repair.arms?.[0]?.child;
     if(inheritedRepair){capabilities.push(inheritedRepair);repairAsset=inheritedRepair.asset;}
     }
    }
   }
  }
  }
  activeAccount='service_work';
 }
 // The actual changed request and actual repair inputs are now exposed for service only AFTER construction/freezing.
 const changed=changedPlan(initial,payload.changes);
 phases.push(await deliver(changed,{label:'Changed requirements',strategy:dispatch?.asset?.qualification?.correctness?dispatch.asset.strategy:null,phaseIndex:1}));
 if(!phases[1].qualified)return {phases,capabilities,inheritance:{diagnostics,parent_benefit:'NOT_ESTABLISHED'},decision:'HOLD_CHANGED_TARGET_NOT_MET'};
 await checkpoint('derive-repair-from-verified-receipt');const repaired=repairPlan(phases[1],payload.repair);await charge('service_work',blocks(repaired)+blocks(phases[1].receipt),'derive-current-baseline-and-locks');
 if(repairCorpus&&[...repairCorpus.training,...repairCorpus.validation].some(t=>semanticHash(t)===semanticHash(repaired))){if(repairAsset){repairAsset.fresh_service_trial_eligible=false;repairAsset.freshness_refusal='SERVICE_CORPUS_COLLISION';}capabilities.push({decision:'DEFER_FRESH_REPAIR_CORPUS_COLLISION',asset_eligible_for_fresh_trial:false});repairAsset=null;}
 const baselineSource={receipt_hash:phases[1].receipt_hash,task_id:phases[1].task_id,verified:true,observed_at:payload.repair.observed_at,baseline_from:'actual preceding independently verified planning delivery',prefix_basis:'Operator-supplied planning observation; prefix inferred from schedule, no physical completion observed.',completed_jobs:repaired.disruption.completed_jobs,in_progress_jobs:repaired.disruption.in_progress_jobs};
 phases.push(await deliver(repaired,{label:'Repair the same project',phaseIndex:2,strategy:repairAsset?.qualification?.correctness?repairAsset.strategy:null,baselineSource}));
 const repairPhase=phases[2],candidate=repairPhase.attempts.find(a=>a.method==='retained-qualified-trial'),references=repairPhase.attempts.filter(a=>a.method!=='retained-qualified-trial'&&a.valid),bestReference=references.sort((a,b)=>quality(repaired,a,b))[0];
 const relation=candidate?.valid&&bestReference?(quality(repaired,candidate,bestReference)<0?'WIN':quality(repaired,candidate,bestReference)>0?'LOSS':'TIE'):candidate?'REFUSED_OR_UNQUALIFIED':'DEFER_NO_FROZEN_REPAIR';
 return {phases,capabilities,inheritance:{diagnostics,parent_benefit:diagnostics.length===2&&diagnostics.every(d=>d.all_currently_qualified)?'MEASURED_LOCAL_CONSTRUCTION_COSTS_ONLY':'NOT_ESTABLISHED',lineage:capabilities.filter(c=>c.lineage).map(c=>c.lineage),scope:'Parent construction comparison is separate from actual fresh repair end-usefulness; no positive consequence is presumed.'},repair_usefulness:{fresh_task_id:repaired.id,fresh_semantic_hash:semanticHash(repaired),training_qualification:repairCorpus?{training:repairCorpus.training.map(t=>semanticHash(t)),qualification:repairCorpus.validation.map(t=>semanticHash(t))}:null,candidate_frozen_digest:repairAsset?.digest??null,candidate_trial:candidate??null,best_current_specialist:bestReference??null,consequence:relation,selected_method:repairPhase.selected_method,production_promotion:false,economic_decision:'HOLD_FULL_COST_UNKNOWN',scope:candidate?'Frozen repair candidate was trialled only now on actual fresh disruption. All ordinary/native/candidate attempts and costs remain separate.':'No frozen candidate was trialled; only current ordinary/native service executed. Improvement deferral is retained.'},decision:phases.every(p=>p.qualified)?'THREE_LOCAL_PLANNING_RESULTS_VERIFIED':'HOLD_TARGET_NOT_MET'};
}

try{
 const first=await iterator.next();require(!first.done&&Buffer.byteLength(first.value)<=131072,'REQUEST_LIMIT');request=JSON.parse(first.value);keys(request,['method','payload','limits'],'REQUEST_SCHEMA');
 require(['run-mission','construct','run-journey'].includes(request.method),'FIXED_METHOD');limits=request.limits;require(limits&&typeof limits==='object','LIMITS');
 for(const field of ['service_work','improvement_work','native_calls'])require(integer(limits[field],0,field==='native_calls'?6:5000000),'LIMIT_'+field);
 require(Number.isFinite(limits.native_solve_seconds)&&limits.native_solve_seconds>=0&&limits.native_solve_seconds<=60,'LIMIT_NATIVE_SECONDS');require(typeof limits.allow_native==='boolean'&&/^[a-f0-9]{64}$/.test(limits.source_hash),'LIMIT_SOURCE');
 require(limits.allow_native||limits.native_calls===0,'NATIVE_NOT_APPROVED');workerManifest=verifySources();await checkpoint('source-and-operating-scope-verified');
 let result;
 if(request.method==='run-mission'){keys(request.payload,['task','strategy'],'MISSION_SCHEMA');result={phases:[await deliver(task(request.payload.task).task,{strategy:request.payload.strategy??null})]};}
 else if(request.method==='construct')result=await construct(request.payload);
 else result=await journey(request.payload);
 result.provenance={scientific_source_hash:SCIENTIFIC_SOURCE_HASH,worker_manifest_hash:workerManifest,engineering_addition:true,frozen_research_changed:false,authority:[],proof:[]};result.events=events;result.native_telemetry=pythonTelemetry;
 const cpu=process.cpuUsage(startedCPU);result.native_allocated_solver_seconds=nativeReservedSeconds;result.runtime_telemetry={node_cpu_seconds:(cpu.user+cpu.system)/1000000,wall_seconds:(performance.now()-startedWall)/1000};
 if(request.method==='construct'){activeAccount='improvement_work';await charge('improvement_work',blocks(result),'construction-final-export-and-retention');}
 else {
  const improvementRecords={capabilities:result.capabilities,inheritance:result.inheritance,repair_usefulness:result.repair_usefulness,events:events.filter(e=>e.account==='improvement_work')};
  if(result.capabilities?.some(c=>c.search)){activeAccount='improvement_work';await charge('improvement_work',blocks(improvementRecords),'construction-final-export-and-retention');}
  activeAccount='service_work';await charge('service_work',blocks({...result,capabilities:undefined,inheritance:undefined,repair_usefulness:undefined,events:events.filter(e=>e.account!=='improvement_work')}),'service-final-export-and-retention');
 }
 result.accounting={improvement_ledger:workLedger.filter(e=>e.account==='improvement_work'),improvement_total:costs.improvement_work,service_total:costs.service_work,native_counter_semantics:'Charged 2-second solve allowance per approved attempt; observed wall/CPU are separate native telemetry.',scope:'All modelled construction/diagnostic/check/retention/integration/export debits are retained. Bookkeeping/source/IPC CPU remains separately measured, not converted into JS units.'};
 process.stdout.write(JSON.stringify({type:'result',result,costs,source_hash:limits.source_hash,verified:request.method==='construct'?Boolean(result.qualification?.correctness):Boolean(result.phases?.length&&result.phases.every(p=>p.verified))})+'\n');
}catch(error){process.stdout.write(JSON.stringify({type:'error',error:error.message,costs,source_hash:limits?.source_hash??null,verified:false})+'\n');process.exitCode=1;}
finally{lines.close();}
