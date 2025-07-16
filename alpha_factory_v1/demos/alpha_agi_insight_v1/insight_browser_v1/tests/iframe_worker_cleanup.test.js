// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { createSandboxWorker } from '../src/utils/sandbox.ts';

// Minimal DOM stubs
let added = 0;
let removed = 0;
let appended = 0;
let iframeRemoved = 0;
let revoked = 0;
let lastHandler;

const windowMock = {
  addEventListener(type, handler) {
    if (type === 'message') {
      added += 1;
      lastHandler = handler;
    }
  },
  removeEventListener(type, handler) {
    if (type === 'message' && handler === lastHandler) {
      removed += 1;
    }
  },
};

const iframeMock = {
  sandbox: '',
  style: {},
  src: '',
  contentWindow: { postMessage() {} },
  remove() { iframeRemoved += 1; },
};

const documentMock = {
  createElement() {
    return iframeMock;
  },
  body: { appendChild() { appended += 1; } },
};

const URLMock = {
  createObjectURL() {
    return 'blob:xyz';
  },
  revokeObjectURL() { revoked += 1; },
};

// Inject mocks
global.window = windowMock;
global.document = documentMock;
global.URL = URLMock;


test.skip('iframe sandboxed and cleaned up', async () => {
  const w = await createSandboxWorker('x.js');
  assert.equal(appended, 1);
  assert.equal(iframeMock.sandbox, 'allow-scripts');
  assert.equal(added, 1);
  w.terminate();
  assert.equal(removed, 1);
  assert.equal(iframeRemoved, 1);
  assert.equal(revoked, 2);
});

