// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import os from 'node:os';
import {performance} from 'node:perf_hooks';
import {createCompiler,executeProgram,inspectProgram,canonical,validateProblem} from './compiler.mjs';
import {digitalFault,mixtureAssay} from './domains.mjs';
import {referenceCatalogue,conventionalStatic,conventionalAdaptive,verifyProgramReference,decodeReference} from './reference.mjs';

const sourceCommit='ece8f2aa1480ec7b50f633b7893a11c3f22de894';
const report={schema:'discoverability.independent-review.v1',sourceCommit,
 observedAt:new Date().toISOString(),environment:{node:process.version,platform:process.platform,arch:process.arch,
 cpu:os.cpus()[0].model,logicalCpus:os.cpus().length},sourceHashes:{},developmentCases:[],randomCases:[],regressions:[],claims:[]};
for(const f of ['compiler.mjs','domains.mjs','reference.mjs','review.mjs'])report.sourceHashes[f]=createHash('sha256').update(await readFile(new URL(f,import.meta.url))).digest('hex');
const sha=x=>createHash('sha256').update(canonical(x)).digest('hex');
const clone=x=>structuredClone(x);
const regress=(name,fn)=>{fn();report.regressions.push({name,passed:true});};
async function compare(problem,kind) {
 const start=performance.now(),compiler=createCompiler({strategy:'fresh'}),actual=await compiler.compile(problem);
 const compiledMs=performance.now()-start,refStart=performance.now(),ref=conventionalStatic(problem),
 adaptive=conventionalAdaptive(problem),referenceMs=performance.now()-refStart;
 assert.notEqual(ref.status,'REFERENCE_BUDGET_EXHAUSTED');assert.notEqual(adaptive.status,'REFERENCE_BUDGET_EXHAUSTED');
 assert.equal(actual.status,ref.status);
 const record={problem,problemSha256:sha(problem),status:actual.status,templateCount:actual.templateCount,
 productionLogicalWork:actual.work,referenceLogicalWork:ref.work,adaptiveLogicalWork:adaptive.work,
 timingMs:{compiler:compiledMs,staticAndAdaptiveReferences:referenceMs},
 staticMinimum:ref.minimumCost??null,adaptiveWorst:adaptive.worstAcquisitionCost??null,
 subsetsChecked:ref.subsetsChecked??null,adaptiveStates:adaptive.states,productionProgram:actual.program??null};
 if(actual.program) {
   assert.equal(actual.program.totalCost,ref.minimumCost);
   assert.ok(adaptive.worstAcquisitionCost<=ref.minimumCost);
   assert.equal(verifyProgramReference(problem,actual.program,{requireBudget:actual.status==='COMPILED'}).valid,true);
   if(actual.status==='COMPILED')for(let wi=0;wi<problem.worlds.length;wi++) {
     const ys=actual.program.experiments.map(e=>({numerator:2*e.responses[wi].center+e.radius,denominator:2}));
     assert.deepEqual(executeProgram(problem,actual.program,ys),decodeReference(problem,actual.program,ys));
     assert.equal(decodeReference(problem,actual.program,ys).decision,problem.worlds[wi].goal);
   }
 } else {
   assert.equal(actual.status,'UNIDENTIFIABLE_WITHIN_GRAMMAR');
   const complete=referenceCatalogue(problem);assert.equal(complete.status,'COMPLETE');
   assert.equal(actual.experiments.length,complete.experiments.length);
   assert.equal(canonical(actual.experiments),canonical(complete.experiments));
   const {left,right,observationTwice}=actual.witness;
   const i=problem.worlds.findIndex(w=>w.id===left),j=problem.worlds.findIndex(w=>w.id===right);
   assert.notEqual(problem.worlds[i].goal,problem.worlds[j].goal);
   for(let k=0;k<actual.experiments.length;k++)for(const wi of [i,j]) {
     const e=actual.experiments[k];assert.ok(Math.abs(observationTwice[k]-2*e.responses[wi].center)<=2*e.radius);
   }
   record.witness=actual.witness;
 }
 report[kind].push(record);return actual;
}
for(const problem of [digitalFault(),digitalFault({goal:'health'}),mixtureAssay(),mixtureAssay({goal:'quantify'})])await compare(problem,'developmentCases');
let seed=0x51a7c0de;
const rnd=bound=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%bound;};
for(let index=0;index<120;index++){
 const n=2+index%2,worlds=2+rnd(5),nuisanceMode=index%4;
 const p={schema:'discoverability.problem.v1',id:'random-'+index,channels:Array.from({length:n},(_,i)=>({id:'c'+i,cost:1+rnd(7),noise:rnd(3)})),
 worlds:Array.from({length:worlds},(_,i)=>({id:'w'+i,goal:'g'+rnd(3),signal:Array.from({length:n},()=>rnd(17)-8)})),
 nuisance:Array.from({length:n},(_,i)=>nuisanceMode===0?[]:nuisanceMode===1?[1]:nuisanceMode===2?[i+1]:[1,i]),
 grammar:{maxSupport:Math.min(n,2),weightLimit:1,maxL1:2},missionBudget:1+rnd(30)};
 await compare(p,'randomCases');
}
const simple=(centers,noise=0)=>({schema:'discoverability.problem.v1',id:'interval-check',channels:[{id:'signal',cost:1,noise}],
 worlds:centers.map((x,i)=>({id:'w'+i,goal:'g'+i,signal:[x]})),nuisance:[[]],grammar:{maxSupport:1,weightLimit:1,maxL1:1},missionBudget:10});
