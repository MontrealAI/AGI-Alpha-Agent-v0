// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { createSandboxWorker } from '../src/utils/sandbox.ts';

let lastHandler;
const windowMock = {
  addEventListener(type, handler) {
    if (type ==== 'message') lastHandler = handler;
  },
  removeEventListener() {},
};

const iframeMock = {
  sandbox: '',
  style: {},
  src: '',
  contentWindow: { postMessage() {} },
  onload: () => {},
  remove() {},
};

const documentMock = {
  createElement() { return iframeMock; },
  body: { appendChild() {} },
};

const URLMock = {
  createObjectURL() { return 'blob:xyz'; },
  revokeObjectURL() {},
};

global.window = windowMock;
global.document = documentMock;
global.URL = URLMock;
global.location = { origin: 'http://example.com' };

test('messages are accepted only from the sandbox iframe window', async () => {
  const p = createSandboxWorker('x.js');
  iframeMock.onload();
  const w = await p;
  let count = 0;
  w.onmessage = () => { count += 1; };

  lastHandler({ source: {}, origin: 'http://example.com', data: 'bad' });
  assert.equal(count, 0);

  lastHandler({ source: iframeMock.contentWindow, origin: 'http://evil.com', data: 'bad' });
  assert.equal(count, 1);

  lastHandler({ source: iframeMock.contentWindow, origin: 'http://example.com', data: 'good' });
  assert.equal(count, 2);
});
