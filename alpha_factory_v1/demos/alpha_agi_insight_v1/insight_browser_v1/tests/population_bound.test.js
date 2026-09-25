// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { selectPopulation } from '../src/evolve/selection.ts';

test('an oversized Pareto front cannot grow the configured population', () => {
  const candidates = Array.from({length: 300}, (_, id) => ({id}));
  const selected = selectPopulation(candidates, candidates, 20);
  assert.equal(selected.length, 20);
  assert.equal(new Set(selected).size, 20);
  assert.deepEqual(selected, candidates.slice(0, 20));
});
test('elites survive once and slots fill with distinct candidates, including small populations', () => {
  const candidates = Array.from({length: 20}, (_, id) => ({id}));
  assert.deepEqual(selectPopulation(candidates, [candidates[5], candidates[5]], 3), [candidates[5], candidates[0], candidates[1]]);
  assert.throws(() => selectPopulation(candidates, [], NaN));
  assert.throws(() => selectPopulation(candidates, [], 0));
});
