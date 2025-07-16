// SPDX-License-Identifier: Apache-2.0
import { mutate } from '../src/evolve/mutate.ts';

function fixed(v) {
  return () => v;
}

test('sigma scales with horizon years', () => {
  const pop = [{ logic: 0.5, feasible: 0.5, strategy: 'base', depth: 0, horizonYears: 4 }];
  const out = mutate(pop, fixed(1), ['gaussian'], 1);
  const child = out[1];
  const expected = 0.5 * 0.12 * Math.log1p(4);
  expect(child.logic - 0.5).toBeCloseTo(expected, 5);
});

test('sigma halves on convergence', () => {
  const pop = Array.from({ length: 3 }, () => ({ logic: 0.5, feasible: 0.5, strategy: 'base', depth: 0, horizonYears: 2 }));
  const out = mutate(pop, fixed(1), ['gaussian'], 1, true);
  const child = out[pop.length];
  const expected = 0.5 * 0.12 * Math.log1p(2) * 0.5;
  expect(child.logic - 0.5).toBeCloseTo(expected, 5);
});
