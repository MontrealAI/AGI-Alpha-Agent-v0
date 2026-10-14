// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const root = new URL('../../', import.meta.url);
const read = relative => readFileSync(new URL(relative, root), 'utf8');

test('native Studio engine imports bypass an existing gallery worker while legacy offline use remains', async () => {
  const expected = '?nova-cycle=' + createHash('sha256').update(read('docs/assets/successor/engine.mjs')).digest('hex');
  const imports = [];
  for (const name of readdirSync(new URL('docs/assets/nova-studio/', root)).filter(name => name.endsWith('.mjs'))) {
    for (const match of read('docs/assets/nova-studio/' + name).matchAll(/\.\.\/successor\/engine\.mjs([^'"\s]*)/g)) {
      assert.equal(match[1], expected, `${name} must request the exact current engine outside old gallery caches`);
      imports.push(match[0]);
    }
  }
  assert(imports.length >= 3);
  const events = new Map(), cached = { historicalOfflineEngine: true };
  let opened = 0;
  runInNewContext(read('docs/service-worker.js'), {
    URL,
    self: { location: { href: 'https://fixture.test/service-worker.js' }, addEventListener: (name, handler) => events.set(name, handler) },
    caches: { open: async () => { opened++; return { match: async () => cached }; } },
    fetch: async () => { throw Error('Unexpected network fallback in the cache boundary test'); },
  }, { filename: fileURLToPath(new URL('docs/service-worker.js', root)) });
  let response;
  const request = url => events.get('fetch')({ request: { method: 'GET', mode: 'cors', url }, respondWith: value => { response = value; } });
  request('https://fixture.test/assets/successor/engine.mjs');
  assert.equal(await response, cached);
  assert.equal(opened, 1);
  for (const specifier of imports) {
    response = undefined;
    request(new URL(specifier, 'https://fixture.test/assets/nova-studio/workflow.mjs').href);
    assert.equal(response, undefined, 'the existing service worker must allow the browser network request through');
  }
  assert.equal(opened, 1, 'wallet imports must never read the legacy cached engine');
});
