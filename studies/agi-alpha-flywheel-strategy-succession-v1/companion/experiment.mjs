// SPDX-License-Identifier: Apache-2.0
// One bounded confirmation launcher. It refuses an absent/changed source freeze.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import zlib from 'node:zlib';
import readline from 'node:readline';import {spawn,spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';import {once} from 'node:events';
import {createMissionStream} from './stream.mjs';import {createChecker} from './checker-client.mjs';import {verifySource} from './verify-source.mjs';
import {createConfirmationInputs,developmentConfiguration,makeTask} from './scenarios.mjs';
import {MAIN_SEEDS,DIAGNOSTIC_SEEDS,assertDisjoint,scanDevelopment} from './seed-registry.mjs';
import {runMission} from './adapter.mjs';import {inspectTask,lowerBound} from './core.mjs';
import {SOURCE_HASH} from './binding.mjs';

const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'..'),args=process.argv.slice(2);
const value=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const smoke=args.includes('--development-smoke');
if(!args.includes('--confirm')&&!smoke)throw Error('EXPLICIT_CONFIRM_FLAG_REQUIRED_AFTER_ROOT_AUTHORIZATION');
if(smoke&&args.includes('--confirm'))throw Error('MUTUALLY_EXCLUSIVE_RUN_MODES');
verifySource({requireFrozen:!smoke});
const python=value('--python','python3');
const freezeCheck=smoke?{status:0,stdout:'DEVELOPMENT_ONLY_NO_PROTECTED_INPUTS'}:spawnSync(python,[path.join(root,'scripts/freeze_study.py')],{encoding:'utf8'});
if(freezeCheck.status!==0)throw Error('TOP_LEVEL_FREEZE_REFUSED: '+freezeCheck.stdout+freezeCheck.stderr);
const protocol=JSON.parse(fs.readFileSync(path.join(root,'protocol/MAIN_PROTOCOL.json')));
const out=path.resolve(value('--out',path.join(root,'results/confirmation-v1')));
if(fs.existsSync(out))throw Error('CONFIRMATION_OUTPUT_MUST_BE_NEW');
fs.mkdirSync(out,{recursive:true});
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const write=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});const temporary=file+'.pending';fs.writeFileSync(temporary,JSON.stringify(value)+'\n');fs.renameSync(temporary,file);};
const allStart=performance.now(),allCPU=process.cpuUsage();
write(path.join(out,'RUN_START.json'),{started_utc:new Date().toISOString(),source_hash:SOURCE_HASH,run_mode:smoke?'DEVELOPMENT_SMOKE':'CONFIRMATION',top_freeze_sha256:smoke?null:sha(fs.readFileSync(path.join(root,'protocol/STUDY_FREEZE.json'))),
 checker_sha256:sha(fs.readFileSync(path.join(root,'review/check.py'))),protocol_sha256:sha(fs.readFileSync(path.join(root,'protocol/MAIN_PROTOCOL.json'))),node:process.version,authorization:'Explicit --confirm after root custody checkpoint',
 common_engineering_and_human_cost:null,one_commissioning_brief_duration:null});
write(path.join(out,'protocol.json'),protocol);

// Materialize each WORLD configuration exactly once, before any arm sees it.
const genStart=performance.now(),genCPU=process.cpuUsage();
const main=(smoke?[370001]:MAIN_SEEDS).map((seed,i)=>({id:`stream-${String(i+1).padStart(2,'0')}`,role:smoke?'development-main':'main',config:smoke?developmentConfiguration(seed,{missions:9}):createConfirmationInputs(seed)}));
const diagnostic=(smoke?[470001]:DIAGNOSTIC_SEEDS).map((seed,i)=>{const config=developmentConfiguration(seed,{missions:4});
 config.tasks=[makeTask(seed,'ordinary',{prefix:'diagnostic'}),makeTask(seed+1,'ordinary',{prefix:'diagnostic'}),makeTask(seed+2,'tight',{prefix:'diagnostic'}),makeTask(seed+3,'repair',{prefix:'diagnostic'})];
 Object.assign(config.policy,{mode:'diagnostic',totalWork:5000000,discoveryWork:1500000,qualificationWork:100000,stageAt:[1,2,3],actor:'experiment-driver'});
 return {id:`diagnostic-${String(i+1).padStart(2,'0')}`,role:'diagnostic',config};});
