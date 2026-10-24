// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {fork} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createGzip} from 'node:zlib';
import {pipeline} from 'node:stream/promises';
import {scenarioWorld,conventionalGreedy,SCENARIOS,hash} from './engine_adapter.mjs';
import {expertSchedule,evaluateSchedule} from './independent_evaluator.mjs';
import {missionRecorder} from './evidence_adapter.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const METHODS=['idea','greedy','disclosed','verified','clone','expert','adaptive-expert'];
const argv=process.argv.slice(2),arg=name=>{const i=argv.indexOf(name);return i<0?null:argv[i+1];};
const mode=arg('--mode')||'dev',output=path.resolve(arg('--out')||path.join(root,'results',mode));
if(!['dev','holdout','pilot'].includes(mode))throw Error('mode must be dev, pilot or holdout');
if(fs.existsSync(output))throw Error('Output directory already exists; evidence is never overwritten.');
const seeds=mode==='holdout'?Array.from({length:32},(_,i)=>101+i):mode==='dev'?Array.from({length:8},(_,i)=>1+i):[1];
const epochs=mode==='pilot'?2:12,scenarios=mode==='pilot'?['ordinary','measurement-drift','expensive-evidence']:SCENARIOS;

function sourceInventory(){
  const files=[];for(const folder of ['src','vendor']){
    function visit(dir){for(const name of fs.readdirSync(dir).sort()){const file=path.join(dir,name);if(fs.statSync(file).isDirectory())visit(file);else files.push(file);}}visit(path.join(root,folder));
  }
  return Object.fromEntries(files.map(file=>[path.relative(root,file),createHash('sha256').update(fs.readFileSync(file)).digest('hex')]));
}
const inventory=sourceInventory(),inventoryHash=hash(inventory);
if(mode==='holdout'){
  const freeze=JSON.parse(fs.readFileSync(path.join(root,'protocol','source-freeze.json'),'utf8'));
  if(freeze.sourceInventoryHash!==inventoryHash||freeze.status!=='FROZEN_BEFORE_HOLDOUT')throw Error('Source or protocol is not frozen for holdout');
}
fs.mkdirSync(output,{recursive:true});
const started=performance.now(),parentCpu=process.cpuUsage(),startedAt=new Date().toISOString();
const cloneRoot=fs.mkdtempSync(path.join(os.tmpdir(),'nova-seeds-full-copy-')),copyStart=performance.now();
for(const folder of ['src','vendor'])fs.cpSync(path.join(root,folder),path.join(cloneRoot,folder),{recursive:true});
const copying={wallMs:performance.now()-copyStart,sourceFiles:Object.keys(inventory).length,sourceBytes:Object.keys(inventory).reduce((n,file)=>n+fs.statSync(path.join(root,file)).size,0),method:'Actual full source copy and independent Node process; no shared function object or runtime cache.'};
const copyEvidenceImportStart=performance.now(),copyEvidence=await import(pathToFileURL(path.join(cloneRoot,'src','evidence_adapter.mjs')));
copying.evidenceImportMs=performance.now()-copyEvidenceImportStart;
copying.evidenceBoundary='Copied evidence module in parent process; separate ephemeral signer and ledger. Same external evaluator and OS; not organizational independence.';
let serial=0;
async function startWorker(directory){
  const launched=performance.now(),worker=fork(path.join(directory,'src','native_worker.mjs'),[],{execArgv:['--max-old-space-size=512'],stdio:['ignore','ignore','pipe','ipc']}),pending=new Map();let errors='';
  worker.stderr.on('data',data=>{errors=(errors+data.toString()).slice(-5000);});
  const ready=await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{worker.kill('SIGKILL');reject(Error('Worker startup timeout'));},20000);
    worker.once('error',reject);worker.once('exit',code=>reject(Error('Worker exited '+code+': '+errors)));
    worker.once('message',message=>{clearTimeout(timer);resolve(message);});
  });
  worker.on('message',message=>{const record=pending.get(message.id);if(record){clearTimeout(record.timer);pending.delete(message.id);message.error?record.reject(Error(message.error.message)):record.resolve(message);}});
  worker.on('exit',()=>{for(const item of pending.values()){clearTimeout(item.timer);item.reject(Error('Worker exited: '+errors));}pending.clear();});
  return {startupMs:performance.now()-launched,ready,
    async run(mission,options){const id=String(++serial),sent=performance.now();return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);worker.kill('SIGKILL');reject(Error('20-second method deadline exceeded'));},20000);pending.set(id,{timer,resolve:m=>resolve({...m,ipcRoundTripMs:performance.now()-sent}),reject});worker.send({id,mission,options,lease:{missionId:mission.id,scope:'local-synthetic-allocation',expiresAt:Date.now()+20000}});});},
    async stats(){const id=String(++serial);return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Stats timeout')),1000);pending.set(id,{timer,resolve,reject});worker.send({id,stats:true});});},
    close(){worker.send({close:true});}
  };
}
const primary=await startWorker(root),replica=await startWorker(cloneRoot);copying.importStartupMs=replica.startupMs;
function gzipSink(file){
  const zipper=createGzip({level:6}),target=fs.createWriteStream(file,{flags:'wx'});let failure=null;
  const completed=pipeline(zipper,target).catch(error=>{failure=error;});
  return {async write(text){if(failure)throw failure;await new Promise((resolve,reject)=>zipper.write(text,error=>error?reject(error):resolve()));if(failure)throw failure;},async close(){zipper.end();await completed;if(failure)throw failure;}};
}
const recordsFile=path.join(output,'missions.jsonl.gz'),ledgersFile=path.join(output,'ledgers.jsonl.gz'),proofDir=path.join(output,'proofs');fs.mkdirSync(proofDir);
const recordsSink=gzipSink(recordsFile),ledgersSink=gzipSink(ledgersFile);
const totals={missions:0,rows:0,methodFailures:0,externalEvaluatorMs:0,externalEvaluatorCpuMicros:{user:0,system:0},methods:{},diagnosticAcquisitionsPerPolicyPerMission:4};
const knownFailure=[];
try{
  for(const scenario of scenarios)for(const seed of seeds){
    let pastQc=null;
    for(let epoch=0;epoch<epochs;epoch++){
      if(performance.now()-started>30*60*1000)throw Error('Thirty-minute study budget exhausted');
      const world=scenarioWorld(seed,epoch,scenario),mission=world.mission,prior=structuredClone(pastQc),rows=[];
      mission.pastQc=structuredClone(prior);
      const order=METHODS.map((_,i)=>METHODS[(i+seed+epoch)%METHODS.length]),retained=seed===seeds[0]&&[0,6].includes(epoch);
      const ledgerDirectories=[],recorders=new Map();
      try{
        for(const method of order){
          const timeBefore=performance.now(),cpuBefore=process.cpuUsage();let result,measuredOutcome,receipt=null,maxRssKiB=null,ipcRoundTripMs=0;
          try{
            if(['disclosed','verified','clone'].includes(method)){
              const response=await (method==='clone'?replica:primary).run(mission,{evidenceRepeats:method==='disclosed'?0:scenario==='expensive-evidence'?8:1,retainProof:retained});
              ({result,maxRssKiB,ipcRoundTripMs}=response);
            }else{
              const output=method==='greedy'?conventionalGreedy(mission):expertSchedule(mission,{ideaOnly:method==='idea',predictedBias:method==='adaptive-expert'&&prior?prior.relativeBias:null});
              result={status:'COMPLETE',...output,wallMs:performance.now()-timeBefore,cpuMicros:process.cpuUsage(cpuBefore),proofBytes:0,evidenceRepeats:0};
            }
            if(!result.plan)throw Error('No complete schedule');
            const checkStart=performance.now(),checkCpu=process.cpuUsage();
            const outcome=measuredOutcome=evaluateSchedule(world,result.plan,{ideaOnly:method==='idea'});
            const evaluatorMs=performance.now()-checkStart,evaluatorCpu=process.cpuUsage(checkCpu);
            totals.externalEvaluatorMs+=evaluatorMs;totals.externalEvaluatorCpuMicros.user+=evaluatorCpu.user;totals.externalEvaluatorCpuMicros.system+=evaluatorCpu.system;
            if(!outcome.valid)throw Error('Independent replay rejected the proposed physical schedule');
            if(['verified','clone','expert','adaptive-expert','greedy'].includes(method)){
              const setupStart=performance.now(),setupCpu=process.cpuUsage(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'nova-seeds-policy-ledger-'));
              ledgerDirectories.push(directory);
              const recorder=(method==='clone'?copyEvidence.missionRecorder:missionRecorder)(directory,mission);recorders.set(method,recorder);
              const setupWallMs=performance.now()-setupStart,setupCpuMicros=process.cpuUsage(setupCpu);
              receipt={...await recorder.append(method,result,outcome),setupWallMs,setupCpuMicros};
            }
            if(retained&&result.completion){fs.writeFileSync(path.join(proofDir,`${scenario}-s${seed}-e${epoch}-${method}.json`),JSON.stringify(result.completion,null,2)+'\n');}
            const {completion,...summary}=result;
            const row={schema:'nova-seeds-mission-result/v1',seed,epoch,scenario,method,world,pastQc:prior,qcPolicy:method==='adaptive-expert'?'uses-prior-profile':'offered-but-static-policy-ignores',
              result:summary,outcome,receipt,diagnosticAcquisitions:4,simulated:{sampleAcquisitions:outcome.attemptedJobs,calibrationAcquisitions:outcome.calibrations,diagnosticAcquisitions:4,instrumentOccupationTicks:outcome.resourceTicks},
              measured:{methodWallMs:result.wallMs,methodCpuMicros:result.cpuMicros,externalEvaluatorMs:evaluatorMs,externalEvaluatorCpuMicros:evaluatorCpu,evidenceMs:receipt?.wallMs||0,evidenceCpuMicros:receipt?.cpuMicros||{user:0,system:0},recorderSetupMs:receipt?.setupWallMs||0,recorderSetupCpuMicros:receipt?.setupCpuMicros||{user:0,system:0},ipcRoundTripMs,maxRssKiB},
              monetary:{revenue:null,profit:null,humanEffort:null,providerBilling:null},status:'complete'};
            rows.push(row);
          }catch(error){totals.methodFailures++;const failure={schema:'nova-seeds-mission-result/v1',seed,epoch,scenario,method,world,pastQc:prior,result:result||null,outcome:measuredOutcome||null,status:'failed',reason:error.message,spentWallMs:performance.now()-timeBefore,spentParentCpuMicros:process.cpuUsage(cpuBefore)};rows.push(failure);knownFailure.push({seed,epoch,scenario,method,reason:error.message});}
        }
        const modelExpert=rows.find(row=>row.method==='expert'),reference=rows.find(row=>row.method==='verified'),cloneRow=rows.find(row=>row.method==='clone');
        const policyRecords=Object.fromEntries([...recorders.entries()].map(([method,recorder])=>[method,recorder.close()]));await ledgersSink.write(JSON.stringify({missionId:mission.id,seed,epoch,scenario,policyRecords})+'\n');
        for(const row of rows){await recordsSink.write(JSON.stringify(row)+'\n');totals.rows++;if(row.status==='complete'){const t=totals.methods[row.method]??={rows:0,utility:0,completedJobs:0,failures:0,wallMs:0,cpuMicros:0,evidenceMs:0};t.rows++;t.utility+=row.outcome.utility;t.completedJobs+=row.outcome.completedJobs;t.failures+=row.outcome.failures;t.wallMs+=row.measured.methodWallMs;t.cpuMicros+=row.measured.methodCpuMicros.user+row.measured.methodCpuMicros.system;t.evidenceMs+=row.measured.evidenceMs;}}
        let disagreement=null;
        if(reference?.status==='complete'&&modelExpert?.status==='complete'&&reference.result.objective!==modelExpert.result.objective)disagreement='Independent model objective disagreement';
        if(reference?.status==='complete'&&cloneRow?.status==='complete'&&(JSON.stringify(reference.result.plan)!==JSON.stringify(cloneRow.result.plan)||JSON.stringify(reference.outcome)!==JSON.stringify(cloneRow.outcome)))disagreement='Full source replica plan or realized-outcome disagreement';
        if(disagreement){knownFailure.push({seed,epoch,scenario,method:'cross-check',reason:disagreement});await recordsSink.write(JSON.stringify({status:'fatal-cross-check',seed,epoch,scenario,reason:disagreement})+'\n');throw Error(disagreement);}
        const qcStart=performance.now();pastQc={sourceEpoch:epoch,relativeBias:world.bias.map(value=>value-world.bias[0]),diagnosticAcquisitions:4,scope:'Exact synthetic auxiliary reference channel revealed after all current policies finish.'};
        totals.qcConstructionMs=(totals.qcConstructionMs||0)+(performance.now()-qcStart);totals.missions++;
      }finally{for(const directory of ledgerDirectories)fs.rmSync(directory,{recursive:true,force:true});}
    }
    process.stderr.write(JSON.stringify({completedScenario:scenario,seed,missions:totals.missions,elapsedSeconds:Math.round((performance.now()-started)/1000)})+'\n');
  }
}finally{
  await recordsSink.close();await ledgersSink.close();
  const workers={primary:await primary.stats().catch(error=>({unavailable:error.message})),clone:await replica.stats().catch(error=>({unavailable:error.message}))};
  primary.close();replica.close();fs.rmSync(cloneRoot,{recursive:true,force:true});
  const report={schema:'nova-seeds-study-metrics/v1',mode,seeds,epochs,scenarios,methods:METHODS,startedAt,finishedAt:new Date().toISOString(),node:process.version,sourceInventory:inventory,sourceInventoryHash:inventoryHash,copying,workerStartupMs:primary.startupMs,workers,
    wallMs:performance.now()-started,parentCpuMicros:process.cpuUsage(parentCpu),maxParentRssKiB:process.resourceUsage().maxRSS,totals,failures:knownFailure,storageBytes:fs.statSync(recordsFile).size+fs.statSync(ledgersFile).size+fs.readdirSync(proofDir).reduce((sum,name)=>sum+fs.statSync(path.join(proofDir,name)).size,0),recordEncoding:'gzip-compressed UTF-8 JSON lines; full records retained without semantic truncation',
    costLimits:'Synthetic resource quantities, declared native logical work, expert enumerations, measured wall/CPU, bytes and monetary unknowns remain separate. Not full-cost commercial profit.',futureEvidence:'Auxiliary diagnostic reference observations revealed after each epoch; identical previous profile offered to every policy.'};
  fs.writeFileSync(path.join(output,'metrics.json'),JSON.stringify(report,null,2)+'\n');
  fs.writeFileSync(path.join(output,'source-inventory.json'),JSON.stringify(inventory,null,2)+'\n');
  console.log(JSON.stringify({output,missions:totals.missions,rows:totals.rows,methodFailures:totals.methodFailures,wallSeconds:report.wallMs/1000,copying,methods:totals.methods},null,2));
}
