// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {loadDeploymentInventory, deploymentSummary, assessDeploymentContext, inspectReadOnlyDeployment,
    prepareOperatorIntent, DEPLOYMENT_INVENTORY_DIGEST} from './discovery-lab-deployments.mjs';
const raw = fs.readFileSync(new URL('../../docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json', import.meta.url), 'utf8');
const original = JSON.parse(raw), handle = await loadDeploymentInventory(raw);
const route = original.routes['jobs-agialpha'], contract = original.deployments.jobs.contracts.find(row => row.name === route.contract);
const token = original.tokens[route.currency];
const context = {chainId: 1, deploymentAddress: contract.address, currency: route.currency, tokenAddress: token.address,
    tokenDecimals: token.decimals, runtimeKeccak256: contract.runtimeKeccak256, abiSha256: null,
    owner: route.owner, ensRoots: route.ensRoots};
test('one pinned inventory retains all39 contracts and historical Fleet instance without readiness promotion', () => {
    const summary = deploymentSummary(handle);
    assert.equal(summary.recordedContracts, 39); assert.equal(summary.authority, 'none');
    assert.equal(summary.operationallyReady, false); assert.equal(summary.liveObservation, 'NOT_RUN');
    assert.equal(summary.fleetCompatibility.historicalClaimsMigrated, false);
    assert.equal(original.deployments.manager.explorerVerification.exactMatches, 6);
    assert.equal(original.deployments.manager.explorerVerification.retainedSimilarMatches, 3);
    assert.equal(original.deployments.alpha.recordedOperationalState.globalPauseAvailable, false);
    assert.equal(original.deployments.jobs.recordedOperationalState.allEightManagedModulesPaused, true);
});
test('inventory source mismatch, forged handles and malicious data fail closed', async () => {
    const changed = structuredClone(original); changed.routes['jobs-agialpha'].currency = 'USDC6';
    await assert.rejects(loadDeploymentInventory(changed), /source mismatch/);
    await assert.rejects(loadDeploymentInventory(raw, 'not-a-digest'), /trusted inventory/);
    assert.throws(() => deploymentSummary({inventory: original, digest: DEPLOYMENT_INVENTORY_DIGEST}), /authenticated/);
    const trap = {}; Object.defineProperty(trap, 'schema', {enumerable: true, get() { throw Error('must not run'); }});
    await assert.rejects(loadDeploymentInventory(trap), /Accessor/);
    assert.equal(Object.isFrozen(handle.inventory.deployments.jobs.contracts[0]), true);
});
test('wrong chain,address,runtime,ABI,role,identity root and token route remain blocked', () => {
    const mutations = [['chainId', 31337, 'WRONG_CHAIN'], ['deploymentAddress', original.fleetCompatibility.historicalManager, 'STALE_OR_WRONG_DEPLOYMENT'],
        ['runtimeKeccak256', '0x' + '0'.repeat(64), 'WRONG_RUNTIME_CODE'], ['owner', '0x' + '0'.repeat(40), 'WRONG_ROLE'],
        ['tokenAddress', original.tokens.USDC6.address, 'WRONG_TOKEN_ROUTE'], ['currency', 'USDC6', 'WRONG_TOKEN_ROUTE'],
        ['tokenDecimals', 6, 'WRONG_TOKEN_ROUTE'], ['ensRoots', {...route.ensRoots, agentRootNode: '0x' + '0'.repeat(64)}, 'WRONG_IDENTITY_ROOT']];
    for (const [key, value, reason] of mutations) {
        const report = assessDeploymentContext(handle, 'jobs-agialpha', {...context, [key]: value});
        assert.ok(report.reasons.includes(reason)); assert.equal(report.compatible, false); assert.equal(report.operationallyReady, false);
    }
    const missing = assessDeploymentContext(handle, 'jobs-agialpha', context);
    assert.deepEqual(missing.reasons, ['ABI_PIN_UNAVAILABLE']);
    const wrongAbi = assessDeploymentContext(handle, 'jobs-agialpha', {...context, abiSha256: '0'.repeat(64)});
    assert.ok(wrongAbi.reasons.includes('ABI_PIN_UNAVAILABLE')); assert.equal(wrongAbi.compatible, false);
    assert.throws(() => assessDeploymentContext(handle, '__proto__', context), /Unknown deployment route/);
});
function syntheticProvider({wrongCode = false, wrongOwner = false, reorg = false} = {}) {
    const rows = original.deployments.alpha.contracts, block = {number: '0x1900000', hash: '0x' + 'a'.repeat(64), timestamp: '0x12345678'};
    let addressForHash = null;
    return {provider: 'synthetic-test-provider',
        async rpc({method, params}) {
            if (method === 'eth_chainId') return '0x1';
            if (method === 'eth_getBlockByNumber') return {...block, hash: reorg && params[0] !== 'finalized' ? '0x' + 'b'.repeat(64) : block.hash};
            if (method === 'eth_getCode') { addressForHash = params[0]; return '0x6000'; }
            if (method === 'eth_call') {
                assert.equal(params[0].data, '0x8da5cb5b');
                const owner = rows.find(row => row.address === params[0].to).recordedOwner;
                return '0x' + '0'.repeat(24) + (wrongOwner ? '0'.repeat(40) : owner.slice(2));
            }
            throw Error('Unexpected RPC method');
        },
        async keccak256() { return wrongCode ? '0x' + '0'.repeat(64) : rows.find(row => row.address === addressForHash).runtimeKeccak256; }};
}
test('read-only inspector pins a common block, records calls and keeps all remaining readiness separate', async () => {
    const result = await inspectReadOnlyDeployment(handle, 'alpha', syntheticProvider());
    assert.equal(result.status, 'OBSERVED_CODE_AND_RECORDED_OWNERS'); assert.equal(result.contracts.length, 5);
    assert.equal(result.operationallyReady, false); assert.ok(result.incomplete.includes('TOKEN_AND_IDENTITY_ROOTS'));
    assert.equal(result.calls[1].params[0], 'finalized');
    assert.ok(result.calls.filter(row => ['eth_getCode', 'eth_call'].includes(row.method)).every(row => row.params.at(-1) === result.block.number));
    assert.ok(result.calls.every(row => !/send|sign|approve|personal|wallet/i.test(row.method)));
    for (const change of [{wrongCode: true}, {wrongOwner: true}]) {
        assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', syntheticProvider(change))).status, 'REJECTED_IDENTITY_MISMATCH');
    }
    const reorg = await inspectReadOnlyDeployment(handle, 'alpha', syntheticProvider({reorg: true}));
    assert.equal(reorg.status, 'INCONCLUSIVE'); assert.equal(reorg.partialContracts.length, 5);
    assert.equal(reorg.stoppedAt, 'block-recheck'); assert.equal(reorg.observationComplete, false);
    assert.ok(reorg.block.hash);
});
test('unavailable,wrong-chain,timeout,cancelled and immutable-error providers do not create success', async () => {
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha')).status, 'NOT_RUN');
    const wrongChain = {...syntheticProvider(), rpc: async () => '0x7a69'};
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', wrongChain)).status, 'INCONCLUSIVE');
    const failed = {...syntheticProvider(), rpc: async () => { throw Object.freeze(Error('secret provider URL')); }};
    const report = await inspectReadOnlyDeployment(handle, 'alpha', failed);
    assert.equal(report.status, 'INCONCLUSIVE'); assert.ok(!JSON.stringify(report).includes('secret provider'));
    const hung = {...syntheticProvider(), rpc: () => new Promise(() => {}), maxDurationMs: 10};
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', hung)).status, 'INCONCLUSIVE');
    const hashHung = {...syntheticProvider(), keccak256: () => new Promise(() => {}), maxDurationMs: 10};
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', hashHung)).status, 'INCONCLUSIVE');
    const controller = new AbortController(); controller.abort();
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', {...syntheticProvider(), signal: controller.signal})).status, 'CANCELLED');
});
test('unsigned operator drafts have no signing or submission path and preserve actor/ABI/readiness gates', () => {
    const input = {actor: route.owner, currency: route.currency, abiSha256: null, data: '0x12345678',
        consequences: 'Operator must independently decode this call, verify all prerequisites and explicitly approve any transaction.'};
    const report = prepareOperatorIntent(handle, 'jobs-agialpha', input);
    assert.equal(report.proposedCall.target, contract.address); assert.equal(report.requiredActor, contract.recordedOwner);
    assert.equal(report.unsignedDraft, null); assert.equal(report.ownerContract, 'SystemPause');
    assert.equal(report.ultimateGovernor, original.deployments.jobs.configuredAtDeployment.governance);
    assert.ok(report.reasons.includes('CONTRACT_OWNER_EXECUTION_PATH_UNQUALIFIED'));
    const governor = assessDeploymentContext(handle, 'jobs-agialpha', {...context, owner: route.ultimateGovernor});
    assert.ok(governor.reasons.includes('WRONG_ROLE'));
    assert.equal(report.executable, false); assert.equal(report.signed, false); assert.equal(report.submitted, false);
    assert.ok(report.reasons.includes('ABI_PIN_UNAVAILABLE_OR_MISMATCHED')); assert.equal(report.callsPerformed, 0);
    assert.throws(() => prepareOperatorIntent(handle, 'jobs-agialpha', {...input, to: original.fleetCompatibility.historicalManager}), /Exact operator/);
});

