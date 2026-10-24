// SPDX-License-Identifier: Apache-2.0
// Later post-freeze verification. Enumerates cells; does not modify frozen source.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {executeProgram,inspectProgram} from './compiler.mjs';
import {verifyProgramReference} from './reference.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const expectedHashes={
 'compiler.mjs':'746853fe817f7f98e4e41a6534c87f1949acc150e9742d935637d56b6e03f898',
 'reference.mjs':'ee44edad7224cdb58cc4aa0e132416efb2904d95eebd96af93fefcd0082a1812',
 'heldout.mjs':'815f9db960f0e634d371c8aa0ddae5576ee45e73f0ad2ea7cc9cb85970801022'
};
const firstRaw=await readFile(new URL('heldout-first-results.json',import.meta.url));
const first=JSON.parse(firstRaw);
const report={
 schema:'discoverability.heldout-observation-cells.v1',
 campaignId:'successor-discoverability-20261022',
 chronology:'Later verification of preserved first-result programs; same-team verification, not independently preregistered.',
 firstResultsObservedAt:first.observedAt,
 firstResultsSha256:hash(firstRaw),
 observedAt:new Date().toISOString(),
 environment:{node:process.version,platform:process.platform,arch:process.arch},
 sourceHashes:{},cases:[]
};
for(const [f,expected] of Object.entries(expectedHashes)){
 const observed=hash(await readFile(new URL(f,import.meta.url)));
 assert.equal(observed,expected);report.sourceHashes[f]=observed;
}
report.sourceHashes['observation-cells.mjs']=hash(await readFile(new URL('observation-cells.mjs',import.meta.url)));
const abs=x=>x<0n?-x:x;
function derive(p,weights){
 let radius=0n;
 for(let i=0;i<weights.length;i++)radius+=abs(BigInt(weights[i]))*BigInt(p.channels[i].noise);
 const centers=p.worlds.map(world=>{
  let sum=0n;for(let i=0;i<weights.length;i++)sum+=BigInt(weights[i])*BigInt(world.signal[i]);return sum;
 });
 return {radius,centers};
}
function partition(e){
 const endpoints=[...new Set(e.centers.flatMap(c=>[(c-e.radius).toString(),(c+e.radius).toString()]))].map(BigInt).sort((a,b)=>a<b?-1:a>b?1:0);
 const cells=[{kind:'left-exterior',lower:null,upper:endpoints[0].toString(),twice:(2n*(endpoints[0]-1n)).toString()}];
 for(let i=0;i<endpoints.length;i++){
  cells.push({kind:'point',lower:endpoints[i].toString(),upper:endpoints[i].toString(),twice:(2n*endpoints[i]).toString()});
  if(i+1<endpoints.length)cells.push({kind:'open-interval',lower:endpoints[i].toString(),upper:endpoints[i+1].toString(),twice:(endpoints[i]+endpoints[i+1]).toString()});
 }
 cells.push({kind:'right-exterior',lower:endpoints.at(-1).toString(),upper:null,twice:(2n*(endpoints.at(-1)+1n)).toString()});
 return cells;
}
function independentDecision(p,derived,ys2){
 const compatible=[];
 for(let wi=0;wi<p.worlds.length;wi++){
  let included=true;
  for(let ei=0;ei<derived.length;ei++)if(abs(ys2[ei]-2n*derived[ei].centers[wi])>2n*derived[ei].radius){included=false;break;}
  if(included)compatible.push(p.worlds[wi]);
 }
 const goals=[...new Set(compatible.map(w=>w.goal))];
 return {status:goals.length===1?'DECIDED':goals.length===0?'OUT_OF_SCOPE':'AMBIGUOUS',
 decision:goals.length===1?goals[0]:null,compatibleWorlds:compatible.map(w=>w.id)};
}
const began=performance.now();
for(const entry of first.cases){
 if(entry.production.status!=='COMPILED')continue;
 const {problem:p}=entry,program=entry.production.program;
 assert.equal(verifyProgramReference(p,program).valid,true);
 const derived=program.experiments.map(e=>derive(p,e.weights)),axes=derived.map(partition);
 const raw=[],counts={cells:0,DECIDED:0,OUT_OF_SCOPE:0,AMBIGUOUS:0,mismatches:0};
 const indices=[],ys2=[];
 function visit(axis){
  if(axis<axes.length){
   for(let j=0;j<axes[axis].length;j++){
    indices.push(j);ys2.push(BigInt(axes[axis][j].twice));visit(axis+1);indices.pop();ys2.pop();
   }return;
  }
  const observations=ys2.map(x=>({numerator:Number(x),denominator:2}));
  for(const o of observations)assert.ok(Number.isSafeInteger(o.numerator));
  const expected=independentDecision(p,derived,ys2);
  const actual=executeProgram(p,program,observations);
  const matched=JSON.stringify(expected)===JSON.stringify(actual);
  counts.cells++;counts[expected.status]++;if(!matched)counts.mismatches++;
  raw.push({cellIndices:[...indices],observations,expected,actual,matched});
 }
 visit(0);
 assert.equal(counts.cells,axes.reduce((n,a)=>n*a.length,1));
 assert.equal(counts.mismatches,0);assert.equal(counts.AMBIGUOUS,0);assert.ok(counts.OUT_OF_SCOPE>0);
 report.cases.push({problemId:p.id,problem:p,program,axes,axisCellCounts:axes.map(a=>a.length),counts,raw,passed:true});
}
assert.equal(report.cases.length,3);
const route=first.cases[0],repair=first.cases[1],quadratic=first.cases[2],extended=first.cases[3];
const stale=[];
for(const entry of [repair,quadratic,extended]){
 let threw=false,message=null;
 try{inspectProgram(entry.problem,route.production.program);}catch(e){threw=true;message=e.message;}
 assert.equal(threw,true);
 const independent=verifyProgramReference(entry.problem,route.production.program);
 assert.equal(independent.valid,false);
 stale.push({newProblemId:entry.problem.id,producerRefused:threw,reason:message,independent});
}
report.staleParentScope=stale;
report.elapsedMilliseconds=performance.now()-began;
report.summary={programs:report.cases.length,cells:report.cases.reduce((n,c)=>n+c.counts.cells,0),
 decided:report.cases.reduce((n,c)=>n+c.counts.DECIDED,0),
 outOfScope:report.cases.reduce((n,c)=>n+c.counts.OUT_OF_SCOPE,0),
 ambiguous:report.cases.reduce((n,c)=>n+c.counts.AMBIGUOUS,0),
 mismatches:report.cases.reduce((n,c)=>n+c.counts.mismatches,0),staleParentRefusals:stale.length,passed:true};
report.scope=[
 'Each axis is partitioned at all independently recomputed closed interval endpoints, including point cells, every open interval, and both exterior rays.',
 'Exact integer or half-integer representatives cover all cells because interval membership is constant within each open cell and checked separately at every boundary.',
 'The Cartesian product covers complete transcripts for the declared fresh independent continuous bounded-error model.',
 'The observation API accepts safe rational observations; this finite partition checks its exact arithmetic on representatives and, together with the interval-membership rule, establishes the stated model property.',
 'No physical graph, off-model fault, external independence, customer value or promotion authority is established.',
 'The original first results and frozen compiler/reference/family are unchanged.'
];
await writeFile(new URL('observation-cells-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({observedAt:report.observedAt,sourceHashes:report.sourceHashes,summary:report.summary,
 cases:report.cases.map(c=>({id:c.problemId,axes:c.axisCellCounts,counts:c.counts})),
 firstResultsSha256:report.firstResultsSha256,elapsedMilliseconds:report.elapsedMilliseconds},null,2));

