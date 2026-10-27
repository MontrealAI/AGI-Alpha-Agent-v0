// SPDX-License-Identifier: Apache-2.0
// Independent exhaustive-oracle check of the residual-network validator.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/template.html','utf8');
const source=html.slice(html.indexOf('function enumerate('),html.indexOf('function renderInstance('));
const c={};vm.createContext(c);vm.runInContext(source,c);
let state=771029;const random=()=>{state=(1664525*state+1013904223)>>>0;return state/4294967296};
let checked=0,feasible=0,optimal=0,mutations=0,infeasible=0;
for(let t=0;t<30;t++){
 const x={costs:Array.from({length:6},()=>Array.from({length:3},()=>Math.floor(random()*71)-20)),capacities:Array.from({length:3},()=>Math.floor(random()*5)),allowed:Array.from({length:6},()=>Array.from({length:3},()=>random()>.25))};
 const oracle=c.enumerate(x);if(!oracle.best)infeasible++;
 for(let k=0;k<729;k++){
  let v=k,a=[];for(let i=0;i<6;i++){a.push(v%3);v=Math.floor(v/3)}
  const valid=a.every((j,i)=>x.allowed[i][j])&&[0,1,2].every(j=>a.filter(z=>z===j).length<=x.capacities[j]);
  const cost=a.reduce((s,j,i)=>s+x.costs[i][j],0),expected=valid&&oracle.best!==null&&cost===oracle.best.cost;
  const result=c.verify(x,{assignment:a,cost});assert.equal(result.accepted,expected,JSON.stringify({t,k,x,a,cost,oracle:oracle.best,result}));checked++;if(valid)feasible++;if(expected){optimal++;assert.equal(c.verify(x,{assignment:a,cost:cost+1}).accepted,false);mutations++}
 }
}
const report={scope:'Local six-job/three-resource deterministic widget only',instances:30,all_candidate_checks:checked,feasible_candidates:feasible,optimal_candidates:optimal,objective_mutations_rejected:mutations,infeasible_instances:infeasible,passed:true};
fs.writeFileSync(__dirname+'/mechanism_qa.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