const generationCPU=process.cpuUsage(genCPU),generation={wall_ms:performance.now()-genStart,node_cpu_ms:(generationCPU.user+generationCPU.system)/1000,
 known_baseline_work:[...main,...diagnostic].reduce((s,x)=>s+[...x.config.tasks,...Object.values(x.config.qualification).flatMap(q=>[...q.training,...q.validation])].reduce((a,t)=>a+(t.fixture_generation?.baseline_work??0),0),0),
 claim:'One common supplied-WORLD construction cost, reported separately from the conditional per-arm mission-work endpoint; not free in total experimental effort.'};
const exposed=[...scanDevelopment(path.join(root,'development')),...scanDevelopment(path.join(root,'review')),
 ...Object.values(JSON.parse(fs.readFileSync(path.join(here,'schema-examples.json')))).filter(x=>x&&typeof x==='object'&&x.task).map(x=>x.task)];
const registry=assertDisjoint([...main,...diagnostic],{development:exposed});
write(path.join(out,'INPUT_REGISTRY.json'),registry);write(path.join(out,'WORLD_GENERATION.json'),generation);
for(const entry of [...main,...diagnostic])write(path.join(out,'inputs',entry.id+'.json'),entry.config);

function compressedLog(file){const destination=fs.createWriteStream(file),gzip=zlib.createGzip({level:6});gzip.pipe(destination);return {
 async append(value){if(!gzip.write(JSON.stringify(value)+'\n'))await once(gzip,'drain');},async close(){gzip.end();await once(destination,'finish');}};}
