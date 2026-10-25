// SPDX-License-Identifier: Apache-2.0
// Closed, auditable strategy search. No evaluator or authority is a candidate.
import {SPECIALISTS,specialistMethods,constructLookaheads,constructRepairs,inspectStrategy} from './core.mjs';
import {digest} from './vendor/docs/assets/successor/engine.mjs';

export const clone=value=>JSON.parse(JSON.stringify(value));
export const STRATEGY_MENU=Object.freeze([
 clone(SPECIALISTS[0]),
 {kind:'dispatch',name:'critical-work-short',weights:{cp:1,work:1,duration:-1}},
 {kind:'dispatch',name:'critical-long',weights:{cp:1,duration:1}},
 clone(SPECIALISTS[3]),clone(SPECIALISTS[2]),
 {kind:'dispatch',name:'critical-short',weights:{cp:1,duration:-1}},
 clone(SPECIALISTS[4]),clone(SPECIALISTS[1]),
]);

export async function strategyIdentity(strategy){inspectStrategy(strategy);return digest('release-strategy',JSON.stringify(strategy));}
export function equivalentRecipe(strategy){
 inspectStrategy(strategy);const out=clone(strategy);delete out.name;
 if(out.base)out.base=equivalentRecipe(out.base);
 if(out.weights){const gcd=(a,b)=>b?gcd(b,a%b):a;const factor=Object.values(out.weights).map(Math.abs).filter(Boolean).reduce(gcd,0)||1;out.weights=Object.fromEntries(Object.entries(out.weights).filter(([,v])=>v).map(([k,v])=>[k,v/factor]));}
 return out;
}
export function methodsFor(stage,parent,{conventional=false,noSuccession=false}={}){
 if(conventional)return specialistMethods(stage==='repair'?'repair':'plan').map(clone);
 if(stage==='dispatch')return STRATEGY_MENU.map(clone);
 if(stage==='lookahead')return constructLookaheads(noSuccession?SPECIALISTS[0]:parent);
 if(stage==='repair')return constructRepairs(noSuccession?{kind:'lookahead',base:clone(SPECIALISTS[0]),width:2,steps:1,trigger:'contention'}:parent);
 throw Error('UNKNOWN_DISCOVERY_STAGE');
}

function summary(rows){return {count:rows.length,valid:rows.filter(r=>r.valid).length,qualified:rows.filter(r=>r.qualified).length,
 work:rows.reduce((s,r)=>s+r.work,0),makespan:rows.reduce((s,r)=>s+(r.result?.makespan??10000),0)};}
function candidateOrder(a,b){return b.summary.qualified-a.summary.qualified||a.summary.work-b.summary.work||a.summary.makespan-b.summary.makespan||a.index-b.index;}

export async function discover({stage,parent,training,evaluate,remaining,options={}}){
 const methods=methodsFor(stage,parent,options),trials=methods.map((strategy,index)=>({index,strategy,complete:false,summary:summary([]),rows:[],eliminated_after:null}));
 let active=trials.map(t=>t.index),stop='TRAINING_RACE_COMPLETE';
 for(let round=0;round<training.length;round++){
  // Each complete round exposes every remaining strategy to the SAME task.
  // A partial budget-stopped round never becomes a basis for elimination.
  for(const index of active){
   if(remaining()<=0){stop='DISCOVERY_BUDGET';break;}
   const trial=trials[index],row=await evaluate(training[round],trial.strategy,'discovery');trial.rows.push(row);trial.summary=summary(trial.rows);
   if(row.error==='CHECK_RESERVE'){stop='DISCOVERY_BUDGET';break;}
  }
  if(stop==='DISCOVERY_BUDGET')break;
  const valid=active.map(i=>trials[i]).filter(t=>t.rows.every(r=>r.valid&&!r.truncated)).sort(candidateOrder);
  if(!valid.length){stop='NO_VALID_TRAINING_CANDIDATE';break;}
  const keep=valid.slice(0,Math.max(1,Math.ceil(valid.length/2))).map(t=>t.index);
  for(const index of active)if(!keep.includes(index))trials[index].eliminated_after=round+1;
  active=keep;
 }
 for(const trial of trials)trial.complete=trial.rows.length===training.length&&trial.rows.every(r=>!r.truncated);
 const complete=trials.filter(t=>t.complete&&t.summary.valid===training.length).sort(candidateOrder);
 const selected=complete[0]||null;
 // This hash is made BEFORE the caller exposes qualification tasks to it.
 const candidate=selected?{strategy:clone(selected.strategy),digest:await strategyIdentity(selected.strategy),training:clone(selected.summary),selected_index:selected.index}:null;
 return {stage,parent_digest:parent?await strategyIdentity(parent):null,menu_size:methods.length,search_rule:'Fixed equal-prefix successive halving; all eliminated rows retained',trials,candidate,stop};
}

