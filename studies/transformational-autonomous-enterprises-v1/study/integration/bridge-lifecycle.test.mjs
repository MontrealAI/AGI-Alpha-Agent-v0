// SPDX-License-Identifier: Apache-2.0
// Exact delivery-module bytes, isolated beside a controlled import dependency.
// No repository bridge, native worker, Git operation or EVM is executed.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { solve } from '../enterprise/compiler.mjs';
import { flatControl } from '../enterprise/development-cases.mjs';
import { checkArtifact } from '../evaluation/checker.mjs';
import { externalAdmission } from './artifact.mjs';

const criteria = fs.readFileSync(new URL('../evaluation/criteria.json', import.meta.url));
const admit = externalAdmission(checkArtifact, criteria);
const observe = pending => pending.then(value => ({ value }), error => ({ error }));
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
const tick = () => new Promise(setImmediate);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const work = id => { const mission = { ...flatControl, missionId: id }; return { mission, result: solve(mission) }; };
const marker = () => Object.assign(Error('CONTROLLED_TEST_BRIDGE_RUN'), { code: 'CONTROLLED_TEST_BRIDGE_RUN' });

async function until(predicate) {
  for (let attempt = 0; attempt < 200 && !predicate(); attempt++) await tick();
  assert.ok(predicate(), 'The bounded controlled schedule reached its expected state');
}

async function isolatedService(initialize, { concurrency = 2 } = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'tae-bridge-lifecycle-'));
  const source = fs.readFileSync(new URL('./mission-delivery.mjs', import.meta.url));
  const entry = path.join(directory, 'mission-delivery.mjs');
  fs.writeFileSync(entry, source, { flag: 'wx' });
  assert.ok(fs.readFileSync(entry).equals(source), 'The tested module must be an exact byte copy');
  const key = '__tae_controlled_bridge_' + randomUUID();
  globalThis[key] = initialize;
  fs.writeFileSync(path.join(directory, 'source-bridge.mjs'),
    '// CONTROLLED TEST DEPENDENCY ONLY: no repository/native implementation.\n' +
    'export function createBridge(repositories) { return globalThis[' + JSON.stringify(key) + '](repositories); }\n', { flag: 'wx' });
  const module = await import(pathToFileURL(entry).href);
  const service = module.createMissionDelivery({ repositories: { controlledTestOnly: true }, check: admit, concurrency });
  console.log('Controlled dependency; exact delivery module SHA256 ' + sha256(source));
  return { service, cleanup: () => { delete globalThis[key]; fs.rmSync(directory, { recursive: true, force: true }); } };
}

test('abort during initialization prevents native launch and permits a later fresh delivery', async () => {
  const loading = deferred(), started = deferred(), controller = new AbortController();
  let initializations = 0, runs = 0;
  const bridge = { run: async () => { runs++; throw marker(); } };
  const fixture = await isolatedService(() => { initializations++; started.resolve(); return loading.promise; });
  const input = work('bridge-abort-control');
  const outcome = observe(fixture.service.deliver(input.mission, input.result, { signal: controller.signal }));
  try {
    await started.promise;
    controller.abort();
    loading.resolve(bridge);
    assert.equal((await outcome).error?.code, 'INTERRUPTED');
    assert.equal(runs, 0);
    assert.equal(fixture.service.statistics().active, 0);
    const retry = await observe(fixture.service.deliver(input.mission, input.result));
    assert.equal(retry.error?.code, 'CONTROLLED_TEST_BRIDGE_RUN');
    assert.equal(initializations, 1);
    assert.equal(runs, 1);
  } finally { loading.resolve(bridge); await outcome; fixture.cleanup(); }
});