test('synchronous final recheck and Keccak overruns cannot win the timeout microtask race', async () => {
    const stall = () => { const stop = performance.now() + 30; while (performance.now() < stop) {} };
    const final = syntheticProvider(), originalRpc = final.rpc;
    final.maxDurationMs = 20;
    final.rpc = async request => {
        if (request.method === 'eth_getBlockByNumber' && request.params[0] !== 'finalized') stall();
        return originalRpc(request);
    };
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', final)).status, 'INCONCLUSIVE');
    const hashing = syntheticProvider(), originalKeccak = hashing.keccak256;
    hashing.maxDurationMs = 20;
    hashing.keccak256 = async code => { stall(); return originalKeccak(code); };
    assert.equal((await inspectReadOnlyDeployment(handle, 'alpha', hashing)).status, 'INCONCLUSIVE');
});

test('timeout aborts the actual outstanding RPC through an owned signal', async () => {
    let receivedSignal, aborted = false;
    const report = await inspectReadOnlyDeployment(handle, 'alpha', {
        provider: 'synthetic-abort-aware-provider', maxDurationMs: 10, keccak256: async () => '0x' + '0'.repeat(64),
        rpc: ({signal}) => {
            receivedSignal = signal;
            return new Promise((_, reject) => signal?.addEventListener('abort', () => {
                aborted = true; reject(Object.freeze(Error('Transport aborted')));
            }, {once: true}));
        }
    });
    assert.equal(report.status, 'INCONCLUSIVE'); assert.ok(receivedSignal instanceof AbortSignal);
    assert.equal(receivedSignal.aborted, true); assert.equal(aborted, true);
    assert.equal(report.costs.rpcCalls, 1); assert.equal(report.observationComplete, false);
    assert.equal(report.authority, 'none'); assert.equal(report.operationallyReady, false);
});

