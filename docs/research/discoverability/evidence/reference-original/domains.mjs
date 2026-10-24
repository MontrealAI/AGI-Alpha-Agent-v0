// SPDX-License-Identifier: Apache-2.0
import {SCHEMA,validateProblem} from './compiler.mjs';
export function digitalFault({noise=1,goal='repair',drift=1,missionBudget=40}={}){
  const stimuli=[[0,0],[0,1],[1,0],[1,1]];
  const gates={xor:(a,b)=>a^b,and:(a,b)=>a&b,or:(a,b)=>a|b,nand:(a,b)=>1-(a&b),stucklow:()=>0,stuckhigh:()=>1};
  const channels=['reference-before','input-00','input-01','input-10','input-11','reference-after'].map(id=>({id,cost:1,noise}));
  return validateProblem({schema:SCHEMA,id:'digital-fault-'+goal,channels,
    worlds:Object.entries(gates).map(([id,fn])=>({id,goal:goal==='health'?(id==='xor'?'retain':'replace'):id==='xor'?'retain':'replace-'+id,signal:[0,...stimuli.map(([a,b])=>24*fn(a,b)),0]})),
    nuisance:channels.map((_,i)=>drift?[1,i]:[1]),grammar:{maxSupport:3,weightLimit:2,maxL1:4},missionBudget});
}
export function mixtureAssay({noise=1,goal='disposition',drift=1,missionBudget=48}={}){
  const a=[1,4,2,0],b=[3,0,1,4],worlds=[];
  for(let ca=0;ca<=2;ca++)for(let cb=0;cb<=2;cb++)worlds.push({id:'a'+ca+'b'+cb,
    goal:goal==='quantify'?'a'+ca+'b'+cb:ca>0?'quarantine-a':cb>0?'recover-b':'clear',
    signal:[0,...a.map((x,i)=>20*(x*ca+b[i]*cb)),0]});
  const channels=['blank-before','band-violet','band-blue','band-green','band-red','blank-after'].map((id,i)=>({id,cost:i===0||i===5?1:3,noise}));
  return validateProblem({schema:SCHEMA,id:'mixture-assay-'+goal,channels,worlds,nuisance:channels.map((_,i)=>drift?[1,i]:[1]),
    grammar:{maxSupport:3,weightLimit:2,maxL1:4},missionBudget});
}
export function acquireSynthetic(problem,program,worldId,{nuisanceScale=13,errorSign=0}={}){
  const world=problem.worlds.find(w=>w.id===worldId); if(!world)throw new Error('unknown evaluator world');
  const raw=[],observations=[];
  for(let j=0;j<program.experiments.length;j++){
    const e=program.experiments[j];
    const values=problem.channels.map((c,i)=>{
      const nuisance=problem.nuisance[i].reduce((s,x,k)=>s+x*(nuisanceScale+(j+1)*(k+1)),0);
      const sign=errorSign===0?((i+j)%3)-1:errorSign;
      return world.signal[i]+nuisance+sign*c.noise;
    });
    observations.push(e.weights.reduce((s,w,i)=>s+w*values[i],0)); raw.push(values);
  }
  return {observations,raw,mode:'NEWLY_EXECUTED_SYNTHETIC',truthForEvaluatorOnly:{worldId,requiredDecision:world.goal},
    limits:['Finite supplied world class; synthetic acquisition; no external instrument, real customer or settlement.']};
}
export const DOMAIN_CATALOG=[
 {id:'digital-fault',title:'Diagnose a faulty digital module',output:'A decision and a reusable drift-rejecting probe program',builder:'digitalFault'},
 {id:'mixture-assay',title:'Choose a mixture disposition',output:'A decision and a reusable assay program',builder:'mixtureAssay'}
];
