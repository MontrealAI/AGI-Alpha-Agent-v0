// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { createWorkbench, example, run, validate, semanticIdentity, inspectPack } from './engine.mjs';
import { digest } from '../../docs/assets/successor/engine.mjs';
const sourceHash='a'.repeat(64);

test('public and licensed input rights compile into the pinned Jobs vocabulary',async()=>{
  for(const dataClass of ['public','licensed-nonpersonal']){
    const spec=example('public-data');spec.rights.dataClass=dataClass;
    const pack=await run(spec,{sourceHash});
    assert.equal(pack.spec.rights.dataClass,dataClass);
    assert.ok(JSON.stringify(pack.compilation).includes('public-licensed-nonpersonal'));
    assert.equal((await inspectPack(pack)).spec.rights.dataClass,dataClass);
  }
});

test('strong comparator retains an already correct incumbent',async()=>{
  const spec=example();spec.inputs.source=spec.inputs.source.replaceAll(' < ',' <= ');
  const result=await run(spec,{sourceHash});
  assert.equal(result.result.decision,'RETAIN_INCUMBENT');
  assert.equal(result.evaluation.independentProof,false);
});
test('negative numerical result is retained without admission',async()=>{
  const spec=example('numerical');spec.inputs.coefficients=[0,0,0,0,1];spec.inputs.steps=2;spec.inputs.tolerancePpm=0;
  const result=await run(spec,{sourceHash});
  assert.equal(result.result.decision,'REPAIR_REQUIRED');
  assert.equal(result.result.summary.simpson,false);
  assert.equal(result.evaluation.admission,'HOLD');
});
test('public CSV quotation, reconciliation and formula escaping',async()=>{
  const spec=example('public-data');spec.inputs.csv='group,amount\r\n"a,b",4\r\n"a,b",-1\r\n=hostile,2\r\n';
  const result=await run(spec,{sourceHash});
  assert.equal(result.result.summary.total,5);
  assert.equal(result.result.summary.groups,2);
  const csv=result.result.artifacts.find(item=>item.name==='summary.csv').content;
  assert.ok(csv.includes("'=hostile"));
});
test('malformed input and absent review capacity fail before work',()=>{
  const spec=example();spec.reviewMinutes=0;assert.throws(()=>validate(spec),/review/);
  spec.reviewMinutes=10;spec.inputs.source+='\neval("malicious")';assert.throws(()=>validate(spec),/GRAMMAR/);
  const data=example('public-data');data.inputs.csv='group,amount\na,1.4\n';assert.throws(()=>validate(data));
});
test('cancellation and elapsed deadline do not produce accepted evidence',async()=>{
  const controller=new AbortController();controller.abort();
  await assert.rejects(run(example(),{sourceHash,signal:controller.signal}),/CANCELLED/);
  let time=0;await assert.rejects(run(example(),{sourceHash,clock:()=>time+=61000}),/TIME_BUDGET/);
});
test('semantic identity excludes cosmetics, includes rights and inputs',async()=>{
  const spec=example();const before=await semanticIdentity(spec);spec.name='Nouveau Ω';spec.language='fr';
  assert.equal(before,await semanticIdentity(spec));spec.rights.license='Different permission';
  assert.notEqual(before,await semanticIdentity(spec));
});
test('rehashed hostile artifact paths and copied results remain inert',async()=>{
  const pack=await run(example(),{sourceHash});
  const artifact=pack.result.artifacts[0];artifact.name='../escape';
  const {digest:old,...content}=artifact;artifact.digest=await digest('workbench-artifact',content);
  const {integrityDigest,...body}=pack;pack.integrityDigest=await digest('workbench-pack',body);
  await assert.rejects(inspectPack(pack),/ARTIFACT_POLICY/);
});
test('installed extension uses the same binding and refuses unknown imports',async()=>{
  const adapter={manifest:{id:'sum-check',version:1,en:'Sum',fr:'Somme',scope:'Sum two bounded integers',artifact:'sum.json'},
    validate(input){assert.deepEqual(Object.keys(input).sort(),['a','b']);for(const value of Object.values(input))assert.ok(Number.isSafeInteger(value)&&Math.abs(value)<=1000);},
    async execute(input,checkpoint){await checkpoint('adding');return {decision:'REVIEW',summary:{sum:input.a+input.b},evidence:{method:'integer addition'},artifacts:[{name:'sum.json',type:'application/json',content:JSON.stringify({sum:input.a+input.b})}],limits:['Local only']};}};
  const runtime=createWorkbench([adapter]),spec={...example(),family:'sum-check',inputs:{a:2,b:7}};
  const pack=await runtime.run(spec,{sourceHash});assert.equal(pack.result.summary.sum,9);
  assert.equal((await runtime.inspectPack(pack)).activeAuthority.length,0);
  await assert.rejects(inspectPack(pack),/UNSUPPORTED/);
  assert.throws(()=>createWorkbench([adapter,adapter]),/ADAPTER_ID/);
});
