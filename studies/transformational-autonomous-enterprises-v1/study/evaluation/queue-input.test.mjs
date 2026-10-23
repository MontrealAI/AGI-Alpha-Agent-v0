// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { LocalQueue } from './queue.mjs';
import { reference, sha256, stable } from './checker.mjs';

test('queued execution and duplicate lookup retain the exact admitted input after caller mutation', async () => {
  const mission = { schema: 'tae/mission-v1', missionId: 'captured-before-queue', kind: 'flat-reduction', rows: [{ group: 'a', amount: 1 }] };
  const admitted = structuredClone(mission);
  const queue = new LocalQueue();
  try {
    const pending = queue.submit('captured-input', mission);
    mission.rows[0].amount = 'mutated-after-admission';
    const result = await pending;
    assert.equal(reference(admitted).accepted, true);
    assert.equal(result.accepted, true);
    assert.equal(result.expectedValid, true);
    assert.equal(queue.exportHistory().find(event => event.event === 'queued').inputSha256, sha256(stable(admitted)));
    assert.equal(queue.submit('captured-input', admitted), pending);
    assert.deepEqual(await queue.submit('captured-input', admitted), result);
    await assert.rejects(queue.submit('captured-input', mission), /IDEMPOTENCY_INPUT_MISMATCH/);
  } finally { await queue.stop(); }
});

test('a retry uses the same admitted nested input after the caller changes it', async () => {
  const mission = { schema: 'tae/mission-v1', missionId: 'captured-retry', kind: 'flat-reduction', rows: [{ group: 'a', amount: 2 }] };
  const queue = new LocalQueue();
  try {
    const pending = queue.submit('captured-retry', mission, { failFirst: true });
    mission.rows.length = 0;
    const result = await pending;
    assert.equal(result.accepted, true);
    assert.equal(result.attempts, 2);
    assert.equal(queue.exportHistory().filter(event => event.event === 'attempt-failed').length, 1);
  } finally { await queue.stop(); }
});
