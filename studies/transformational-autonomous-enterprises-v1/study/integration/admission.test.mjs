// SPDX-License-Identifier: Apache-2.0
// External scientific admission boundary, using public development cases only.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { checkArtifact } from '../evaluation/checker.mjs';
import { solve } from '../enterprise/compiler.mjs';
import { diamondImpact, diamondBOM } from '../enterprise/development-cases.mjs';
import { createMissionDelivery, prepareDelivery } from './mission-delivery.mjs';
import { externalAdmission } from './artifact.mjs';

const criteria = readFileSync(new URL('../evaluation/criteria.json', import.meta.url), 'utf8');
const check = externalAdmission(checkArtifact, criteria);
test('wrong mission algebra is denied before loading any repository bridge', async () => {
  const wrong = solve(diamondImpact, { variant: 'wrong-algebra' });
  const receipt = await check(diamondImpact, wrong);
  assert.equal(receipt.accepted, false); assert.equal(receipt.proof.accepted, false);
  const delivery = createMissionDelivery({ repositories: {}, check });
  await assert.rejects(delivery.deliver(diamondImpact, wrong), { code: 'SEMANTIC_ADMISSION' });
  assert.equal(delivery.statistics().completed, 0); assert.equal(delivery.statistics().failed, 1);
});
test('canonical input, output, capability, and CSV bindings reject altered data', () => {
  const result = solve(diamondBOM); assert.equal(prepareDelivery(diamondBOM, result).total, '74');
  assert.throws(() => prepareDelivery({ ...diamondBOM, missionId: 'changed' }, result), { code: 'MISSION_IDENTITY' });
  assert.throws(() => prepareDelivery(diamondBOM, { ...result, outputHash: '0'.repeat(64) }), { code: 'OUTPUT_BINDING' });
  assert.throws(() => prepareDelivery(diamondBOM, { ...result, csv: `${result.csv}n,1\n` }), { code: 'CSV_BINDING' });
  assert.throws(() => prepareDelivery(diamondBOM, { ...result, capability: { ...result.capability, id: '0'.repeat(64) } }), { code: 'CAPABILITY_BINDING' });
});
test('oversized output and forged candidate permissions fail before scientific or native execution', () => {
  const result = solve(diamondBOM);
  assert.throws(() => prepareDelivery(diamondBOM, { ...result, authority: ['transfer'] }), { code: 'CANDIDATE_AUTHORITY' });
  const oversized = solve({ ...diamondBOM, seeds: [{ node: 'assembly', amount: 1000000 }] });
  assert.throws(() => prepareDelivery({ ...diamondBOM, seeds: [{ node: 'assembly', amount: 1000000 }] }, oversized), { code: 'NOT_DELIVERABLE' });
});
test('an already interrupted delivery cannot obtain scientific admission', async () => {
  let calls = 0;
  const delivery = createMissionDelivery({ repositories: {}, check: () => { calls++; throw Error('must not be called'); } });
  await assert.rejects(delivery.deliver(diamondBOM, solve(diamondBOM), { signal: { aborted: true } }), { code: 'INTERRUPTED' });
  assert.equal(calls, 0); assert.equal(delivery.statistics().active, 0); assert.equal(delivery.statistics().failed, 1);
});

test('concurrent identical attempts share one admission and rejected attempts can be retried', async () => {
  let calls = 0;
  const wrong = solve(diamondImpact, { variant: 'wrong-algebra' });
  const delivery = createMissionDelivery({ repositories: {}, check: async (...args) => { calls++; await new Promise(setImmediate); return check(...args); } });
  const attempts = await Promise.allSettled([delivery.deliver(diamondImpact, wrong), delivery.deliver(diamondImpact, wrong)]);
  assert.ok(attempts.every(item => item.status === 'rejected' && item.reason.code === 'SEMANTIC_ADMISSION'));
  assert.equal(calls, 1); assert.equal(delivery.statistics().idempotentReuses, 1);
  await assert.rejects(delivery.deliver(diamondImpact, wrong), { code: 'SEMANTIC_ADMISSION' });
  assert.equal(calls, 2); assert.equal(delivery.statistics().failed, 2);
});

test('queue ceiling and concurrency limits hold before any native execution', async () => {
  const releases = []; let checks = 0;
  const delivery = createMissionDelivery({ repositories: {}, concurrency: 1, maxQueued: 1, check: async () => { checks++; await new Promise(resolve => releases.push(resolve)); return { accepted: false, proof: { accepted: false } }; } });
  const create = n => { const mission = { ...diamondBOM, missionId: `queue-control-${n}` }; return { mission, result: solve(mission) }; };
  const one = create(1), two = create(2), three = create(3);
  const first = delivery.deliver(one.mission, one.result); const firstDenied = assert.rejects(first, { code: 'SEMANTIC_ADMISSION' });
  await new Promise(setImmediate);
  const second = delivery.deliver(two.mission, two.result); const secondDenied = assert.rejects(second, { code: 'SEMANTIC_ADMISSION' });
  await assert.rejects(delivery.deliver(three.mission, three.result), { code: 'QUEUE_FULL' });
  assert.equal(checks, 1); assert.equal(delivery.statistics().queued, 1); assert.equal(delivery.statistics().maxObserved, 1);
  releases.shift()(); await firstDenied; await new Promise(setImmediate);
  assert.equal(checks, 2); releases.shift()(); await secondDenied;
  assert.equal(delivery.statistics().active, 0); assert.equal(delivery.statistics().queued, 0); assert.equal(delivery.statistics().failed, 3);
});

test('queued interruption suppresses later admission and returns its queue slot', async () => {
  let release; let checks = 0; const controller = new AbortController();
  const delivery = createMissionDelivery({ repositories: {}, concurrency: 1, check: async () => { checks++; await new Promise(resolve => { release = resolve; }); return { accepted: false, proof: { accepted: false } }; } });
  const first = delivery.deliver(diamondBOM, solve(diamondBOM)); const firstDenied = assert.rejects(first, { code: 'SEMANTIC_ADMISSION' });
  await new Promise(setImmediate);
  const other = { ...diamondBOM, missionId: 'queued-interruption' };
  const second = delivery.deliver(other, solve(other), { signal: controller.signal }); const secondDenied = assert.rejects(second, { code: 'INTERRUPTED' });
  controller.abort(); release(); await Promise.all([firstDenied, secondDenied]);
  assert.equal(checks, 1); assert.equal(delivery.statistics().active, 0); assert.equal(delivery.statistics().queued, 0);
});

test('a valid semantic receipt rebound to a different input is refused before native execution', async () => {
  const result = solve(diamondBOM);
  const delivery = createMissionDelivery({ repositories: {}, check: async (...args) => { const admission = await check(...args); return { ...admission, proof: { ...admission.proof, inputSha256: '0'.repeat(64) } }; } });
  await assert.rejects(delivery.deliver(diamondBOM, result), { code: 'PROOF_BINDING' });
  assert.equal(delivery.statistics().completed, 0);
});
