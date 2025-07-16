// SPDX-License-Identifier: Apache-2.0
import { createStore, set, get } from '../src/utils/keyval.ts';

beforeEach(() => {
  indexedDB.deleteDatabase('jest');
});

test('createStore uses indexedDB when available', async () => {
  const store = createStore('jest', 'runs');
  await store.dbp;
  expect(store.memory).toBeNull();
  await set('a', 1, store);
  const v = await get('a', store);
  expect(v).toBe(1);
});

test('fallback to memory when indexedDB unavailable', async () => {
  const orig = global.indexedDB;
  delete global.indexedDB;
  const store = createStore('jest', 'runs');
  await store.dbp;
  expect(store.memory).toBeInstanceOf(Map);
  await set('b', 2, store);
  const v = await get('b', store);
  expect(v).toBe(2);
  global.indexedDB = orig;
});