export async function qualify({candidate,tasks,evaluate,incumbent,allocation,canFundPair=()=>true}){
 const rows=[],reference=[];
 for(const [index,task]of tasks.entries()){
  if(!canFundPair()){const missing={task_id:task.id,result:null,valid:false,qualified:false,work:0,error:'UNFUNDED_QUALIFICATION_PAIR',truncated:true,allocated_budget:0};rows.push({...missing});reference.push({...missing});continue;}
  if(index%2===0){rows.push(await evaluate(task,candidate.strategy,'qualification',allocation));reference.push(await evaluate(task,incumbent,'qualification-reference',allocation));}
  else{reference.push(await evaluate(task,incumbent,'qualification-reference',allocation));rows.push(await evaluate(task,candidate.strategy,'qualification',allocation));}
 }
 const fairAllocation=rows.length===tasks.length&&reference.length===tasks.length&&[...rows,...reference].every(r=>r.allocated_budget===allocation);
 return {candidate_digest:candidate.digest,candidate:summary(rows),incumbent:summary(reference),rows,reference,
  registered_per_output_allocation:allocation,fair_allocation:fairAllocation,
  correctness:fairAllocation&&rows.every(r=>r.valid&&!r.truncated),independence:'Separate checker implementation; common project authorship and one machine.'};
}

export function admission({qualification,acquisition,remainingMissions,remainingBudget,maintenance=0,force=false}){
 const q=qualification.candidate,r=qualification.incumbent,n=q.count;
 const candidateMean=n?q.work/n:Infinity,referenceMean=n?r.work/n:Infinity;
 const usableBudget=Math.max(0,remainingBudget-maintenance),candidateCapacity=Number.isFinite(candidateMean)&&candidateMean>0?Math.min(remainingMissions,Math.floor(usableBudget/candidateMean)):0;
 const referenceCapacity=Number.isFinite(referenceMean)&&referenceMean>0?Math.min(remainingMissions,Math.floor((remainingBudget+acquisition)/referenceMean)):0;
 const candidateCoverage=n?candidateCapacity*q.qualified/n:0,referenceCoverage=n?referenceCapacity*r.qualified/n:0;
 const predictedSavings=remainingMissions*(referenceMean-candidateMean)-acquisition-maintenance;
 const breakEven=referenceMean>candidateMean?Math.ceil((acquisition+maintenance)/(referenceMean-candidateMean)):null;
 const netBenefit=qualification.correctness&&(candidateCoverage>referenceCoverage+1e-12||Math.abs(candidateCoverage-referenceCoverage)<1e-12&&predictedSavings>0);
 return {correctness:qualification.correctness,net_benefit:netBenefit,accepted:qualification.correctness&&(force||netBenefit),
  decision:!qualification.fair_allocation?'DEFER_UNFUNDED_COMPARISON':!qualification.correctness?'REJECT_CORRECTNESS':netBenefit?'ADMIT_NET_BENEFIT':force?'DIAGNOSTIC_CORRECTNESS_ONLY':'RETAIN_INCUMBENT',
  forecast_remaining_missions:remainingMissions,forecast_remaining_budget:remainingBudget,acquisition,maintenance,candidate_maintenance:maintenance,incumbent_maintenance:0,
  candidate_mean_work:candidateMean,incumbent_mean_work:referenceMean,forecast_candidate_qualified:candidateCoverage,
  forecast_incumbent_qualified:referenceCoverage,predicted_net_savings:predictedSavings,break_even_missions:breakEven,
  assumption:'Qualification frequencies and mean costs generalize only to the declared remaining same-scope mission count; no demand or monetary value is inferred.'};
}
