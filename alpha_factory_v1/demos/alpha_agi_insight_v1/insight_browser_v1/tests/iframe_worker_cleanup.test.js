// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { createSandboxWorker } from '../src/utils/sandbox.ts';

test('iframe remains script-only and cleans up after the worker handshake', async (t) => {
  const previous = { window: global.window, document: global.document, fetch: global.fetch };
  t.after(() => Object.assign(global, previous));
  let handler;
  let removed = 0;
  let detached = 0;
  const messages = [];
  const frameWindow = {
    postMessage(message) {
      messages.push(message);
      if (message.type === 'sandbox-start') {
        global.queueMicrotask(() => handler({ source: frameWindow, data: { type: 'sandbox-ready' } }));
      }
    },
  };
  const iframe = {
    style: {}, contentWindow: frameWindow,
    setAttribute(name, value) { assert.equal(name, 'sandbox'); assert.equal(value, 'allow-scripts'); },
    remove() { removed += 1; },
  };
  global.window = {
    location: { href: 'http://localhost/index.html', origin: 'http://localhost' },
    addEventListener(type, value) { assert.equal(type, 'message'); handler = value; },
    removeEventListener(type, value) { assert.equal(type, 'message'); assert.equal(value, handler); detached += 1; },
  };
  global.document = {
    createElement(tag) { assert.equal(tag, 'iframe'); return iframe; },
    body: { appendChild(value) { assert.equal(value, iframe); global.queueMicrotask(() => iframe.onload()); } },
  };
  global.fetch = async (url) => {
    assert.equal(url.href, 'http://localhost/worker/evolver.js');
    return new global.Response('self.onmessage = () => {};');
  };
  const worker = await createSandboxWorker('./worker/evolver.js');
  assert.equal(messages[0].script, 'self.onmessage = () => {};');
  worker.terminate();
  assert.equal(messages[1].type, 'sandbox-terminate');
  assert.equal(removed, 1);
  assert.equal(detached, 1);
  await assert.rejects(createSandboxWorker('https://example.test/worker.js'), /same-origin/);
});
