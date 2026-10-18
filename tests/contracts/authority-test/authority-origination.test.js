// SPDX-License-Identifier: Apache-2.0
// Offline, disposable engine and numeric loopback only. No selected-account qualification.
const { expect } = require('chai');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { ethers: E, network } = require('hardhat');
const policy = require('../scripts/mainnet-authority');
const origin = require('../scripts/authority-origination');
const legacy = require('../scripts/mainnet');
const transport = require('../scripts/authority-rpc');
const exporter = require('../scripts/authority-verification-package');
const { installToken } = require('../test/utils/token');
const { requireDisposableLocalNetwork } = require('../scripts/disposable');
const { AGIALPHA_ADDRESS: TOKEN } = require('../../../token.config');
const revision = process.env.ALPHA_EXPECTED_HEAD_SHA ? require('../scripts/authority-revision').reviewedRevision() : { commit: 'bd1728f067e3fd1e94d81a19142733d308de1e43', tree: '19e498dd8d082a397555ed2006269512422444fb', lockSha256: '070e3c6652f4939fabe14788a0c80b38ed3d6e2ad792cebad4a5bbf842308667' };
const address = n => E.getAddress('0x' + n.toString(16).padStart(40, '0'));
const clone = x => JSON.parse(JSON.stringify(x));
const fixture = policy.digest('SYNTHETIC DISPOSABLE EVIDENCE ONLY; NO QUALIFICATION');
const delegateCode = '0x600160005500'; // would change slot0 if executed
function config(deployer = address(101), governor = address(102)) {
    const target = address(201);
    return { schema: 'agialpha.mainnet.config.v2', chainId: 1, deployer, nonce: 7, block: { number: 100, hash: E.id('synthetic pin') },
        governor: { kind: 'ledger-eoa', address: governor, addressAcknowledgement: governor },
        dependencies: Object.fromEntries(Object.entries({ token: TOKEN, ens: legacy.ENS, wrapper: legacy.WRAPPER }).map(([k, a]) => [k, { address: a, codeHash: E.keccak256('0x6000') }])),
        rootOwners: Object.fromEntries(legacy.roots.map(n => [n, address(106)])), parameters: { minimumValidatorStake: '10000000000000000000', minimumAgentStake: '10000000000000000000', quorum: 2, maximumRiskBps: 2000 },
        sender: { mode: origin.MARKER, delegationCode: '0xef0100' + target.slice(2).toLowerCase(), target, targetCodeHash: E.keccak256(delegateCode),
            storageChecks: [{ address: deployer, slot: E.ZeroHash, value: E.ZeroHash }, { address: target, slot: E.ZeroHash, value: E.ZeroHash }], qualification: null },
        envelope: { gasLimit: '8000000', maxFeePerGas: '10000000000', maxPriorityFeePerGas: '1000000000', accessList: [] } };
}
function journal(c) { return { schema: 'ethereum.cross-project-nonce-journal.v1', journalId: 'synthetic-marker-origin', revision: 1, chainId: 1, sender: c.deployer, scope: ['alpha', 'jobs', 'manager'], block: c.block,
    latestNonce: c.nonce, pendingNonce: c.nonce, allocations: [{ project: 'alpha', startNonce: c.nonce, count: 5 }] }; }
