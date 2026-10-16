// SPDX-License-Identifier: Apache-2.0
// Inspect the exact private HTTPS relay body with a fake fetch. No network or signing occurs.
const { expect } = require('chai');
const fs = require('fs');
const vm = require('vm');
const { createRequire } = require('module');
const filename = require.resolve('../scripts/authority-session');
function factory(fetch) {
    const module = { exports: {} };
    // Test-only exposure of the unmodified private function; no production export/bypass is added.
    vm.runInNewContext(fs.readFileSync(filename, 'utf8') + '\nmodule.exports.inspectRelay = createRawRelay;\n',
        { require: createRequire(filename), module, exports: module.exports, fetch, URL, Buffer, AbortSignal, process: { argv: [] }, console }, { filename });
    return module.exports.inspectRelay;
}
async function rejects(fn, text) { let error; try { await fn(); } catch (e) { error = e; } expect(error && typeof error.message === 'string').to.equal(true); if (text) expect(error.message).to.include(text); return error; }
describe('Alpha user-run raw relay transport (fake HTTP only)', () => {
    it('keeps the real relay factory private and rejects insecure/credential endpoints before fetch', async () => {
        expect(require('../scripts/authority-session').createRawRelay).to.equal(undefined);
        let calls = 0; const create = factory(() => { calls++; });
        for (const url of ['http://127.0.0.1', 'https://user:secret@example.invalid', 'https://example.invalid/#secret']) await rejects(() => create(url), 'HTTPS');
        expect(calls).to.equal(0);
    });
    it('posts exactly once with the exact raw bytes, timeout and redirect rejection', async () => {
        const hash = '0x' + '12'.repeat(32), calls = [];
        const relay = factory(async (url, request) => { calls.push({ url, request }); return new Response(JSON.stringify({ jsonrpc: '2.0', id: 1, result: hash })); })('https://example.invalid/operator-secret');
        expect(await relay('0x02abcd')).to.equal(hash); expect(calls.length).to.equal(1);
        const request = calls[0].request; expect(request.method).to.equal('POST'); expect(request.redirect).to.equal('error'); expect(request.signal).to.exist;
        expect(JSON.parse(request.body)).to.deep.equal({ jsonrpc: '2.0', id: 1, method: 'eth_sendRawTransaction', params: ['0x02abcd'] });
        await rejects(() => relay('0x02abcd'), 'one-shot'); expect(calls.length).to.equal(1);
    });
    it('redacts ambiguous errors and refuses retries after oversized or malformed responses', async () => {
        for (const reply of [() => { throw Error('https://provider.invalid/SECRET'); }, () => new Response('x'.repeat(65537)),
            () => new Response(JSON.stringify({ jsonrpc: '2.0', id: 9, result: '0x' + '12'.repeat(32) })), () => new Response('redirect', { status: 302 }),
            () => new Response(JSON.stringify({ jsonrpc: '2.0', id: 1, error: { message: 'SECRET' } }))]) {
            let calls = 0; const relay = factory(async () => { calls++; return reply(); })('https://example.invalid/SECRET');
            const error = await rejects(() => relay('0x02abcd'), 'ambiguous'); expect(error.message).not.to.include('SECRET');
            await rejects(() => relay('0x02abcd'), 'one-shot'); expect(calls).to.equal(1);
        }
    });
});
