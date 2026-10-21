// SPDX-License-Identifier: Apache-2.0
import {canonical, parseBounded, payloadDigest} from './discovery-lab-contract.mjs';

export const DEPLOYMENT_INVENTORY_DIGEST = "9638704a60477c383c3e9cf684a099f087fd9d926f498fc67acaa93639ed9492";
const handles = new WeakSet();
const address = /^0x[0-9a-fA-F]{40}$/;
const hash = /^0x[0-9a-fA-F]{64}$/;
const digest = /^[0-9a-f]{64}$/;
const snapshot = value => parseBounded(typeof value === 'string' ? value : canonical(value));
const same = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();
function requireValue(condition, message) { if (!condition) throw Error(message); }
function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
}
function trusted(handle) { requireValue(handles.has(handle), 'A source-authenticated inventory handle is required'); return handle; }
function routeFor(handle, route) {
    trusted(handle);
    requireValue(Object.hasOwn(handle.inventory.routes, route), 'Unknown deployment route');
    const selected = handle.inventory.routes[route], deployment = handle.inventory.deployments[selected.deployment];
    const contract = deployment.contracts.find(row => row.name === selected.contract);
    return {selected, deployment, contract, token: handle.inventory.tokens[selected.currency]};
}

export async function loadDeploymentInventory(raw, expectedDigest = DEPLOYMENT_INVENTORY_DIGEST) {
    const inventory = snapshot(raw);
    requireValue(digest.test(expectedDigest), 'A trusted inventory digest is required');
    requireValue(await payloadDigest(inventory) === expectedDigest, 'Deployment inventory source mismatch');
    requireValue(inventory.schema === 'successor-deployment-compatibility/v1' && inventory.chainId === 1
        && inventory.authority === 'none' && inventory.operationallyReady === false, 'Invalid deployment inventory');
    for (const [name, count] of Object.entries({alpha: 5, manager: 9, jobs: 25})) {
        const deployment = inventory.deployments[name];
        requireValue(deployment.contracts.length === count && deployment.liveObservation.status === 'NOT_RUN', 'Invalid recorded deployment scope');
        requireValue(deployment.contracts.every(row => address.test(row.address) && hash.test(row.runtimeKeccak256)), 'Invalid contract identity');
        requireValue(new Set(deployment.contracts.map(row => row.address.toLowerCase())).size === count, 'Duplicate deployment contract');
    }
    for (const [route, currency] of [['manager-usdc', 'USDC6'], ['jobs-agialpha', 'AGIALPHA18']]) {
        requireValue(inventory.routes[route].currency === currency && address.test(inventory.tokens[currency].address), 'Mixed token route');
    }
    const handle = freeze({inventory, digest: expectedDigest}); handles.add(handle); return handle;
}

export function deploymentSummary(handle) {
    trusted(handle);
    return freeze({schema: 'successor-deployment-summary/v1', inventoryDigest: handle.digest,
        recordedContracts: Object.values(handle.inventory.deployments).reduce((n, row) => n + row.contracts.length, 0),
        liveObservation: 'NOT_RUN', operationallyReady: false, authority: 'none',
        routes: Object.fromEntries(Object.keys(handle.inventory.routes).map(route => {
            const {selected, contract, token, deployment} = routeFor(handle, route);
            return [route, {address: contract.address, currency: selected.currency, token: token.address,
                decimals: token.decimals, directOwner: selected.owner, ultimateGovernor: selected.ultimateGovernor,
                ownerContract: selected.ownerContract, operatorPath: selected.operatorPath, historicalObservation: deployment.historicalObservation,
                missingAbiPin: contract.abiSha256 === null, ensRoots: selected.ensRoots}];
        })), fleetCompatibility: handle.inventory.fleetCompatibility, unresolved: handle.inventory.unresolved});
}

