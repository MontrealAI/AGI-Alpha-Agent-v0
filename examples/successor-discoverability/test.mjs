// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import {createCompiler,validateProblem,executeProgram,inspectProgram,canonical,snapshot} from './compiler.mjs';
import {digitalFault,mixtureAssay,acquireSynthetic} from './domains.mjs';
const clone=x=>JSON.parse(JSON.stringify(x));
test('declared decision modes retain their intended decisions and defaults',()=>{
 const repair=digitalFault({goal:'repair'}),health=digitalFault({goal:'health'});
 assert.deepEqual(digitalFault(),repair);
 assert.deepEqual(digitalFault({goal:undefined}),repair);
 assert.equal(repair.id,'digital-fault-repair');assert.equal(health.id,'digital-fault-health');
 assert.deepEqual(repair.worlds.map(w=>w.goal),['retain','replace-and','replace-or','replace-nand','replace-stucklow','replace-stuckhigh']);
 assert.deepEqual(health.worlds.map(w=>w.goal),['retain','replace','replace','replace','replace','replace']);
 const disposition=mixtureAssay({goal:'disposition'}),quantify=mixtureAssay({goal:'quantify'});
 assert.deepEqual(mixtureAssay(),disposition);
 assert.deepEqual(mixtureAssay({goal:undefined}),disposition);
 assert.equal(disposition.id,'mixture-assay-disposition');assert.equal(quantify.id,'mixture-assay-quantify');
 assert.deepEqual(disposition.worlds.map(w=>w.goal),['clear','recover-b','recover-b','quarantine-a','quarantine-a','quarantine-a','quarantine-a','quarantine-a','quarantine-a']);
 assert.deepEqual(quantify.worlds.map(w=>w.goal),['a0b0','a0b1','a0b2','a1b0','a1b1','a1b2','a2b0','a2b1','a2b2']);
});
for(const [name,builder,otherMode,message] of [
 ['digitalFault',digitalFault,'disposition','digitalFault goal must be health or repair'],
 ['mixtureAssay',mixtureAssay,'health','mixtureAssay goal must be disposition or quantify']
])test(name+' rejects unsupported decision modes without coercion',()=>{
 let coercions=0;
 const coercible={[Symbol.toPrimitive](){coercions++;return name==='digitalFault'?'health':'quantify';}};
 for(const goal of ['heath','quantfy','',otherMode,'HEALTH','health ',' quantify',null,false,0,[],{},new String('health'),Symbol('health'),coercible]){
  assert.throws(()=>builder({goal}),{name:'TypeError',message});
 }
 assert.equal(coercions,0);
});
test('newly executed acquisitions recover every development decision at both error extremes',async()=>{
 for(const p of [digitalFault(),mixtureAssay()]){
  const r=await createCompiler().compile(p);assert.equal(r.status,'COMPILED');assert.equal(r.certificate.optimalWithinGrammar,true);
  for(const w of p.worlds)for(const errorSign of [-1,0,1]){
   const run=acquireSynthetic(p,r.program,w.id,{nuisanceScale:-123,errorSign});
   assert.equal(executeProgram(p,r.program,run.observations).decision,w.goal);
  }
 }
});
test('compiler builds experiments, rather than selecting a supplied catalogue',async()=>{
 const p=digitalFault(),r=await createCompiler().compile(p);
 assert.ok(r.program.experiments.every(e=>e.weights.filter(Boolean).length>1));
 assert.ok(r.templateCount>r.program.experiments.length);
});
test('cached and fresh construction preserve the complete program and optimum',async()=>{
 const p=digitalFault(),c=createCompiler(),a=await c.compile(p),b=await c.compile(p),d=await createCompiler({strategy:'fresh'}).compile(p);
 assert.equal(canonical(a.program),canonical(b.program));assert.equal(canonical(a.program),canonical(d.program));
 assert.equal(b.libraryHit,true);assert.ok(b.work.used<a.work.used);assert.equal(c.stats().hits,1);
});
test('changed nuisance cannot reuse the old library or certificate',async()=>{
 const c=createCompiler(),p=digitalFault({drift:0}),a=await c.compile(p),q=digitalFault(),b=await c.compile(q);
 assert.equal(b.libraryHit,false);assert.throws(()=>inspectProgram(q,a.program),/scope/);
 const forged=clone(a.program);forged.problemKey=canonical(q);assert.throws(()=>inspectProgram(q,forged),/illegal|certificate/);
});
test('changing the required decision reuses only structure and recomputes targets',async()=>{
 const c=createCompiler(),p=mixtureAssay(),a=await c.compile(p),q=mixtureAssay({goal:'quantify'}),b=await c.compile(q);
 assert.equal(b.libraryHit,true);assert.notEqual(a.program.problemKey,b.program.problemKey);
 assert.equal(b.goalPairCount,36);assert.equal(a.goalPairCount,20);
});
test('noise touching is ambiguous and returns an actual transcript witness',async()=>{
 const p={schema:'discoverability.problem.v1',id:'touching-intervals',channels:[{id:'read',cost:1,noise:1}],
 worlds:[{id:'a',goal:'a',signal:[0]},{id:'b',goal:'b',signal:[2]}],nuisance:[[]],
 grammar:{maxSupport:1,weightLimit:1,maxL1:1},missionBudget:2};
 const r=await createCompiler().compile(p);assert.equal(r.status,'UNIDENTIFIABLE_WITHIN_GRAMMAR');assert.equal(r.witness.observationTwice[0],2);
});
test('small budgets exhaust explicitly without claiming a completed negative',async()=>{
 for(const budget of [1,20,100,1000]){
  const r=await createCompiler().compile(digitalFault(),{budget});
  assert.equal(r.status,'BUDGET_EXHAUSTED');assert.equal(r.certificate.searchComplete,false);assert.ok(r.work.used<=budget);
  assert.equal(Object.values(r.work.counters).reduce((s,x)=>s+x,0),r.work.used);assert.equal(r.program,undefined);
 }
});
test('mission budget is enforced after complete minimum-cost search',async()=>{
 const r=await createCompiler().compile(digitalFault({missionBudget:5}));
 assert.equal(r.status,'OVER_MISSION_BUDGET');assert.equal(r.program.totalCost,6);assert.equal(r.certificate.acceptedForBudget,false);
 assert.throws(()=>inspectProgram(digitalFault({missionBudget:5}),r.program),/cost/);
});
test('cooperative stop propagates, preserving the stopped outcome',async()=>{
 let calls=0;await assert.rejects(createCompiler().compile(digitalFault(),{checkpoint:async()=>{if(++calls===3)throw Error('STOP_REQUESTED');}}),/STOP_REQUESTED/);
 assert.equal(calls,3);
});
test('input mutation after await cannot change the captured problem',async()=>{
 const p=clone(digitalFault()),original=clone(p);
 const r=await createCompiler().compile(p,{checkpoint:async()=>{p.worlds[0].goal='corrupted';}});
 assert.equal(r.program.problemKey,canonical(original));assert.notEqual(r.program.problemKey,canonical(p));
});
test('accessors and unsupported values fail without executing caller getters',()=>{
 let called=0;const p=clone(digitalFault());Object.defineProperty(p.channels[0],'cost',{enumerable:true,get(){called++;return 1;}});
 assert.throws(()=>validateProblem(p),/accessor/);assert.equal(called,0);
 for(const value of [1.5,Infinity,NaN,undefined,()=>1])assert.throws(()=>snapshot({value}));
 const sparse=[];sparse[2]=1;assert.throws(()=>snapshot(sparse),/dense/);
});
test('strict schema and prototype boundaries hold',()=>{
 const p=clone(digitalFault());p.extra=true;assert.throws(()=>validateProblem(p),/fields/);
 const q=clone(digitalFault());q.nuisance[1]=[];assert.throws(()=>validateProblem(q),/matrix/);
 const malicious=JSON.parse('{"__proto__": {}}');assert.throws(()=>snapshot(malicious),/forbidden/);
});
test('forged interval, cost, response and scope are rejected',async()=>{
 const p=digitalFault(),r=await createCompiler().compile(p);
 for(const mutate of [x=>x.experiments[0].radius=0,x=>x.totalCost=0,x=>x.experiments[0].responses[0].center++,x=>x.problemKey='other']){
  const x=clone(r.program);mutate(x);assert.throws(()=>inspectProgram(p,x));
 }
});
test('out-of-model measurements cannot be silently assigned',async()=>{
 const p=mixtureAssay(),r=await createCompiler().compile(p);
 assert.equal(executeProgram(p,r.program,r.program.experiments.map(()=>999999999)).status,'OUT_OF_SCOPE');
});
test('identical signals with conflicting required decisions remain unidentifiable',async()=>{
 const p=clone(digitalFault());p.worlds[1].signal=[...p.worlds[0].signal];
 const r=await createCompiler().compile(p);assert.equal(r.status,'UNIDENTIFIABLE_WITHIN_GRAMMAR');
 assert.notEqual(r.witness.leftGoal,r.witness.rightGoal);
});
test('same decision requires no unnecessary identification',async()=>{
 const p=clone(digitalFault());for(const w of p.worlds)w.goal='retain-for-secondary-check';
 const r=await createCompiler().compile(p);assert.equal(r.program.totalCost,0);assert.equal(r.program.experiments.length,0);
 assert.equal(executeProgram(p,r.program,[]).decision,'retain-for-secondary-check');
});
test('cached structural templates remain isolated from caller edits',async()=>{
 const p=clone(digitalFault()),c=createCompiler(),a=await c.compile(p);a.program.experiments[0].weights.fill(0);
 const b=await c.compile(p);assert.ok(b.program.experiments.every(e=>e.weights.some(Boolean)));
});

