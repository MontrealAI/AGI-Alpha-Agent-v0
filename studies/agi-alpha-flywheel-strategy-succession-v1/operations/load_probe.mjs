// SPDX-License-Identifier: Apache-2.0
// Fixed finite load probe; no discovery and no protected confirmation inputs.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {runMission} from '../companion/adapter.mjs';
import {makeTask,SCOPES} from '../companion/scenarios.mjs';
import {createChecker} from '../companion/checker-client.mjs';
import {SOURCE_HASH,SOURCE_STATUS} from '../companion/binding.mjs';
import {verifySource} from '../companion/verify-source.mjs';

const args=process.argv.slice(2);
const value=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const out=path.resolve(value('--out','load-probe'));
if(fs.existsSync(out))throw Error('OUTPUT_MUST_BE_NEW');
fs.mkdirSync(out,{recursive:true});
fs.mkdirSync(path.join(out,'packs'));
const python=value('--python','python3');
verifySource({requireFrozen:true});
const studyRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const frozen=spawnSync(python,[path.join(studyRoot,'scripts/freeze_study.py')],{encoding:'utf8'});
if(frozen.status!==0)throw Error('TOP_LEVEL_FREEZE_REFUSED: '+frozen.stdout+frozen.stderr);
const protocol={schema:'release-load-probe/v1',source_hash:SOURCE_HASH,
 source_status:SOURCE_STATUS,batch_sizes:[1,4,16,64],concurrency_ceiling:4,
 seed_base:670000,task_scope_cycle:SCOPES,per_output_work_limit:100000,
 checker_timeout_ms:2000,batch_wall_limit_ms:120000,
 success:'All delivered valid schedules pass the separately implemented checker; report deadline misses without exclusion.',
 timing:'Batch wall includes client creation, task generation, plan/check, evidence write and checker shutdown. Per-task latency is enqueue-to-durable-record, including queue delay.',
 limits:'A finite local source experiment. No daemon, production service, external traffic, demand or general scalability inference.'};
fs.writeFileSync(path.join(out,'protocol.json'),JSON.stringify(protocol,null,2)+'\n');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const batches=[];let globalOrdinal=0;
for(const size of protocol.batch_sizes){
 const begin=performance.now(),cpuStart=process.cpuUsage();
 const clients=Array.from({length:Math.min(size,protocol.concurrency_ceiling)},()=>createChecker({python,timeoutMs:protocol.checker_timeout_ms}));
 let next=0,inflight=0,maxInflight=0,fixtureWork=0;
 const generationStart=performance.now();
 const tasks=Array.from({length:size},(_,i)=>makeTask(protocol.seed_base+globalOrdinal+i,SCOPES[(globalOrdinal+i)%SCOPES.length],{prefix:'load-probe'}));
 for(const t of tasks)fixtureWork+=t.fixture_generation?.baseline_work??0;
 const generationMs=performance.now()-generationStart,enqueue=performance.now();
 globalOrdinal+=size;
 const rows=[];const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),protocol.batch_wall_limit_ms);
 try{
  await Promise.all(clients.map(async client=>{
   while(next<tasks.length&&!controller.signal.aborted){
    const i=next++,task=tasks[i],start=performance.now();inflight++;maxInflight=Math.max(maxInflight,inflight);
    let row;
    try{
     row=await runMission(task,{strategy:'portfolio',budget:protocol.per_output_work_limit,check:client.check,signal:controller.signal});
    }catch(error){row={task_id:task.id,valid:false,qualified:false,error:String(error.message),work:null,result:null,checker:null,pack:null};}
    inflight--;
    const packText=JSON.stringify(row.pack);
    fs.writeFileSync(path.join(out,'packs',`batch-${size}-${String(i).padStart(3,'0')}.json`),packText);
    const record={index:i,task,task_id:task.id,valid:row.valid,qualified:row.qualified,
     error:row.error,work:row.work,counts:row.counts??null,result:row.result,checker:row.checker,
     solve_and_check_ms:performance.now()-start,enqueue_to_completion_ms:performance.now()-enqueue,
     source_hash:SOURCE_HASH,pack_sha256:sha(packText),pack_bytes:Buffer.byteLength(packText)};
    const raw=JSON.stringify(record)+'\n';fs.appendFileSync(path.join(out,`batch-${size}-raw.jsonl`),raw);
    record.enqueue_to_durable_record_ms=performance.now()-enqueue;
    record.record_bytes=Buffer.byteLength(raw);rows.push(record);
   }
  }));
 }finally{
  clearTimeout(timer);await Promise.all(clients.map(c=>c.close()));
 }
 fs.writeFileSync(path.join(out,`batch-${size}-latencies.json`),JSON.stringify(rows.map(r=>({index:r.index,task_id:r.task_id,enqueue_to_durable_record_ms:r.enqueue_to_durable_record_ms,solve_and_check_ms:r.solve_and_check_ms})),null,2)+'\n');
 const elapsed=performance.now()-begin,cpu=process.cpuUsage(cpuStart),lat=rows.map(r=>r.enqueue_to_durable_record_ms).sort((a,b)=>a-b);
 const quantile=p=>lat.length?lat[Math.min(lat.length-1,Math.floor(p*(lat.length-1)))]:null;
 const batch={offered:size,attempted:rows.length,valid:rows.filter(r=>r.valid).length,qualified:rows.filter(r=>r.qualified).length,
  max_in_flight:maxInflight,elapsed_ms:elapsed,throughput_per_second:rows.length/(elapsed/1000),
  latency_p50_ms:quantile(.5),latency_p95_ms:quantile(.95),latency_max_ms:lat.at(-1)??null,
  node_cpu_ms:(cpu.user+cpu.system)/1000,python_cpu_ms:null,
  measured_policy_work:rows.reduce((s,r)=>s+(r.work??0),0),unknown_work_rows:rows.filter(r=>r.work===null).length,
  common_fixture_generation_ms:generationMs,known_fixture_baseline_work:fixtureWork,
  stored_result_bytes:rows.reduce((s,r)=>s+r.record_bytes,0),stored_pack_bytes:rows.reduce((s,r)=>s+r.pack_bytes,0),
  deadline_expired:controller.signal.aborted,mid_batch_manual_interventions:0,
  scope_counts:Object.fromEntries(SCOPES.map(s=>[s,tasks.filter(t=>t.scope===s).length])),
  note:'One observation at each load; task mixtures differ slightly. No throughput confidence interval, service-level claim or scale extrapolation.'};
 batches.push(batch);fs.writeFileSync(path.join(out,`batch-${size}-summary.json`),JSON.stringify(batch,null,2)+'\n');
 console.log(JSON.stringify(batch));
}
const report={schema:'release-load-result/v1',source_hash:SOURCE_HASH,protocol,batches,
 offered:batches.reduce((s,b)=>s+b.offered,0),valid:batches.reduce((s,b)=>s+b.valid,0),
 qualified:batches.reduce((s,b)=>s+b.qualified,0),interventions:[{actor:'experiment-driver',action:'One explicit bounded probe start',human_minutes:null}],
 conclusion:'Finite increasing-load measurements only; no commercial or sustained operational-growth claim.'};
fs.writeFileSync(path.join(out,'LOAD_RESULTS.json'),JSON.stringify(report,null,2)+'\n');