export function assessDeploymentContext(handle, route, raw) {
    const context = snapshot(raw), {selected, contract, token} = routeFor(handle, route), reasons = [];
    if (context.chainId !== handle.inventory.chainId) reasons.push('WRONG_CHAIN');
    if (!same(context.deploymentAddress, contract.address)) reasons.push('STALE_OR_WRONG_DEPLOYMENT');
    if (context.currency !== selected.currency || !same(context.tokenAddress, token.address)
        || context.tokenDecimals !== token.decimals) reasons.push('WRONG_TOKEN_ROUTE');
    if (!same(context.runtimeKeccak256, contract.runtimeKeccak256)) reasons.push('WRONG_RUNTIME_CODE');
    if (contract.abiSha256 === null) reasons.push('ABI_PIN_UNAVAILABLE');
    else if (context.abiSha256 !== contract.abiSha256) reasons.push('WRONG_ABI');
    if (!same(context.owner, selected.owner)) reasons.push('WRONG_ROLE');
    if (selected.ensRoots === null) reasons.push('IDENTITY_ROOTS_UNAVAILABLE');
    else if (canonical(context.ensRoots ?? null) !== canonical(selected.ensRoots)) reasons.push('WRONG_IDENTITY_ROOT');
    return freeze({schema: 'successor-deployment-context-assessment/v1', inventoryDigest: handle.digest,
        route, compatible: reasons.length === 0, reasons, operationallyReady: false, authority: 'none'});
}

/** Caller supplies trusted read-only transport and Keccak implementation; imported data cannot install either. */
export async function inspectReadOnlyDeployment(handle, deploymentName, {rpc, keccak256, provider, signal,
    maxDurationMs = 30000} = {}) {
    trusted(handle);
    const initial = {schema: 'successor-deployment-observation/v1', inventoryDigest: handle.digest,
        deployment: deploymentName, authority: 'none', operationallyReady: false};
    requireValue(Object.hasOwn(handle.inventory.deployments, deploymentName), 'Unknown deployment');
    if (typeof rpc !== 'function' || typeof keccak256 !== 'function') return freeze({...initial, status: 'NOT_RUN', reasons: ['READ_ONLY_PROVIDER_OR_KECCAK_UNAVAILABLE']});
    requireValue(typeof provider === 'string' && /^[a-zA-Z0-9._-]{1,128}$/.test(provider), 'Use a public provider label without a credential or URL');
    requireValue(Number.isSafeInteger(maxDurationMs) && maxDurationMs >= 1 && maxDurationMs <= 60000, 'Bound the observation duration');
    const start = performance.now(), calls = [], rows = [], deployment = handle.inventory.deployments[deploymentName];
    let observedBlock = null, phase = 'chain';
    async function call(method, params) {
        requireValue(['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call'].includes(method), 'Read-only RPC method required');
        requireValue(!signal?.aborted && performance.now() - start < maxDurationMs && calls.length < 100, 'Observation cancelled or budget exhausted');
        calls.push({method, params});
        const result = parseBounded(canonical(await bounded(() => rpc({method, params, signal}))));
        requireValue(performance.now() - start <= maxDurationMs, 'Observation deadline exceeded');
        return result;
    }
    async function bounded(operation) {
        let timer, abort;
        const operationDeadline = Math.min(start + maxDurationMs, performance.now() + 5000);
        try {
            const result = await Promise.race([Promise.resolve().then(operation), new Promise((_, reject) => {
                timer = setTimeout(() => reject(Error('Bounded RPC timeout')), Math.min(5000, maxDurationMs - (performance.now() - start)));
                if (signal) { abort = () => reject(Error('Cancelled')); signal.addEventListener('abort', abort, {once: true}); }
            })]);
            requireValue(!signal?.aborted, 'Cancelled');
            requireValue(performance.now() <= operationDeadline, 'Observation deadline exceeded');
            return result;
        } finally { clearTimeout(timer); if (abort) signal.removeEventListener('abort', abort); }
    }
    try {
        const chain = await call('eth_chainId', []); requireValue(chain === '0x1', 'Wrong chain');
        phase = 'block';
        const block = await call('eth_getBlockByNumber', ['finalized', false]);
        requireValue(hash.test(block.hash) && /^0x[0-9a-f]+$/i.test(block.number) && /^0x[0-9a-f]+$/i.test(block.timestamp), 'Invalid observation block');
        observedBlock = {number: block.number, hash: block.hash, timestamp: block.timestamp};
        for (const contract of deployment.contracts) {
            phase = 'runtime:' + contract.name;
            const code = await call('eth_getCode', [contract.address, block.number]);
            requireValue(typeof code === 'string' && code.length <= 200000 && /^0x(?:[0-9a-fA-F]{2})+$/.test(code), 'Invalid or absent contract code');
            const actualHash = await bounded(() => keccak256(code)); requireValue(typeof actualHash === 'string' && hash.test(actualHash), 'Invalid Keccak result');
            const row = {name: contract.name, address: contract.address, runtimeKeccak256: actualHash,
                codeMatches: same(actualHash, contract.runtimeKeccak256), actualOwner: null, ownerMatches: null,
                completion: 'CODE_CHECKED', ownerStatus: contract.recordedOwner ? 'NOT_RUN' : 'NOT_APPLICABLE'};
            rows.push(row);
            if (contract.recordedOwner) {
                phase = 'owner:' + contract.name;
                const encoded = await call('eth_call', [{to: contract.address, data: '0x8da5cb5b'}, block.number]);
                requireValue(typeof encoded === 'string' && /^0x0{24}[0-9a-fA-F]{40}$/.test(encoded), 'Invalid owner response');
                row.actualOwner = '0x' + encoded.slice(-40); row.ownerMatches = same(row.actualOwner, contract.recordedOwner);
                row.ownerStatus = 'OBSERVED';
            }
            row.completion = 'CODE_AND_RECORDED_OWNER_CHECKS_COMPLETE';
        }
        phase = 'block-recheck';
        const recheck = await call('eth_getBlockByNumber', [block.number, false]);
        requireValue(same(recheck.hash, block.hash), 'Observation block changed');
        requireValue(!signal?.aborted && performance.now() - start <= maxDurationMs, 'Observation cancelled or deadline exceeded');
        const accepted = rows.every(row => row.codeMatches && row.ownerMatches !== false);
        return freeze({...initial, provider, status: accepted ? 'OBSERVED_CODE_AND_RECORDED_OWNERS' : 'REJECTED_IDENTITY_MISMATCH',
            block: observedBlock, contracts: rows, calls,
            costs: {rpcCalls: calls.length, elapsedMs: Math.max(0, Math.ceil(performance.now() - start))},
            incomplete: ['ABI_AND_COMPILER_SOURCE', 'PROXY_AND_EXTERNAL_AUTHORITY', 'TOKEN_AND_IDENTITY_ROOTS',
                'PAUSE_BALANCES_ALLOWANCES_AND_POLICY', 'INDEPENDENT_OPERATOR_AND_ACTIVATION_APPROVAL']});
    } catch {
        return freeze({...initial, provider, status: signal?.aborted ? 'CANCELLED' : 'INCONCLUSIVE', calls,
            block: observedBlock, partialContracts: rows, stoppedAt: phase, observationComplete: false,
            reasons: ['READ_ONLY_OBSERVATION_INCOMPLETE'], costs: {rpcCalls: calls.length, elapsedMs: Math.max(0, Math.ceil(performance.now() - start))}});
    }
}

