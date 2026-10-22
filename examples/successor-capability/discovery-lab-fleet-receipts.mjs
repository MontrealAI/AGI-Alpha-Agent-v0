// SPDX-License-Identifier: Apache-2.0
// Inspect inert actual Fleet receipt bytes; imported provenance grants no authority.
import * as contract from './discovery-lab-contract.mjs';
const same = (a, b) => contract.canonical(a) === contract.canonical(b);
const copy = value => JSON.parse(contract.canonical(value));
const need = (condition, message) => { if (!condition) throw Error(message); };
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const git = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const identity = value => typeof value === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$/.test(value);
const bytes = text => new TextEncoder().encode(text).length;
const zero = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
const digest = async text => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))]
    .map(value => value.toString(16).padStart(2, '0')).join('');
export const FLEET_RETURN_SCHEMA = 'agi-fleet/discovery-review-return/v1';
export function parseFleetReturn(raw) {
    const value = contract.parseBounded(raw);
    need(exact(value, ['schema', 'original', 'receiptRaw']) && value.schema === FLEET_RETURN_SCHEMA
        && typeof value.original === 'string' && typeof value.receiptRaw === 'string', 'Unsupported Fleet return envelope.');
    return value;
}
export async function fleetReceiptBindings(raw) {
    const envelope = parseFleetReturn(raw), request = await contract.parseWorkRequest(envelope.original);
    return Object.fromEntries(contract.BINDING_KEYS.map(key => [key, request[key]]));
}
export async function inspectFleetReceipt(input, context, options = {}) {
    ({input, context, options} = copy({input, context, options}));
    need(exact(input, ['raw', 'source']), 'Fleet needs exact raw return bytes and declared source.');
    need(exact(context, ['campaignDigest', 'attempt', 'bindings', 'lineageQualified', 'charter', 'result', 'artifacts', 'ancestors']),
        'Fleet needs the independently replayed minimal campaign context.');
    contract.validateBindings(context.bindings);
    const envelope = parseFleetReturn(input.raw), receipt = contract.parseBounded(envelope.receiptRaw);
    const request = await contract.parseWorkRequest(envelope.original), source = input.source;
    need(exact(source, ['repository', 'commit', 'tree', 'adapterSha256', 'contractSha256'])
        && source.repository === 'MontrealAI/AGI-Fleet-Linux' && git(source.commit) && git(source.tree)
        && hash(source.adapterSha256) && hash(source.contractSha256), 'Fleet receiver source identity differs.');
    need(exact(options, []) || exact(options, ['expectedReceiverSources']), 'Unsupported Fleet inspection options.');
    if (options.expectedReceiverSources !== undefined) {
        need(Array.isArray(options.expectedReceiverSources) && options.expectedReceiverSources.some(item => same(item, source)),
            'Fleet receiver is absent from the installed source context.');
    }
    const bound = Object.fromEntries(contract.BINDING_KEYS.map(key => [key, request[key]]));
    need(same(bound, context.bindings) && context.lineageQualified !== false && hash(context.campaignDigest)
        && Array.isArray(context.ancestors) && context.ancestors.length <= 8 && Array.isArray(context.artifacts)
        && context.artifacts.length === 6, 'Fleet receipt has no unique qualified campaign.');
    need(same(request.payload, {schema: 'discovery-lab-review-payload/v1', charter: context.charter,
        result: context.result, ancestors: context.ancestors}) && request.commission.id === context.attempt
        && same(request.inputArtifacts, context.artifacts.slice(0, contract.STAGES.indexOf(request.stage)).map(item => item.digest)),
    'Fleet request payload, artifacts or ancestry differ.');
    const fields = ['schema', 'state', 'reasons', 'missionId', 'revision', 'stage', 'requestDigest', 'payloadDigest',
        'sourceDigest', 'evaluatorDigest', 'commission', 'executorId', 'runtimeDigest', 'executionMode', 'scope',
        'resourceUsed', 'resourceAccounting', 'authority', 'remoteExecution', 'settlement', 'organizationalIndependence', 'protectedHoldout'];
    need(exact(receipt, fields) && receipt.schema === 'agi-fleet/discovery-review/v1'
        && receipt.requestDigest === await digest(envelope.original)
        && ['missionId', 'revision', 'stage', 'payloadDigest', 'sourceDigest', 'evaluatorDigest'].every(key => receipt[key] === request[key])
        && same(receipt.commission, request.commission), 'Fleet receipt does not bind the exact original request.');
    need(receipt.executionMode === 'synthetic-local' && receipt.scope === 'bounded-synthetic-semantic-review'
        && receipt.authority === 'none' && receipt.remoteExecution === 'unprovisioned' && receipt.settlement === 'not-connected'
        && receipt.organizationalIndependence === false && receipt.protectedHoldout === false,
    'Fleet receipt forges execution, independence or settlement authority.');
    need(Array.isArray(receipt.reasons) && receipt.reasons.length <= 32
        && receipt.reasons.every(value => typeof value === 'string' && /^[A-Z0-9_:-]{1,120}$/.test(value))
        && ['accepted-local-review', 'rejected-local-review', 'inconclusive', 'unprovisioned', 'rejected', 'unsupported'].includes(receipt.state),
    'Fleet receipt has an unsupported outcome.');
    need((receipt.executorId === null && receipt.runtimeDigest === null)
        || identity(receipt.executorId) && hash(receipt.runtimeDigest), 'Fleet installed runtime declaration differs.');
    const used = contract.validateResources(receipt.resourceUsed), encodedReceiptBytes = bytes(contract.canonical(receipt));
    const nativeWork = {...used, checking: used.checking - 1, storageBytes: used.storageBytes - encodedReceiptBytes};
    need(nativeWork.checking >= 0 && nativeWork.storageBytes >= 0 && used.memoryBytes >= bytes(envelope.original),
        'Fleet receipt omits admission or exact receipt storage.');
    const logicalKeys = ['acquisitions', 'search', 'checking', 'storageBytes', 'installations', 'workerCapacity'];
    const prefixes = [zero()], inspection = {...zero(), checking: 10_000};
    prefixes.push({...inspection});
    for (const item of [...context.ancestors, {charter: context.charter, result: context.result}]) {
        for (const key of ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']) inspection[key] += item.result.resources[key];
        inspection.memoryBytes = Math.max(inspection.memoryBytes, item.result.resources.memoryWords * 8);
        inspection.workerCapacity = Math.max(inspection.workerCapacity, item.result.resources.workerSlots);
        prefixes.push({...inspection});
    }
    const matching = prefixes.filter(prefix => logicalKeys.every(key => nativeWork[key] === prefix[key])
        && used.memoryBytes >= bytes(envelope.original) + prefix.memoryBytes);
    need(matching.length > 0, 'Fleet logical replay work does not match an executed ancestry prefix.');
    const full = prefixes.at(-1), complete = logicalKeys.every(key => nativeWork[key] === full[key]);
    const modeled = receipt.resourceAccounting === 'reported-model-work-plus-input-and-receipt-bytes';
    const admissionOnly = receipt.resourceAccounting === 'admission-only-known-input-and-receipt-bytes';
    const checkerFailed = receipt.resourceAccounting === 'lower-bound-checker-failed';
    need(modeled || admissionOnly || checkerFailed, 'Unsupported Fleet resource accounting; retain overflow outside admitted history.');
    if (modeled) need(nativeWork.checking >= 10_000 && receipt.executorId !== null,
        'Fleet modeled review omits its installed inspection charge.');
    const within = contract.RESOURCE_KEYS.every(key => used[key] <= request.resourceLimits[key]);
    if (!within) need(receipt.state === 'inconclusive' && receipt.reasons.includes('DISCOVERY_REVIEW_BUDGET_EXHAUSTED'),
        'Fleet over-budget receipt omits its inconclusive budget disposition.');
    const terminal = receipt.reasons.some(value => /(?:BUDGET_EXHAUSTED|SEARCH_TRUNCATED|CHECK_INCOMPLETE)$/.test(value));
    if (receipt.state === 'accepted-local-review') {
        need(modeled && complete && within && receipt.reasons.length === 0 && receipt.executorId !== null
            && context.result.stages[contract.STAGES.indexOf(request.stage)].status === 'accepted',
        'Fleet receipt forges complete finite acceptance.');
    } else if (receipt.state === 'rejected-local-review') {
        need(modeled && complete && within && !terminal && receipt.reasons.length > 0 && receipt.executorId !== null
            && context.result.stages[contract.STAGES.indexOf(request.stage)].status !== 'accepted',
        'Fleet receipt contradicts the replayed stage disposition.');
    } else {
        need(receipt.reasons.length > 0, 'Fleet refusal must retain a reason.');
        if (receipt.state !== 'inconclusive') need(admissionOnly && nativeWork.checking === 0,
            'Fleet admission refusal invents native replay work.');
        if (receipt.state === 'inconclusive') need(terminal || checkerFailed,
            'Fleet inconclusive outcome requires incomplete work or a retained checker failure.');
        if (admissionOnly) need(logicalKeys.every(key => nativeWork[key] === 0), 'Fleet admission-only receipt invents native work.');
    }
    const identityValue = {schema: 'discovery-lab-fleet-receipt-identity/v1', request,
        source: {adapterSha256: source.adapterSha256, contractSha256: source.contractSha256},
        admissionChecking: 1, nativeWork: Object.fromEntries(logicalKeys.map(key => [key, nativeWork[key]]))};
    return {receiptId: await contract.payloadDigest(identityValue), receiptDigest: await digest(input.raw),
        nativeReceiptDigest: await digest(envelope.receiptRaw), requestDigest: await digest(envelope.original),
        campaignDigest: context.campaignDigest, commission: copy(request.commission), state: receipt.state,
        resources: copy(used), source: copy(source), inspectionKind: 'fleet-local-review',
        installedRuntime: {executorId: receipt.executorId, runtimeDigest: receipt.runtimeDigest, provenance: 'unattested-declaration'},
        accounting: 'separate Fleet invocation observation; no aggregate system-total or authenticated invocation multiplicity',
        provenance: 'retained-unattested-source', authenticity: 'not-attested', authority: 'none'};
}
