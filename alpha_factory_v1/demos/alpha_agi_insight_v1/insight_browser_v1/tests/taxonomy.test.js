// SPDX-License-Identifier: Apache-2.0
import { mineTaxonomy, saveTaxonomy, loadTaxonomy, proposeSectorNodes } from '../../src/taxonomy.ts';

jest.mock('../../src/utils/llm.ts', () => ({
  chat: async () => 'Yes',
}));

beforeEach(() => {
  indexedDB.deleteDatabase('sectorTaxonomy');
});

test('mineTaxonomy extracts sector nodes', () => {
  const g = mineTaxonomy([{ params: { sector: 'A' } }]);
  expect(g.nodes['A']).toBeDefined();
  expect(g.nodes['A'].id).toBe('A');
});

test('taxonomy persists across saves and respects versioning', async () => {
  const g = mineTaxonomy([{ params: { sector: 'B' } }]);
  await saveTaxonomy(g);
  let loaded = await loadTaxonomy();
  expect(Object.keys(loaded.nodes)).toContain('B');

  // simulate old version by writing 0 to meta store
  const db = await new Promise((resolve, reject) => {
    const req = indexedDB.open('sectorTaxonomy', 1);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  const tx = db.transaction('meta', 'readwrite');
  tx.objectStore('meta').put(0, 'version');
  await new Promise((resolve) => (tx.oncomplete = resolve));
  db.close();

  loaded = await loadTaxonomy();
  expect(loaded.nodes['B']).toBeUndefined();
});

test('proposeSectorNodes creates cluster nodes and saves', async () => {
  const runs = [
    { keywords: ['solar', 'energy'] },
    { keywords: ['wind', 'energy'] },
  ];
  let g = { nodes: {} };
  g = await proposeSectorNodes(runs, g);
  const keys = Object.keys(g.nodes);
  expect(keys.length).toBeGreaterThan(0);
  await saveTaxonomy(g);
  const loaded = await loadTaxonomy();
  expect(Object.keys(loaded.nodes)).toEqual(keys);
});