test('caller cancellation reaches owned transport signal and terminal cleanup detaches the link', async () => {
    const caller = new AbortController(); let receivedSignal, aborted = false, begin;
    const started = new Promise(resolve => { begin = resolve; });
    const originalAdd = caller.signal.addEventListener.bind(caller.signal);
    const originalRemove = caller.signal.removeEventListener.bind(caller.signal);
    let adds = 0, removes = 0;
    caller.signal.addEventListener = (...args) => { adds++; return originalAdd(...args); };
    caller.signal.removeEventListener = (...args) => { removes++; return originalRemove(...args); };
    const pending = inspectReadOnlyDeployment(handle, 'alpha', {
        provider: 'synthetic-linked-abort-provider', signal: caller.signal,
        keccak256: async () => '0x' + '0'.repeat(64),
        rpc: ({signal}) => {
            receivedSignal = signal;
            return new Promise((_, reject) => {
                signal?.addEventListener('abort', () => { aborted = true; reject(Error('Transport aborted')); }, {once: true});
                begin();
            });
        }
    });
    await started; caller.abort(); const report = await pending;
    assert.equal(report.status, 'CANCELLED'); assert.notEqual(receivedSignal, caller.signal);
    assert.equal(receivedSignal.aborted, true); assert.equal(aborted, true);
    assert.equal(adds, 1); assert.equal(removes, 1); assert.equal(report.costs.rpcCalls, 1);
});

