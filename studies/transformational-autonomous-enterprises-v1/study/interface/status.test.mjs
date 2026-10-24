// SPDX-License-Identifier: Apache-2.0
// Exact companion script with controlled DOM/fetch/time; no browser or runtime runs.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createHash } from 'node:crypto';

const source = fs.readFileSync(new URL('./app.js', import.meta.url));
const tick = () => new Promise(setImmediate);
const flush = async () => { for (let i = 0; i < 4; i++) await tick(); };
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const status = busy => ({ local: true, busy, token: 'CONTROLLED_TEST_ONLY_TOKEN' });
const response = (data, code = 200) => ({ ok: code >= 200 && code < 300, status: code, json: async () => data });

async function fixture(replies) {
  const elements = new Map(), listeners = new Map(), timers = new Map(), requests = [];
  let nextTimer = 0;
  function element(key) {
    if (elements.has(key)) return elements.get(key);
    const node = { textContent: '', innerHTML: '', disabled: false, dataset: {}, style: {}, attributes: {}, children: [],
      setAttribute(name, value) { this.attributes[name] = value; },
      append(...children) { this.children.push(...children); },
      replaceChildren(...children) { this.children = children; },
      addEventListener(name, listener) { this['on' + name] = listener; },
      closest(selector) { return element(key + ' closest ' + selector); },
      focus() {}, scrollIntoView() {}, click() { return this.onclick?.(); }, remove() {} };
    elements.set(key, node); return node;
  }
  const steps = Array.from({ length: 6 }, (_, i) => { const node = element('step-' + i); node.dataset.step = String(i); return node; });
  const document = { documentElement: {}, body: element('body'), getElementById: element,
    querySelector: element, querySelectorAll: selector => selector === '[data-step]' ? steps : [],
    createElement: tag => element('created-' + tag + '-' + elements.size) };
  const window = { TAE_EVIDENCE: null, addEventListener: (name, listener) => { listeners.set(name, listener); } };
  const fetch = async (url, options) => {
    const request = { url, options }; requests.push(request);
    const next = replies.shift(); assert.ok(next, 'Every fetch must have a declared controlled response');
    return typeof next === 'function' ? await next(request) : response(next);
  };
  const context = vm.createContext({ window, document, fetch, AbortController, Intl, console,
    setTimeout: (callback, delay) => { const id = ++nextTimer; timers.set(id, { callback, delay }); return id; },
    clearTimeout: id => timers.delete(id) });
  // Read the complete exact script, without injected statements or replaced functions.
  vm.runInContext(source.toString('utf8'), context, { filename: 'exact-companion-app.js' });
  console.log('Controlled DOM/fetch/time; exact interface script SHA256 ' + createHash('sha256').update(source).digest('hex'));
  await flush();
  const pending = () => [...timers.values()].filter(timer => timer.delay === 1000).length;
  async function poll() {
    const entry = [...timers.entries()].find(([, timer]) => timer.delay === 1000);
    assert.ok(entry, 'An observed server-owned run needs a scheduled status refresh');
    timers.delete(entry[0]); entry[1].callback(); await flush();
  }
  const dispatch = name => listeners.get(name)?.();
  return { element, requests, pending, poll, dispatch, cleanup: () => dispatch('pagehide') };
}

test('a page observing an existing run returns idle without claiming its result or posting an action', async () => {
  const page = await fixture([status(true), status(false)]);
  try {
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    await page.poll();
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.element('restore').disabled, false);
    assert.equal(page.element('stop-run').disabled, true);
    assert.match(page.element('connection').textContent, /ready/i);
    assert.doesNotMatch(page.element('connection').textContent, /completed|fresh/i);
    assert.equal(page.element('export').disabled, true);
    assert.equal(page.pending(), 0);
    assert.ok(page.requests.every(request => request.url === '/api/status' && !request.options.method));
  } finally { page.cleanup(); }
});

test('slow status reads never overlap and a still-busy reply schedules one next read', async () => {
  const waiting = deferred();
  const page = await fixture([status(true), () => waiting.promise, status(false)]);
  try {
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.pending(), 0); assert.equal(page.requests.length, 2);
    await flush(); assert.equal(page.requests.length, 2);
    waiting.resolve(response(status(true))); await flush();
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.requests.length, 3); assert.equal(page.pending(), 0);
  } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
});

