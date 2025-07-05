// SPDX-License-Identifier: Apache-2.0
/* global indexedDB */
import test from 'node:test';
import assert from 'node:assert/strict';
import { mineMemes, saveMemes, loadMemes } from '../src/memeplex.ts';

const DB_NAME = 'memeplex';

function resetDB() {
  indexedDB.deleteDatabase(DB_NAME);
}

resetDB();

test('mineMemes counts edges and persists', async () => {
  resetDB();
  const runs = [
    { edges: [{ from: 'A', to: 'B' }, { from: 'B', to: 'C' }] },
    { edges: [{ from: 'A', to: 'B' }] },
    { edges: [{ from: 'A', to: 'B' }] },
  ];
  const memes = mineMemes(runs, 2);
  assert.equal(memes.length, 1);
  assert.equal(memes[0].count, 3);
  await saveMemes(memes);
  const loaded = await loadMemes();
  assert.deepEqual(loaded, memes);
});
