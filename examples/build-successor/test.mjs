// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { buildPack, compilePlan, missionFor } from './model.mjs';
import { compileJobs, verifyWorkOrderSeal } from './vendor/agijobs/compiler.mjs';
const engineSourceHash=createHash('sha256').update(fs.readFileSync(new URL('../../docs/assets/successor/engine.mjs',import.meta.url))).digest('hex');

test('paired engine and compiler produce bounded draft work, never proof or authority',async()=>{
  const pack=await buildPack({engineSourceHash,events:256,budget:'1'});
  assert.equal(pack.discovery.attempts.length,4);
  assert.equal(pack.evaluation.cases.length,6);
  assert.equal(pack.evaluation.correctness,true);
  assert.equal(pack.frozen.release_hash,pack.evaluation.release_hash);
  assert.equal(pack.compilation.graph.nodes.length,21);
  assert.ok(pack.compilation.coverage.every(c=>c.status==='PLANNED_NOT_ACCEPTED'));
  assert.ok(pack.compilation.graph.nodes.every(j=>j.state==='DRAFT' && j.signatureStatus==='UNSIGNED_COMMITMENT'));
  assert.ok((await Promise.all(pack.compilation.graph.nodes.map(verifyWorkOrderSeal))).every(Boolean));
  assert.ok(BigInt(pack.compilation.budgetReservations.reservedBaseUnits)<=10n**18n);
  assert.equal(pack.admission.decision,'HOLD');assert.equal(pack.admission.independentProof,false);
  assert.deepEqual(pack.admission.authority,[]);assert.equal(pack.settlement.spentBaseUnits,'0');
});
test('compiler refuses collapsed reviewers and changed sealed terms',async()=>{
  const mission=missionFor();mission.roles.verifier=mission.roles.producer;
  await assert.rejects(compileJobs(mission),e=>e.code==='ROLE_CONFLICT');
  const plan=await compilePlan();const changed={...plan.graph.nodes[0],objective:'Changed after sealing'};
  assert.equal(await verifyWorkOrderSeal(changed),false);
});
test('invalid amounts and missing source identity fail before a build',async()=>{
  for(const budget of ['-1','0','1.5','1e3','1000001',' 21'])assert.throws(()=>missionFor({budget}));
  assert.throws(()=>missionFor({name:' '}));
  await assert.rejects(buildPack({events:256}),/source identity/);
});
test('cancellation cannot return a completed candidate',async()=>{
  const controller=new AbortController();controller.abort();
  await assert.rejects(buildPack({engineSourceHash,events:256},{signal:controller.signal}),{name:'AbortError'});
});
test('the pinned Jobs modules remain unchanged and attributable',()=>{
  const base=new URL('./vendor/agijobs/',import.meta.url), record=JSON.parse(fs.readFileSync(new URL('provenance.json',base),'utf8'));
  for(const file of record.files)assert.equal(createHash('sha256').update(fs.readFileSync(new URL(file.path.split('/').at(-1),base))).digest('hex'),file.sha256);
});