test('failed or malformed refreshes retain busy guards and report uncertainty until recovery', async () => {
  for (const failure of [() => { throw Error('CONTROLLED_STATUS_NETWORK_FAILURE'); }, () => response({ error: 'CONTROLLED_STATUS_HTTP_FAILURE' }, 503), { local: true, token: 'CONTROLLED_TEST_ONLY_TOKEN' }]) {
    const page = await fixture([status(true), failure, status(false)]);
    try {
      await page.poll();
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.element('connection').dataset.state, 'error');
      assert.match(page.element('connection').textContent, /may still be running/i);
      page.element('language').onclick();
      assert.match(page.element('connection').textContent, /serveur est peut-être toujours actif/i);
      assert.equal(page.pending(), 1); await page.poll();
      assert.equal(page.element('run').disabled, false);
      assert.equal(page.element('connection').dataset.state, 'ready');
      assert.doesNotMatch(page.element('connection').textContent, /FAILURE|may still be running/i);
    } finally { page.cleanup(); }
  }
});

test('leaving before a refresh cancels its timer and returning reads current state', async () => {
  const page = await fixture([status(true), status(false)]);
  try {
    assert.equal(page.pending(), 1); page.dispatch('pagehide');
    assert.equal(page.pending(), 0); await flush();
    assert.equal(page.requests.length, 1);
    page.dispatch('pageshow'); await flush();
    assert.equal(page.requests.length, 2);
    assert.equal(page.element('restore').disabled, false);
    assert.equal(page.pending(), 0);
  } finally { page.cleanup(); }
});

test('page lifecycle aborts an in-flight refresh, fences stale replies and refreshes on return', async () => {
  const waiting = deferred();
  const page = await fixture([status(true), () => waiting.promise, status(false)]);
  try {
    await page.poll(); const reading = page.requests[1];
    page.dispatch('pagehide');
    assert.equal(reading.options.signal.aborted, true);
    waiting.resolve(response(status(false))); await flush();
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.pending(), 0);
    page.dispatch('pageshow'); await flush();
    assert.equal(page.requests.length, 3);
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.pending(), 0);
  } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
});

test('stop cancels observation and a stale busy response cannot undo the stopped state', async () => {
  const waiting = deferred();
  const page = await fixture([status(true), () => waiting.promise, { stopped: true }, status(false)]);
  try {
    await page.poll(); await page.element('stop-run').onclick();
    assert.equal(page.requests[1].options.signal.aborted, true);
    const stop = page.requests[2];
    assert.equal(stop.url, '/api/stop'); assert.equal(stop.options.method, 'POST');
    assert.equal(stop.options.headers['X-TAE-Token'], 'CONTROLLED_TEST_ONLY_TOKEN'); assert.equal(stop.options.body, '{}');
    waiting.resolve(response(status(true))); await flush();
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.element('restore').disabled, false);
    assert.match(page.element('connection').textContent, /run stopped/i);
    assert.equal(page.pending(), 0);
  } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
});

test('a run owned by this page keeps its existing request lifecycle without status polling', async () => {
  const waiting = deferred();
  const page = await fixture([status(false), () => waiting.promise]);
  try {
    const running = page.element('run').onclick(); await flush();
    assert.equal(page.requests[1].url, '/api/run'); assert.equal(page.requests[1].options.method, 'POST');
    assert.equal(page.requests[1].options.headers['X-TAE-Token'], 'CONTROLLED_TEST_ONLY_TOKEN');
    assert.equal(page.element('restore').disabled, true); assert.equal(page.pending(), 0);
    page.dispatch('pagehide'); page.dispatch('pageshow'); await flush();
    assert.equal(page.requests.length, 2);
    waiting.resolve(response({ evm: { controlledTestOnly: true } })); await running;
    assert.equal(page.element('run').disabled, false); assert.equal(page.pending(), 0);
    assert.match(page.element('connection').textContent, /completed/i);
  } finally { waiting.resolve(response({ evm: { controlledTestOnly: true } })); await flush(); page.cleanup(); }
});

test('a failed stop keeps busy guards and resumes observation without claiming a stop', async () => {
  const page = await fixture([status(true), () => response({ error: 'CONTROLLED_STOP_FAILURE' }, 503), status(false)]);
  try {
    await page.element('stop-run').onclick();
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.match(page.element('connection').textContent, /CONTROLLED_STOP_FAILURE/);
    assert.match(page.element('toast').textContent, /stop request failed.*may still be running/i);
    assert.doesNotMatch(page.element('connection').textContent, /run stopped/i);
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.element('restore').disabled, false);
    assert.equal(page.pending(), 0);
    assert.equal(page.requests[1].url, '/api/stop');
    assert.equal(page.requests[2]?.url, '/api/status');
  } finally { page.cleanup(); }
});

