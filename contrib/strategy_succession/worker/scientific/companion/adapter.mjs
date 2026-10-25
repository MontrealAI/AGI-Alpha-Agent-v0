// SPDX-License-Identifier: Apache-2.0
import {Meter,WorkLimit,inspectTask,inspectStrategy,plan,portfolio,verifyLocal} from './core.mjs';
import {createWorkbench} from './vendor/examples/successor-workbench/engine.mjs';
import {digest} from './vendor/docs/assets/successor/engine.mjs';
import {SOURCE_HASH} from './binding.mjs';

const bytes=value=>new TextEncoder().encode(JSON.stringify(value,(key,value)=>key==='elapsedMilliseconds'||key.endsWith('_ms')?0:value)).length;
const clock=()=>globalThis.performance.now();
export const ADAPTER_MANIFEST=Object.freeze({id:'release-strategy',version:1,en:'Plan a resource-constrained release',fr:'Planifier une livraison contrainte',
 scope:'Finite synthetic or public worker-constrained planning and disruption repair; no operational execution or inherited authority.',artifact:'release-plan.json'});
export function checkerReserve(task,result){
 const n=task.jobs.length,H=task.capacity.length,E=task.jobs.reduce((s,j)=>s+j.deps.length,0),B=bytes({task,result});
 return 2*B+4*n*n+220*n+(2*n+50)*E+18*H+1024;
}
export async function localCheck(task,result){const meter=new Meter();try{return {...verifyLocal(task,result,meter),counts:{...meter.counts,total:meter.spent},errors:[]};}catch(error){return {valid:false,qualified:false,errors:[{code:error.message}],counts:{...meter.counts,total:meter.spent}};}}

export async function runMission(task,{strategy='portfolio',sourceHash=SOURCE_HASH,check=localCheck,budget=100000,signal,onEvent=()=>{}}={}){
 const started=clock(),validationMeter=new Meter(),meter=new Meter(Math.max(0,budget-18000));let checked=null,delivered=null,error=null,checkerWork=0,attempts=[],selectedMethod=null;
 if(!Number.isSafeInteger(budget)||budget<0)throw Error('MISSION_BUDGET');
 const adapter={manifest:ADAPTER_MANIFEST,
  validate(input){inspectTask(input.task,validationMeter);if(input.strategy!=='portfolio')inspectStrategy(input.strategy);if(input.budget!==budget)throw Error('BUDGET_BINDING');},
  async execute(input,checkpoint){
   await checkpoint('Out-Execute');onEvent({kind:'OUT_EXECUTE',mission_id:task.id});
   try{
    if(input.strategy==='portfolio'){const outcome=portfolio(input.task,meter,undefined,{stopOnQualified:true});delivered=outcome.result;attempts=outcome.attempts;selectedMethod=outcome.method;}
    else{delivered=plan(input.task,input.strategy,meter);selectedMethod=input.strategy;}
    const reserve=checkerReserve(input.task,delivered);meter.tick('accounting:check-reserve',1);
    if(meter.spent+validationMeter.spent+reserve+2048>budget)throw Error('CHECK_RESERVE');
    checkerWork=reserve; // On a timeout/failed acknowledgement the ceiling is charged.
    checked=await check(input.task,delivered);checkerWork=checked?.counts?.total??0;
    if(!Number.isSafeInteger(checkerWork)||checkerWork<0||checkerWork>reserve)throw Error('CHECKER_ACCOUNTING_BOUND');
    if(!checked.valid)error='INDEPENDENT_CHECK_REFUSED';
   }catch(e){error=e instanceof WorkLimit?'WORK_LIMIT':e.message;}
   await checkpoint('Out-Evolve');
   const evidence={task_id:input.task.id,valid:Boolean(checked?.valid&&!error),qualified:Boolean(checked?.qualified&&!error),
    strategy_digest:await digest('release-strategy',JSON.stringify(input.strategy)),candidate_error:error,
    proof:[],authority:[],checker:'Injected checker; see experiment custodian and implementation manifest.'};
   return {decision:error?'REFUSED':evidence.qualified?'QUALIFIED_LOCAL_RESULT':'FEASIBLE_TARGET_NOT_MET',
    summary:{jobs:task.jobs.length,makespan:delivered?.makespan??null,deadline:task.deadline??task.capacity.length,qualified:evidence.qualified},
    evidence,artifacts:[{name:'release-plan.json',type:'application/json',content:JSON.stringify({task:input.task,result:delivered,checker:checked,error},null,2)+'\n'}],
    limits:['Planning software only; schedules do not perform physical work.','Current receipt does not create production authority or a signed settlement.',
     'Named work units are an explicit accounting model, not machine instructions, dollars, or independent human review.']};
  }};
 const workbench=createWorkbench([adapter]);
 const spec={schema:'successor-workbench/v1',family:'release-strategy',name:'AGI ALPHA · Release strategy',language:'en',owner:'local-research-owner',
  rights:{dataClass:task.public_or_synthetic==='public'?'public':'synthetic',source:'Bounded nonpersonal release-planning input',license:task.input_license??'Apache-2.0'},reviewMinutes:10,
  inputs:{task,strategy,budget}};
 let pack=null;
 try{pack=await workbench.run(spec,{sourceHash,signal,onProgress:phase=>onEvent({kind:'PHASE',mission_id:task.id,phase})});}
 catch(e){error=e.message;}
 const envelopeWork=Math.ceil((bytes(spec)+(pack?bytes(pack):0))/64),work=meter.spent+validationMeter.spent+checkerWork+envelopeWork;
 if(work>budget)error='TOTAL_BUDGET_EXCEEDED';
 return {task_id:task.id,result:delivered,valid:Boolean(checked?.valid&&!error),qualified:Boolean(checked?.qualified&&!error),
  checker:checked,error,truncated:['WORK_LIMIT','CHECK_RESERVE','TOTAL_BUDGET_EXCEEDED'].includes(error),work,
  counts:{...meter.counts,'workbench:validation':validationMeter.spent,'checker:reference':checkerWork,'workbench:envelope-block64':envelopeWork},
  wall_ms:clock()-started,attempts,selected_method:selectedMethod,pack};
}

export async function inspectMissionPack(pack){
 const adapter={manifest:ADAPTER_MANIFEST,
  validate(input){inspectTask(input.task);if(input.strategy!=='portfolio')inspectStrategy(input.strategy);},execute:async()=>{throw Error('INSPECTION_ONLY');}};
 return createWorkbench([adapter]).inspectPack(pack);
}
