// SPDX-License-Identifier: Apache-2.0
const { Simulator } = require('../src/simulator.ts');

jest.setTimeout(10000);

test('500-generation run', async () => {
  const sim = Simulator.run({ popSize: 5, generations: 500 });
  let count = 0;
  for await (const g of sim) {
    count = g.gen;
    for (const d of g.population) {
      expect(Number.isNaN(d.logic)).toBe(false);
      expect(Number.isNaN(d.feasible)).toBe(false);
    }
  }
  expect(count).toBe(500);
});

test('memory usage stable', async () => {
  const start = process.memoryUsage().heapUsed;
  const sim = Simulator.run({ popSize: 5, generations: 100 });
  for await (const _unused of sim) {
    void _unused;
  }
  const end = process.memoryUsage().heapUsed;
  expect(end - start).toBeLessThan(10 * 1024 * 1024);
});