test('restore stays guarded during observation and keeps historical proof and authority requirements', async () => {
  const page = await fixture([status(true), status(false)]);
  const data = { schema: 'tae.interface-export.v1', evidence: { evm: { controlledTestOnly: true } }, currentProof: null, authority: [] };
  const change = value => ({ target: { value: 'controlled-test-file', files: [{ size: 100, text: async () => JSON.stringify(value) }] } });
  try {
    await page.element('restore').onchange(change(data));
    assert.match(page.element('restore-status').textContent, /already active/i);
    assert.equal(page.element('export').disabled, true);
    await page.poll();
    await page.element('restore').onchange(change({ ...data, authority: ['invented'] }));
    assert.match(page.element('restore-status').textContent, /Unsupported evidence/i);
    assert.equal(page.element('export').disabled, true);
    await page.element('restore').onchange(change(data));
    assert.match(page.element('restore-status').textContent, /historical evidence.*proof and authority are empty/i);
    assert.equal(page.element('export').disabled, false);
  } finally { page.cleanup(); }
});

test('a rejected run reconciles server ownership before releasing busy guards', async () => {
  for (const failure of [
    () => response({ error: 'CONTROLLED_OTHER_TAB_OWNS_RUN' }, 409),
    () => { throw Error('CONTROLLED_RUN_RESPONSE_LOST'); },
  ]) {
    const waiting = deferred();
    const page = await fixture([status(false), failure, () => waiting.promise, status(true), status(false)]);
    try {
      const running = page.element('run').onclick(); await flush();
      assert.equal(page.requests[1].url, '/api/run');
      assert.equal(page.requests[2]?.url, '/api/status');
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.element('stop-run').disabled, false);
      assert.equal(page.pending(), 0);
      waiting.resolve(response(status(true))); await running;
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.pending(), 1); await page.poll();
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.pending(), 1); await page.poll();
      assert.equal(page.element('run').disabled, false);
      assert.equal(page.element('restore').disabled, false);
      assert.equal(page.element('stop-run').disabled, true);
      assert.equal(page.element('export').disabled, true);
      assert.doesNotMatch(page.element('connection').textContent, /completed/i);
      assert.equal(page.pending(), 0);
    } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
  }
});

test('failed reconciliation after a rejected run retains guards and retry until verified idle', async () => {
  for (const failure of [
    () => { throw Error('CONTROLLED_RECONCILIATION_NETWORK_FAILURE'); },
    () => response({ error: 'CONTROLLED_RECONCILIATION_HTTP_FAILURE' }, 503),
    { local: true, token: 'CONTROLLED_TEST_ONLY_TOKEN' },
  ]) {
    const page = await fixture([status(false), () => response({ error: 'CONTROLLED_OTHER_TAB_OWNS_RUN' }, 409), failure, status(false)]);
    try {
      await page.element('run').onclick();
      assert.equal(page.requests[2]?.url, '/api/status');
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.element('stop-run').disabled, false);
      assert.match(page.element('connection').textContent, /may still be running/i);
      page.element('language').onclick();
      assert.match(page.element('connection').textContent, /serveur est peut-être toujours actif/i);
      assert.equal(page.pending(), 1); await page.poll();
      assert.equal(page.element('run').disabled, false);
      assert.equal(page.element('restore').disabled, false);
      assert.equal(page.pending(), 0);
      assert.doesNotMatch(page.element('connection').textContent, /CONTROLLED_RECONCILIATION/);
    } finally { page.cleanup(); }
  }
});

test('stop fences an in-flight reconciliation after a rejected run', async () => {
  const waiting = deferred();
  const page = await fixture([status(false), () => response({ error: 'CONTROLLED_OTHER_TAB_OWNS_RUN' }, 409), () => waiting.promise, { stopped: true }, status(false)]);
  try {
    const running = page.element('run').onclick(); await flush();
    assert.equal(page.requests[2]?.url, '/api/status');
    await page.element('stop-run').onclick();
    assert.equal(page.requests[2].options.signal.aborted, true);
    assert.equal(page.requests[3].url, '/api/stop');
    waiting.resolve(response(status(true))); await running; await flush();
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.element('restore').disabled, false);
    assert.match(page.element('connection').textContent, /run stopped/i);
    assert.equal(page.pending(), 0);
  } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
});

