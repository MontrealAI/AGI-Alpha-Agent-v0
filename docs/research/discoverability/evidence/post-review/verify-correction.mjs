// SPDX-License-Identifier: Apache-2.0
// Review-assisted correction check. Reads historical reports; never rewrites them.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createCompiler,canonical,executeProgram} from '../../../../../examples/successor-discoverability/compiler.mjs';
import {digitalFault} from '../../../../../examples/successor-discoverability/domains.mjs';
import {conventionalStatic,verifyProgramReference} from '../../../../../examples/successor-discoverability/reference.mjs';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
const read=relative=>readFile(new URL(relative,import.meta.url));
const frozenBytes=await read('../frozen-source/compiler.mjs.txt');
assert.equal(sha(frozenBytes),'746853fe817f7f98e4e41a6534c87f1949acc150e9742d935637d56b6e03f898');
const frozen=await import('data:text/javascript;base64,'+frozenBytes.toString('base64'));
const independentBytes=await read('../independent-reference-report.json');
const heldoutBytes=await read('../heldout-first-results.json');
const independent=JSON.parse(independentBytes),heldout=JSON.parse(heldoutBytes);
const report={
 schema:'discoverability.post-review-compiler-check.v1',
 observedAtUtc:new Date().toISOString(),node:process.version,
 mode:'REVIEW_ASSISTED_CORRECTION_CHECK',
 frozenCompilerSha256:sha(frozenBytes),
 correctedCompilerSha256:sha(await read('../../../../../examples/successor-discoverability/compiler.mjs')),
 independentReferenceSha256:sha(await read('../../../../../examples/successor-discoverability/reference.mjs')),
 historicalInputs:{independentReferenceReportSha256:sha(independentBytes),heldoutFirstResultsSha256:sha(heldoutBytes)},
 cases:[],
 scope:'Checks a post-review code correction against already public inputs and unchanged numerical reference. This is not new withholding, autonomous RSI, institutional acceptance, a load campaign or an EVM run.'
};

const problem=structuredClone(digitalFault());
for(const world of problem.worlds)world.goal='retain-for-secondary-check';
const budget=2000;
const before=await frozen.createCompiler().compile(problem,{budget});
const after=await createCompiler().compile(problem,{budget});
assert.equal(before.status,'BUDGET_EXHAUSTED');
assert.equal(before.program,undefined);
assert.equal(after.status,'COMPILED');
assert.equal(after.program.totalCost,0);
assert.deepEqual(after.program.experiments,[]);
assert.equal(executeProgram(problem,after.program,[]).decision,'retain-for-secondary-check');
assert.equal(verifyProgramReference(problem,after.program).valid,true);
assert.equal(conventionalStatic(problem).minimumCost,0);
report.regression={problem,budget,before,after,independentMinimumCost:0,passed:true};

const cases=[
 ...independent.developmentCases.map(x=>({origin:'historical-development',...x})),
 ...independent.randomCases.map(x=>({origin:'historical-random',...x})),
 ...heldout.cases.map(x=>({origin:'historical-heldout-now-public',problem:x.problem,status:x.production.status,productionProgram:x.production.program??null}))
];
let exactNontrivial=0,sameGoal=0,independentProgramChecks=0;
for(const entry of cases){
 const p=entry.problem,oldResult=await frozen.createCompiler().compile(p),newResult=await createCompiler().compile(p);
 const decisionsDiffer=new Set(p.worlds.map(w=>w.goal)).size>1;
 assert.equal(newResult.status,entry.status);
 assert.equal(canonical(newResult.program??null),canonical(entry.productionProgram??null));
 if(decisionsDiffer){
  const {compilerVersion:oldVersion,...oldComparable}=oldResult;
  const {compilerVersion:newVersion,...newComparable}=newResult;
  assert.equal(oldVersion,'1.0.0-experimental');assert.equal(newVersion,'1.0.1-experimental');
  assert.equal(canonical(newComparable),canonical(oldComparable));
  exactNontrivial++;
 }else{
  assert.equal(canonical(newResult.program),canonical(oldResult.program));
  assert.equal(newResult.program.totalCost,0);
  assert.equal(newResult.templateCount,0);
  sameGoal++;
 }
 if(newResult.program){
  assert.equal(verifyProgramReference(p,newResult.program,{requireBudget:newResult.status==='COMPILED'}).valid,true);
  independentProgramChecks++;
 }
 report.cases.push({origin:entry.origin,problemId:p.id,problemSha256:sha(canonical(p)),status:newResult.status,
  decisionsDiffer,completeResultUnchangedExceptCompilerVersion:decisionsDiffer,programMatchesHistoricalRecord:true,
  oldResultSha256:sha(canonical(oldResult)),newResultSha256:sha(canonical(newResult)),
  oldWork:oldResult.work.used,newWork:newResult.work.used,
  independentProgramAccepted:newResult.program?true:null});
}
assert.equal(sha(await read('../frozen-source/compiler.mjs.txt')),report.frozenCompilerSha256);
assert.equal(sha(await read('../independent-reference-report.json')),report.historicalInputs.independentReferenceReportSha256);
assert.equal(sha(await read('../heldout-first-results.json')),report.historicalInputs.heldoutFirstResultsSha256);
report.summary={cases:cases.length,exactNontrivial,sameGoal,independentProgramChecks,historicalInputsUnchanged:true,passed:true};
console.log(JSON.stringify(report,null,2));
