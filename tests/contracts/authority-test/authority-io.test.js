// SPDX-License-Identifier: Apache-2.0
// Offline fixtures and numeric-loopback mock HTTP only. No public provider is contacted.
const { expect } = require('chai');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { ethers } = require('ethers');
const policy = require('../scripts/mainnet-authority');
const legacy = require('../scripts/mainnet');
const transport = require('../scripts/authority-rpc');
const exporter = require('../scripts/authority-verification-package');
const { AGIALPHA_ADDRESS: TOKEN } = require('../../../token.config');
const revision = { commit: 'bd1728f067e3fd1e94d81a19142733d308de1e43', tree: '19e498dd8d082a397555ed2006269512422444fb', lockSha256: '070e3c6652f4939fabe14788a0c80b38ed3d6e2ad792cebad4a5bbf842308667' };
const address = n => ethers.getAddress(`0x${n.toString(16).padStart(40, '0')}`);
const graph = [1, 2, 3, 4, 5].map(address), scope = { graph, all: [...graph, address(6)], earliestBlock: 1 };
const hash = n => ethers.keccak256(ethers.toUtf8Bytes(String(n)));
const clone = x => JSON.parse(JSON.stringify(x));
async function rejects(fn, match) { let error; try { await fn(); } catch (e) { error = e; } expect(error).to.be.instanceOf(Error); if (match) expect(error.message).to.include(match); return error; }
function config() {
    const governor = address(102);
    return { schema: 'agialpha.mainnet.config.v2', chainId: 1, deployer: address(101), nonce: 7, block: { number: 100, hash: hash(100) },
        governor: { kind: 'ledger-eoa', address: governor, addressAcknowledgement: governor },
        dependencies: Object.fromEntries(Object.entries({ token: TOKEN, ens: legacy.ENS, wrapper: legacy.WRAPPER }).map(([k, a]) => [k, { address: a, codeHash: hash('code') }])),
        rootOwners: Object.fromEntries(legacy.roots.map(n => [n, address(106)])), parameters: { minimumValidatorStake: '10000000000000000000', minimumAgentStake: '10000000000000000000', quorum: 2, maximumRiskBps: 2000 },
        sender: { mode: policy.EMPTY }, envelope: { gasLimit: '8000000', maxFeePerGas: '10000000000', maxPriorityFeePerGas: '1000000000', accessList: [] } };
}
function journal(c) { return { schema: 'ethereum.cross-project-nonce-journal.v1', journalId: 'offline-io-fixture', revision: 1, chainId: 1, sender: c.deployer, scope: ['alpha', 'jobs', 'manager'], block: c.block,
    latestNonce: c.nonce, pendingNonce: c.nonce, allocations: [{ project: 'alpha', startNonce: c.nonce, count: 5 }] }; }