test('Stop acknowledgement retains guards until the server confirms idle', async () => {
  const waiting = deferred();
  const page = await fixture([status(true), { stopped: true }, () => waiting.promise, status(true), status(false)]);
  try {
    const stopping = page.element('stop-run').onclick(); await flush();
    assert.equal(page.requests[1].url, '/api/stop');
    assert.equal(page.requests[2]?.url, '/api/status');
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.equal(page.element('stop-run').disabled, true);
    assert.match(page.element('connection').textContent, /stopping/i);
    assert.doesNotMatch(page.element('toast').textContent, /run stopped/i);
    await page.element('stop-run').onclick(); await flush();
    assert.equal(page.requests.length, 3);
    waiting.resolve(response(status(true))); await stopping;
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.element('restore').disabled, false);
    assert.equal(page.element('stop-run').disabled, true);
    assert.equal(page.element('export').disabled, true);
    assert.match(page.element('connection').textContent, /run stopped/i);
    assert.equal(page.pending(), 0);
  } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
});

test('Stop confirmation failures retain uncertainty and retry until verified idle', async () => {
  for (const failure of [
    () => { throw Error('CONTROLLED_STOP_CONFIRMATION_NETWORK_FAILURE'); },
    () => response({ error: 'CONTROLLED_STOP_CONFIRMATION_HTTP_FAILURE' }, 503),
    { local: true, token: 'CONTROLLED_TEST_ONLY_TOKEN' },
  ]) {
    const page = await fixture([status(true), { stopped: true }, failure, status(false)]);
    try {
      await page.element('stop-run').onclick();
      assert.equal(page.requests[2]?.url, '/api/status');
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.element('stop-run').disabled, true);
      assert.match(page.element('connection').textContent, /may still be running/i);
      assert.doesNotMatch(page.element('toast').textContent, /run stopped/i);
      page.element('language').onclick();
      assert.match(page.element('connection').textContent, /serveur est peut-être toujours actif/i);
      assert.equal(page.pending(), 1); await page.poll();
      assert.equal(page.element('run').disabled, false);
      assert.equal(page.element('restore').disabled, false);
      assert.doesNotMatch(page.element('connection').textContent, /CONTROLLED_STOP_CONFIRMATION/);
      assert.equal(page.pending(), 0);
    } finally { page.cleanup(); }
  }
});

test('page lifecycle aborts and fences pending Stop confirmation then resumes on return', async () => {
  const waiting = deferred();
  const page = await fixture([status(true), { stopped: true }, () => waiting.promise, status(true), status(false)]);
  try {
    const stopping = page.element('stop-run').onclick(); await flush();
    assert.equal(page.requests[2]?.url, '/api/status');
    page.dispatch('pagehide');
    assert.equal(page.requests[2].options.signal.aborted, true);
    waiting.resolve(response(status(false))); await stopping;
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.equal(page.pending(), 0);
    page.dispatch('pageshow'); await flush();
    assert.equal(page.requests[3]?.url, '/api/status');
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.element('run').disabled, false);
    assert.equal(page.element('restore').disabled, false);
    assert.match(page.element('connection').textContent, /run stopped/i);
    assert.equal(page.pending(), 0);
  } finally { waiting.resolve(response(status(false))); await flush(); page.cleanup(); }
});

// Additional inert schedule: no product, Git, browser, native or network execution.
test('a failed Run must not unlock restore while its concurrent Stop response is pending', async () => {
  const runFailure = deferred(), stopReply = deferred();
  const page = await fixture([status(false), () => runFailure.promise, () => stopReply.promise, status(false)]);
  let stopping;
  try {
    const running = page.element('run').onclick(); await flush();
    stopping = page.element('stop-run').onclick(); await flush();
    assert.equal(page.requests[2].url, '/api/stop');
    runFailure.resolve(response({ error: 'CONTROLLED_RUN_REJECTS_DURING_STOP' }, 409));
    await running; await flush();
    assert.equal(page.element('run').disabled, true, 'Run stays guarded until Stop settles');
    assert.equal(page.element('restore').disabled, true, 'Restore stays guarded until Stop settles');
    assert.equal(page.element('stop-run').disabled, true, 'Duplicate Stop stays refused');
  } finally {
    runFailure.resolve(response({ error: 'CONTROLLED_RUN_REJECTS_DURING_STOP' }, 409));
    stopReply.resolve(response({ stopped: true }));
    if (stopping) await stopping;
    await flush(); page.cleanup();
  }
});

