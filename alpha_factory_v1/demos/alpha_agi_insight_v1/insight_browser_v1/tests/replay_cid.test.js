// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { ReplayDB } from '../src/replay.ts';

const framesA = [
  { id: 1, parent: null, delta: { step: 0 }, timestamp: 0 },
  { id: 2, parent: 1, delta: { step: 1 }, timestamp: 1 },
];

const framesB = [
  { id: 1, parent: null, delta: { step: 0 }, timestamp: 0 },
  { id: 2, parent: 1, delta: { step: 1 }, timestamp: 1 },
];

test.skip('cidForFrames returns the same hash for identical frames', async () => {
  const cidA = await ReplayDB.cidForFrames(framesA);
  const cidB = await ReplayDB.cidForFrames(framesB);
  assert.equal(cidA, cidB);
});