export function prepareOperatorIntent(handle, route, raw) {
    const input = snapshot(raw), {selected, contract} = routeFor(handle, route);
    requireValue(Object.keys(input).sort().join(',') === 'abiSha256,actor,consequences,currency,data', 'Exact operator intent fields required');
    requireValue(address.test(input.actor) && typeof input.data === 'string' && input.data.length <= 32770
        && /^0x(?:[0-9a-fA-F]{2}){4,}$/.test(input.data), 'Invalid unsigned intent');
    requireValue(typeof input.consequences === 'string' && input.consequences.length >= 10 && input.consequences.length <= 2048, 'Explicit consequences required');
    const reasons = ['CURRENT_READBACK_AND_OPERATOR_APPROVAL_REQUIRED'];
    if (!same(input.actor, selected.owner)) reasons.push('WRONG_ROLE');
    if (selected.ownerContract !== null) reasons.push('CONTRACT_OWNER_EXECUTION_PATH_UNQUALIFIED');
    if (input.currency !== selected.currency) reasons.push('WRONG_TOKEN_ROUTE');
    if (contract.abiSha256 === null || input.abiSha256 !== contract.abiSha256) reasons.push('ABI_PIN_UNAVAILABLE_OR_MISMATCHED');
    return freeze({schema: 'successor-unsigned-operator-intent/v1', route, inventoryDigest: handle.digest,
        status: 'BLOCKED_OPERATOR_REVIEW_REQUIRED', executable: false, authority: 'none', reasons,
        requiredActor: selected.owner, ultimateGovernor: selected.ultimateGovernor, ownerContract: selected.ownerContract,
        operatorPath: selected.operatorPath, consequences: input.consequences,
        unsignedDraft: selected.ownerContract !== null ? null
            : {chainId: handle.inventory.chainId, to: contract.address, from: input.actor, value: '0', data: input.data},
        proposedCall: {chainId: handle.inventory.chainId, target: contract.address, data: input.data},
        callsPerformed: 0, signed: false, submitted: false});
}
