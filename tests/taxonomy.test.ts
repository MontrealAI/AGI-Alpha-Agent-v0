// SPDX-License-Identifier: Apache-2.0
/* global indexedDB, fetch */
import test from 'node:test';
import assert from 'node:assert/strict';
import { mineTaxonomy, pruneTaxonomy, proposeSectorNodes, loadTaxonomy } from '.../src/taxonomy.ts';

// Clean database before each run
const DB_NAME = 'sectorTaxonomy';

function resetDB() {
  indexedDB.deleteDatabase(DB_NAME);
}

resetDB();

test('mineTaxonomy and pruneTaxonomy', () => {
  const g = mineTaxonomy([
    { params: { sector: 'A' } },
    { params: { sector: 'B' } },
    { params: { sector: 'A' } },
  ]);
  assert.deepEqual(Object.keys(g.nodes).sort(), ['A', 'B']);
  const pruned = pruneTaxonomy(g, new Set(['A']));
  assert.deepEqual(Object.keys(pruned.nodes), ['A']);
});

test('proposeSectorNodes clusters keywords and saves', async () => {
  resetDB();
  const origFetch = global.fetch;
  (global as any).fetch = async () => ({
    json: async () => ({ choices: [{ message: { content: 'Yes' } }] })
  }) as any;

  const runs = [
    { keywords: ['solar', 'energy'] },
    { keywords: ['wind', 'energy'] },
  ];
  let g = { nodes: {} as any };
  g = await proposeSectorNodes(runs, g);
  assert.ok(Object.keys(g.nodes).length > 0);
  const loaded = await loadTaxonomy();
  assert.deepEqual(Object.keys(loaded.nodes), Object.keys(g.nodes));

  (global as any).fetch = origFetch;
});
