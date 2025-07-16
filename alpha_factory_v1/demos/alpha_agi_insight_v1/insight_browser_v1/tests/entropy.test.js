// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { paretoEntropy } from '../src/utils/entropy.ts';

const uniform = [];
for (let y = 0; y < 10; y++) {
  for (let x = 0; x < 10; x++) {
    uniform.push({ logic: (x + 0.5) / 10, feasible: (y + 0.5) / 10 });
  }
}

const clustered = Array.from({ length: 100 }, () => ({ logic: 0.5, feasible: 0.5 }));

// Entropy of a uniform 10x10 grid should be close to log2(100)
const UNIFORM_EXPECTED = Math.log2(100);

test('uniform distribution entropy', () => {
  const h = paretoEntropy(uniform, 10);
  assert.ok(Math.abs(h - UNIFORM_EXPECTED) < 0.01);
});

test('clustered distribution entropy', () => {
  const h = paretoEntropy(clustered, 10);
  assert.ok(Math.abs(h) < 1e-9);
});

test('uniform entropy greater than clustered entropy', () => {
  const hUniform = paretoEntropy(uniform, 10);
  const hCluster = paretoEntropy(clustered, 10);
  assert.ok(hUniform > hCluster);
});
