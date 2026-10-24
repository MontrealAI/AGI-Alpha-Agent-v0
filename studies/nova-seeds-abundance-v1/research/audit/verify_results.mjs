// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {createInterface} from 'node:readline';
import {createHash} from 'node:crypto';
import {createGunzip} from 'node:zlib';
import {evaluateSchedule} from '../src/independent_evaluator.mjs';
import {verifySignedPayload} from '../vendor/jobs/packages/successor-core/src/signatures.mjs';
import {verifyLedger} from '../vendor/fleet/fleet/successor/outcomes.mjs';

const directory=path.resolve(process.argv[2]||'research/results/holdout-01');
const inputFile=name=>{
  const plain=path.join(directory,name),compressed=plain+'.gz';
  if(fs.existsSync(plain))return plain;
  if(fs.existsSync(compressed))return compressed;
  throw Error(`Missing audit input: ${name} or ${name}.gz`);
};
const inputFiles={missions:inputFile('missions.jsonl'),ledgers:inputFile('ledgers.jsonl')};
const lines=file=>createInterface({input:file.endsWith('.gz')?fs.createReadStream(file).pipe(createGunzip()):fs.createReadStream(file),crlfDelay:Infinity});
const methods=['idea','greedy','disclosed','verified','clone','expert','adaptive-expert'];
const signedMethods=['verified','clone','expert','adaptive-expert','greedy'];
const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const report={schema:'nova-independent-post-run-audit/v1',directory,inputFiles,scope:'Read-only replay and evidence consistency; no physical truth or external organizational independence is established.',rows:0,missions:0,signedReceipts:0,ledgers:0,errors:[],errorCount:0,totals:{}};
const check=(condition,code,context)=>{if(!condition){report.errorCount++;if(report.errors.length<100)report.errors.push({code,context});}};
const priorByIdentity=new Map(),seenMissions=new Set(),seenKeys=new Set(),bindings=new Map();
let group=[];
async function auditGroup(rows){
  if(!rows.length)return;
  report.missions++;
  const first=rows[0],identity=`${first.scenario}:${first.seed}:${first.epoch}`,mission=first.world?.mission;
  check(rows.length===7&&new Set(rows.map(r=>r.method)).size===7&&methods.every(m=>rows.some(r=>r.method===m)),'method-set',identity);
  if(!mission){check(false,'missing-mission',identity);return;}
  check(!seenMissions.has(mission.id),'reused-mission-id',identity);seenMissions.add(mission.id);
  check(!['scenario','seed','epoch','bias','failedSlots','noise','truth'].some(k=>Object.hasOwn(mission,k)),'planner-future-metadata',identity);
  const historyKey=`${first.scenario}:${first.seed}`,expectedPrior=priorByIdentity.get(historyKey)??null;
  check(same(mission.pastQc,expectedPrior),'prior-qc-timing',identity);
  const keys=[];
  for(const row of rows){
    check(row.status==='complete','incomplete-method',`${identity}:${row.method}`);
    if(row.status!=='complete')continue;
    check(same(row.world,first.world),'unequal-world-inputs',`${identity}:${row.method}`);
    check(same(row.pastQc,expectedPrior)&&same(row.world.mission.pastQc,expectedPrior),'unequal-prior-inputs',`${identity}:${row.method}`);
    const replay=evaluateSchedule(row.world,row.result.plan,{ideaOnly:row.method==='idea'});
    check(replay.valid&&same(replay,row.outcome),'outcome-replay',`${identity}:${row.method}`);
    const key=`${row.scenario}:${row.method}`;
    const total=report.totals[key]??={rows:0,utility:0,completedJobs:0,attemptedJobs:0,failures:0,calibrations:0,diagnosticAcquisitions:0};
    total.rows++;for(const field of ['utility','completedJobs','attemptedJobs','failures','calibrations'])total[field]+=row.outcome[field];total.diagnosticAcquisitions+=row.diagnosticAcquisitions;
    check(row.diagnosticAcquisitions===4&&row.simulated.diagnosticAcquisitions===4,'qc-cost-count',`${identity}:${row.method}`);
    if(!signedMethods.includes(row.method)){check(row.receipt===null,'unexpected-receipt',`${identity}:${row.method}`);continue;}
    report.signedReceipts++;
    const receipt=row.receipt,signed=receipt?.signed;
    if(!signed){check(false,'missing-receipt',`${identity}:${row.method}`);continue;}
    try{
      await verifySignedPayload(signed,{trustStore:receipt.publicTrust,purpose:'nova-seeds-execution-evidence/v1',role:'recorder',context:{institutionId:'nova-seeds-research',missionId:mission.id,environment:'local-synthetic-allocation',mode:'fixture'},now:Date.parse(signed.issuedAt)});
    }catch(error){check(false,'signature-verification',`${identity}:${row.method}:${error.message}`);}
    check(signed.payload.missionDigest===digest(mission)&&signed.payload.outcomeDigest===digest(row.outcome)&&same(signed.payload.plan,row.result.plan)&&signed.payload.method===row.method,'receipt-binding',`${identity}:${row.method}`);
    check(signed.payload.physicalTruthEstablished===false&&signed.payload.authority==='fixture-only','receipt-trust-boundary',`${identity}:${row.method}`);
    const expectedType=row.result.completionHash?'native-finite-model-completion':'finite-schedule-and-replay';
    const expectedArtifact=row.result.completionHash||digest({mission,plan:row.result.plan,objective:row.result.objective});
    check(signed.payload.artifactType===expectedType&&signed.payload.artifactHash===expectedArtifact,'artifact-binding',`${identity}:${row.method}`);
    const publicKey=receipt.publicTrust.keys[0].publicKey;
    check(!seenKeys.has(publicKey),'reused-signing-key',`${identity}:${row.method}`);seenKeys.add(publicKey);keys.push(publicKey);
    bindings.set(`${mission.id}:${row.method}`,{signedDigest:digest(signed),head:receipt.ledgerHead,missionDigest:digest(mission),attempt:digest({mission:mission.id,method:row.method})});
  }
  check(keys.length===5&&new Set(keys).size===5,'independent-keys',identity);
  const byMethod=Object.fromEntries(rows.map(r=>[r.method,r]));
  if(byMethod.verified?.status==='complete'&&byMethod.clone?.status==='complete')check(same(byMethod.verified.result.plan,byMethod.clone.result.plan)&&same(byMethod.verified.outcome,byMethod.clone.outcome),'complete-copy-equivalence',identity);
  if(byMethod.verified?.status==='complete'&&byMethod.expert?.status==='complete')check(byMethod.verified.result.objective===byMethod.expert.result.objective,'independent-optimum',identity);
  priorByIdentity.set(historyKey,{sourceEpoch:first.epoch,relativeBias:first.world.bias.map(v=>v-first.world.bias[0]),diagnosticAcquisitions:4,scope:'Exact synthetic auxiliary reference channel revealed after all current policies finish.'});
}
for await(const line of lines(inputFiles.missions)){
  if(!line.trim())continue;const row=JSON.parse(line);report.rows++;
  if(group.length&&`${group[0].scenario}:${group[0].seed}:${group[0].epoch}`!==`${row.scenario}:${row.seed}:${row.epoch}`){await auditGroup(group);group=[];}
  group.push(row);
}
await auditGroup(group);
for await(const line of lines(inputFiles.ledgers)){
  if(!line.trim())continue;const entry=JSON.parse(line);
  check(Object.keys(entry.policyRecords||{}).length===5,'ledger-policy-count',entry.missionId);
  for(const [method,records] of Object.entries(entry.policyRecords||{})){
    report.ledgers++;try{verifyLedger(records);}catch(error){check(false,'ledger-chain',`${entry.missionId}:${method}:${error.message}`);}
    const binding=bindings.get(`${entry.missionId}:${method}`);
    check(Boolean(binding)&&records.length===2&&records.every(r=>r.event.evidenceSha256===binding.signedDigest)&&records.at(-1).sha256===binding.head,'ledger-receipt-binding',`${entry.missionId}:${method}`);
    if(binding&&records.length===2){
      const [attempt,cost]=records.map(r=>r.event);
      check(attempt.type==='attempt'&&cost.type==='cost'&&attempt.attempt===binding.attempt&&cost.attempt===binding.attempt&&attempt.data.method===method&&attempt.data.projectSha256===binding.missionDigest&&same(attempt.data.inputHashes,[binding.missionDigest])&&same(attempt.data.outputHashes,[binding.signedDigest]),'ledger-content-binding',`${entry.missionId}:${method}`);
      check(cost.data.amountMicros===null&&cost.data.basis==='unknown','unknown-cost-preservation',`${entry.missionId}:${method}`);
    }
    bindings.delete(`${entry.missionId}:${method}`);
  }
}
check(bindings.size===0,'unmatched-receipt-ledgers',bindings.size);
const metrics=JSON.parse(fs.readFileSync(path.join(directory,'metrics.json'),'utf8'));
check(report.rows===metrics.seeds.length*metrics.epochs*metrics.scenarios.length*7,'expected-row-count',report.rows);
check(report.missions===metrics.seeds.length*metrics.epochs*metrics.scenarios.length,'expected-mission-count',report.missions);
check(report.signedReceipts===report.missions*5&&report.ledgers===report.missions*5,'expected-evidence-count',report.signedReceipts);
report.finishedAt=new Date().toISOString();report.passed=report.errorCount===0;
process.stdout.write(JSON.stringify(report,null,2)+'\n');
if(!report.passed)process.exitCode=1;