const checker=createChecker({python,timeoutMs:2000}),trials=[];
async function runTrial(entry,arm,budget,{parentTreatment='inherited',category='main'}={}){
 const folder=path.join(out,category,entry.id,`${arm}-${parentTreatment}-${budget}`);fs.mkdirSync(folder,{recursive:true});
 const cfg=structuredClone(entry.config);Object.assign(cfg.policy,{mode:arm,totalWork:budget,parentTreatment,actor:'experiment-driver'});
 if(category==='main'){cfg.policy.discoveryWork=500000;cfg.policy.qualificationWork=50000;}
 const raw=compressedLog(path.join(folder,'raw.jsonl.gz')),packs=compressedLog(path.join(folder,'workbench-packs.jsonl.gz'));
 let guard=null;
 const storage={async save(snapshot){write(path.join(folder,'checkpoint.json'),snapshot);},async load(){return JSON.parse(fs.readFileSync(path.join(folder,'checkpoint.json')));},
  async saveGuard(value){guard=value;write(path.join(folder,'recovery-guard.json'),value);},async loadGuard(){return guard;}};
 const start=performance.now(),cpu=process.cpuUsage(),controller=createMissionStream({...cfg,check:checker.check,storage,
  onEvent:event=>fs.appendFileSync(path.join(folder,'events.jsonl'),JSON.stringify(event)+'\n'),
  onRecord:record=>raw.append(record),onPack:(pack,metadata)=>packs.append({metadata,pack})});
 let snapshot;try{snapshot=await controller.start({requestId:'one-authorized-experiment-start'});}finally{await raw.close();await packs.close();}
 const cpuTime=process.cpuUsage(cpu),costs={};for(const row of snapshot.ledger)costs[row.kind]=(costs[row.kind]??0)+row.work;
 const windows=Array.from({length:3},(_,i)=>{const offered=category==='main'?24:Math.ceil(cfg.tasks.length/3),rows=snapshot.missions.filter(m=>Math.min(2,Math.floor(m.index/offered))===i),work=snapshot.ledger.filter(e=>Math.min(2,Math.floor(e.mission_index/offered))===i).reduce((s,e)=>s+e.work,0);
  return {window:i+1,offered:category==='main'?24:null,attempted:rows.length,qualified:rows.filter(r=>r.qualified).length,work,qualified_per_100k_work:work?rows.filter(r=>r.qualified).length*100000/work:null};});
 const inheritedCalls={dispatch_rollouts:0,lookahead_repair_decisions:0};for(const row of snapshot.ledger){inheritedCalls.dispatch_rollouts+=row.counts?.['strategy:inherited-dispatch-rollout']??0;inheritedCalls.lookahead_repair_decisions+=row.counts?.['strategy:inherited-lookahead-decision']??0;}
 const record={category,stream:entry.id,arm,parent_treatment:parentTreatment,budget,source_hash:SOURCE_HASH,status:snapshot.status,reason:snapshot.reason,
  offered:cfg.tasks.length,attempted:snapshot.missions.length,valid:snapshot.missions.filter(r=>r.valid).length,qualified:snapshot.missions.filter(r=>r.qualified).length,
  work:snapshot.work,unused_budget:budget-snapshot.work,costs,windows,wall_ms:performance.now()-start,node_cpu_ms:(cpuTime.user+cpuTime.system)/1000,python_cpu_ms:null,
  storage_bytes:fs.statSync(path.join(folder,'checkpoint.json')).size,raw_compressed_bytes:fs.statSync(path.join(folder,'raw.jsonl.gz')).size,
  assets:snapshot.assets.map(a=>({stage:a.stage,digest:a.digest,parent_digest:a.parent_digest,active:a.active,gate:a.gate.decision,strategy:a.strategy})),
  discoveries:snapshot.discoveries.map(d=>({stage:d.stage,decision:d.gate?.decision??d.decision??'NO_COMPLETE_CANDIDATE',acquisition:d.acquisition,candidate_digest:d.search?.candidate?.digest??null,
   correctness:d.gate?.correctness??false,net_benefit:d.gate?.net_benefit??false,fair_allocation:d.qualification?.fair_allocation??null,break_even_missions:d.gate?.break_even_missions??null,
   complete_candidates:d.search?.trials?.filter(t=>t.complete).length??0,truncated_candidates:d.search?.trials?.filter(t=>!t.complete).length??0})),
  inherited_policy_calls:inheritedCalls,constructive_events:snapshot.events.filter(e=>['RECONSTRUCTION','REPLACEMENT'].includes(e.kind)),
  mission_results:snapshot.missions.map(m=>({id:m.task_id,scope:m.scope,valid:m.valid,qualified:m.qualified,makespan:m.result?.makespan??null,lower_bound:m.result?.lower_bound?.value??null,
   movement:m.result?.movement??null,asset_digest:m.asset_digest,schedule_sha256:m.result?sha(JSON.stringify(m.result.schedule)):null})),
  interventions:snapshot.interventions,mid_stream_manual_interventions:snapshot.interventions.filter(i=>!i.automatic).length,artifact_path:path.relative(out,folder)};
 write(path.join(folder,'summary.json'),record);trials.push(record);fs.appendFileSync(path.join(out,'trials.jsonl'),JSON.stringify(record)+'\n');
 console.log(JSON.stringify({category,stream:entry.id,arm,parentTreatment,budget,status:record.status,qualified:record.qualified,work:record.work,assets:record.assets.length}));return record;
}
try{
 for(const budget of smoke?[1000000]:[1000000,250000,2000000])for(const [streamIndex,entry]of main.entries()){
  // Rotated execution order is fixed by stream index, not any observed result.
  const arms=smoke?['portfolio','workflow','learner','flywheel']:protocol.primary.arms,order=[...arms.slice(streamIndex%arms.length),...arms.slice(0,streamIndex%arms.length)];
  for(const arm of order)await runTrial(entry,arm,budget);
 }
 for(const entry of diagnostic)for(const parentTreatment of ['inherited','removed','rebuild','equivalent'])await runTrial(entry,'diagnostic',5000000,{category:'diagnostic',parentTreatment});
}finally{await checker.close();}