const touching=await createCompiler().compile(simple([0,2],1));
regress('Closed noise intervals that touch are not robustly distinguishable',()=>{assert.equal(touching.status,'UNIDENTIFIABLE_WITHIN_GRAMMAR');assert.deepEqual(touching.witness.observationTwice,[2]);});
const separatedProblem=simple([0,3],1),separated=await createCompiler().compile(separatedProblem);
regress('A strict gap permits exact rational observations',()=>{assert.equal(separated.status,'COMPILED');const y=[{numerator:1,denominator:2}];
 assert.equal(executeProgram(separatedProblem,separated.program,y).decision,'g0');assert.deepEqual(executeProgram(separatedProblem,separated.program,y),decodeReference(separatedProblem,separated.program,y));});
regress('Inclusive bounds and an open out-of-scope gap remain exact',()=>{for(const y of [-1,1])assert.equal(executeProgram(separatedProblem,separated.program,[y]).decision,'g0');
 assert.equal(executeProgram(separatedProblem,separated.program,[{numerator:3,denominator:2}]).status,'OUT_OF_SCOPE');});
regress('Boolean identity, negative zero, non-JSON properties and malformed rational observations are refused',()=>{
 for(const bad of [{...separatedProblem,id:true},{...separatedProblem,missionBudget:-0}])assert.throws(()=>validateProblem(bad));
 const symbol=clone(separatedProblem);symbol[Symbol('x')]=1;assert.throws(()=>validateProblem(symbol));
 const hidden=clone(separatedProblem);Object.defineProperty(hidden,'x',{value:1});assert.throws(()=>validateProblem(hidden));
 for(const y of [0.5,{numerator:1,denominator:0},{numerator:1,denominator:1000000001},{numerator:true,denominator:2}])assert.throws(()=>executeProgram(separatedProblem,separated.program,[y]));
});
regress('Forged scope, radius, responses, cost and non-null weights fail independent acceptance',()=>{
 const changes=[p=>{p.problemKey='tampered';},p=>{p.experiments[0].radius++;},p=>{p.experiments[0].responses[0].center++;},
 p=>{p.totalCost++;},p=>{p.experiments[0].weights[0]=0;}];
 for(const change of changes){const p=clone(separated.program);change(p);assert.equal(verifyProgramReference(separatedProblem,p).valid,false);assert.throws(()=>inspectProgram(separatedProblem,p));}
});
const emptyGrammar={...simple([0,3]),nuisance:[[1]]};
const empty=await createCompiler().compile(emptyGrammar);
regress('An empty allowed grammar is an explicit complete negative result',()=>{assert.equal(empty.status,'UNIDENTIFIABLE_WITHIN_GRAMMAR');assert.equal(empty.templateCount,0);assert.deepEqual(empty.witness.observationTwice,[]);});
const sameGoal=simple([0,0]);sameGoal.worlds[1].goal='g0';
const trivial=await createCompiler().compile(sameGoal);
regress('An objective already determined needs no experiment',()=>{assert.equal(trivial.status,'COMPILED');assert.equal(trivial.program.totalCost,0);assert.deepEqual(trivial.program.experiments,[]);assert.equal(executeProgram(sameGoal,trivial.program,[]).decision,'g0');});
const exhausted=await createCompiler().compile(digitalFault(),{budget:1});
regress('Exhaustion is not an impossibility certificate',()=>{assert.equal(exhausted.status,'BUDGET_EXHAUSTED');assert.equal(exhausted.certificate.searchComplete,false);assert.equal(exhausted.program,undefined);});
const shared=createCompiler(),first=await shared.compile(digitalFault()),second=await shared.compile(digitalFault({goal:'health'})),changed=await shared.compile(digitalFault({drift:0}));
regress('A structural cache hit recomputes objectives, while changed nuisance invalidates its boundary',()=>{assert.equal(first.libraryHit,false);assert.equal(second.libraryHit,true);assert.equal(changed.libraryHit,false);
 assert.equal(verifyProgramReference(digitalFault({goal:'health'}),second.program).valid,true);
 assert.equal(second.program.totalCost,conventionalStatic(digitalFault({goal:'health'})).minimumCost);});
