// SPDX-License-Identifier: Apache-2.0
import {parentPort} from 'node:worker_threads';
import {simulate} from './simulator.mjs';
import {auditRun,auditPaired} from '../tests/economics_audit.mjs';
import {compactRun} from './records.mjs';
parentPort.on('message',task=>{
 try{
  if(task.kind==='train'){
   const rows=task.seeds.map(seed=>simulate(task.C,task.P,seed,{retain:false}).summary);
   parentPort.postMessage({ok:true,rows});return;
  }
  const runs=[];let reference=null;
  for(const [arm,P,ablation]of task.arms){
   const run=simulate(task.C,P,task.seed,{ablation});run.arm=arm;run.summary.arm=arm;
   if(task.case){run.case=task.case;Object.assign(run.summary,{case:task.case,parameter:task.parameter,value:task.value});}
   const audit=auditRun(run);if(reference)auditPaired(reference,run);else reference=run;
   runs.push({run:compactRun(run),audit});
  }
  parentPort.postMessage({ok:true,runs});
 }catch(e){parentPort.postMessage({ok:false,error:e.stack});}
});