test('failed initialization is retried while a successful initializer remains cached', async () => {
  const initialError = Error('CONTROLLED_INITIALIZATION_FAILURE');
  let initializations = 0, runs = 0;
  const bridge = { run: async () => { runs++; throw marker(); } };
  const fixture = await isolatedService(async () => { initializations++; if (initializations === 1) throw initialError; return bridge; });
  const input = work('bridge-retry-control');
  try {
    assert.equal((await observe(fixture.service.deliver(input.mission, input.result))).error, initialError);
    assert.equal((await observe(fixture.service.deliver(input.mission, input.result))).error?.code, 'CONTROLLED_TEST_BRIDGE_RUN');
    assert.equal((await observe(fixture.service.deliver(input.mission, input.result))).error?.code, 'CONTROLLED_TEST_BRIDGE_RUN');
    assert.equal(initializations, 2);
    assert.equal(runs, 2);
    assert.equal(fixture.service.statistics().active, 0);
    assert.equal(fixture.service.statistics().failed, 3);
  } finally { fixture.cleanup(); }
});

test('concurrent Promise waiters share failure, then share exactly one fresh initializer', async () => {
  const first = deferred(), second = deferred(), initialError = Error('CONTROLLED_SHARED_FAILURE');
  let initializations = 0, runs = 0;
  const bridge = { run: async () => { runs++; throw marker(); } };
  const fixture = await isolatedService(() => { initializations++; return initializations === 1 ? first.promise : second.promise; });
  const inputs = [work('bridge-concurrent-a'), work('bridge-concurrent-b')];
  const attempts = inputs.map(input => observe(fixture.service.deliver(input.mission, input.result)));
  const retries = [];
  try {
    await until(() => initializations === 1 && fixture.service.statistics().active === 2);
    first.reject(initialError);
    assert.ok((await Promise.all(attempts)).every(outcome => outcome.error === initialError));
    retries.push(...inputs.map(input => observe(fixture.service.deliver(input.mission, input.result))));
    await tick(); await tick();
    second.resolve(bridge);
    assert.ok((await Promise.all(retries)).every(outcome => outcome.error?.code === 'CONTROLLED_TEST_BRIDGE_RUN'));
    assert.equal(initializations, 2);
    assert.equal(runs, 2);
    assert.equal(fixture.service.statistics().active, 0);
  } finally { first.reject(initialError); second.resolve(bridge); await Promise.all([...attempts, ...retries]); fixture.cleanup(); }
});

test('a delayed stale waiter cannot clear a newer initializer under a controlled thenable schedule', async () => {
  const oldWaiters = [], newer = deferred(), initialError = Error('CONTROLLED_STALE_WAITER');
  let closed = false, initializations = 0, runs = 0;
  const original = { then(resolve, reject) { if (closed) reject(initialError); else oldWaiters.push({ resolve, reject }); } };
  const bridge = { run: async () => { runs++; throw marker(); } };
  const fixture = await isolatedService(() => { initializations++; return initializations === 1 ? original : newer.promise; });
  const a = work('bridge-stale-a'), b = work('bridge-stale-b'), c = work('bridge-stale-c');
  const attempts = [observe(fixture.service.deliver(a.mission, a.result)), observe(fixture.service.deliver(b.mission, b.result))];
  try {
    await until(() => oldWaiters.length === 2);
    oldWaiters[0].reject(initialError);
    assert.equal((await attempts[0]).error, initialError);
    const retry = observe(fixture.service.deliver(a.mission, a.result)); attempts.push(retry);
    await tick(); await tick();
    assert.equal(initializations, 2);
    oldWaiters[1].reject(initialError);
    assert.equal((await attempts[1]).error, initialError);
    const later = observe(fixture.service.deliver(c.mission, c.result)); attempts.push(later);
    await tick(); await tick();
    newer.resolve(bridge);
    assert.equal((await retry).error?.code, 'CONTROLLED_TEST_BRIDGE_RUN');
    assert.equal((await later).error?.code, 'CONTROLLED_TEST_BRIDGE_RUN');
    assert.equal(initializations, 2);
    assert.equal(runs, 2);
  } finally {
    closed = true; for (const waiter of oldWaiters) waiter.reject(initialError);
    newer.resolve(bridge); await Promise.all(attempts); fixture.cleanup();
  }
});