const adaptiveProblem={schema:'discoverability.problem.v1',id:'adaptive-tree-control',
 channels:[0,1,2].map(i=>({id:'c'+i,cost:1,noise:0})),
 worlds:[[0,0,0],[0,1,0],[1,0,0],[1,0,1]].map((signal,i)=>({id:'w'+i,goal:'g'+i,signal})),
 nuisance:[[],[],[]],grammar:{maxSupport:1,weightLimit:1,maxL1:1},missionBudget:10};
const adaptiveStatic=conventionalStatic(adaptiveProblem),adaptive=conventionalAdaptive(adaptiveProblem);
regress('Competent centralized adaptive policy can strictly beat the static compiler',()=>{assert.equal(adaptiveStatic.minimumCost,3);assert.equal(adaptive.worstAcquisitionCost,2);});
report.adaptiveAdvantageControl={problem:adaptiveProblem,static:adaptiveStatic,adaptive};
report.cacheControl={coldWork:first.work,warmWork:second.work,changedStructureWork:changed.work,stats:shared.stats()};
report.claims=[
 'Current tested compiler static optimum agrees with complete independent Cartesian grammar and direct subset enumeration on all 124 development/random cases.',
 'The two supplied development families tie competent static and adaptive acquisition baselines; no acquisition advantage is established.',
 'The explicit adaptive control beats the static compiler 2 versus 3 acquisition units.',
 'Reference and compiler work meters count different logical operations. Their values are not a runtime speedup claim.',
 'The reviewer is a separately delegated agent using no producer imports in reference.mjs; this is not institutional or arm\'s-length external review.',
 'These are finite synthetic model tests, not held-out successor acceptance, physical validation, realized revenue or autonomous RSI.',
 'No material mathematical correctness finding remains at the reviewed source within the bounded model. Model adequacy, authorization and deployment remain outside this review.'
];
report.summary={randomCases:report.randomCases.length,developmentCases:report.developmentCases.length,regressions:report.regressions.length,
 statusCounts:report.randomCases.reduce((a,x)=>(a[x.status]=(a[x.status]||0)+1,a),{}),passed:true};
await writeFile(new URL('review-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({sourceCommit,sourceHashes:report.sourceHashes,summary:report.summary,
 development:report.developmentCases.map(x=>({id:x.problem.id,goal:x.problem.worlds[0].goal,status:x.status,static:x.staticMinimum,adaptive:x.adaptiveWorst,templates:x.templateCount,productionWork:x.productionLogicalWork.used})),
 regressions:report.regressions,cache:report.cacheControl,adaptiveControl:{static:adaptiveStatic.minimumCost,adaptive:adaptive.worstAcquisitionCost}},null,2));

