// SPDX-License-Identifier: Apache-2.0
import test, { mock } from 'node:test';
import assert from 'node:assert/strict';
import * as mutateMod from '../alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/evolve/mutate.ts';

function makeMsg(gen) {
  return { pop: [], rngState: 1, mutations: [], popSize: 1, critic: 'none', gen };
}

test.skip('worker updates gpu flag before mutate calls', async () => {
  const selfObj = { navigator: {}, postMessage() {} };
  mock.method(selfObj, 'postMessage', () => {});
  global.self = selfObj;
  const mutateSpy = mock.method(mutateMod, 'mutate', () => []);

  await import('../alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/worker/evolver.ts');
  const handler = selfObj.onmessage;

  handler({ data: { type: 'gpu', available: true } });
  await handler({ data: makeMsg(1) });
  assert.equal(mutateSpy.mock.calls[0].arguments[6], true);

  handler({ data: { type: 'gpu', available: false } });
  await handler({ data: makeMsg(2) });
  assert.equal(mutateSpy.mock.calls[1].arguments[6], false);

  mock.restoreAll();
});
