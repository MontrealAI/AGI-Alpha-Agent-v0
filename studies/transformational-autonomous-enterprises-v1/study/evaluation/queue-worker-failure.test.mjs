// SPDX-License-Identifier: Apache-2.0
// Exact queue/checker bytes beside a controlled worker fixture; no repository/native bridge or EVM.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const fixture = `
import {parentPort} from 'node:worker_threads';
if(process.env.TAE_QUEUE_FIXTURE_STARTUP === 'fail') throw Error('CONTROLLED_STARTUP_FAILURE');
setTimeout(()=>parentPort.postMessage({ready:true}), Number(process.env.TAE_QUEUE_FIXTURE_READY_MS || 0));
parentPort.on('message', ({id,mission,attempt})=>{
  if(mission.action === 'always-crash' || (mission.action === 'crash-once' && attempt === 0)) {
    throw Error('CONTROLLED_WORKER_CRASH');
  }
  if(mission.action === 'exit-once' && attempt === 0) process.exit(0);
  setTimeout(()=>parentPort.postMessage({id,accepted:true,fixture:'controlled-thread',mission}), 25);
});
`;

async function bounded(promise, label) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(Error('QUEUE_TEST_TIMEOUT:' + label)), 1500); }),
    ]);
  } finally { clearTimeout(timer); }
}

async function until(predicate, label) {
  const deadline = performance.now() + 1500;
  while (!predicate()) {
    if (performance.now() >= deadline) throw Error('QUEUE_TEST_TIMEOUT:' + label);
    await new Promise(resolve => setTimeout(resolve, 5));
  }
}

async function queueFor(t, environment = {}) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'tae-queue-worker-'));
  for (const name of ['queue.mjs', 'checker.mjs']) {
    await fs.copyFile(new URL('./' + name, import.meta.url), path.join(directory, name));
  }
  await fs.writeFile(path.join(directory, 'load-worker.mjs'), fixture);
  const { LocalQueue } = await import(pathToFileURL(path.join(directory, 'queue.mjs')).href);
  const saved = Object.fromEntries(Object.keys(environment).map(key => [key, process.env[key]]));
  let queue;
  try {
    Object.assign(process.env, environment);
    queue = new LocalQueue();
  } finally {
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
  t.after(async () => { await queue.stop(); await fs.rm(directory, { recursive: true, force: true }); });
  return queue;
}

test('uncaught worker failure retries on a replacement with the admitted input', async t => {
  const queue = await queueFor(t);
  const mission = { action: 'crash-once', rows: [{ amount: 7 }] };
  const resultPromise = queue.submit('crash-retry', mission);
  mission.rows[0].amount = 999;
  const result = await bounded(resultPromise, 'crash-retry');
  assert.equal(result.fixture, 'controlled-thread');
  assert.equal(result.attempts, 2);
  assert.equal(result.mission.rows[0].amount, 7);
  assert.deepEqual(queue.exportHistory().filter(event => event.event === 'started').map(event => event.attempt), [0, 1]);
  assert.equal(queue.exportHistory().filter(event => event.event === 'attempt-failed').length, 1);
});

test('exhausted worker retry rejects while a later queued job still settles', async t => {
  const queue = await queueFor(t);
  const failed = queue.submit('always-crash', { action: 'always-crash' });
  const later = queue.submit('later', { action: 'success' });
  const [, result] = await Promise.all([
    assert.rejects(bounded(failed, 'exhausted-retry'), /WORKER_FAILURE:CONTROLLED_WORKER_CRASH/),
    bounded(later, 'later-job'),
  ]);
  assert.equal(result.id, 'later');
  assert.equal(result.fixture, 'controlled-thread');
  assert.equal(queue.exportHistory().filter(event => event.id === 'always-crash' && event.event === 'attempt-failed').length, 2);
});

test('late retired-worker messages errors and exit cannot affect its replacement', async t => {
  const queue = await queueFor(t);
  const old = queue.slots[0].worker;
  const callbacks = Object.fromEntries(['message', 'error', 'exit'].map(kind => [kind, old.listeners(kind).at(-1)]));
  const first = queue.submit('first', { action: 'crash-once' });
  await until(() => queue.slots[0].worker !== old && queue.slots[0].job?.id === 'first', 'replacement-active');
  const replacement = queue.slots[0].worker;
  // Node removes listeners after exit; invoke captured queue callbacks to test a delayed retired-generation event.
  callbacks.message({ id: 'first', accepted: true, fixture: 'stale-retired-worker' });
  callbacks.message({ ready: true });
  callbacks.error(Error('STALE_ERROR'));
  callbacks.exit(1);
  const result = await bounded(first, 'stale-worker-fence');
  assert.equal(result.fixture, 'controlled-thread');
  assert.equal(queue.slots[0].worker, replacement);
  assert.equal(queue.exportHistory().filter(event => event.event === 'attempt-failed').length, 1);
});

test('exit without a result retires the slot and preserves the bounded retry', async t => {
  const queue = await queueFor(t);
  const result = await bounded(queue.submit('unexpected-exit', { action: 'exit-once' }), 'unexpected-exit');
  assert.equal(result.attempts, 2);
  assert.equal(result.fixture, 'controlled-thread');
  assert.match(queue.exportHistory().find(event => event.event === 'attempt-failed').error, /WORKER_EXIT:0/);
});

test('startup failure rejects pending and future work rather than restarting forever', async t => {
  const queue = await queueFor(t, { TAE_QUEUE_FIXTURE_STARTUP: 'fail' });
  await assert.rejects(bounded(queue.submit('unstarted', {}), 'startup-failure'), /WORKER_UNAVAILABLE/);
  await assert.rejects(bounded(queue.submit('future', {}), 'unavailable-future'), /WORKER_UNAVAILABLE/);
  assert.equal(queue.exportHistory().filter(event => event.event === 'started').length, 0);
});

test('Stop cancels work queued during replacement initialization', async t => {
  const queue = await queueFor(t);
  await until(() => queue.slots[0].ready, 'initial-ready');
  const old = queue.slots[0].worker;
  const saved = process.env.TAE_QUEUE_FIXTURE_READY_MS;
  process.env.TAE_QUEUE_FIXTURE_READY_MS = '500';
  try {
    const first = queue.submit('stop-retry', { action: 'crash-once' });
    const later = queue.submit('stop-pending', {});
    const settled = Promise.allSettled([first, later]);
    await until(() => queue.slots[0].worker !== old, 'replacement-created');
    await queue.stop();
    const results = await bounded(settled, 'stop-settles');
    assert.equal(results.every(result => result.status === 'rejected' && result.reason.message === 'INTERRUPTED'), true);
    assert.equal(queue.exportHistory().filter(event => event.event === 'completed').length, 0);
  } finally {
    if (saved === undefined) delete process.env.TAE_QUEUE_FIXTURE_READY_MS; else process.env.TAE_QUEUE_FIXTURE_READY_MS = saved;
  }
});
