// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {compilePlan, leaf, verifyPlan, verifyProof, toBaseUnits, formatTokens} from '../../docs/assets/nova-studio/plan.mjs';
const require = createRequire(new URL('../contracts/package.json', import.meta.url));
const existing = require('../contracts/scripts/plan.js');
const spec = (index = 0) => ({goal: `Public numerical experiment ${index}`, successMetric: `Exact result π / é ${index}`,
  bounty: ((1n << 95n) + BigInt(index)).toString(), duration: index % 2 ? 7776000 : 1, priceWeight: index % 2 ? 10000 : 0});

for (const count of [1, 2, 3, 7, 127, 128]) test(`browser compiler matches locked JS for ${count} jobs`, () => {
  const specs = Array.from({length: count}, (_, index) => spec(index)), result = compilePlan(specs);
  assert.deepEqual(result, existing.compilePlan(specs));
  assert.deepEqual(verifyPlan(result), result);
  for (const job of result.jobs) assert.equal(verifyProof(job.index, job.spec, job.proof, result.planRoot), true);
  if (count === 3) assert.equal(result.jobs[2].proof.length, 1);
});
test('zero and 129 jobs are rejected', () => {
  for (const count of [0, 129]) assert.throws(() => compilePlan(Array.from({length: count}, () => spec())), /1–128/);
});
test('exact uint96, Unicode byte, duration and preference bounds', () => {
  const edge = {...spec(), goal: 'é'.repeat(256), successMetric: '🚀'.repeat(128), bounty: (2n ** 96n - 1n).toString()};
  assert.equal(leaf(0, edge), existing.leaf(0, edge));
  for (const change of [{goal: 'é'.repeat(257)}, {goal: '\ud800'}, {goal: ''}, {successMetric: ''},
    {bounty: 100}, {bounty: '99'}, {bounty: '0100'}, {bounty: '1e9'}, {bounty: (2n ** 96n).toString()},
    {duration: 0}, {duration: 7776001}, {duration: 1.2}, {duration: true}, {priceWeight: -1},
    {priceWeight: 10001}, {priceWeight: 1.5}, {unexpected: 'ignored?'}])
    assert.throws(() => compilePlan([{...edge, ...change}]));
});
test('commitments preserve text exactly and bind job order and every proof', () => {
  const plan = compilePlan([spec(), spec(1), spec(2)]);
  assert.notEqual(compilePlan([{...spec(), goal: 'é'}]).planRoot, compilePlan([{...spec(), goal: 'e\u0301'}]).planRoot);
  assert.notEqual(compilePlan([spec(1), spec(), spec(2)]).planRoot, plan.planRoot);
  for (const mutate of [p => p.jobs[0].proof.reverse(), p => p.jobs[0].index++,
    p => p.totalBounty = '100', p => p.jobs[0].spec.goal += ' ', p => p.extra = true]) {
    const changed = structuredClone(plan); mutate(changed); assert.throws(() => verifyPlan(changed));
  }
});
test('human amounts use exact integer conversion including large 18-decimal values', () => {
  const amount = '1234567890.123456789012345678';
  assert.equal(toBaseUnits(amount), '1234567890123456789012345678');
  assert.equal(formatTokens(toBaseUnits(amount)), amount);
  for (const amount of ['1e18', '0.0000000000000000001', '1,000', '-1', '01', 1]) assert.throws(() => toBaseUnits(amount));
});
