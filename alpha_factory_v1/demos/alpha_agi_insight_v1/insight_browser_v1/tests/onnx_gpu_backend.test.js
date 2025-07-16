// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';

// Stub global objects
global.window = {};
global.navigator = { gpu: {} };
window.ort = {};

const { gpuBackend } = await import('../src/utils/llm.ts');

test.skip('gpuBackend uses webgpu when navigator.gpu and ort present', async () => {
  const backend = await gpuBackend();
  assert.equal(backend, 'webgpu');
});