test('exact rational readings preserve the continuous-noise contract',async()=>{
 const p={schema:'discoverability.problem.v1',id:'rational-measurement',channels:[{id:'read',cost:1,noise:1}],
 worlds:[{id:'a',goal:'a',signal:[0]},{id:'b',goal:'b',signal:[5]}],nuisance:[[]],
 grammar:{maxSupport:1,weightLimit:1,maxL1:1},missionBudget:2};
 const r=await createCompiler().compile(p);
 assert.equal(executeProgram(p,r.program,[{numerator:1,denominator:2}]).decision,'a');
 assert.equal(executeProgram(p,r.program,[{numerator:9,denominator:2}]).decision,'b');
 assert.throws(()=>executeProgram(p,r.program,[{numerator:1,denominator:0}]),/denominator/);
 assert.throws(()=>executeProgram(p,r.program,[0.5]),/integer/);
 const q=clone(p);q.id=true;assert.throws(()=>validateProblem(q),/identity/);
});
test('structural cache has a fixed eight-library bound',async()=>{
 const c=createCompiler();
 for(let i=1;i<=10;i++)await c.compile(digitalFault({noise:i}));
 assert.equal(c.stats().entries,8);
});

test('acquisition records contain only charged active channels',async()=>{
 const p=digitalFault(),r=await createCompiler().compile(p),run=acquireSynthetic(p,r.program,p.worlds[0].id);
 assert.equal(run.raw.reduce((s,x)=>s+x.chargedCost,0),r.program.totalCost);
 for(let j=0;j<run.raw.length;j++)assert.deepEqual(run.raw[j].activeChannels,r.program.experiments[j].weights.map((w,i)=>w?i:-1).filter(i=>i>=0));
});
test('JSON frame refuses hidden or unsupported transport values',()=>{
 const a={value:1};a[Symbol('extra')]=1;assert.throws(()=>snapshot(a),/non-JSON/);
 const b={value:1};Object.defineProperty(b,'hidden',{value:1});assert.throws(()=>snapshot(b),/non-JSON/);
 assert.throws(()=>snapshot(-0),/integer/);assert.throws(()=>snapshot('\ud800'),/surrogate/);
});

