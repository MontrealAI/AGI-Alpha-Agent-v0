// SPDX-License-Identifier: Apache-2.0
// Reproduce bounded software construction and load measurements; no financial/backend execution.
import { mkdir, writeFile, readFile, open } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import os from 'node:os';
import { createCompiler, executeProgram, inspectProgram, canonical } from './compiler.mjs';
import { digitalFault, mixtureAssay, acquireSynthetic } from './domains.mjs';
import { networkProblem, acquireNetwork } from './heldout.mjs';
import { conventionalStatic, conventionalAdaptive, verifyProgramReference } from './reference.mjs';
import { createDiscoverabilityWorkbench, discoverabilityMission } from './workbench-adapter.mjs';
import { executeObservations } from './execution.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const output=process.argv[2];
if(!output||process.argv.length!==3)throw Error('Usage: node examples/successor-discoverability/run.mjs NEW_OUTPUT_DIRECTORY');
await mkdir(resolve(output),{recursive:false});
const dir=resolve(output);
const closure=JSON.parse(await readFile(resolve(root,'docs/research/discoverability/source-closure.json'),'utf8'));
const hash=value=>createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const executedFiles={};
for(const [path,expected] of Object.entries(closure.files)) {
  const actual=hash(await readFile(resolve(root,path),'utf8'));
  if(actual!==expected)throw Error('SOURCE_CLOSURE_CHANGED: '+path);
  executedFiles[path]=actual;
}
for(const path of ['examples/successor-discoverability/run.mjs','examples/successor-discoverability/reference.mjs'])executedFiles[path]=hash(await readFile(resolve(root,path),'utf8'));
const executionSourceFiles=Object.fromEntries(Object.entries(executedFiles).sort(([a],[b])=>a.localeCompare(b,'en')));
const sourceHash=hash(executionSourceFiles);
await writeFile(resolve(dir,'execution-source.json'),JSON.stringify({schema:'discoverability-execution-source/v1',sourceHash,browserClosureHash:closure.sourceHash,files:executionSourceFiles},null,2)+'\n',{flag:'wx'});
let previous='0'.repeat(64),sequence=0;
const history=await open(resolve(dir,'history.jsonl'),'wx');
const append=async (kind,data)=>{
  const body={sequence:sequence++,kind,previous,runId:'discoverability-20261022-v1',data};
  const row={...body,sha256:hash(body)};previous=row.sha256;
  await history.write(JSON.stringify(row)+'\n');await history.sync();return row;
};
const save=async(name,value)=>writeFile(resolve(dir,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const startedAt=new Date().toISOString(),timer=performance.now();
await append('start',{startedAt,sourceHash,sourceFiles:executionSourceFiles});
function task(index){
  const family=['digital','mixture','network'][index%3],noise=1+Math.floor(index/3)%2;
  let p=family==='digital'?digitalFault({noise,goal:Math.floor(index/6)%2?'health':'repair'}):
    family==='mixture'?mixtureAssay({noise,goal:Math.floor(index/6)%2?'quantify':'disposition'}):
    networkProblem({requirement:Math.floor(index/6)%2?'repair':'route'});
  p=JSON.parse(JSON.stringify(p));p.id='scale-'+family+'-'+index;
  if(family==='network')p.channels.forEach(c=>c.noise=noise);
  return {family,problem:p,index};
}
const modes=[
  {id:'workbench-inherited',workbench:true,strategy:'cached'},
  {id:'workbench-non-inheriting',workbench:true,strategy:'fresh'},
  {id:'centralized-direct',workbench:false,strategy:'fresh'},
];
const results=[],samples=[];
function percentile(values,p){const a=[...values].sort((a,b)=>a-b);return a[Math.max(0,Math.ceil(a.length*p)-1)]??null;}
async function measure(mode,count,concurrency){
  const compiler=createCompiler({strategy:mode.strategy}),runtime=createDiscoverabilityWorkbench({compiler});
  const rows=Array(count);let next=0;const begin=performance.now();
  async function worker(){
    for(;;){
      const slot=next++;if(slot>=count)return;
      const {family,problem}=task(slot);const submitted=performance.now(),compileStart=performance.now();
      let pack=null,construction;
      if(mode.workbench){
        pack=await runtime.run(discoverabilityMission(problem),{sourceHash});
        construction=pack.result.evidence.construction;
      }else construction=await compiler.compile(problem);
      const compilationMs=performance.now()-compileStart;
      const validationStart=performance.now();
      let reference=null,quality=[],acquisitionUnits=0,validationAcquisitionUnits=0,delivery=null,observed=null;
      if(construction.status==='COMPILED'){
        reference=verifyProgramReference(problem,construction.program);
        for(const [j,world] of problem.worlds.entries()){
          const a=family==='network'?acquireNetwork(problem,construction.program,world.id):
            acquireSynthetic(problem,construction.program,world.id,{nuisanceScale:11+slot,errorSign:j%3-1});
          const actual=executeProgram(problem,construction.program,a.observations);
          quality.push({world:world.id,expected:world.goal,actual,observations:a.observations,
            passed:actual.status==='DECIDED'&&actual.decision===world.goal});
          validationAcquisitionUnits+=construction.program.totalCost;
          if(j===slot%problem.worlds.length)observed=a;
        }
        acquisitionUnits=construction.program.totalCost;
        // The selected-world acquisition is part of the validation loop; do not count it twice.
        validationAcquisitionUnits-=acquisitionUnits;
        if(pack)delivery=await executeObservations(pack,observed.observations);
      }
      const elapsedMs=performance.now()-submitted;
      rows[slot]={slot,family,problem,status:construction.status,construction,
        compilationMs,validationMs:performance.now()-validationStart,serviceLatencyMs:elapsedMs,
        reference,quality,selectedObservation:observed?.observations??null,
        acquisitionUnits,additionalValidationAcquisitionUnits:validationAcquisitionUnits,
        passed:construction.status==='COMPILED'&&reference?.valid===true&&quality.every(x=>x.passed),
        workbenchPackDigest:pack?.integrityDigest??null,deliveryDigest:delivery?.integrityDigest??null,
        providerCostUsd:null,computeCostUsd:null,humanMinutes:null,settlement:'NOT_CONNECTED'};
      if(slot===0&&pack)samples.push({mode:mode.id,count,concurrency,pack,delivery,acquisition:observed});
    }
  }
  await Promise.all(Array.from({length:concurrency},worker));
  const elapsedMs=performance.now()-begin;
  const summary={mode:mode.id,count,concurrency,elapsedMs,throughputPerSecond:count/(elapsedMs/1000),
    p50ServiceLatencyMs:percentile(rows.map(r=>r.serviceLatencyMs),0.5),p95ServiceLatencyMs:percentile(rows.map(r=>r.serviceLatencyMs),0.95),
    completed:rows.filter(r=>r.passed).length,errorRate:rows.filter(r=>!r.passed).length/count,
    composition:Object.fromEntries(['digital','mixture','network'].map(k=>[k,rows.filter(r=>r.family===k).length])),
    compilerLogicalUnits:rows.reduce((s,r)=>s+r.construction.work.used,0),
    acquisitionUnits:rows.reduce((s,r)=>s+r.acquisitionUnits,0),
    additionalValidationAcquisitionUnits:rows.reduce((s,r)=>s+r.additionalValidationAcquisitionUnits,0),
    validationMsSum:rows.reduce((s,r)=>s+r.validationMs,0),cache:compiler.stats(),
    interventionsDuringRun:0,interventionScope:'No external human input was requested during these bounded calls; setup and authoring are excluded and unmeasured.',
    totalCostUsd:null,unitCostUsd:null,validatorHumanMinutes:null};
  await save(mode.id+'-'+count+'-c'+concurrency+'.json',{summary,rows});
  await append('load-result',summary);results.push(summary);
}
// Alternate the ordering of conditions at each load; single host, not distributed workers.
for(const [i,count]of [1,10,100].entries()){
  const ordered=i%2?[...modes].reverse():modes;
  for(const mode of ordered)await measure(mode,count,count===1?1:4);
}
const faultResults=[];
async function control(name,fn){
  const begin=performance.now();
  try{const result=await fn();faultResults.push({name,passed:true,elapsedMs:performance.now()-begin,result});}
  catch(error){faultResults.push({name,passed:false,elapsedMs:performance.now()-begin,error:error.message});}
}
await control('malformed input',async()=>{
  const p=JSON.parse(JSON.stringify(digitalFault()));p.id=true;
  try{await createCompiler().compile(p);}catch(error){return {rejected:error.message};}
  throw Error('Malformed identity accepted');
});
await control('bounded work exhaustion',async()=>{
  const r=await createCompiler().compile(digitalFault(),{budget:1});
  if(r.status!=='BUDGET_EXHAUSTED'||r.certificate.searchComplete)throw Error('Exhaustion misclassified');
  return r;
});
await control('acquisition budget exhaustion',async()=>{
  const p=digitalFault({missionBudget:1}),r=await createCompiler().compile(p);
  if(r.status!=='OVER_MISSION_BUDGET')throw Error('Acquisition budget not enforced');return r;
});
await control('operator stop',async()=>{
  const controller=new AbortController();let checkpoints=0;
  try{await createDiscoverabilityWorkbench().run(discoverabilityMission(digitalFault()),{
    sourceHash,signal:controller.signal,onCheckpoint:async()=>{if(++checkpoints===3)controller.abort();}});
  }catch(error){if(error.message==='CANCELLED')return {error:error.message,checkpoints};throw error;}
  throw Error('Stop did not cancel');
});
await control('executor checkpoint outage and fresh retry',async()=>{
  let points=0;
  try{await createDiscoverabilityWorkbench().run(discoverabilityMission(digitalFault()),{
    sourceHash,onCheckpoint:async()=>{if(++points===4)throw Error('INJECTED_CHECKPOINT_OUTAGE');}});
    throw Error('Outage was ignored');
  }catch(error){if(error.message!=='INJECTED_CHECKPOINT_OUTAGE')throw error;}
  const retry=await createDiscoverabilityWorkbench().run(discoverabilityMission(digitalFault()),{sourceHash});
  if(retry.result.evidence.construction.status!=='COMPILED')throw Error('Fresh retry failed');
  return {outage:'INJECTED_CHECKPOINT_OUTAGE',freshRetry:'COMPILED',retryLimit:1,authority:retry.evaluation.authority,
    scope:'Caller retry after injected local outage; not a native crash-resume or backend exactly-once test.'};
});
await control('duplicate mission identities',async()=>{
  const runtime=createDiscoverabilityWorkbench(),p=digitalFault();
  const a=await runtime.run(discoverabilityMission(p),{sourceHash}),b=await runtime.run(discoverabilityMission(p),{sourceHash});
  if(a.frozen.missionDigest!==b.frozen.missionDigest)throw Error('Semantic identity changed');
  return {sameSemanticIdentity:true,executions:2,financialSideEffects:0,
    duplicateSuppression:'NOT_IMPLEMENTED_IN_LOCAL_WORKBENCH',limits:'Both calls execute and incur work. No exactly-once native behavior is claimed.'};
});
await control('restart evidence recovery',async()=>{
  const sample=samples[0].pack;await save('restart-pack.json',sample);
  const reloaded=JSON.parse(await readFile(resolve(dir,'restart-pack.json'),'utf8'));
  const fresh=createDiscoverabilityWorkbench(),inspection=await fresh.inspectPack(reloaded);
  if(inspection.activeProof.length||inspection.activeAuthority.length)throw Error('Recovered unauthorized authority');
  return {inspection,scope:'Fresh workbench instance after JSON persistence. Not process-kill/native journal recovery.',inheritedCache:false};
});
await control('tampered recovery rejection',async()=>{
  const altered=JSON.parse(JSON.stringify(samples[0].pack));altered.result.summary.acquisitionCost++;
  try{await createDiscoverabilityWorkbench().inspectPack(altered);}catch(error){return {rejected:error.message};}
  throw Error('Tampered pack accepted');
});
await control('invalidated parent certificate',async()=>{
  const parent=networkProblem({requirement:'repair'}),child=networkProblem({requirement:'repair',clockOrder:2});
  const c=createCompiler(),r=await c.compile(parent);
  try{inspectProgram(child,r.program);}catch(error){
    const refused=await c.compile(child),rebuilt=await c.compile(networkProblem({requirement:'repair',clockOrder:2,extendedGrammar:true}));
    if(refused.status!=='UNIDENTIFIABLE_WITHIN_GRAMMAR'||rebuilt.status!=='COMPILED')throw Error('Expected refusal/rebuild absent');
    return {staleRejected:error.message,refused,rebuilt};
  }throw Error('Stale program accepted');
});
await control('accepted bounded reuse improvement',async()=>{
  const p=networkProblem({requirement:'route'}),q=networkProblem({requirement:'repair'}),cache=createCompiler();
  const before=await cache.compile(p),inherited=await cache.compile(q),fresh=await createCompiler({strategy:'fresh'}).compile(q);
  const verified=verifyProgramReference(q,inherited.program),same=canonical(inherited.program)===canonical(fresh.program);
  if(!same||!verified.valid||inherited.work.used>=fresh.work.used)throw Error('Reuse improvement acceptance failed');
  return {status:'FUNCTIONAL_AND_RESOURCE_ACCEPTANCE_PASSED',parentWork:before.work.used,
    inheritedWork:inherited.work.used,freshWork:fresh.work.used,savedLogicalUnits:fresh.work.used-inherited.work.used,
    sameProgram:same,reference:verified,formalPromotion:'NOT_PERFORMED',
    scope:'Preimplemented cache strategy passes unchanged model/decision criterion; no general autonomous RSI claim.'};
});
const conventional=[];
for(const p of [digitalFault(),digitalFault({goal:'health'}),mixtureAssay(),mixtureAssay({goal:'quantify'}),
  networkProblem({requirement:'route'}),networkProblem({requirement:'repair'}),
  networkProblem({requirement:'repair',clockOrder:2}),
  networkProblem({requirement:'repair',clockOrder:2,extendedGrammar:true})]){
  conventional.push({id:p.id,problem:p,static:conventionalStatic(p),adaptive:conventionalAdaptive(p)});
}
await save('controls.json',faultResults);await append('controls',faultResults);
await save('conventional.json',conventional);await append('conventional',conventional);
await save('sample-packs.json',samples);
const report={schema:'discoverability-load-report/v1',runId:'discoverability-20261022-v1',sourceHash,
  startedAt,finishedAt:new Date().toISOString(),elapsedMs:performance.now()-timer,
  environment:{node:process.version,platform:process.platform,architecture:process.arch,kernel:os.release(),
    cpuModel:os.cpus()[0]?.model,cpuCount:os.cpus().length,availableParallelism:os.availableParallelism(),
    totalMemoryBytes:os.totalmem(),processPeakRssBytes:process.resourceUsage().maxRSS*1024,
    isolation:'Shared hosted Linux execution environment; no dedicated machine or CPU isolation assumed.'},
  results,controls: faultResults.map(({name,passed})=>({name,passed})),
  scope:{execution:'Actual Node computation over explicitly synthetic heterogeneous finite models',
    concurrency:'Cooperative calls sharing one Node process and bounded cache; not Fleet worker scalability.',
    quality:'Every world sampled per mission plus independent model/program reference checks.',
    timings:'One run per condition; service latency starts when a worker dequeues a mission, excluding pending queue wait; it includes cooperative scheduling and validation. No confidence interval.',
    costs:'Acquisition and logical work units are separate. Paid compute/inference/setup/human costs unobserved.',
    commercial:'No arm-length executable demand, realized cash or demonstrated value target.',
    authority:'No independent council admission, native promotion or settlement.'}};
await save('report.json',report);await append('finish',{reportSha256:hash(JSON.stringify(report,null,2)+'\n')});
await history.close();
await save('history-root.json',{schema:'discoverability-history-root/v1',runId:report.runId,entries:sequence,sha256:previous,
  authentication:'Hash-chain tamper evidence only. Root needs an independently retained commit or signature; no cryptographic authorship claimed.'});
console.log(JSON.stringify({output:dir,report,historyRoot:previous},null,2));
if(report.results.some(x=>x.errorRate!==0)||faultResults.some(x=>!x.passed))process.exitCode=1;