function log(number = 1) { return { address: graph[0], removed: false, blockNumber: ethers.toQuantity(number), blockHash: hash(number), transactionHash: hash('tx'), transactionIndex: '0x0', logIndex: '0x0', data: '0x', topics: [hash('event')] }; }
describe('Alpha v2 bounded read-only I/O and source export', function () {
    this.timeout(120000);
    let server, url, received, handler, temporary, compiled, plan;
    before(async () => { compiled = policy.compiledContracts(); const c = config(); plan = await policy.makePlan(c, compiled, revision, journal(c)); });
    beforeEach(async () => {
        received = []; temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-io-'));
        handler = (q, res) => res.end(JSON.stringify({ jsonrpc: '2.0', id: q.id, result: q.method === 'eth_getBlockByNumber' ? { number: q.params[0], hash: hash(q.params[0]) } : q.method === 'eth_getLogs' ? [] : '0x1' }));
        server = http.createServer((req, res) => { let text = ''; req.on('data', c => text += c); req.on('end', () => { const q = JSON.parse(text); received.push(q); handler(q, res); }); });
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve)); url = `http://127.0.0.1:${server.address().port}/secret-provider-key`;
    });
    afterEach(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); fs.rmSync(temporary, { recursive: true, force: true }); });
    const rpc = (url, limits) => transport.createTestReadOnlyRpc(url, scope, { limits });
    it('rejects insecure production endpoints, embedded credentials, unsupported options and increased caps', async () => {
        for (const endpoint of [url, 'https://user:password@example.invalid', 'https://example.invalid/#secret']) await rejects(() => transport.createReadOnlyRpc(endpoint, scope));
        await rejects(() => transport.createTestReadOnlyRpc('http://example.invalid', scope));
        await rejects(() => rpc(url, { requests: 2001 }));
        await rejects(() => transport.createReadOnlyRpc('https://example.invalid', scope, { fetchImpl: () => {} }));
        expect(received).to.have.length(0);
    });
    it('rejects all mutation/signing methods, state overrides and out-of-scope reads before HTTP', async () => {
        for (const method of ['eth_sendRawTransaction', 'eth_sendTransaction', 'eth_sign', 'personal_sign', 'hardhat_reset', 'wallet_sendCalls']) await rejects(() => rpc(url)(method, []), 'allowlisted');
        for (const [method, args] of [['eth_call', [{ to: graph[0], data: '0x' }, 'latest', {}]], ['eth_call', [{ to: graph[0], data: '0x', from: graph[1] }, 'latest']], ['eth_getCode', [address(999), 'latest']], ['eth_getBlockByNumber', ['latest', true, {}]]]) await rejects(() => rpc(url)(method, args), 'scope');
        expect(received).to.have.length(0);
    });
    it('allows scoped reads and retains shared cumulative counters', async () => {
        const read = rpc(url); expect(await read('eth_chainId', [])).to.equal('0x1');
        expect(await read('eth_getTransactionCount', [graph[0], 'pending'])).to.equal('0x1');
        expect(read.stats().requests).to.equal(2); expect(read.stats().totalBytes).to.be.greaterThan(0);
    });
    it('allows only scoped well-shaped balance reads and validates quantity results', async () => {
        expect(await rpc(url)('eth_getBalance', [graph[0], 'latest'])).to.equal('0x1');
        for (const args of [[address(999), 'latest'], [graph[0], 'latest', {}], [graph[0], 'unbounded']])
            await rejects(() => rpc(url)('eth_getBalance', args), 'scope');
        expect(received).to.have.length(1);
        handler = (q, res) => res.end(JSON.stringify({ jsonrpc: '2.0', id: q.id, result: '100' }));
        await rejects(() => rpc(url)('eth_getBalance', [graph[0], 'pending']), 'Malformed');
    });
    it('rejects redirects without following them and redacts endpoint/provider errors', async () => {
        handler = (q, res) => { res.writeHead(302, { location: 'https://secret.invalid/token' }); res.end('secret-provider-key'); };
        const read = rpc(url), e = await rejects(() => read('eth_chainId', []), 'HTTP');
        expect(e.message).not.to.include('secret'); expect(received).to.have.length(1); expect(read.stats().stopped).to.equal(true);
        await rejects(() => read('eth_chainId', []), 'stopped'); expect(received).to.have.length(1);
    });
    it('rejects malformed, mismatched, extra-field and error JSON responses', async () => {
        for (const response of ['not-json', { jsonrpc: '2.0', id: 99, result: '0x1' }, { jsonrpc: '2.0', id: 1, result: '0x1', error: { message: 'secret' } }, { jsonrpc: '2.0', id: 1, result: {} }]) {
            handler = (q, res) => res.end(typeof response === 'string' ? response : JSON.stringify(response));
            const e = await rejects(() => rpc(url)('eth_chainId', []), 'Malformed'); expect(e.message).not.to.include('secret');
        }
    });
    it('caps declared and streamed/chunked responses without trusting content-length', async () => {
        handler = (q, res) => { res.writeHead(200, { 'content-length': 999 }); res.end('x'); };
        await rejects(() => rpc(url, { responseBytes: 100 })('eth_chainId', []), 'byte budget');
        handler = (q, res) => { res.writeHead(200); res.write('x'.repeat(60)); res.end('y'.repeat(60)); };
        await rejects(() => rpc(url, { responseBytes: 100 })('eth_chainId', []), 'byte budget');
    });
    it('enforces timeout, operation deadline and total request/byte budgets', async () => {
        const normal = handler; handler = () => {};
        await rejects(() => rpc(url, { timeoutMs: 15 })('eth_chainId', []), 'timeout'); handler = normal;
        const read = rpc(url, { requests: 1 }); await read('eth_chainId', []); await rejects(() => read('eth_chainId', []), 'request budget');
        await rejects(() => rpc(url, { totalBytes: 1 })('eth_chainId', []), 'byte budget');
        const deadline = rpc(url, { deadlineMs: 5 }); await new Promise(resolve => setTimeout(resolve, 15)); await rejects(() => deadline('eth_chainId', []), 'deadline');
    });
    it('refuses latest/unbounded/mutated-address/oversized log scopes before HTTP', async () => {
        for (const filter of [{ address: graph, fromBlock: '0x1', toBlock: 'latest' }, { address: graph.slice(1), fromBlock: '0x1', toBlock: '0x2' }, { address: [...graph.slice(1), address(99)], fromBlock: '0x1', toBlock: '0x2' }, { address: graph, fromBlock: '0x0', toBlock: '0x2' }, { address: graph, fromBlock: '0x1', toBlock: ethers.toQuantity(100001) }, { address: graph, fromBlock: '0x1', toBlock: '0x2', topics: [] }]) await rejects(() => rpc(url)('eth_getLogs', [filter]), 'scope');
        expect(received).to.have.length(0);
    });
    it('chunks logs with the same cumulative budget and canonical boundary rechecks', async () => {
        const read = rpc(url); expect(await read('eth_getLogs', [{ address: graph, fromBlock: '0x1', toBlock: ethers.toQuantity(2001) }])).to.deep.equal([]);
        const batches = received.filter(q => q.method === 'eth_getLogs'); expect(batches).to.have.length(3);
        expect(batches.map(q => q.params[0].toBlock)).to.deep.equal([1000, 2000, 2001].map(ethers.toQuantity)); expect(read.stats().requests).to.equal(7);
        await rejects(() => rpc(url, { requests: 2 })('eth_getLogs', [{ address: graph, fromBlock: '0x1', toBlock: '0x2' }]), 'request budget');
    });
    it('rejects duplicate, removed, malformed and out-of-interval or wrong-address logs', async () => {
        const normal = handler;
        for (const entries of [[log(), log()], [{ ...log(), removed: true }], [{ ...log(), address: address(99) }], [log(99)], [{ ...log(), topics: ['0x1234'] }]]) {
            handler = (q, res) => q.method === 'eth_getLogs' ? res.end(JSON.stringify({ jsonrpc: '2.0', id: q.id, result: entries })) : normal(q, res);
            await rejects(() => rpc(url)('eth_getLogs', [{ address: graph, fromBlock: '0x1', toBlock: '0x2' }]));
        }
    });
    it('rejects canonical boundary reorgs and aggregate log-count overflow', async () => {
        let blocks = 0; const normal = handler;
        handler = (q, res) => { if (q.method === 'eth_getBlockByNumber') { blocks++; res.end(JSON.stringify({ jsonrpc: '2.0', id: q.id, result: { number: q.params[0], hash: hash(blocks > 2 ? 'reorg' : q.params[0]) } })); } else normal(q, res); };
        await rejects(() => rpc(url)('eth_getLogs', [{ address: graph, fromBlock: '0x1', toBlock: '0x2' }]), 'boundary changed');
        handler = (q, res) => q.method === 'eth_getLogs' ? res.end(JSON.stringify({ jsonrpc: '2.0', id: q.id, result: [log(), { ...log(), logIndex: '0x1' }] })) : normal(q, res);
        await rejects(() => rpc(url, { logs: 1 })('eth_getLogs', [{ address: graph, fromBlock: '0x1', toBlock: '0x2' }]), 'log count');
    });
    it('exports exact v2 Standard JSON, qualified compiler, constructors and hashed prediction labels', async () => {
        const bundle = await exporter.plannedPackage(plan, revision, compiled);
        expect(bundle.manifest.schema).to.equal('agialpha.explorer-verification-package.v2'); expect(bundle.manifest.addressStatus).to.equal('predicted');
        expect(bundle.manifest.sourceClosureSha256).to.equal(policy.digest(plan.builds));
        for (const [i, name] of policy.NAMES.entries()) {
            const request = JSON.parse(bundle.files[`${name}/etherscan-request.json`]);
            expect(JSON.parse(request.sourceCode)).to.deep.equal(plan.builds[plan.contracts[name].buildId].input);
            expect(request.contractaddress).to.equal(plan.transactions[i].expectedAddress);
            expect(request.contractname).to.equal(`${plan.contracts[name].sourceName}:${name}`);
            expect(ethers.concat([plan.contracts[name].bytecode, `0x${request.constructorArguments}`])).to.equal(plan.transactions[i].envelope.data);
            expect(bundle.manifest.contracts[name].addressStatus).to.equal('predicted');
        }
        for (const [name, digest] of Object.entries(bundle.manifest.files)) expect(policy.digest(bundle.files[name])).to.equal(digest);
        expect(bundle.files['README.txt']).not.to.include('predates later settlement fixes'); expect(bundle.files['README.txt']).not.to.include('recorded deployment is immutable');
        const destination = path.join(temporary, 'package'); exporter.writePackage(bundle, destination);
        expect(fs.readFileSync(path.join(destination, 'manifest.json'), 'utf8')).to.equal(bundle.files['manifest.json']);
        await rejects(() => exporter.writePackage(bundle, destination));
    });
    it('refuses missing or altered independent revision, source drift and v1-policy substitution', async () => {
        await rejects(() => exporter.plannedPackage(plan, undefined, compiled), 'independently observed');
        for (const key of ['commit', 'tree', 'lockSha256']) {
            const p = clone(plan); p.revision[key] = 'a'.repeat(p.revision[key].length); delete p.payloadSha256; const sealed = policy.seal(p);
            await rejects(() => exporter.plannedPackage(sealed, revision, compiled), 'revision differs');
        }
        const p = clone(plan), build = p.builds[p.contracts.NovaSeed.buildId]; build.input.sources[p.contracts.NovaSeed.sourceName].content += '\n// drift'; delete p.payloadSha256;
        await rejects(() => exporter.plannedPackage(policy.seal(p), revision, compiled), 'source/constructor mismatch');
        const old = clone(plan); old.schema = 'agialpha.mainnet.unsigned-plan.v1'; delete old.payloadSha256;
        await rejects(() => exporter.plannedPackage(policy.seal(old), revision, compiled), 'policy');
    });
    it('refuses unverified receipt claims before producing a receipt-proven package', async () => {
        let calls = 0; const read = async () => { calls++; throw Error('no provider fixture'); };
        await rejects(() => exporter.receiptProvenPackage(plan, read, {}, undefined, compiled), 'independently observed'); expect(calls).to.equal(0);
        await rejects(() => exporter.receiptProvenPackage(plan, read, { graphAuthorityVerified: true }, revision, compiled)); expect(calls).to.equal(0);
    });
    it('refuses symlink parents/outputs and traversal package members', async () => {
        const bundle = await exporter.plannedPackage(plan, revision, compiled);
        fs.symlinkSync(temporary, path.join(temporary, 'alias'));
        await rejects(() => exporter.writePackage(bundle, path.join(temporary, 'alias', 'package')));
        await rejects(() => exporter.writePackage(bundle, path.join(temporary, 'alias')));
        await rejects(() => exporter.writePackage({ files: { 'manifest.json': '{}', '../escape': 'x' } }, path.join(temporary, 'bad')));
        expect(fs.existsSync(path.join(temporary, 'bad'))).to.equal(false);
    });
});