// Established exact/feasibility specialist: one persistent Python process;
// startup, model, solve, check and end-to-end costs remain separate.
async function nativeReference(){
 const start=performance.now(),worker=spawn(python,[path.join(here,'specialist.py')],{stdio:['pipe','pipe','pipe']}),pending=[];let stderr='';worker.stderr.on('data',x=>stderr+=x.toString());
 const lines=readline.createInterface({input:worker.stdout});lines.on('line',line=>{const p=pending.shift();if(!p)return;clearTimeout(p.timer);try{p.resolve(JSON.parse(line));}catch(e){p.reject(e);}});
 let closed=false;worker.on('exit',code=>{closed=true;for(const p of pending.splice(0)){clearTimeout(p.timer);p.reject(Error(`NATIVE_EXIT_${code}: ${stderr}`));}});
 const request=value=>new Promise((resolve,reject)=>{if(closed)return reject(Error('NATIVE_UNAVAILABLE'));const p={resolve,reject,timer:setTimeout(()=>{const i=pending.indexOf(p);if(i>=0)pending.splice(i,1);worker.kill('SIGKILL');reject(Error('NATIVE_RESPONSE_TIMEOUT'));},10000)};pending.push(p);worker.stdin.write(JSON.stringify(value)+'\n');});
 const metadata=await request({op:'metadata'}),startupMs=performance.now()-start,oracle=createChecker({python,timeoutMs:2000}),rows=[];
 try{for(const entry of main)for(const task of entry.config.tasks.slice(0,3)){
  const preparationStart=performance.now(),base=await runMission(task,{check:oracle.check,budget:100000}),preparationMs=performance.now()-preparationStart;
  for(const mode of ['deadline','makespan']){const begin=performance.now();let response=null,checked=null,error=null,checkMs=0;
   try{response=await request({task,time_limit:2,mode,upper_bound:mode==='makespan'&&base.valid?base.result.makespan:null});
    if(!response.ok)throw Error(response.error);const result=response.result;
    if(result.schedule){const bound=lowerBound(inspectTask(task));const candidate={schema:'release-plan-result/v1',task_id:task.id,schedule:result.schedule,makespan:result.makespan,movement:result.movement,
     lower_bound:bound,optimal_by_lower_bound:result.makespan===bound.value,dispatch_order:result.schedule.filter(j=>!(j.id in(task.locked??{}))).map(j=>j.id),lookahead_steps:0,proof:[],authority:[]};
     const checkStart=performance.now();checked=await oracle.check(task,candidate);checkMs=performance.now()-checkStart;result.checked_schedule=candidate;}
   }catch(e){error=e.message;}
   const row={stream:entry.id,task_id:task.id,scope:task.scope,mode,deadline:task.deadline,portfolio_preparation_work:base.work,portfolio_preparation_ms:preparationMs,
    portfolio_valid:base.valid,portfolio_qualified:base.qualified,portfolio_makespan:base.result?.makespan??null,native:response?.result??null,checker:checked,error,
    valid:checked?.valid??false,qualified:checked?.qualified??false,checker_ms:checkMs,native_and_check_ms:performance.now()-begin,
    attributable_end_to_end_ms:performance.now()-begin+(mode==='makespan'?preparationMs:0),
    practical_workflow_valid:Boolean(checked?.valid||base.valid),practical_workflow_qualified:Boolean(checked?.qualified||base.qualified),
    practical_workflow_end_to_end_ms:performance.now()-begin+preparationMs,
    fallback_available:base.valid,solver_only_result_is_not_the_fallback: true,internal_work_units:null};rows.push(row);
   fs.appendFileSync(path.join(out,'native-reference.jsonl'),JSON.stringify(row)+'\n');
  }
 }}finally{worker.stdin.end();await oracle.close();if(!closed)await once(worker,'exit');}
 const result={startup_ms:startupMs,metadata,wall_ms:performance.now()-start,rows,task_count:main.length*3,attempts:main.length*6,
  note:'Fixed subset. Deadline objective0 does not prove makespan optimality. Primary JS resource units are not equated with opaque native computation; no hidden startup or upper-bound construction is labeled free.'};write(path.join(out,'NATIVE_REFERENCE.json'),result);return result;
}
const native=await nativeReference();
const analysis=spawnSync(python,[path.join(here,'analyze.py'),out],{encoding:'utf8'});if(analysis.status!==0)throw Error('ANALYSIS_FAILED: '+analysis.stderr);
const totalCPU=process.cpuUsage(allCPU);write(path.join(out,'RUN_COMPLETE.json'),{completed_utc:new Date().toISOString(),source_hash:SOURCE_HASH,
 wall_ms:performance.now()-allStart,node_cpu_ms:(totalCPU.user+totalCPU.system)/1000,python_cpu_ms:null,trials:trials.length,run_mode:smoke?'DEVELOPMENT_SMOKE':'CONFIRMATION',main_unique_tasks:main.reduce((s,x)=>s+x.config.tasks.length,0),
 diagnostic_unique_fresh_successor_tasks:diagnostic.length*3,diagnostic_founder_tasks:diagnostic.length,native_comparisons:native.rows.length,one_explicit_launch:true,
 manually_triggered_phases:0,common_world_generation:generation,monetary_cost:null,authoring_cost:null});
console.log(JSON.stringify({complete:true,out,trials:trials.length,summary:path.join(out,'SUMMARY.json')}));