test('same-goal low-budget mission needs no grammar but still pays framing and serialization',async()=>{
 const p=clone(digitalFault());for(const w of p.worlds)w.goal='retain-for-secondary-check';
 for(const strategy of ['cached','fresh']){
  const compiler=createCompiler({strategy}),r=await compiler.compile(p,{budget:2000});
  assert.equal(r.status,'COMPILED');assert.equal(r.program.totalCost,0);assert.deepEqual(r.program.experiments,[]);
  assert.deepEqual(r.certificate,{decisionIdentifiable:true,optimalWithinGrammar:true,searchComplete:true,acceptedForBudget:true});
  assert.equal(r.goalPairCount,0);assert.equal(r.templateCount,0);assert.equal(r.libraryHit,false);
  assert.deepEqual(compiler.stats(),{hits:0,misses:0,entries:0});
  assert.equal(r.work.counters.grammarNodes,undefined);assert.equal(r.work.counters.responseEvaluation,undefined);
  assert.ok(r.work.counters.frame>0);assert.ok(r.work.counters.serializedUnits>0);assert.ok(r.work.used<=2000);
  assert.equal(Object.values(r.work.counters).reduce((s,x)=>s+x,0),r.work.used);
  assert.equal(executeProgram(p,r.program,[]).decision,'retain-for-secondary-check');
  const exhausted=await createCompiler({strategy}).compile(p,{budget:r.work.used-1});
  assert.equal(exhausted.status,'BUDGET_EXHAUSTED');assert.equal(exhausted.program,undefined);
 }
});
