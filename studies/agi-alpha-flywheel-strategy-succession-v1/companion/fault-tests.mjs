// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
import {createMissionStream} from './stream.mjs';import {createChecker} from './checker-client.mjs';import {digest} from './vendor/docs/assets/successor/engine.mjs';import {verifySource} from './verify-source.mjs';
import {SOURCE_HASH,SOURCE_STATUS} from './binding.mjs';import {runMission} from './adapter.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),out=path.resolve(process.argv[2]??path.join(here,'../development/operating-faults'));
fs.mkdirSync(out,{recursive:true});verifySource();
const sample=JSON.parse(fs.readFileSync(path.join(here,'schema-examples.json'),'utf8'));
const task=i=>({...structuredClone(sample.plan.task),id:`fault-task-${i}`,scope:'ordinary'});
const config={tasks:[task(1),task(2),task(3)],qualification:{},policy:{mode:'portfolio',totalWork:1000000,perMissionWork:100000,discoveryWork:500000,wallTimeMs:120000,
 stageAt:[1,2,3],actor:'experiment-driver',authority:{scope:'LOCAL_SYNTHETIC_RELEASE_PLANNING',expires:'2099-01-01T00:00:00Z'}}};
const configPath=path.join(out,'configuration.json');fs.writeFileSync(configPath,JSON.stringify(config,null,2)+'\n');
const results=[];
async function test(name,fn){const start=performance.now();try{const evidence=await fn();results.push({name,passed:true,wall_ms:performance.now()-start,evidence});}catch(error){results.push({name,passed:false,error:error.message,stack:error.stack});}}
const cli=(sub,args=[])=>spawnSync(process.execPath,[path.join(here,'run.mjs'),'--config',configPath,'--out',path.join(out,sub),...args],{encoding:'utf8',timeout:15000});
await test('separate-process lost acknowledgement after accepted effect',async()=>{
 const first=cli('lost-ack',['--crash-at','accepted']);assert.equal(first.status,24);
 const saved=JSON.parse(fs.readFileSync(path.join(out,'lost-ack/checkpoint.json')));assert.equal(saved.cursor,1);
 const second=cli('lost-ack',['--resume']);assert.equal(second.status,0,second.stderr);
 const done=JSON.parse(fs.readFileSync(path.join(out,'lost-ack/checkpoint.json')));assert.equal(done.cursor,3);assert.equal(new Set(done.missions.map(m=>m.task_id)).size,3);
 const raw=fs.readFileSync(path.join(out,'lost-ack/raw-results.jsonl'),'utf8').trim().split('\n').map(JSON.parse);assert.equal(raw.filter(r=>r.phase==='mission').length,3);
 const third=cli('lost-ack',['--resume']);assert.equal(third.status,0,third.stderr);
 const rawAfter=fs.readFileSync(path.join(out,'lost-ack/raw-results.jsonl'),'utf8').trim().split('\n');assert.equal(rawAfter.length,raw.length);
 return {first_exit:first.status,restart_exit:second.status,accepted_missions:3,mission_executions:3,duplicate_request_executions:0,restore_cost_is_charged:true};
});
await test('separate-process interrupted intent charges unknown work ceiling',async()=>{
 const first=cli('intent',['--crash-at','intent']);assert.equal(first.status,23);
 const pending=JSON.parse(fs.readFileSync(path.join(out,'intent/checkpoint.json'))).pending;assert(pending.reserved_work>0);
 const second=cli('intent',['--resume']);assert.equal(second.status,0,second.stderr);
 const saved=JSON.parse(fs.readFileSync(path.join(out,'intent/checkpoint.json'))),entry=saved.ledger.find(e=>e.kind==='uncertain-interrupted-execution');assert.equal(entry.work,pending.reserved_work);
 return {reserved_work:pending.reserved_work,charged_uncertain_work:entry.work,exactly_once_CPU_execution_claimed:false,accepted_missions:saved.missions.length};
});
const checker=createChecker();let saved;
await test('STOP then explicit resume keeps accepted output',async()=>{
 let stream;stream=createMissionStream({...config,check:checker.check,onEvent:event=>{if(event.kind==='RESULT')stream.stop();}});saved=await stream.start();assert.equal(saved.status,'STOPPED');assert.equal(saved.cursor,1);
 const recovered=createMissionStream({...config,check:checker.check});await recovered.restore(saved);const done=await recovered.start({resume:true});assert.equal(done.missions.length,3);assert.equal(done.missions[0].receipt_digest,saved.missions[0].receipt_digest);return {first_receipt_preserved:true,final_missions:3};
});
await test('changed dependency refuses snapshot binding',async()=>{
 const changed=structuredClone(config);changed.tasks[0].jobs[2].deps=['J1'];const stream=createMissionStream({...changed,check:checker.check});await assert.rejects(()=>stream.restore(saved),/SOURCE_OR_CONFIGURATION_CHANGED/);return {refused:true};
});
await test('well-hashed invalid receipt independently refused',async()=>{
 const tampered=structuredClone(saved),m=tampered.missions[0];m.result.schedule[0].end++;
 m.receipt_digest=await digest('release-stream',JSON.stringify({task_id:m.task_id,result:m.result,checker:m.checker,source_hash:tampered.source_hash}));
 delete tampered.integrity;tampered.integrity=await digest('release-stream',JSON.stringify(tampered));
 const stream=createMissionStream({...config,check:checker.check});await assert.rejects(()=>stream.restore(tampered),/INVALID_RECEIPT_CURRENT_CHECK/);return {outer_and_receipt_hashes_recomputed:true,independent_refusal:true};
});
await test('finite authority expiry and malformed expiry refuse',async()=>{
 const outcomes=[];for(const expires of ['2000-01-01T00:00:00Z','not-a-date']){const c=structuredClone(config);c.policy.authority.expires=expires;const s=await createMissionStream({...c,check:checker.check}).start();assert.equal(s.reason,'EXPIRED_AUTHORITY');assert.equal(s.missions.length,0);outcomes.push(s.reason);}return {outcomes};
});
await test('exhausted declared budget stops before new mission',async()=>{
 const c=structuredClone(config);c.policy.totalWork=20000;const s=await createMissionStream({...c,check:checker.check}).start();assert.equal(s.reason,'BUDGET_EXHAUSTED');assert(s.work<=c.policy.totalWork);return {work:s.work,budget:c.policy.totalWork,missions:s.missions.length};
});
await test('finite wall deadline stops at phase boundary',async()=>{
 const c=structuredClone(config);c.policy.wallTimeMs=1;const s=await createMissionStream({...c,check:checker.check}).start();assert.equal(s.reason,'WALL_DEADLINE');return {reason:s.reason};
});
await test('same-cursor older paid checkpoint cannot restore',async()=>{
 const guard={source_hash:saved.source_hash,high_water:saved.cursor,work:saved.work+100,sequence:saved.sequence+1,rejected:[],completed_stages:saved.completed_stages};
 const storage={loadGuard:async()=>guard,saveGuard:async()=>{},save:async()=>{}};const stream=createMissionStream({...config,storage,check:checker.check});await assert.rejects(()=>stream.restore(saved),/STALE_OR_REJECTED_SNAPSHOT/);return {cursor_unchanged:true,paid_high_water_preserved:true};
});
await test('new code source refuses old acquired history',async()=>{
 const stream=createMissionStream({...config,check:checker.check,sourceHash:'f'.repeat(64)});await assert.rejects(()=>stream.restore(saved),/SOURCE_OR_CONFIGURATION_CHANGED/);return {refused:true};
});
await test('rollback restores incumbent and rejected asset cannot reenter through retry or stale restore',async()=>{
 const c=structuredClone(config);c.tasks=[task(11),task(12)];Object.assign(c.policy,{mode:'diagnostic',totalWork:5000000,discoveryWork:1500000,stageAt:[1,99,99]});
 c.qualification={dispatch:{training:[task(101),task(102)],validation:[task(201),task(202)]}};
 let checkpoint=null,guard=null;const storage={async save(value){checkpoint=value;},async load(){return checkpoint;},async saveGuard(value){guard=value;},async loadGuard(){return guard;}};
 const stream=createMissionStream({...c,storage,check:checker.check});const before=await stream.start();assert.equal(before.assets.length,1);assert(before.assets[0].active);
 const after=await stream.rollback(before.assets[0].digest,'FIXTURE_ROLLBACK');assert(!after.assets[0].active);assert(after.rejected.some(x=>x.digest===before.assets[0].digest));
 const retry=await stream.start({resume:true});assert(!retry.assets[0].active);
 const restored=createMissionStream({...c,storage,check:checker.check});await assert.rejects(()=>restored.restore(before),/STALE_OR_REJECTED_SNAPSHOT/);
 const tampered=structuredClone(after);tampered.assets[0].active=true;delete tampered.integrity;tampered.integrity=await digest('release-stream',JSON.stringify(tampered));
 await assert.rejects(()=>restored.restore(tampered),/STALE_OR_REJECTED_SNAPSHOT|INVALID_RETAINED_ASSET/);
 return {real_retained_digest:before.assets[0].digest,incumbent:'portfolio',retry_kept_rejection:true,older_same_cursor_restore_refused:true,rehash_cannot_resurrect:true,
  rollback_intervention_recorded:after.interventions.some(x=>x.kind==='ROLLBACK')};
});
await test('unresponsive separate checker times out and costs its reserved ceiling',async()=>{
 const fixture=path.join(out,'unresponsive-checker.py');fs.writeFileSync(fixture,'import sys,time\nfor line in sys.stdin:\n time.sleep(10)\n');
 const slow=createChecker({script:fixture,timeoutMs:100});const result=await runMission(task(901),{check:slow.check,budget:100000});await slow.close();
 assert.equal(result.error,'CHECKER_TIMEOUT');assert.equal(result.valid,false);assert(result.counts['checker:reference']>0);
 return {error:result.error,charged_checker_ceiling:result.counts['checker:reference'],delivered:false,wall_ms:result.wall_ms};
});
await checker.close();
fs.writeFileSync(path.join(out,'fault-results.json'),JSON.stringify({scope:'Development operating fault tests; no confirmatory inputs',source_hash:SOURCE_HASH,source_status:SOURCE_STATUS,tests:results,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length},null,2)+'\n');
console.log(JSON.stringify({passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length,results:results.map(r=>({name:r.name,passed:r.passed,error:r.error}))}));
if(results.some(r=>!r.passed))process.exitCode=1;
