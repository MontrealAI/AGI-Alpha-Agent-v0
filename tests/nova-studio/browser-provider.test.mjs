// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('./browser-provider.js', import.meta.url), 'utf8');
function fixture(fetch) {
    const window = { __novaActors: ['synthetic-local-account'], fetch };
    vm.runInNewContext(source, { window });
    return window;
}
const response = result => ({ json: async () => ({ result }) });
const invoke = window => window.ethereum.request({ method: 'eth_call', params: [{ private: 'never-retain-this' }] });

test('pending metadata is cleared after successful response without retaining parameters or response values', async () => {
    let release;
    const window = fixture(() => new Promise(resolve => { release = resolve; }));
    const pending = invoke(window);
    assert.equal(window.__nova.pendingReads.length, 1);
    const entry = window.__nova.pendingReads[0];
    assert.deepEqual(Object.keys(entry), ['id', 'method', 'startedAt']);
    assert.equal(entry.method, 'eth_call'); assert.ok(Number.isSafeInteger(entry.startedAt));
    release(response('private-response-value'));
    assert.equal(await pending, 'private-response-value');
    assert.equal(window.__nova.pendingReads.length, 0);
    assert.equal(window.__nova.recentReads.length, 1);
    assert.equal(window.__nova.recentReads[0].outcome, 'completed');
    assert.equal(window.__nova.recentReads[0].errorCode, null);
    assert.ok(window.__nova.recentReads[0].finishedAt >= entry.startedAt);
    const recorded = JSON.stringify([window.__nova.pendingReads, window.__nova.recentReads]);
    assert.equal(recorded.includes('never-retain-this'), false);
    assert.equal(recorded.includes('private-response-value'), false);
});

test('RPC and transport errors clear pending metadata and preserve the original error', async () => {
    const rpc = fixture(async () => ({ json: async () => ({ error: { message: 'private-rpc-message', code: -32000 } }) }));
    await assert.rejects(invoke(rpc), error => error.code === -32000 && error.message === 'private-rpc-message');
    assert.equal(rpc.__nova.pendingReads.length, 0);
    assert.equal(rpc.__nova.recentReads[0].outcome, 'failed');
    assert.equal(rpc.__nova.recentReads[0].errorCode, -32000);
    assert.equal(JSON.stringify(rpc.__nova.recentReads).includes('private-rpc-message'), false);
    const original = Error('private-transport-message');
    const transport = fixture(async () => { throw original; });
    await assert.rejects(invoke(transport), error => error === original);
    assert.equal(transport.__nova.pendingReads.length, 0);
    assert.equal(transport.__nova.recentReads[0].errorCode, null);
    assert.equal(JSON.stringify(transport.__nova.recentReads).includes('private-transport-message'), false);
});

test('active and completed metadata remain bounded to 32 entries without canceling requests', async () => {
    const releases = [];
    const window = fixture(() => new Promise(resolve => { releases.push(resolve); }));
    const pending = Array.from({ length: 40 }, () => invoke(window));
    assert.equal(window.__nova.pendingReads.length, 32);
    assert.equal(releases.length, 40);
    releases.forEach(release => release(response('0xresult')));
    assert.equal((await Promise.all(pending)).length, 40);
    assert.equal(window.__nova.pendingReads.length, 0);
    assert.equal(window.__nova.recentReads.length, 32);
    assert.ok(window.__nova.recentReads.every(entry => entry.outcome === 'completed'));
    assert.equal(window.__nova.sends, 0);
});

test('synthetic transport loss preserves the original successful broadcast and never retries', async () => {
    let requests = 0;
    const window = fixture(async () => { requests += 1; return response('0xactual-local-hash'); });
    window.__nova.loseNext = true;
    await assert.rejects(window.ethereum.request({ method: 'eth_sendTransaction', params: [{ from: 'synthetic-owner' }] }),
        /Synthetic transport loss AFTER real local broadcast/);
    assert.equal(requests, 1); assert.equal(window.__nova.sends, 1);
    assert.equal(window.__nova.lastHash, '0xactual-local-hash'); assert.equal(window.__nova.loseNext, false);
    assert.equal(window.__nova.pendingReads.length, 0);
    assert.equal(window.__nova.recentReads[0].method, 'eth_sendTransaction');
    assert.equal(window.__nova.recentReads[0].outcome, 'failed');
    assert.equal(JSON.stringify(window.__nova.recentReads).includes('synthetic-owner'), false);
    assert.equal(JSON.stringify(window.__nova.recentReads).includes('0xactual-local-hash'), false);
});
