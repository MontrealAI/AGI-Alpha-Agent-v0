import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {network,updated,Meter,matrix,factor,triangular,inspectParent,validateConfig} from './core.mjs';
import {checkResponse} from './checker.mjs';
import {executeMission,hash} from './mission.mjs';
const checks=[];const ok=(name,value)=>{assert(value,name);checks.push({name,passed:true});};
let state={stage:0,config:{load:1.25,strength:.75},accepted:[],run_id:'browser-checker-development',parent:null,successor:null};
for(let phase=0;phase<4;phase++){const r=await executeMission(state,phase,{sourceHash:'b'.repeat(64)});state=r.next;ok('phase_'+phase+'_verified',r.record.valid);}
const r=state.accepted[3];
for(const [name,mutate]of[
 ['wrong_answer',x=>{x.x[12]+=.1;}],['wrong_load',x=>{x.b[12]+=.1;}],['wrong_edge',x=>{x.network.edges[0].g+=1;}],['invalid_edge',x=>{x.network.edges[0].g=-1;}],['nonfinite_output',x=>{x.x[0]=NaN;}],['missing_output',x=>{x.x.pop();}]
]){const x=structuredClone(r);mutate(x);ok(name+'_refused',!checkResponse(x.network,x.b,x.x).valid);}
ok('json_roundtrip_checked',checkResponse(...(()=>{const x=JSON.parse(JSON.stringify(r));return[x.network,x.b,x.x];})()).valid);
assert.throws(()=>validateConfig({load:-1,strength:.5}));ok('invalid_configuration_refused',true);
assert.throws(()=>updated(network(),[{index:0,delta:-1}]));ok('negative_update_refused',true);
assert.throws(()=>inspectParent(state.parent,'different','b'.repeat(64)));ok('changed_network_refused',true);
const stale=structuredClone(state);stale.stage=3;stale.accepted=stale.accepted.slice(0,3);stale.successor.source_hash='c'.repeat(64);
await assert.rejects(()=>executeMission(stale,3,{sourceHash:'b'.repeat(64)}),/STALE_SUCCESSOR/);ok('changed_dependency_refused',true);
const badB=structuredClone(stale);badB.stage=2;badB.accepted=badB.accepted.slice(0,2);badB.accepted[1].x[0]+=1;
await assert.rejects(()=>executeMission(badB,2,{sourceHash:'b'.repeat(64)}),/PRIOR_ACCEPTED_RESPONSE_BINDING/);ok('actual_prior_response_required',true);
const low=new Meter(2);assert.throws(()=>matrix(network(),low),/BUDGET/);ok('operation_ceiling_enforced',true);
await mkdir(new URL('./qa/',import.meta.url),{recursive:true});await writeFile(new URL('./qa/CHECKER_QA.json',import.meta.url),JSON.stringify({checks,pass:true,identity:'Independent edge-based checker, same authoring context; no candidate factorization imported.'},null,2));console.log(JSON.stringify(checks));