function qualify(c, compiled, j = journal(c), tracesHash = fixture) {
    const scope = policy.qualificationRequest(c, compiled, revision, j).scope;
    const reports = {
        consensusEvidenceSha256: { schema: 'agialpha.direct-consensus-report.v1', disposition: 'direct-type2-create-does-not-invoke-origin-code', scope,
            reviewReference: 'SYNTHETIC fixture; never an actual-account qualification', artifacts: { consensusSourceSha256: fixture, analysisSha256: fixture } },
        directExecutionEvidenceSha256: { schema: 'agialpha.direct-execution-report.v1', disposition: 'five-direct-creates-no-creator-or-target-invocation', scope,
            reviewReference: 'SYNTHETIC fixture; never an actual-account qualification', artifacts: { sourceCallGraphSha256: fixture, initcodeCallGraphSha256: fixture, traceSha256: tracesHash }, invocations: { creator: 0, target: 0 } }
    };
    c.sender.qualification = Object.fromEntries(Object.entries(reports).map(([k, report]) => [k, policy.digest(report)]));
    return { schema: 'agialpha.marker-direct-qualification-evidence.v1', scope, reports };
}
async function rejects(fn, match) { let e; try { await fn(); } catch (error) { e = error; } expect(e).to.be.instanceOf(Error); if (match) expect(e.message).to.include(match); return e; }
function mockRpc(c, reads = []) {
    return async (m, a) => {
        reads.push({ method: m, params: a });
        if (m === 'eth_chainId') return '0x1';
        if (m === 'eth_getBlockByNumber') return { number: E.toQuantity(c.block.number), hash: c.block.hash, timestamp: '0x100', gasLimit: '0x1c9c380' };
        if (m === 'eth_getCode') {
            if (a[0] === c.deployer) return c.sender.delegationCode;
            if (a[0] === c.sender.target) return delegateCode;
            if (Object.values(c.dependencies).some(d => d.address.toLowerCase() === a[0].toLowerCase())) return '0x6000';
            return '0x';
        }
        if (m === 'eth_getTransactionCount') return E.toQuantity(a[0] === c.deployer ? c.nonce : 0);
        if (m === 'eth_getStorageAt') return E.ZeroHash;
        if (m === 'eth_call') {
            expect([c.deployer, c.sender.target]).not.to.include(a[0].to);
            if (a[0].data.startsWith(E.id('decimals()').slice(0, 10))) return E.AbiCoder.defaultAbiCoder().encode(['uint8'], [18]);
            if (a[0].data.startsWith(E.id('owner(bytes32)').slice(0, 10))) return E.AbiCoder.defaultAbiCoder().encode(['address'], [c.rootOwners[legacy.roots[0]]]);
        }
        throw Error('Unexpected mock request');
    };
}
let compiled, indirectCounterexample;
describe('Additive marker direct-origination profile', function () {
    this.timeout(180000);
    before(() => { if (process.env.ALPHA_EXPECTED_HEAD_SHA) expect(revision.commit).equals(process.env.ALPHA_EXPECTED_HEAD_SHA); compiled = policy.compiledContracts(); });
    it('derives review-only scopes and generic exact-address plans without changing old profiles', async () => {
        for (const creator of [address(101), address(103), '0x6c8B8897Fb6b08B4070387233B89b3E9A94eD00E']) {
            const c = config(creator), j = journal(c), request = policy.qualificationRequest(c, compiled, revision, j);
            expect(request.readyToSign).equals(false); expect(request.scope.operations).has.length(5);
            await rejects(() => policy.makePlan(c, compiled, revision, j));
            const evidence = qualify(c, compiled, j), p = await policy.makePlan(c, compiled, revision, j, evidence);
            await policy.checkPlan(p, compiled, revision);
            expect(p.transactions.every(t => t.envelope.type === 2 && t.envelope.to === null && t.envelope.from === creator && t.envelope.value === '0')).equals(true);
            expect(p.governanceCalls.every(t => t.from === c.governor.address && Object.values(p.addresses).includes(t.to))).equals(true);
            const bundle = await exporter.plannedPackage(p, revision, compiled);
            expect(bundle.manifest.senderMode).equals(origin.MARKER); expect(bundle.files['origination-evidence.json']).to.exist;
        }
        const c = config(); c.sender = { mode: policy.EMPTY };
        const p = await policy.makePlan(c, compiled, revision, journal(c)); expect(p).not.to.have.property('directOriginationEvidence');
        await rejects(() => policy.makePlan(c, compiled, revision, journal(c), {}), 'Only marker');
        const strict = config(); strict.sender.mode = policy.DELEGATED; await rejects(() => policy.makePlan(strict, compiled, revision, journal(strict)));
    });
    it('fails closed on malformed fields, dependency aliases, missing or changed report scope and claimed invocations', async () => {
        const original = config(), e = qualify(original, compiled), j = journal(original);
        for (const change of [c => c.sender.mode = 'type4', c => c.sender.delegationCode += '00', c => c.sender.target = c.deployer,
            c => c.sender.targetCodeHash = E.ZeroHash, c => c.sender.stateChecks = [], c => c.sender.storageChecks = null,
            c => c.sender.storageChecks[0].address = address(999), c => c.sender.storageChecks[0].slot = '0x0',
            c => c.sender.storageChecks.push(c.sender.storageChecks[0]), c => c.sender.qualification.forkEvidenceSha256 = fixture,
            c => { c.sender.target = TOKEN; c.sender.delegationCode = '0xef0100' + TOKEN.slice(2).toLowerCase(); c.sender.storageChecks = []; }]) {
            const c = clone(original); change(c); expect(() => policy.validateConfig(c)).to.throw();
        }
        await rejects(() => policy.makePlan(original, compiled, revision, j), 'fields');
        for (const change of [x => x.scope.creator = address(8), x => x.scope.operations[0].nonce++, x => x.scope.operations[0].to = address(8),
            x => x.scope.source.tree = 'a'.repeat(40), x => x.reports.directExecutionEvidenceSha256.invocations.target = 1,
            x => x.reports.directExecutionEvidenceSha256.scope.block.hash = E.id('other'), x => delete x.reports.consensusEvidenceSha256,
            x => x.reports.consensusEvidenceSha256.disposition = 'wallet-uncompromised']) {
            const evidence = clone(e); change(evidence); await rejects(() => policy.makePlan(original, compiled, revision, j, evidence));
        }
        // Rehashing a false claim does not turn it into the required proposition.
        const bad = clone(e); bad.reports.directExecutionEvidenceSha256.invocations.creator = 1;
        const c = clone(original); c.sender.qualification.directExecutionEvidenceSha256 = policy.digest(bad.reports.directExecutionEvidenceSha256);
        await rejects(() => policy.makePlan(c, compiled, revision, j, bad), 'invocation');
        const p = await policy.makePlan(original, compiled, revision, j, e); let reads = 0;
        await rejects(() => policy.preflight(p, async () => { ++reads; }, { ...revision, tree: 'f'.repeat(40) }), 'revision'); expect(reads).equals(0);
        for (const change of [x => x.config.parameters.quorum++, x => x.transactions[0].envelope.type = 4, x => x.transactions[0].envelope.to = original.deployer]) {
            const altered = clone(p); change(altered); const { payloadSha256, ...payload } = altered; await rejects(() => policy.checkPlan(policy.seal(payload), compiled, revision));
        }
    });
    it('performs only code/nonce/selected-storage reads on creator and target, with drift rejection', async () => {
        const c = config(), evidence = qualify(c, compiled), p = await policy.makePlan(c, compiled, revision, journal(c), evidence), reads = [];
        expect((await policy.preflight(p, mockRpc(c, reads), revision)).nextIndex).equals(0);
        expect(reads.filter(r => r.method === 'eth_getStorageAt')).has.length(4);
        expect(reads.some(r => r.method === 'eth_call' && [c.deployer, c.sender.target].includes(r.params[0].to))).equals(false);
        const noSlots = config(); noSlots.sender.storageChecks = []; const noSlotEvidence = qualify(noSlots, compiled), noSlotReads = [];
        const noSlotPlan = await policy.makePlan(noSlots, compiled, revision, journal(noSlots), noSlotEvidence);
        await policy.preflight(noSlotPlan, mockRpc(noSlots, noSlotReads), revision); expect(noSlotReads.some(r => r.method === 'eth_getStorageAt')).equals(false);
        for (const change of [(m, a) => m === 'eth_getStorageAt' ? E.toBeHex(1, 32) : undefined,
            (m, a) => m === 'eth_getCode' && a[0] === c.deployer ? '0x' : undefined,
            (m, a) => m === 'eth_getCode' && a[0] === c.sender.target ? '0x6000' : undefined,
            (m, a) => m === 'eth_getTransactionCount' && a[0] === c.deployer && a[1] === 'pending' ? '0x8' : undefined])
            await rejects(() => policy.preflight(p, (m, a) => change(m, a) ?? mockRpc(c)(m, a), revision));
    });
    it('bounds declared storage and refuses creator/target calls before loopback HTTP', async () => {
        const c = config(), evidence = qualify(c, compiled), p = await policy.makePlan(c, compiled, revision, journal(c), evidence), scope = transport.scopeForPlan(p), received = [];
        const server = http.createServer((req, res) => { let bytes = ''; req.on('data', x => bytes += x); req.on('end', () => { const q = JSON.parse(bytes); received.push(q); res.end(JSON.stringify({ jsonrpc: '2.0', id: q.id, result: E.ZeroHash })); }); });
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
        const url = 'http://127.0.0.1:' + server.address().port, rpc = () => transport.createTestReadOnlyRpc(url, scope);
        try {
            expect(await rpc()('eth_getStorageAt', [c.deployer, E.ZeroHash, 'latest'])).equals(E.ZeroHash);
            for (const args of [[c.deployer, E.toBeHex(1, 32), 'latest'], [address(999), E.ZeroHash, 'latest'], [c.deployer, '0x0', 'latest'], [c.deployer, E.ZeroHash, 'latest', {}]])
                await rejects(() => rpc()('eth_getStorageAt', args), 'scope');
            for (const to of [c.deployer, c.sender.target]) await rejects(() => rpc()('eth_call', [{ to, data: '0x' }, 'latest']), 'scope');
            for (const method of ['eth_sendRawTransaction', 'eth_sendTransaction', 'debug_traceTransaction']) await rejects(() => rpc()(method, []), 'allowlisted');
            for (const mutate of [s => s.storage = null, s => s.noCall = null, s => s.storage.push(s.storage[0]), s => s.noCall.push(s.noCall[0])]) {
                const s = clone(scope); mutate(s); expect(() => transport.createTestReadOnlyRpc(url, s)).to.throw();
            }
            expect(received).has.length(1);
        } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
    });
    it('rejects incomplete, unsupported, callback and indirectly delegated trace claims', () => {
        const creator = address(101), target = address(201), other = address(301);
        const simple = { failed: false, gas: 10, returnValue: '', structLogs: [{ depth: 1, pc: 0, op: 'STOP', stack: [] }] };
        expect(origin.analyzeTrace(simple, creator, target, {}).invocations).deep.equals({ creator: 0, target: 0 });
        for (const mutate of [t => t.failed = true, t => t.structLogs = [], t => t.structLogs[0].depth = 2, t => t.structLogs[0].op = 'CREATE', t => t.structLogs[0].op = 'SELFDESTRUCT', t => t.structLogs[0].op = 'FUTURECALL', t => t.structLogs[0].op = 'PUSH1']) {
            const t = clone(simple); mutate(t); expect(() => origin.analyzeTrace(t, creator, target, {})).to.throw();
        }
        for (const op of ['CALL', 'CALLCODE', 'STATICCALL', 'DELEGATECALL']) for (const to of [creator, target, other]) {
            const t = clone(simple); t.structLogs.unshift({ depth: 1, pc: 0, op, stack: [to.slice(2).padStart(64, '0'), 'ffff'] });
            if (to !== other) expect(() => origin.analyzeTrace(t, creator, target, {})).to.throw('invokes');
            else {
                expect(() => origin.analyzeTrace(t, creator, target, {})).to.throw('Missing');
                expect(() => origin.analyzeTrace(t, creator, target, { [other]: '0xef0100' + target.slice(2).toLowerCase() })).to.throw('Marker-bearing');
                expect(origin.analyzeTrace(t, creator, target, { [other]: '0x6000' }).calls).has.length(1);
            }
        }
    });
    it('rejects an actual indirect marker callee whose target is absent from CALL destinations', async () => {
        await requireDisposableLocalNetwork(); await E.provider.send('hardhat_reset', []);
        const [sender] = await E.getSigners(), alias = address(701), target = address(702), caller = address(703);
        await E.provider.send('hardhat_setCode', [target, '0xfe']);
        await E.provider.send('hardhat_setCode', [alias, '0xef0100' + target.slice(2).toLowerCase()]);
        await E.provider.send('hardhat_setCode', [caller, '0x6000600060006000600073' + alias.slice(2).toLowerCase() + '61fffff15000']);
        const tx = await sender.sendTransaction({ type: 2, to: caller, gasLimit: 200000 }), receipt = await tx.wait(); expect(receipt.status).equals(1);
        const trace = await E.provider.send('debug_traceTransaction', [tx.hash, { disableMemory: true, disableStorage: true, disableStack: false }]);
        const calls = trace.structLogs.filter(s => ['CALL', 'CALLCODE', 'STATICCALL', 'DELEGATECALL'].includes(s.op));
        expect(calls).has.length(1); expect(E.getAddress(E.toBeHex(BigInt('0x' + calls[0].stack.at(-2).replace(/^0x/, '')), 20))).equals(alias);
        expect(trace.structLogs.some(s => s.depth === 2 && s.op === 'INVALID')).equals(true);
        const code = await E.provider.send('eth_getCode', [alias, E.toQuantity(receipt.blockNumber)]);
        expect(() => origin.analyzeTrace(trace, sender.address, target, { [alias]: code })).to.throw('Marker-bearing');
        indirectCounterexample = { scope: 'Separate synthetic alias-marker counterexample', transactionHash: tx.hash, blockHash: receipt.blockHash, creator: sender.address, target, callCode: { [alias]: code }, trace, expectedDisposition: 'rejected-marker-bearing-secondary-callee' };
    });
    it('traces five genuine signed direct CREATEs and verifies the fresh governor-bound graph without invoking marker code', async () => {
        await requireDisposableLocalNetwork(); expect(network.config.hardfork).equals('osaka'); await E.provider.send('hardhat_reset', []);
        const [, governor] = await E.getSigners(), creator = E.Wallet.createRandom().connect(E.provider);
        await E.provider.send('hardhat_setBalance', [creator.address, E.toQuantity(E.parseEther('100'))]); await installToken();
        for (const [name, to] of [['MockAscensionENS', legacy.ENS], ['MockAscensionWrapper', legacy.WRAPPER]]) {
            const mock = await (await E.getContractFactory(name)).deploy(); await E.provider.send('hardhat_setCode', [to, await E.provider.getCode(mock.target)]);
        }
        const ens = await E.getContractAt('MockAscensionENS', legacy.ENS);
        for (const n of legacy.roots) await (await ens.setOwner(E.namehash(n), governor.address)).wait();
        const c = config(creator.address, governor.address);
        // Synthetic local state construction only; no type4 authorization or selected real-account mutation.
        await E.provider.send('hardhat_setCode', [c.sender.target, delegateCode]); await E.provider.send('hardhat_setCode', [creator.address, c.sender.delegationCode]);
        c.nonce = await E.provider.getTransactionCount(creator.address);
        for (const dep of Object.values(c.dependencies)) dep.codeHash = E.keccak256(await E.provider.getCode(dep.address));
        c.rootOwners = Object.fromEntries(legacy.roots.map(n => [n, governor.address]));
        const block = await E.provider.send('eth_getBlockByNumber', ['latest', false]); c.block = { number: Number(BigInt(block.number)), hash: block.hash };
        const j = journal(c), evidence = qualify(c, compiled, j), plan = await policy.makePlan(c, compiled, revision, j, evidence), creationHashes = [], governanceHashes = [], traces = [], reads = [];
        const rpc = (m, a) => { reads.push({ method: m, params: a }); if (m === 'eth_call') expect([c.deployer, c.sender.target]).not.to.include(a[0].to);
            return E.provider.send(m, m === 'eth_getBlockByNumber' && a[0] === 'finalized' ? ['latest', false] : a); };
        expect((await policy.preflight(plan, rpc, revision)).nextIndex).equals(0);
        for (let i = 0; i < 5; ++i) {
            const { from, ...envelope } = plan.transactions[i].envelope, raw = await creator.signTransaction(envelope);
            const decoded = E.Transaction.from(raw); expect(decoded.from).equals(creator.address); expect(decoded.to).equals(null); expect(decoded.type).equals(2);
            const tx = await E.provider.broadcastTransaction(raw), receipt = await tx.wait(); creationHashes.push(tx.hash); expect(receipt.contractAddress).equals(plan.transactions[i].expectedAddress);
            const canonicalBlock = await E.provider.send('eth_getBlockByNumber', [E.toQuantity(receipt.blockNumber), false]);
            expect(canonicalBlock.hash).equals(receipt.blockHash); expect(canonicalBlock.transactions).deep.equals([tx.hash]);
            const trace = await E.provider.send('debug_traceTransaction', [tx.hash, { disableMemory: true, disableStorage: true, disableStack: false }]), callCode = {};
            for (const step of trace.structLogs) if (['CALL', 'CALLCODE', 'STATICCALL', 'DELEGATECALL'].includes(step.op)) {
                const to = E.getAddress(E.toBeHex(BigInt('0x' + step.stack.at(-2).replace(/^0x/, '')) & ((1n << 160n) - 1n), 20));
                callCode[to] = await E.provider.send('eth_getCode', [to, E.toQuantity(receipt.blockNumber)]);
            }
            const analysis = origin.analyzeTrace(trace, creator.address, c.sender.target, callCode);
            expect(BigInt(analysis.gas)).equals(receipt.gasUsed); expect(analysis.invocations).deep.equals({ creator: 0, target: 0 });
            traces.push({ transactionHash: tx.hash, blockHash: receipt.blockHash, blockNumber: receipt.blockNumber, blockTransactionHashes: canonicalBlock.transactions, envelopeSha256: policy.digest(plan.transactions[i].envelope), initcodeKeccak256: E.keccak256(envelope.data), callCode, analysis, trace });
            expect((await policy.preflight(plan, rpc, revision, creationHashes)).nextIndex).equals(i + 1);
        }
        expect(await E.provider.getCode(creator.address)).equals(c.sender.delegationCode); expect(await E.provider.getCode(c.sender.target)).equals(delegateCode);
        for (const a of [creator.address, c.sender.target]) expect(await E.provider.getStorage(a, 0)).equals(E.ZeroHash);
        expect(await E.provider.getTransactionCount(creator.address)).equals(c.nonce + 5);
        for (const tx of plan.governanceCalls) { const sent = await governor.sendTransaction({ type: 2, to: tx.to, data: tx.data, value: 0, accessList: [] }); await sent.wait(); governanceHashes.push(sent.hash); }
        const final = await E.provider.send('eth_getBlockByNumber', ['latest', false]), receipts = { creationHashes, governanceHashes, acceptanceBlock: { number: Number(BigInt(final.number)), hash: final.hash } };
        c.sender.qualification = null; const tracedEvidence = qualify(c, compiled, j, policy.digest(traces)), tracedPlan = await policy.makePlan(c, compiled, revision, j, tracedEvidence);
        expect(tracedPlan.transactions).deep.equals(plan.transactions);
        const report = await policy.verifyAuthority(tracedPlan, rpc, receipts, revision); expect(report.graphAuthorityVerified).equals(true); expect(report.activationAllowed).equals(false);
        const bundle = await exporter.receiptProvenPackage(tracedPlan, rpc, receipts, revision, compiled); expect(bundle.manifest.addressStatus).equals('receipt-proven'); expect(bundle.manifest.senderMode).equals(origin.MARKER);
        expect(reads.some(r => r.method === 'eth_call' && [c.deployer, c.sender.target].includes(r.params[0].to))).equals(false);
        const output = process.env.ALPHA_DISPOSABLE_TRACE_OUTPUT;
        if (output) { expect(path.isAbsolute(output)).equals(true); fs.writeFileSync(output, JSON.stringify({ schema: 'agialpha.disposable-direct-traces.v1', scope: tracedEvidence.scope, directOriginationEvidence: tracedEvidence,
            negativeAliasTrace: indirectCounterexample, limitation: 'Synthetic local Osaka and dependencies, disposable key, fixture hashes and latest-as-finalized. No real-account, hardware, fork, finality, audit or production authorization.', traces,
            authority: report, operations: { creationHashes, governanceHashes }, observedCreatorNonce: c.nonce + 5 }, null, 2) + '\n', { flag: 'wx', mode: 0o600 }); }
    });
});
