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
