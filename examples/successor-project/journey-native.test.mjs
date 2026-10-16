// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {canonical} from './journey-codec.mjs';
import {exactDigest} from './engine.mjs';
import {fixture,freshCycle} from './journey-fixture.mjs';
import {createJourney,inspectJourney,appendJourney,agialphaBaseUnits,agialphaTokens} from './journey.mjs';
async function reseal(value){delete value.sha256;return canonical({...value,sha256:await exactDigest(canonical(value))});}
test('native project→fresh changed cycle keeps rejected history and resets current external bindings',async()=>{
  const original=await fixture(),raw=await createJourney(canonical(original)),next=await freshCycle(original);
  const joined=await appendJourney(raw,'alpha-cycle',canonical(next)),read=await inspectJourney(joined);
  assert.deepEqual(read.project.cycles[0],original.cycles[0]);
  assert.equal(JSON.parse(read.project.cycles[0].records.at(-1).bytes).review.decision,'rejected');
  const record=JSON.parse(read.project.cycles.at(-1).records.at(-1).bytes);
  assert.equal(record.result.pack.result.summary.total,12);assert.equal(record.review,null);
  assert.equal(read.project.projectId,original.projectId);assert.equal(read.fleet,null);assert.equal(read.latestTransfer,null);
  assert.equal(read.journey.authority,'none');assert.equal(read.journey.settlement,'not-connected');
});
test('resealed authority, wrong project, rewritten event and ambiguous imports fail closed',async()=>{
  const project=await fixture(),raw=await createJourney(canonical(project));
  for(const change of [v=>v.authority='approved',v=>v.projectId='other',v=>v.history[0].kind='fleet-return',v=>v.native.raw+=' ']){
    const v=JSON.parse(raw);change(v);await assert.rejects(inspectJourney(await reseal(v)));
  }
  await assert.rejects(inspectJourney('{"schema":"a","schema":"b"}'),/Duplicate/);
  await assert.rejects(inspectJourney('\ufeff'+raw),/Expected/);
  await assert.rejects(inspectJourney(' '.repeat(16_000_001)),/16 MB/);
  await assert.rejects(appendJourney(raw,'alpha-cycle',canonical(project)),/PROJECT_LINEAGE/);
  const other=await freshCycle(await fixture('en','other'));
  await assert.rejects(appendJourney(raw,'alpha-cycle',canonical(other)),/CROSS_PROJECT/);
});
test('exact token prices retain every base unit and reject rounding or notation changes',()=>{
  assert.equal(agialphaBaseUnits('10'),'10000000000000000000');
  assert.equal(agialphaTokens('2000000000000000007'),'2.000000000000000007');
  assert.equal(agialphaBaseUnits('0.000000000000000007'),'7');
  assert.equal(agialphaBaseUnits('1000000'),'1000000000000000000000000');
  for(const text of ['0','0.000000000000000006','0.0000000000000000007','1e3','+1','01','1.','1000000.000000000000000001',' 1','NaN'])assert.throws(()=>agialphaBaseUnits(text));
});
