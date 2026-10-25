// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash,randomUUID} from 'node:crypto';
import os from 'node:os';
import {spawn} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {ARMS,METHODS,makeStream,runEpoch,inspectEpoch,selectOne,Meter,makeSpec,verifyCapability,comparisonUnits,adapter,workbench} from './kernel.mjs';
import {canonical,digest} from './vendor/docs/assets/successor/engine.mjs';
import {runComparison,evaluate} from './vendor/docs/assets/transformational-intelligence/source-understanding.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const sha=data=>createHash('sha256').update(data).digest('hex');
const json=async file=>JSON.parse(await fs.readFile(file,'utf8'));
const write=async(file,value)=>{await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,JSON.stringify(value,null,2)+'\n',{flag:'wx'});};
const lines=async(file,values)=>{await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,values.map(x=>JSON.stringify(x)).join('\n')+'\n',{flag:'wx'});};
const size=async directory=>{let total=0;for(const entry of await fs.readdir(directory,{withFileTypes:true})){const name=path.join(directory,entry.name);total+=entry.isDirectory()?await size(name):(await fs.stat(name)).size;}return total;};
const categories=['construction','qualification','execution','validation','routing','retention','maintenance','runtime'];
export async function sourceManifest(){
  const upstream=await json(path.join(ROOT,'upstream-manifest.json'));
  const paths=['kernel.mjs','run.mjs','protocol.json',...upstream.files.map(x=>'vendor/'+x.path)];
  const files=[];for(const name of paths){const content=await fs.readFile(path.join(ROOT,name));files.push({path:name,bytes:content.length,sha256:sha(content)});}
  files.sort((a,b)=>a.path.localeCompare(b.path));return {files,sourceHash:sha(JSON.stringify(files))};
}
export function nextDue(tasks,completed,clock){const item=tasks.find(x=>!completed.has(x.id));return !item?{state:'COMPLETE'}:item.at>clock?{state:'WAIT',next:item.at}:{state:'READY',id:item.id};}
function checkPermit(permit,sourceHash,clock=Date.now()){
  if(permit.sourceHash!==sourceHash)throw Error('SOURCE_DEPENDENCY_CHANGED');
  if(!Number.isFinite(Date.parse(permit.expires))||clock>=Date.parse(permit.expires))throw Error('RESEARCH_PERMIT_EXPIRED');
  if(permit.stopped)throw Error('STOP_ACTIVE');
}
async function inspectSemantic(pack){
  await inspectEpoch(pack);const input=pack.spec.inputs;
  for(let index=0;index<pack.result.evidence.observations.length;index++){const row=pack.result.evidence.observations[index];if(canonical(row.document)!==canonical(input.missions[index])||row.stream!==input.stream||row.arm!==input.arm||row.epoch!==input.epoch||row.max_clauses!==input.max_clauses||row.mission_id!==`s${input.stream}-g${input.epoch}-m${index}`)throw Error('RECEIPT_TASK_BINDING');}
  for(const item of pack.result.evidence.retained)await verifyCapability(item);
  const meter=new Meter(2_000_000);
  for(const row of pack.result.evidence.observations){const value=selectOne(row.document,row.method,row.max_clauses,meter,'maintenance'),comparison=runComparison(row.document,row.max_clauses);meter.charge('maintenance',comparisonUnits(row.document,row.max_clauses),'recovery-semantic-validation');const optimum=comparison.methods.find(x=>x.method==='dependency-graph-before-compression').structural_score;if(canonical(value.selected)!==canonical(row.selected)||value.structural_score!==row.structural_score||optimum!==row.optimal_score||row.qualified!==(!value.missing.length&&value.structural_score===optimum))throw Error('SEMANTIC_RECEIPT_INVALID');}
  if(input.sourceHash!==pack.frozen.sourceHash)throw Error('SOURCE_RECEIPT_INVALID');
  const recomputed=await adapter.execute(input,async()=>{});
  const semantic=value=>JSON.parse(JSON.stringify(value,(key,item)=>key==='elapsed_ns'?undefined:item));
  if(canonical(semantic(recomputed))!==canonical(semantic({...pack.result,artifacts:pack.result.artifacts.map(({digest,...artifact})=>artifact)})))throw Error('EPOCH_SEMANTIC_BINDING');
  return {verification_units:meter.spent+recomputed.evidence.spent-input.spent,verified_rows:pack.result.evidence.observations.length,verification_reexecutions:1,limitation:'Explicit deterministic verification recomputes pure work; original measurements are retained and no fresh mission result is issued.'};
}
async function executeSaved(input,directory,permit,options={}){
  const loaded=await sourceManifest();checkPermit(permit,loaded.sourceHash);if(input.sourceHash!==loaded.sourceHash)throw Error('SOURCE_DEPENDENCY_CHANGED');const name=path.join(directory,`s${input.stream}-${input.arm}-g${input.epoch}.json`),spec=makeSpec(input);
  try {
    const pack=await json(name);
    if(canonical(pack.spec)!==canonical(spec))throw Error('DUPLICATE_REQUEST_CONFLICT');
    const recovery=await inspectSemantic(pack);return {pack,reused:true,recovery,fresh_invocations:0};
  }catch(error){if(error.code!=='ENOENT')throw error;}
  let checkpoints=0;const started=performance.now();
  const pack=await runEpoch(input,{signal:options.signal,onCheckpoint:async()=>{checkPermit(permit,(await sourceManifest()).sourceHash);checkpoints++;await options.onCheckpoint?.(checkpoints);}});
  const content=JSON.stringify(pack);await fs.mkdir(directory,{recursive:true});
  const handle=await fs.open(name,'wx');try{await handle.writeFile(content+'\n');await handle.sync();}finally{await handle.close();}
  if(options.loseAcknowledgement){const error=Error('SIMULATED_ACKNOWLEDGEMENT_LOSS');error.committedFile=name;error.fresh_invocations=1;throw error;}
  return {pack,reused:false,fresh_invocations:1,checkpoints,wall_ms:performance.now()-started};
}
async function freeze(){
  const protocol=await json(path.join(ROOT,'protocol.json')),manifest=await sourceManifest();
  const tasks={schema:'flywheel-frozen-tasks/v1',streams:protocol.seeds.map((seed,index)=>makeStream(seed,index,'primary'))};
  await write(path.join(ROOT,'tasks.json'),tasks);
  const independent=[];for(const name of ['verify.py','receipt_verify.py','review_results.py','dev_check.py','preconfirmation-checker-snapshot.json','preconfirmation-adapter-snapshot.json']){const content=await fs.readFile(path.join(ROOT,'../review/independent',name));independent.push({path:'../review/independent/'+name,bytes:content.length,sha256:sha(content)});}
  const result={schema:'flywheel-freeze/v1',created_at:new Date().toISOString(),primary_has_started:false,protocol_sha256:sha(await fs.readFile(path.join(ROOT,'protocol.json'))),tasks_sha256:sha(await fs.readFile(path.join(ROOT,'tasks.json'))),independent_checker_files:independent,...manifest};
  await write(path.join(ROOT,'freeze.json'),result);console.log(JSON.stringify({freeze_sha256:sha(await fs.readFile(path.join(ROOT,'freeze.json'))),sourceHash:manifest.sourceHash,task_hash:result.tasks_sha256,status:'FROZEN_UNEXECUTED'}));
}
function stripGeneration(result,pack){const {observations,cost_events,...rest}=result;return {...rest,packDigest:pack.integrityDigest};}
async function primary(destination='results',resume=false){
  const frozen=await json(path.join(ROOT,'freeze.json')),current=await sourceManifest(),protocol=await json(path.join(ROOT,'protocol.json'));
  if(current.sourceHash!==frozen.sourceHash||sha(await fs.readFile(path.join(ROOT,'tasks.json')))!==frozen.tasks_sha256)throw Error('FREEZE_CHANGED');
  const tasks=await json(path.join(ROOT,'tasks.json')),output=path.resolve(ROOT,destination);
  try{await fs.mkdir(output,{recursive:false});}catch(error){if(!resume||error.code!=='EEXIST')throw error;}
  const permit={scope:'finite-public-local-research',sourceHash:current.sourceHash,issued:new Date().toISOString(),expires:new Date(Date.now()+4*3600_000).toISOString(),stopped:false};
  await write(path.join(output,resume?`research-permit-resume-${Date.now()}.json`:'research-permit.json'),permit);
  const allRows=[],allGenerations=[],allLedger=[],streams=[],timing=[];const wholeStart=performance.now(),wholeCPU=process.cpuUsage();
  for(const stream of tasks.streams){
    const order=ARMS.slice(stream.stream%ARMS.length).concat(ARMS.slice(0,stream.stream%ARMS.length));
    for(const arm of order){
      let retained=[],spent=0,qualified=0,state='finite-stream-complete';const costs=Object.fromEntries(categories.map(x=>[x,0]));
      for(const epoch of stream.epochs){
        const input={...epoch,stream:stream.stream,arm,budget:protocol.primary_budget_per_stream,spent,retained,sourceHash:current.sourceHash};
        const t0=performance.now(),cpu=process.cpuUsage();
        const execution=await executeSaved(input,path.join(output,'packs'),permit),pack=execution.pack,result=pack.result.evidence;
        timing.push({stream:stream.stream,arm,epoch:epoch.epoch,wall_ms:performance.now()-t0,cpu_microseconds:process.cpuUsage(cpu),pack_bytes:(await fs.stat(path.join(output,'packs',`s${stream.stream}-${arm}-g${epoch.epoch}.json`))).size,fresh_invocations:execution.fresh_invocations,recovery:execution.recovery||null,measurement_scope:execution.reused?'verification elapsed, not original mission measurement':'fresh mission process elapsed'});
        spent=result.spent;retained=result.retained;qualified+=result.coverage;
        allRows.push(...result.observations);allGenerations.push(stripGeneration(result,pack));
        for(const event of result.cost_events)allLedger.push({stream:stream.stream,arm,epoch:epoch.epoch,...event});
        for(const category of categories)costs[category]+=result.costs[category];
        if(result.failure){state=result.failure;break;}
      }
      streams.push({stream:stream.stream,arm,qualified,requested:36,spent,costs,state,active_capabilities:retained.length});
    }
  }
  const cpu=process.cpuUsage(wholeCPU),arms={};
  for(const arm of ARMS){const chosen=streams.filter(x=>x.arm===arm);arms[arm]={qualified:chosen.reduce((n,x)=>n+x.qualified,0),requested:288,total_units:chosen.reduce((n,x)=>n+x.spent,0),costs:Object.fromEntries(categories.map(c=>[c,chosen.reduce((n,x)=>n+x.costs[c],0)])),per_stream:chosen.map(x=>({stream:x.stream,qualified:x.qualified,spent:x.spent}))};}
  const budgetCurves=Object.fromEntries(ARMS.map(arm=>[arm,protocol.secondary_budget_points.map(budget=>({budget,qualified:allRows.filter(x=>x.arm===arm&&x.qualified&&x.cost_after<=budget).length,note:'Descriptive prefix accounting projection, not fresh policy runs at altered budgets.'}))]));
  if(resume){
    const resumeDirectory=path.join(output,'resume-'+Date.now());await fs.mkdir(resumeDirectory);
    await write(path.join(resumeDirectory,'reconciliation.json'),{sourceHash:current.sourceHash,streams,arms,timing,fresh_invocations:timing.reduce((n,x)=>n+x.fresh_invocations,0),verification_units:timing.reduce((n,x)=>n+(x.recovery?.verification_units||0),0),scope:'Previous packs retained unchanged. Explicit deterministic verification re-execution is measured separately; no historical timing is relabeled fresh.'});
    await lines(path.join(resumeDirectory,'observations.jsonl'),allRows);console.log(JSON.stringify({status:'RECONCILED',directory:resumeDirectory,fresh_invocations:timing.reduce((n,x)=>n+x.fresh_invocations,0)}));return;
  }
  await lines(path.join(output,'observations.jsonl'),allRows);await lines(path.join(output,'ledger.jsonl'),allLedger);await write(path.join(output,'generations.json'),allGenerations);await write(path.join(output,'timing.json'),timing);
  const summary={schema:'flywheel-results/v1',sourceHash:current.sourceHash,protocol_sha256:frozen.protocol_sha256,tasks_sha256:frozen.tasks_sha256,budget:protocol.primary_budget_per_stream,streams,arms,budgetCurves,wall_ms:performance.now()-wholeStart,cpu_microseconds:cpu,storage_bytes_before_summary:await size(output),human_interventions_during_primary:0,primary_launches:1,independent_streams:8,scope:'source-extension synthetic structural work; no economic or production growth established'};
  await write(path.join(output,'summary.json'),summary);console.log(JSON.stringify(summary));
}
async function differential(output){
  const failures=[],checks=[];
  for(const seed of [101,211,307,409])for(let epoch=0;epoch<6;epoch++){
    const task=makeStream(seed,0,'development-parity').epochs[epoch];
    for(const doc of task.development){const expected=runComparison(doc,task.max_clauses);for(const method of METHODS){const value=selectOne(doc,method,task.max_clauses,new Meter(2_000_000)),other=expected.methods.find(x=>x.method===method),pass=canonical(value)===canonical(Object.fromEntries(Object.entries(other).filter(([key])=>key!=='method')));checks.push({seed,epoch,method,passed:pass});if(!pass)failures.push({seed,epoch,method,value,other});}}
  }
  await write(output,{scope:'development-only; no primary tasks',checks,failures,passed:failures.length===0});if(failures.length)throw Error('DIFFERENTIAL_FAILURE');
}
async function faults(destination='faults'){
  const output=path.resolve(ROOT,destination);await fs.mkdir(output,{recursive:false});const source=await sourceManifest(),stream=makeStream(919,0,'fault-only'),permit={scope:'finite-public-local-research',sourceHash:source.sourceHash,issued:new Date().toISOString(),expires:new Date(Date.now()+3600_000).toISOString(),stopped:false};
  const input={...stream.epochs[1],stream:0,arm:'flywheel',budget:500000,spent:0,retained:[],sourceHash:source.sourceHash},cases=[];
  const first=await executeSaved(input,path.join(output,'saved'),permit,{loseAcknowledgement:true}).catch(error=>({error:error.message,fresh_invocations:error.fresh_invocations}));
  const recovered=await executeSaved(input,path.join(output,'saved'),permit),duplicate=await executeSaved(input,path.join(output,'saved'),permit);
  cases.push({name:'lost-acknowledgement',first,recovery:{reused:recovered.reused,fresh_invocations:recovered.fresh_invocations,...recovered.recovery},passed:first.error==='SIMULATED_ACKNOWLEDGEMENT_LOSS'&&recovered.reused});
  cases.push({name:'duplicate-request',fresh_invocations:duplicate.fresh_invocations,...duplicate.recovery,passed:duplicate.reused});
  const changed={...input,max_clauses:3};try{await executeSaved(changed,path.join(output,'saved'),permit);cases.push({name:'changed-input',passed:false});}catch(error){cases.push({name:'changed-input',error:error.message,passed:error.message==='DUPLICATE_REQUEST_CONFLICT'});}
  const child=await spawnJSON(['recover-worker'],{input,directory:path.join(output,'saved'),permit});cases.push({name:'process-restart',...child,passed:child.reused&&child.fresh_invocations===0});
  const copyRoot=path.join(output,'changed-source');
  for(const file of [...source.files.map(x=>x.path),'upstream-manifest.json']){const destination=path.join(copyRoot,file);await fs.mkdir(path.dirname(destination),{recursive:true});await fs.copyFile(path.join(ROOT,file),destination);}
  const dep=path.join(copyRoot,'vendor/docs/assets/transformational-intelligence/source-understanding.mjs');await fs.appendFile(dep,'\n// changed local dependency fixture\n');
  const changedHash=sha(await fs.readFile(dep)),changedResult=await spawnJSON(['recover-worker'],{input,directory:path.join(output,'saved'),permit},path.join(copyRoot,'run.mjs'));cases.push({name:'changed-dependency',changed_file_sha256:changedHash,...changedResult,passed:changedResult.error==='SOURCE_DEPENDENCY_CHANGED'&&changedResult.fresh_invocations===0});
  const invalid=JSON.parse(JSON.stringify(recovered.pack));invalid.result.evidence.observations[0].structural_score+=1;
  try{await inspectSemantic(invalid);cases.push({name:'invalid-receipt',passed:false});}catch(error){cases.push({name:'invalid-receipt',error:error.message,passed:error.message==='PACK_INTEGRITY'});}
  const {integrityDigest,...body}=invalid;invalid.integrityDigest=await digest('workbench-pack',body);const nativeAccepted=await inspectEpoch(invalid).then(()=>true).catch(()=>false);
  try{await inspectSemantic(invalid);cases.push({name:'self-consistent-invalid-receipt',nativeAccepted,passed:false});}catch(error){cases.push({name:'self-consistent-invalid-receipt',nativeAccepted,error:error.message,passed:error.message==='SEMANTIC_RECEIPT_INVALID',limit:'Native integrity inspection alone is not semantic final proof.'});}
  const swapped=JSON.parse(JSON.stringify(recovered.pack));swapped.result.evidence.observations[0].document=swapped.spec.inputs.development[0];const {integrityDigest:oldHash,...swappedBody}=swapped;swapped.integrityDigest=await digest('workbench-pack',swappedBody);
  try{await inspectSemantic(swapped);cases.push({name:'self-consistent-task-swap',passed:false});}catch(error){cases.push({name:'self-consistent-task-swap',error:error.message,passed:error.message==='RECEIPT_TASK_BINDING'});}
  const forged=JSON.parse(JSON.stringify(recovered.pack));forged.result.evidence.retained[0].method='lead-order';const {integrityDigest:forgedHash,...forgedBody}=forged;forged.integrityDigest=await digest('workbench-pack',forgedBody);
  try{await inspectSemantic(forged);cases.push({name:'forged-retained-candidate',passed:false});}catch(error){cases.push({name:'forged-retained-candidate',error:error.message,passed:error.message==='CAPABILITY_BINDING'});}
  const exhausted=await runEpoch({...input,budget:2});cases.push({name:'exhausted-budget',spent:exhausted.result.evidence.spent,decision:exhausted.result.decision,passed:exhausted.result.decision==='STOP_BUDGET'&&exhausted.result.evidence.spent<=2});
  try{await executeSaved(input,path.join(output,'expired'),{...permit,expires:'2000-01-01T00:00:00.000Z'});cases.push({name:'expired-authority',passed:false});}catch(error){cases.push({name:'expired-authority',error:error.message,passed:error.message==='RESEARCH_PERMIT_EXPIRED',scope:'Local research permit; no production authority existed.'});}
  const controller=new AbortController();let interrupted;
  try{await executeSaved({...input,epoch:2},path.join(output,'interrupted'),permit,{signal:controller.signal,onCheckpoint:n=>{if(n===5)controller.abort();}});}catch(error){interrupted={error:error.message,partial:error.research_partial||null};}
  cases.push({name:'STOP',...interrupted,passed:interrupted?.error==='CANCELLED'});
  const retry=await executeSaved({...input,epoch:2},path.join(output,'interrupted'),permit);cases.push({name:'precommit-recovery',fresh_invocations:retry.fresh_invocations,passed:retry.fresh_invocations===1,limit:'Pure uncommitted work is recomputed; interrupted costs above remain additional.'});
  cases.push({name:'WAIT',waiting:nextDue([{id:'next',at:100}],new Set(),99),ready:nextDue([{id:'next',at:100}],new Set(),100),passed:nextDue([{id:'next',at:100}],new Set(),99).state==='WAIT'});
  const exact=JSON.parse(JSON.stringify(recovered.pack.result.evidence.retained));for(const item of exact)await verifyCapability(item);
  const rollbackTask=stream.epochs[4],rollback=await runEpoch({...rollbackTask,stream:0,arm:'flywheel',budget:500000,spent:recovered.pack.result.evidence.spent,retained:exact,sourceHash:source.sourceHash});
  cases.push({name:'rollback',prior_digests:exact.map(x=>x.digest),reused_digests:rollback.result.evidence.observations.map(x=>x.capability_digest),decision:rollback.result.decision,proof:[],authority:[],passed:rollback.result.evidence.observations.some(x=>exact.some(y=>y.digest===x.capability_digest))&&rollback.result.evidence.retained.every(x=>x.proof.length===0&&x.authority.length===0),scope:'Actually re-executed prior accepted recipe on a new requirement; no production grant or native deployment rollback.'});
  const rejectInput={...stream.epochs[5],stream:1,arm:'flywheel',budget:500000,spent:0,retained:[],sourceHash:source.sourceHash};
  rejectInput.development=rejectInput.development.map((doc,index)=>({...doc,claims:[{schema_version:1,id:'A',text:`Fault-only development ${index} minor observation.`,weight:1,depends_on:[],provenance:'Synthetic fault'},{schema_version:1,id:'B',text:`Fault-only development ${index} major observation.`,weight:20,depends_on:[],provenance:'Synthetic fault'}]}));
  rejectInput.qualification=[{...rejectInput.qualification[0],claims:[{schema_version:1,id:'R',text:'Fault-only root premise.',weight:1,depends_on:[],provenance:'Synthetic fault'}, {schema_version:1,id:'D',text:'Fault-only dependent conclusion.',weight:20,depends_on:['R'],provenance:'Synthetic fault'}]},rejectInput.qualification[1]];
  const rejected=await executeSaved(rejectInput,path.join(output,'rejected'),permit),rejectedRestart=await spawnJSON(['recover-worker'],{input:rejectInput,directory:path.join(output,'rejected'),permit});
  cases.push({name:'rejected-result-restart',decision:rejected.pack.result.decision,...rejectedRestart,passed:rejected.pack.result.decision==='REJECT_DESCENDANT'&&rejectedRestart.reused&&rejectedRestart.fresh_invocations===0,scope:'Rejected descendant remains unadmitted after exact deterministic validation.'});
  await write(path.join(output,'failure_cases.json'),{cases,passed:cases.every(x=>x.passed),storage_bytes:await size(output)});console.log(JSON.stringify({faults:cases.length,passed:cases.every(x=>x.passed)}));
}
async function spawnJSON(args,input,script=fileURLToPath(import.meta.url)){const directory=path.join(os.tmpdir(),'flywheel-worker-'+randomUUID());await fs.mkdir(directory);const inputFile=path.join(directory,'input.json'),outputFile=path.join(directory,'output.json');await fs.writeFile(inputFile,JSON.stringify(input));return new Promise((resolve,reject)=>{const processChild=spawn(process.execPath,[script,...args,inputFile,outputFile],{stdio:['ignore','inherit','inherit']});processChild.on('error',reject);processChild.on('close',async code=>{if(code!==0)return reject(Error('CHILD_FAILED:'+code));try{const value=await json(outputFile);await fs.rm(directory,{recursive:true});resolve(value);}catch(error){reject(error);}});});}
async function workerInput(){return json(process.argv[3]);}
async function workerOutput(value){await fs.writeFile(process.argv[4],JSON.stringify(value));}
async function load(destination='load'){
  const output=path.resolve(ROOT,destination);await fs.mkdir(output,{recursive:false});const source=await sourceManifest(),cases=[];
  for(const workers of [1,2,4]){const work=Array.from({length:16},(_,i)=>({seed:10001+i,task:i,sourceHash:source.sourceHash})),start=performance.now();const results=(await Promise.all(Array.from({length:workers},(_,worker)=>spawnJSON(['load-worker'],{jobs:work.filter((_,i)=>i%workers===worker)})))).flatMap(x=>x.results);const duration=performance.now()-start,latencies=results.map(x=>x.latency_ms).sort((a,b)=>a-b);cases.push({workers,actual_processes:workers,tasks:16,wall_ms:duration,throughput_tasks_per_second:16000/duration,p50_latency_ms:latencies[Math.floor(latencies.length*.5)],p95_latency_ms:latencies[Math.min(latencies.length-1,Math.ceil(latencies.length*.95)-1)],qualified:results.reduce((n,x)=>n+x.qualified,0),requested:96,cpu_microseconds:results.reduce((n,x)=>n+x.cpu_microseconds.user+x.cpu_microseconds.system,0),output_bytes:results.reduce((n,x)=>n+x.output_bytes,0),results,human_interventions:0});}
  await write(path.join(output,'load.json'),{scope:'Finite source-extension batch; wall includes process startup; per-task latency excludes waiting before its worker starts it.',cases});console.log(JSON.stringify(cases.map(({results,...rest})=>rest)));
}
async function ablations(destination='ablations'){
  const output=path.resolve(ROOT,destination);await fs.mkdir(output,{recursive:false});const rows=(await fs.readFile(path.join(ROOT,'results/observations.jsonl'),'utf8')).trim().split('\n').map(JSON.parse).filter(x=>x.stream===0&&x.arm==='flywheel'),results=[];
  const source=await sourceManifest();
  for(const row of rows){for(const variant of ['remove','replace']){
    const meter=new Meter(2_000_000);let method='lead-order',replacement=null;
    if(variant==='replace'){replacement={schema:'flywheel-capability/v1',method:row.method,scope:row.method==='weighted-without-dependencies'?'independent-clauses':row.method==='lead-order'?'ordered-independent':'acyclic-graph',sourceHash:source.sourceHash,created_epoch:row.epoch+1000,proof:[],authority:[],reuse:'Fresh result checks remain required.'};replacement.digest=await digest('flywheel-capability',replacement);await verifyCapability(replacement);meter.charge('retention',Math.ceil(Buffer.byteLength(canonical(replacement))/1024),'replacement-artifact-build-and-read');method=replacement.method;}
    const value=selectOne(row.document,method,row.max_clauses,meter,'execution'),comparison=runComparison(row.document,row.max_clauses);meter.charge('validation',comparisonUnits(row.document,row.max_clauses),'ablation-oracle');const optimum=comparison.methods.find(x=>x.method==='dependency-graph-before-compression').structural_score;
    results.push({pair_id:row.mission_id,variant,original_method:row.method,method,original_capability_digest:row.capability_digest,had_inherited_capability:row.capability_digest!==null,replacement,original_qualified:row.qualified,qualified:!value.missing.length&&value.structural_score===optimum,structural_score:value.structural_score,optimal_score:optimum,selected:value.selected,missing:value.missing,document:row.document,max_clauses:row.max_clauses,units:meter.spent,replacement_semantics_unchanged:variant==='replace'});
  }}
  await lines(path.join(output,'ablations.jsonl'),results);
  const frozenTasks=await json(path.join(ROOT,'tasks.json')),counterfactual={schema:'flywheel-archive-cleared/v1',stream:0,budget:500000,qualified:0,spent:0,observations:[],generations:[],scope:'Same exact registered stream0 flywheel policy and budget; discard archive before each epoch, allow full reconstruction and requalification. Secondary intervention only.'};
  for(const epoch of frozenTasks.streams[0].epochs){const pack=await runEpoch({...epoch,stream:0,arm:'flywheel',budget:500000,spent:counterfactual.spent,retained:[],sourceHash:source.sourceHash}),result=pack.result.evidence;counterfactual.spent=result.spent;counterfactual.qualified+=result.coverage;counterfactual.observations.push(...result.observations);counterfactual.generations.push(stripGeneration(result,pack));await write(path.join(output,'archive-cleared-packs',`generation-${epoch.epoch}.json`),pack);if(result.failure)break;}
  counterfactual.requested=36;await write(path.join(output,'archive-cleared.json'),counterfactual);
  const doc={schema_version:1,schema:'source-document/v1',title:'Omitted prerequisite model challenge',source_url:'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',public_non_personal:true,claims:[{schema_version:1,id:'premise',text:'Synthetic hidden premise is required.',weight:1,depends_on:[],provenance:'Evaluator-only semantic challenge'},{schema_version:1,id:'conclusion',text:'Synthetic conclusion actually requires the premise.',weight:20,depends_on:[],provenance:'Submitted annotation deliberately omits the dependency'}]};
  const submitted=runComparison(doc,1),candidate=submitted.methods.find(x=>x.method==='dependency-graph-before-compression'),truth=JSON.parse(JSON.stringify(doc));truth.claims[1].depends_on=['premise'];const actual=evaluate(truth,candidate.selected);
  await write(path.join(output,'annotation-challenge.json'),{submitted_document:doc,hidden_true_document:truth,max_clauses:1,selected:candidate.selected,locally_supported:candidate.missing.length===0,true_supported:actual.missing.length===0,local_score:candidate.structural_score,true_score:actual.structural_score,units:comparisonUnits(doc,1)+truth.claims.length+1,scope:'Excluded evaluator-only model-invalidity challenge; preserve locally accepted invalidity.'});console.log(JSON.stringify({pairs:rows.length,observations:results.length,archive_cleared_qualified:counterfactual.qualified,archive_cleared_units:counterfactual.spent,annotation_failure:actual.missing.length>0}));
}
const action=process.argv[2];
if(action==='freeze')await freeze();
else if(action==='primary'||action==='reproduce')await primary(process.argv[3]||'results');
else if(action==='resume')await primary(process.argv[3]||'results',true);
else if(action==='development')await differential(path.join(ROOT,process.argv[3]||'development-differential.json'));
else if(action==='faults')await faults(process.argv[3]||'faults');
else if(action==='load')await load(process.argv[3]||'load');
else if(action==='ablations')await ablations(process.argv[3]||'ablations');
else if(action==='recover-worker'){const value=await workerInput();try{const result=await executeSaved(value.input,value.directory,value.permit);await workerOutput({reused:result.reused,fresh_invocations:result.fresh_invocations,...result.recovery});}catch(error){await workerOutput({error:error.message,fresh_invocations:0});}}
else if(action==='load-worker'){const {jobs}=await workerInput(),results=[];for(const job of jobs){const task=makeStream(job.seed,job.task,'load-only').epochs[2],start=performance.now(),cpu=process.cpuUsage(),pack=await runEpoch({...task,stream:job.task,arm:'flywheel',budget:500000,spent:0,retained:[],sourceHash:job.sourceHash});results.push({task:job.task,latency_ms:performance.now()-start,cpu_microseconds:process.cpuUsage(cpu),qualified:pack.result.summary.qualified,output_bytes:Buffer.byteLength(JSON.stringify(pack))});}await workerOutput({results});}
else throw Error('Use: node run.mjs development | freeze | primary [new-directory] | reproduce <new-directory> | resume <directory> | faults | load | ablations');
