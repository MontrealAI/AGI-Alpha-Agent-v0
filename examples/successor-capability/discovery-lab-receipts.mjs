// SPDX-License-Identifier: Apache-2.0
// Pure structural receipt checks. Caller supplies already replayed campaign context.
// Content identity is not authenticated invocation identity or execution authority.
import * as contract from './discovery-lab-contract.mjs';
const same = (left, right) => contract.canonical(left) === contract.canonical(right);
const copy = value => JSON.parse(contract.canonical(value));
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const need = (condition, message) => { if (!condition) throw Error(message); };
const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const git = value => typeof value === 'string' && /^[0-9a-f]{40}$/.test(value);
const bytes = value => new TextEncoder().encode(value).length;
const terminalIncomplete = reason => /(?:BUDGET_EXHAUSTED|SEARCH_TRUNCATED|CHECK_INCOMPLETE)$/.test(reason);
const receiptZero = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
const fits = (used, limits) => contract.RESOURCE_KEYS.every(key => used[key] <= limits[key]);
const bindings = value => Object.fromEntries(contract.BINDING_KEYS.map(key => [key, value[key]]));
const CONTEXT_KEYS = ['campaignDigest', 'attempt', 'bindings', 'lineageQualified', 'charter', 'result', 'artifacts', 'ancestors'];
export async function rawReceiptDigest(text) {
    need(typeof text === 'string' && text.length <= contract.MAX_INPUT_BYTES
        && bytes(text) <= contract.MAX_INPUT_BYTES, 'Docket raw data exceeds its bound.');
    return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))]
        .map(value => value.toString(16).padStart(2, '0')).join('');
}
function own(value, key) {
    const descriptor = value && Object.getOwnPropertyDescriptor(value, key);
    need(descriptor && Object.hasOwn(descriptor, 'value'), 'Receipt context requires inert own data fields.');
    return descriptor.value;
}
/** Capture a minimal flat context; never copy recursively nested parent records. */
export function makeReceiverContext(campaign) {
    const context = Object.fromEntries(CONTEXT_KEYS.filter(key => key !== 'ancestors').map(key => [key, own(campaign, key)]));
    const ancestors = [], seen = new Set([context.campaignDigest]);
    for (let parent = own(campaign, 'parent'); parent; parent = own(parent, 'parent')) {
        const digest = own(parent, 'campaignDigest');
        need(ancestors.length < 8 && hash(digest) && !seen.has(digest), 'Receipt context ancestry is cyclic or unbounded.');
        seen.add(digest); ancestors.unshift({charter: own(parent, 'charter'), result: own(parent, 'result')});
    }
    context.ancestors = ancestors;
    return JSON.parse(contract.canonical(context));
}
const sourceKeys = ['repository', 'commit', 'tree', 'adapterSha256', 'contractSha256'];
function receiverSource(input, route) {
    need(exact(input, sourceKeys) && git(input.commit) && git(input.tree)
        && hash(input.adapterSha256) && hash(input.contractSha256)
        && input.repository === (route === 'manager-usdc' ? 'MontrealAI/AGIJobManager' : 'MontrealAI/AGIJobsv0'),
    'Docket receiver source identity differs.');
    return input;
}
function semanticReceipt(receipt, request) {
    const inspection = copy(receipt);
    // Raw JSON framing has its own exact-byte digest. It cannot mint another
    // inspection identity, including through sizes derived from that framing.
    delete inspection.original; delete inspection.requestSha256;
    for (const key of ['receiverUsed', 'receiverReservation', 'nativeLimits', 'totalUsed']) {
        if (inspection.resources[key] === null) continue;
        delete inspection.resources[key].storageBytes;
        delete inspection.resources[key].memoryBytes;
    }
    // Native work, limits in the parsed request, stage, outcome and diagnostics
    // remain bound. Without an invocation nonce identical executions cannot be
    // distinguished; no caller-supplied identity is invented for them.
    return {schema: 'discovery-lab-receipt-identity/v2', request, inspection};
}
export async function inspectReceiverReceipt(input, context, options = {}) {
    const frame = JSON.parse(contract.canonical({input, context, options}));
    input = frame.input; context = frame.context; options = frame.options;
    need(exact(options, []) || exact(options, ['expectedReceiverSources']), 'Unsupported receiver inspection options.');
    const expectedReceiverSources = options.expectedReceiverSources;
    need(exact(context, CONTEXT_KEYS), 'Receiver needs an independently replayed campaign context.');
    contract.validateBindings(context.bindings);
    need(hash(context.campaignDigest) && typeof context.attempt === 'string' && Array.isArray(context.ancestors)
        && context.ancestors.length <= 8 && Array.isArray(context.artifacts) && context.artifacts.length === 6,
    'Malformed receiver campaign context.');
    need(exact(input, ['raw', 'source']) && typeof input.raw === 'string', 'Docket needs exact raw receiver bytes.');
    const receipt = contract.parseBounded(input.raw);
    const receiptKeys = ['schema', 'state', 'original', 'requestSha256', 'bindings', 'commission', 'stage',
        'inputArtifacts', 'payloadDigest', 'source', 'checker', 'resources', 'reason', 'lifecycle',
        'capabilityAcceptance', 'authority'];
    need(exact(receipt, receiptKeys), 'Unsupported docket receiver receipt.');
    const request = await contract.parseWorkRequest(receipt.original);
    const route = request.commission.route;
    const source = receiverSource(input.source, route);
    need(receipt.schema === (route === 'manager-usdc' ? 'agijobmanager' : 'agijobsv0') + '/discovery-lab-admission/v1'
        && same(receipt.bindings, bindings(request)) && same(receipt.commission, request.commission)
        && receipt.stage === request.stage && same(receipt.inputArtifacts, request.inputArtifacts)
        && receipt.payloadDigest === request.payloadDigest && receipt.requestSha256 === await rawReceiptDigest(receipt.original)
        && same(receipt.source, {adapterSha256: source.adapterSha256, contractSha256: source.contractSha256}),
    'Docket receiver request, route or source binding differs.');
    if (expectedReceiverSources !== undefined) {
        need(expectedReceiverSources.some(item => same(item, source)), 'Receiver is absent from the installed source context.');
    }
    const campaign = context;
    need(same(campaign.bindings, receipt.bindings) && campaign.lineageQualified !== false,
        'Docket receipt has no unique qualified mission campaign.');
    const ancestors = campaign.ancestors;
    need(same(request.payload, {schema: 'discovery-lab-review-payload/v1', charter: campaign.charter,
        result: campaign.result, ancestors}) && same(request.inputArtifacts,
        campaign.artifacts.slice(0, contract.STAGES.indexOf(request.stage)).map(item => item.digest))
        && request.commission.id === campaign.attempt,
    'Docket receipt artifact, payload or ancestry differs.');
    need(exact(receipt.checker, ['report', 'withinResourceEnvelope', 'nativeWithinResourceEnvelope'])
        && exact(receipt.resources, ['units', 'receiverUsed', 'checkerUsed', 'totalUsed', 'receiverReservation',
            'nativeLimits', 'reservationAvailable']) && typeof receipt.resources.units === 'string',
    'Unsupported docket receiver resource evidence.');
    const resources = receipt.resources;
    for (const key of ['receiverUsed', 'checkerUsed', 'totalUsed', 'receiverReservation']) contract.validateResources(resources[key]);
    need(resources.reservationAvailable === fits(resources.receiverReservation, request.resourceLimits),
        'Docket receiver reservation differs.');
    if (resources.reservationAvailable) {
        need(receipt.checker.report !== null, 'A returned admitted receipt must retain its native report.');
        contract.validateResources(resources.nativeLimits);
        need(contract.RESOURCE_KEYS.every(key => resources.nativeLimits[key]
            === request.resourceLimits[key] - resources.receiverReservation[key]), 'Docket native allowance differs.');
    } else need(resources.nativeLimits === null && receipt.checker.report === null, 'Unavailable receiver reservation invoked native work.');
    need(resources.receiverUsed.checking === 10_000 && resources.receiverReservation.checking === 10_000
        && ['acquisitions', 'search', 'workerCapacity', 'installations'].every(key => resources.receiverUsed[key] === 0)
        && resources.receiverUsed.memoryBytes >= bytes(receipt.original), 'Docket omits declared receiver charges.');
    const report = receipt.checker.report;
    if (report !== null) {
        need(exact(report, ['accepted', 'resourceUsed', 'reasons']) && typeof report.accepted === 'boolean'
            && Array.isArray(report.reasons) && report.reasons.length <= 32
            && report.reasons.every(reason => typeof reason === 'string' && reason.length > 0 && reason.length <= 500)
            && (report.accepted || report.reasons.length > 0)
            && !(report.accepted && report.reasons.some(terminalIncomplete)), 'Docket checker report differs.');
        contract.validateResources(report.resourceUsed);
        need(same(resources.checkerUsed, report.resourceUsed)
            && (!report.accepted || campaign.result.stages[contract.STAGES.indexOf(request.stage)].status === 'accepted'),
        'Docket receipt forges finite acceptance or omits checker costs.');
        const prefix = {acquisitions: 0, search: 0, checking: 10_000, storageBytes: 0, installations: 0,
            memoryBytes: 0, workerCapacity: 0};
        const replayPrefixes = [{...prefix}];
        for (const item of [...ancestors, {charter: campaign.charter, result: campaign.result}]) {
            for (const key of ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']) prefix[key] += item.result.resources[key];
            prefix.memoryBytes = Math.max(prefix.memoryBytes, item.result.resources.memoryWords * 8);
            prefix.workerCapacity = Math.max(prefix.workerCapacity, item.result.resources.workerSlots);
            replayPrefixes.push({...prefix});
        }
        const allowed = report.accepted ? replayPrefixes.slice(-1) : replayPrefixes;
        need(allowed.some(item => Object.keys(item).every(key => key === 'memoryBytes'
            ? resources.checkerUsed[key] >= item[key] : resources.checkerUsed[key] === item[key])),
        'Docket native replay costs do not match any executed ancestry prefix.');
    } else need(same(resources.checkerUsed, receiptZero()), 'Absent checker has invented costs.');
    for (const key of contract.RESOURCE_KEYS.filter(key => key !== 'elapsedMs')) {
        need(resources.totalUsed[key] === resources.receiverUsed[key] + resources.checkerUsed[key]
            && Number.isSafeInteger(resources.totalUsed[key]), 'Docket receiver component sum differs.');
    }
    need(resources.totalUsed.elapsedMs >= Math.max(resources.receiverUsed.elapsedMs, resources.checkerUsed.elapsedMs)
        && resources.totalUsed.elapsedMs <= resources.receiverUsed.elapsedMs + resources.checkerUsed.elapsedMs,
    'Docket elapsed receipt omits or double-counts native overlap.');
    need(resources.receiverUsed.storageBytes === bytes(JSON.stringify(receipt)), 'Docket receipt storage charge differs.');
    const nativeWithin = Boolean(report && fits(resources.checkerUsed, resources.nativeLimits));
    const within = fits(resources.totalUsed, request.resourceLimits);
    const incomplete = Boolean(report && !report.accepted && report.reasons.some(terminalIncomplete));
    const state = !resources.reservationAvailable || !nativeWithin || !within || incomplete ? 'inconclusive'
        : report.accepted ? 'local-checked' : 'local-rejected';
    const reason = !resources.reservationAvailable ? 'RECEIVER_RESERVATION_UNAVAILABLE'
        : !nativeWithin ? 'NATIVE_RESOURCE_ENVELOPE_EXCEEDED' : null;
    need(receipt.state === state && receipt.reason === reason && receipt.checker.withinResourceEnvelope === within
        && receipt.checker.nativeWithinResourceEnvelope === nativeWithin
        && same(receipt.lifecycle, {commission: 'DRAFT_NOT_SUBMITTED', reservedBaseUnits: '0', execution: 'unprovisioned',
            review: 'separate-review-required', settlement: 'not-connected'})
        && receipt.capabilityAcceptance === 'not-granted-by-import' && receipt.authority === 'none',
    'Docket receiver status or authority is forged.');
    return {receiptId: await contract.payloadDigest(semanticReceipt(receipt, request)), receiptDigest: await rawReceiptDigest(input.raw), requestDigest: receipt.requestSha256,
        campaignDigest: campaign.campaignDigest, commission: copy(receipt.commission), state,
        resources: copy(resources.totalUsed), source: copy(source),
        provenance: 'retained-unattested-source',
        authenticity: 'not-attested', authority: 'none'};
}
