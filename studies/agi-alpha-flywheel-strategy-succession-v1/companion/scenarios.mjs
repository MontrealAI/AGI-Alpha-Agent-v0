// SPDX-License-Identifier: Apache-2.0
// Deterministic synthetic inputs. Confirmation creation is a separate, frozen
// evaluator operation; importing this module does not generate confirmation.
import {Meter,SPECIALISTS,plan,portfolio,inspectTask,lowerBound} from './core.mjs';
import {rng} from './development_tasks.mjs';

export const SCOPES=['ordinary','tight','repair'];
export function makeTask(seed,scope,{prefix='development',slack=null}={}){
 if(!SCOPES.includes(scope))throw Error('SCENARIO_SCOPE');
 const random=rng(seed),count=scope==='ordinary'?10+2*Math.floor(random()*2):14,capacity=2+Math.floor(random()*3),jobs=[];
 for(let i=0;i<count;i++){
  const deps=[];for(let j=0;j<i;j++)if(random()<(seed%2===0?.05:.12))deps.push(`J${j+1}`);
  jobs.push({id:`J${i+1}`,duration:1+Math.floor(random()*9),crew:1+Math.floor(random()*Math.min(3,capacity)),deps});
 }
 const task={schema:'release-plan/v1',id:`${prefix}-${seed}-${scope}`,kind:'plan',scope,jobs,capacity:Array(128).fill(capacity),release:{},locked:{},
  public_or_synthetic:'synthetic',planning_only:true,fixture_seed:seed};
 if(scope==='repair'){
  const meter=new Meter();const old=portfolio(task,meter).result;
  const cut=Math.max(1,Math.floor(old.makespan*.3)),outageEnd=Math.min(127,cut+5+Math.floor(random()*5));
  task.kind='repair';task.baseline=Object.fromEntries(old.schedule.map(j=>[j.id,j.start]));
  task.locked=Object.fromEntries(old.schedule.filter(j=>j.start<cut).map(j=>[j.id,j.start]));
  task.release=Object.fromEntries(jobs.filter(j=>!(j.id in task.locked)).map(j=>[j.id,cut]));
  const lockedUsage=Array(128).fill(0);for(const j of old.schedule)if(j.id in task.locked){const spec=jobs.find(x=>x.id===j.id);for(let t=j.start;t<j.end;t++)lockedUsage[t]+=spec.crew;}
  for(let t=cut;t<outageEnd;t++)task.capacity[t]=Math.max(lockedUsage[t],capacity-1);
  task.disruption={observed_at:cut,capacity_reduced_until:outageEnd,locked_jobs:Object.keys(task.locked).length};
  task.fixture_generation={baseline_method:'Five-rule conventional portfolio, before capacity change',baseline_work:meter.spent,
   note:'Synthetic user input construction common to every arm; not an acquired candidate or paid demand.'};
 }
 const bound=lowerBound(inspectTask(task)).value;
 const choices=scope==='ordinary'?[120,135]:scope==='tight'?[100,108]:[108,120];
 const slackPercent=slack??choices[Math.floor(random()*choices.length)];
 task.deadline=Math.min(128,Math.ceil(bound*slackPercent/100));
 task.requirement={bound_based_slack_percent:slackPercent,deadline_origin:'Registered structural lower bound × fixed slack coin; no candidate output.'};
 return task;
}

export function developmentConfiguration(seed=32001,{missions=9}={}){
 const tasks=Array.from({length:missions},(_,i)=>makeTask(seed+i,SCOPES[i%3]));
 const qualification={};
 for(const [index,stage]of ['dispatch','lookahead','repair'].entries()){
  const scope=SCOPES[index];qualification[stage]={training:Array.from({length:6},(_,i)=>makeTask(seed+1000+index*100+i,scope)),
   validation:Array.from({length:4},(_,i)=>makeTask(seed+2000+index*100+i,scope))};
 }
 return {tasks,qualification,policy:{mode:'flywheel',totalWork:1000000,perMissionWork:100000,discoveryWork:500000,wallTimeMs:120000,
  stageAt:[1,Math.max(2,Math.floor(missions/3)+1),Math.max(3,Math.floor(2*missions/3)+1)],maxAssets:3,
  authority:{scope:'LOCAL_SYNTHETIC_RELEASE_PLANNING',expires:'2099-01-01T00:00:00Z'},label:'Development example, not confirmation'}};
}

export function demoConfiguration({diagnostic=false}={}){
 // A browser convenience stream; it is not the protected confirmatory sample.
 const config=developmentConfiguration(43001,{missions:6});
 config.tasks=[makeTask(43001,'ordinary'),makeTask(43002,'ordinary'),makeTask(43003,'tight'),makeTask(43004,'tight'),makeTask(43005,'repair'),makeTask(43006,'repair')];
 config.policy.mode=diagnostic?'diagnostic':'flywheel';config.policy.totalWork=diagnostic?5000000:3000000;config.policy.discoveryWork=diagnostic?1500000:750000;
 config.policy.stageAt=[1,3,5];config.policy.actor='browser-user';config.policy.label=diagnostic?'Fresh diagnostic construction; correctness-only retention is separate from economic admission':'Fresh selective execution; full costs can rationally retain the incumbent';
 return config;
}

export function createConfirmationInputs(seed){
 const tasks=[];
 for(let window=0;window<3;window++)for(let i=0;i<24;i++)tasks.push(makeTask(seed+window*100+i,SCOPES[i%3],{prefix:'confirmation'}));
 const config=developmentConfiguration(seed+10000,{missions:3});
 config.tasks=tasks;config.policy.stageAt=[1,25,49];config.policy.label='Confirmation: generated only after frozen protocol/source/checker checkpoint';
 return config;
}