test('hidden return and idle status cannot release pending Stop or admit a late Run result', async () => {
  const runReply = deferred(), stopReply = deferred();
  const page = await fixture([status(false), () => runReply.promise, () => stopReply.promise, status(false), status(true), status(false)]);
  let stopping;
  try {
    const retained = { schema: 'tae.interface-export.v1', evidence: { evm: { controlledTestOnly: 'prior-evidence' } }, currentProof: null, authority: [] };
    await page.element('restore').onchange({ target: { value: 'controlled-historical-file', files: [{ size: 100, text: async () => JSON.stringify(retained) }] } });
    assert.equal(page.element('export').disabled, false);
    const running = page.element('run').onclick(); await flush();
    stopping = page.element('stop-run').onclick(); await flush();
    assert.equal(page.requests[1].options.signal.aborted, true);
    page.dispatch('pagehide'); page.dispatch('pageshow'); await flush();
    assert.equal(page.requests[3].url, '/api/status');
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.equal(page.element('stop-run').disabled, true);
    await page.element('run').onclick(); await page.element('stop-run').onclick();
    assert.equal(page.requests.length, 4, 'Pending Stop refuses both new and duplicate actions');
    runReply.resolve(response({ evm: { controlledTestOnly: 'late-run-result' } })); await running; await flush();
    assert.match(page.element('contract-data').textContent, /prior-evidence/);
    assert.doesNotMatch(page.element('contract-data').textContent, /late-run-result/);
    stopReply.resolve(response({ error: 'CONTROLLED_PENDING_STOP_FAILURE' }, 503)); await stopping; await flush();
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.equal(page.element('stop-run').disabled, false);
    assert.match(page.element('toast').textContent, /stop request failed.*may still be running/i);
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.element('run').disabled, true);
    assert.equal(page.element('restore').disabled, true);
    assert.equal(page.pending(), 1); await page.poll();
    assert.equal(page.element('restore').disabled, false);
    assert.doesNotMatch(page.element('connection').textContent, /completed|fresh/i);
    assert.equal(page.requests.filter(request => request.options.method === 'POST').length, 2);
  } finally {
    runReply.resolve(response({ evm: { controlledTestOnly: 'late-run-result' } }));
    stopReply.resolve(response({ error: 'CONTROLLED_PENDING_STOP_FAILURE' }, 503));
    if (stopping) await stopping;
    await flush(); page.cleanup();
  }
});

for (const stopFails of [false, true]) {
  test(`a pre-ack idle read cannot release guards after Stop ${stopFails ? 'fails' : 'succeeds'}`, async () => {
    const runReply = deferred(), stopReply = deferred(), beforeAck = deferred(), afterAck = deferred();
    const page = await fixture([status(false), () => runReply.promise, () => stopReply.promise, () => beforeAck.promise, () => afterAck.promise, status(false)]);
    let stopping;
    try {
      const running = page.element('run').onclick(); await flush();
      stopping = page.element('stop-run').onclick(); await flush();
      page.dispatch('pagehide'); page.dispatch('pageshow'); await flush();
      const reading = page.requests[3]; assert.equal(reading.url, '/api/status');
      assert.equal(page.element('stop-run').disabled, true);
      stopReply.resolve(stopFails ? response({ error: 'CONTROLLED_STOP_SETTLES_WITH_FAILURE' }, 503) : response({ stopped: true }));
      if (stopFails) {
        await stopping; await flush();
        assert.equal(page.pending(), 1); await page.poll();
      } else { await flush(); }
      assert.equal(reading.options.signal.aborted, true, 'A pre-ack status generation must be fenced at Stop settlement');
      assert.equal(page.requests[4].url, '/api/status');
      assert.equal(page.requests.length, 5, 'Only one fresh post-ack read is pending');
      beforeAck.resolve(response(status(false))); await flush();
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.element('stop-run').disabled, !stopFails, 'Successful Stop keeps the accepted duplicate-Stop guard until idle');
      assert.equal(page.pending(), 0, 'The aborted pre-ack read cannot schedule another read');
      assert.equal(page.requests.length, 5);
      runReply.resolve(response({ error: 'CONTROLLED_OLD_RUN_COMPLETION' }, 409)); await running; await flush();
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      afterAck.resolve(response(status(true))); if (!stopFails) await stopping; await flush();
      assert.equal(page.element('run').disabled, true);
      assert.equal(page.element('restore').disabled, true);
      assert.equal(page.pending(), 1); await page.poll();
      assert.equal(page.element('run').disabled, false);
      assert.equal(page.element('restore').disabled, false);
      assert.equal(page.element('stop-run').disabled, true);
      assert.equal(page.pending(), 0);
      assert.equal(page.requests.filter(request => request.options.method === 'POST').length, 2);
      assert.doesNotMatch(page.element('connection').textContent, /completed|fresh/i);
    } finally {
      runReply.resolve(response({ error: 'CONTROLLED_OLD_RUN_COMPLETION' }, 409));
      stopReply.resolve(response({ stopped: true })); beforeAck.resolve(response(status(false))); afterAck.resolve(response(status(false)));
      if (stopping) await stopping;
      await flush(); page.cleanup();
    }
  });
}