test('success and late owner-query failure close owned signals while preserving caller and partial outputs', async () => {
    for (const failOwner of [false, true]) {
        const caller = new AbortController(), supplied = syntheticProvider(), baseRpc = supplied.rpc, observed = [];
        const add = caller.signal.addEventListener.bind(caller.signal), remove = caller.signal.removeEventListener.bind(caller.signal);
        let links = 0, unlinks = 0;
        caller.signal.addEventListener = (...args) => { links++; return add(...args); };
        caller.signal.removeEventListener = (...args) => { unlinks++; return remove(...args); };
        supplied.signal = caller.signal;
        supplied.rpc = request => {
            observed.push(request.signal);
            if (failOwner && request.method === 'eth_call') throw Object.freeze(Error('Opaque provider failure'));
            return baseRpc(request);
        };
        const report = await inspectReadOnlyDeployment(handle, 'alpha', supplied);
        assert.equal(report.status, failOwner ? 'INCONCLUSIVE' : 'OBSERVED_CODE_AND_RECORDED_OWNERS');
        assert.ok(observed.every(signal => signal instanceof AbortSignal && signal.aborted));
        assert.ok(observed.every(signal => signal === observed[0] && signal !== caller.signal));
        assert.equal(caller.signal.aborted, false); assert.equal(links, 1); assert.equal(unlinks, 1);
        if (failOwner) {
            assert.equal(report.partialContracts.length, 1); assert.equal(report.partialContracts[0].codeMatches, true);
            assert.equal(report.partialContracts[0].ownerStatus, 'NOT_RUN'); assert.ok(report.block.hash);
        }
    }
});

test('a transport ignoring abort cannot resume the observer after its deadline', async () => {
    let finish, receivedSignal;
    const report = await inspectReadOnlyDeployment(handle, 'alpha', {
        provider: 'synthetic-noncooperative-provider', maxDurationMs: 10,
        keccak256: async () => '0x' + '0'.repeat(64),
        rpc: ({signal}) => { receivedSignal = signal; return new Promise(resolve => { finish = resolve; }); }
    });
    assert.equal(report.status, 'INCONCLUSIVE'); assert.equal(receivedSignal.aborted, true);
    const before = JSON.stringify(report); finish('0x1');
    await new Promise(resolve => queueMicrotask(resolve));
    await new Promise(resolve => queueMicrotask(resolve));
    assert.equal(JSON.stringify(report), before); assert.equal(report.calls.length, 1);
    assert.equal(report.observationComplete, false);
});

test('pre-aborted callers make no transport calls and cannot start Keccak work', async () => {
    const caller = new AbortController(); caller.abort(); let calls = 0, hashes = 0;
    const report = await inspectReadOnlyDeployment(handle, 'alpha', {
        provider: 'synthetic-preaborted-provider', signal: caller.signal,
        rpc: async () => { calls++; return '0x1'; }, keccak256: async () => { hashes++; return '0x' + '0'.repeat(64); }
    });
    assert.equal(report.status, 'CANCELLED'); assert.equal(calls, 0); assert.equal(hashes, 0);
    assert.equal(report.costs.rpcCalls, 0);
});

test('the five-second per-call deadline aborts transport before the longer total allowance', async () => {
    let receivedSignal, aborted = false;
    const report = await inspectReadOnlyDeployment(handle, 'alpha', {
        provider: 'synthetic-percall-timeout-provider', maxDurationMs: 60000,
        keccak256: async () => '0x' + '0'.repeat(64),
        rpc: ({signal}) => {
            receivedSignal = signal;
            return new Promise((_, reject) => signal?.addEventListener('abort', () => {
                aborted = true; reject(Error('Transport aborted by per-call deadline'));
            }, {once: true}));
        }
    });
    assert.equal(report.status, 'INCONCLUSIVE'); assert.equal(receivedSignal.aborted, true); assert.equal(aborted, true);
    assert.equal(report.costs.rpcCalls, 1); assert.ok(report.costs.elapsedMs >= 4000 && report.costs.elapsedMs < 60000);
});

test('terminal abort cleanup is charged before freezing and cannot escape the total deadline', async t => {
    let clock = 0; t.mock.method(performance, 'now', () => clock);
    const supplied = syntheticProvider(), originalRpc = supplied.rpc;
    let listenerInstalled = false, cleanupRan = false;
    supplied.maxDurationMs = 20;
    supplied.rpc = request => {
        if (!listenerInstalled) {
            listenerInstalled = true;
            request.signal.addEventListener('abort', () => {
                cleanupRan = true;
                clock += 40;
            }, {once: true});
        }
        return originalRpc(request);
    };
    const report = await inspectReadOnlyDeployment(handle, 'alpha', supplied);
    assert.equal(cleanupRan, true); assert.equal(report.status, 'INCONCLUSIVE');
    assert.equal(report.stoppedAt, 'cleanup'); assert.equal(report.observationComplete, false);
    assert.equal(report.partialContracts.length, 5); assert.ok(report.block.hash);
    assert.ok(report.costs.elapsedMs >= 40); assert.equal(report.costs.rpcCalls, report.calls.length);
    assert.ok(Object.isFrozen(report));
});
