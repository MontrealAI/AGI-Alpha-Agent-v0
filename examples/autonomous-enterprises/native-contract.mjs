// SPDX-License-Identifier: Apache-2.0
// Fixed-source local inspection. Data selects no code, provider, transaction or authority.
import * as workspace from '../successor-capability/workspace.mjs';
import {canonical, parseBounded, payloadDigest} from '../successor-capability/discovery-lab-contract.mjs';
import {exportDiscoveryDocket, verifyDiscoveryDocket, DOCKET_PATHS} from '../successor-capability/discovery-lab-docket.mjs';
import {auditSnapshot} from './protocol.mjs';

export const REQUEST_SCHEMA = 'autonomous-enterprise-native-request/v1';
export const CONTEXT_SCHEMA = 'autonomous-enterprise-native-context/v1';
export const RECEIPT_SCHEMA = 'autonomous-enterprise-native-inspection/v1';
export const NATIVE_ADMISSION_UNITS = 10_000;
export const MAX_NATIVE_INSPECTIONS = 4;
export const RECEIPT_KEYS = Object.freeze(['schema', 'state', 'accepted', 'requestDigest', 'reconciliationKey',
    'binding', 'route', 'source', 'payloadDigest', 'docketDigest', 'resourceUsed', 'work', 'reasons',
    'historicalState', 'authority', 'externalSubmission', 'settlement', 'reconciliation', 'scope']);
const REQUEST_KEYS = ['schema', 'inspectionId', 'logicalCommissionId', 'route', 'source', 'binding',
    'payloadDigest', 'docketDigest', 'payload', 'limits', 'authority', 'externalSubmission', 'settlement'];
const CONTEXT_KEYS = ['schema', 'source', 'binding', 'inspectionId', 'logicalCommissionId', 'route', 'limits'];
const BINDING_KEYS = ['missionId', 'revision', 'eventHead', 'eventPrefixDigest', 'attempt', 'state',
    'freezeDigest', 'artifactDigests', 'invocationId'];
const SOURCE_KEYS = ['repository', 'commit', 'constructor', 'checker', 'closure'];
const LIMIT_KEYS = ['checkingUnits', 'elapsedMs', 'memoryBytes'];
const FROZEN_STATES = ['FROZEN', 'TASKS_COMMITTED', 'INVOCATION_RESERVED', 'INVOCATION_RECONCILED',
    'READY_FOR_SUCCESSOR', 'SUCCESSOR_RESERVED', 'SUCCESSOR_ACCEPTED_LOCAL', 'INCONCLUSIVE', 'REJECTED', 'CANCELLED'];
const MEASUREMENT = 'Declared current shared-session replay delta; native inspections are serialized; unrelated host work is not excluded. '
    + 'Memory bytes reserve four canonical UTF-8 input/context/options footprints, not measured peak VM heap; output, control and framing overhead remain unmeasured. '
    + 'Checking and elapsed limits are soft checks before and after complete bounded replays; JavaScript execution is not preempted.';
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const git = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const id = value => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_.:-]{0,127}$/.test(value);
const nonnegative = (value, maximum) => Number.isSafeInteger(value) && !Object.is(value, -0)
    && value >= 0 && value <= maximum;
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const need = (condition, message) => { if (!condition) throw Error(message); };
const own = value => JSON.parse(canonical(value));
const same = (left, right) => canonical(left) === canonical(right);
const now = () => performance.now();
const ROUTES = {
    'manager-usdc': {id: 'manager-usdc', kind: 'alternative-commission-inspection', currency: 'USDC6',
        decimals: 6, chainId: 1, tokenAddress: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        capBaseUnits: '0', status: 'DRAFT_NOT_SUBMITTED'},
    'jobs-agialpha': {id: 'jobs-agialpha', kind: 'alternative-commission-inspection', currency: 'AGIALPHA18',
        decimals: 18, chainId: 1, tokenAddress: '0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA',
        capBaseUnits: '0', status: 'DRAFT_NOT_SUBMITTED'},
    'fleet-check': {id: 'fleet-check', kind: 'execution-review', currency: 'NONE', decimals: 0,
        chainId: null, tokenAddress: null, capBaseUnits: '0', status: 'INSPECTION_ONLY'}
};
export function routeFor(routeId) {
    need(typeof routeId === 'string' && Object.hasOwn(ROUTES, routeId), 'Unsupported enterprise inspection route.');
    return own(ROUTES[routeId]);
}
export function validateRoute(input, expectedId = null) {
    const route = own(input);
    need(exact(route, Object.keys(ROUTES['manager-usdc'])) && same(route, routeFor(route.id))
        && (expectedId === null || route.id === expectedId), 'Route, currency, chain, token or zero-cap binding differs.');
    return route;
}
export function validateLimits(input) {
    const limits = own(input);
    need(exact(limits, LIMIT_KEYS) && nonnegative(limits.checkingUnits, 100_000_000)
        && nonnegative(limits.elapsedMs, 60_000) && nonnegative(limits.memoryBytes, 32_000_000),
    'Finite native inspection limits are required.');
    return limits;
}
function validateSource(input) {
    const source = own(input);
    need(exact(source, SOURCE_KEYS) && source.repository === 'MontrealAI/AGI-Alpha-Agent-v0'
        && git(source.commit) && ['constructor', 'checker', 'closure'].every(key => hash(source[key])),
    'Installed Alpha repository, commit and source identities are required.');
    return source;
}
function validateBinding(input) {
    const binding = own(input);
    need(exact(binding, BINDING_KEYS) && /^capability-[a-f0-9-]{36}$/.test(binding.missionId)
        && nonnegative(binding.revision, workspace.LIMITS.events - 1) && hash(binding.eventHead)
        && hash(binding.eventPrefixDigest) && /^enterprise-[a-f0-9-]{36}$/.test(binding.attempt)
        && FROZEN_STATES.includes(binding.state) && hash(binding.freezeDigest)
        && Array.isArray(binding.artifactDigests) && binding.artifactDigests.length >= 4
        && binding.artifactDigests.length <= 9 && binding.artifactDigests.every(hash)
        && new Set(binding.artifactDigests).size === binding.artifactDigests.length
        && (binding.invocationId === null || /^invocation-[a-f0-9-]{36}$/.test(binding.invocationId)),
    'Frozen mission, event prefix, artifact and invocation bindings are required.');
    return binding;
}
export function validateInstalledContext(input) {
    const value = own(input);
    need(exact(value, CONTEXT_KEYS) && value.schema === CONTEXT_SCHEMA
        && id(value.inspectionId) && id(value.logicalCommissionId), 'Independent native context is required.');
    value.source = validateSource(value.source); value.binding = validateBinding(value.binding);
    value.route = validateRoute(value.route); value.limits = validateLimits(value.limits);
    return value;
}
export async function rawDigest(text) {
    need(typeof text === 'string' && new TextEncoder().encode(text).length <= 2_000_000,
        'Bounded exact UTF-8 text required.');
    return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))]
        .map(value => value.toString(16).padStart(2, '0')).join('');
}
function selectedRow(inspection, attempt) {
    const rows = inspection.enterprises?.attempts.filter(row => row.attempt === attempt) || [];
    need(rows.length === 1 && rows[0].freeze && rows[0].bundle, 'Select one actually accepted and frozen enterprise attempt.');
    return rows[0];
}
async function bindingFor(value, inspection, row) {
    const artifacts = row.successor?.retainedArtifactDigests || row.freeze.artifactDigests;
    return validateBinding({missionId: value.missionId, revision: value.revision, eventHead: inspection.head,
        eventPrefixDigest: await payloadDigest({missionId: value.missionId, revision: value.revision,
            eventDigests: value.events.map(event => event.digest)}),
        attempt: row.attempt, state: row.state, freezeDigest: row.freeze.digest,
        artifactDigests: artifacts, invocationId: row.invocation?.invocationId || null});
}
function sourceMatchesRow(source, row) {
    return ['constructor', 'checker', 'closure'].every(key => source[key] === row.charter.source[key]);
}
function historicalState(row) {
    return {state: row.state, unknownConstructionSpent: row.unknownSpent === true,
        unresolvedReservation: row.unresolvedReservation === true || row.state === 'INVOCATION_RESERVED'
            || row.state === 'SUCCESSOR_RESERVED', futureSpent: row.futureSpent ?? null,
        successorSpent: row.successorSpent ?? null};
}
function acceptableState(row) {
    return ['FROZEN', 'TASKS_COMMITTED', 'INVOCATION_RECONCILED', 'READY_FOR_SUCCESSOR', 'SUCCESSOR_ACCEPTED_LOCAL'].includes(row.state)
        && !row.unknownSpent && !row.unresolvedReservation
        && row.futureSpent !== 'unknown-reservation-retained' && row.successorSpent !== 'unknown-reservation-retained';
}
export async function createNativeExport(workspaceInput, optionsInput) {
    // Capture both complete caller graphs before the first digest/replay await.
    const value = own(workspaceInput), options = own(optionsInput);
    need(exact(options, ['attempt', 'inspectionId', 'logicalCommissionId', 'route', 'source', 'limits'])
        && id(options.inspectionId) && id(options.logicalCommissionId), 'Exact native export options required.');
    const source = validateSource(options.source), route = routeFor(options.route), limits = validateLimits(options.limits);
    const inspection = await workspace.inspectWorkspace(value), row = selectedRow(inspection, options.attempt);
    need(sourceMatchesRow(source, row), 'Export source differs from the frozen mission charter.');
    const binding = await bindingFor(value, inspection, row);
    const payload = {workspace: value};
    const docket = await exportDiscoveryDocket(value);
    const request = {schema: REQUEST_SCHEMA, inspectionId: options.inspectionId,
        logicalCommissionId: options.logicalCommissionId, route, source, binding,
        payloadDigest: await payloadDigest(payload), docketDigest: await rawDigest(docket), payload, limits,
        authority: [], externalSubmission: 'NOT_SUBMITTED', settlement: 'NOT_RUN'};
    return {request: own(request), docket};
}
async function validateRequest(request, context, docket) {
    need(exact(request, REQUEST_KEYS) && request.schema === REQUEST_SCHEMA && id(request.inspectionId)
        && id(request.logicalCommissionId) && exact(request.payload, ['workspace'])
        && same(request.authority, []) && request.externalSubmission === 'NOT_SUBMITTED'
        && request.settlement === 'NOT_RUN', 'Unsupported native request frame or authority.');
    validateSource(request.source); validateRoute(request.route); validateBinding(request.binding); validateLimits(request.limits);
    need(['source', 'binding', 'inspectionId', 'logicalCommissionId', 'route', 'limits']
        .every(key => same(request[key], context[key])), 'Request differs from independently installed native context.');
    need(hash(request.payloadDigest) && hash(request.docketDigest)
        && request.payloadDigest === await payloadDigest(request.payload)
        && request.docketDigest === await rawDigest(docket), 'Native payload or exact docket commitment differs.');
}
function replayDelta(before, after) {
    const result = ['bundleReplayWork', 'futureReplayWork', 'successorReplayWork']
        .reduce((total, key) => total + after[key] - before[key], 0);
    need(Number.isSafeInteger(result) && result >= 0, 'Current inspection work counter changed incompatibly.');
    return {known: result, unknown: after.rejectedReplaysWithUnknownPartialWork > before.rejectedReplaysWithUnknownPartialWork};
}
let inspectionQueue = Promise.resolve();
let retainedNativeAdmissions = 0;
function queueFullReceipt(started) {
    return own({schema: RECEIPT_SCHEMA, state: 'INCONCLUSIVE', accepted: false,
        requestDigest: null, reconciliationKey: null, binding: null, route: null, source: null,
        payloadDigest: null, docketDigest: null,
        resourceUsed: {checkingUnits: NATIVE_ADMISSION_UNITS, elapsedMs: Math.max(0, Math.ceil(now() - started)), memoryBytes: 0},
        work: {admissionUnits: NATIVE_ADMISSION_UNITS, knownReplayWork: 0, unknownPartialReplay: false, measurement: MEASUREMENT},
        reasons: ['NATIVE_INSPECTION_QUEUE_FULL_NOT_STARTED'], historicalState: null,
        authority: [], externalSubmission: 'NOT_SUBMITTED', settlement: 'NOT_RUN',
        reconciliation: 'RECEIVER_HISTORY_COMMIT_REQUIRED', scope: 'LOCAL_FIXED_SOURCE_INSPECTION_ONLY'});
}

/** Caller supplies approved installed context and commits the returned key once in its existing receiver history. */
export async function inspectNativeRequest(requestInput, contextInput, optionsInput) {
    const started = now();
    // Refuse excess admissions before retaining or capturing their potentially large caller graphs.
    if (retainedNativeAdmissions >= MAX_NATIVE_INSPECTIONS) return queueFullReceipt(started);
    retainedNativeAdmissions++;
    try {
        let memoryBytes = 0, request = null, context = null, options = null;
        let effective = null, requestDigest = null, reconciliationKey = null, retainedState = null;
        let before = null, replayStarted = false, invalidFrame = false, validContext = false, reportedBinding = null;
        const used = {checkingUnits: NATIVE_ADMISSION_UNITS, elapsedMs: 0, memoryBytes: 0};
        const work = {admissionUnits: NATIVE_ADMISSION_UNITS, knownReplayWork: 0,
            unknownPartialReplay: false, measurement: MEASUREMENT};
        const capture = input => { const text = canonical(input); memoryBytes += 4 * new TextEncoder().encode(text).length;
            return JSON.parse(text); };
        try {
            request = capture(requestInput); context = capture(contextInput); options = capture(optionsInput);
            need(exact(options, ['docket']) || exact(options, ['docket', 'effectiveLimits']), 'Unsupported native inspection options.');
            need(typeof options.docket === 'string', 'The unchanged thirteen-section docket is required.');
            context = validateInstalledContext(context);
            validContext = true;
            reportedBinding = validateBinding(request.binding);
            effective = validateLimits(options.effectiveLimits || context.limits);
            need(LIMIT_KEYS.every(key => effective[key] <= context.limits[key]), 'Effective limit exceeds installed commitment.');
        } catch { invalidFrame = true; }
        const finish = (state, reasons) => {
            used.memoryBytes = memoryBytes; used.elapsedMs = Math.max(0, Math.ceil(now() - started));
            if (before) {
                const delta = replayDelta(before, auditSnapshot());
                work.knownReplayWork = delta.known; work.unknownPartialReplay ||= delta.unknown;
                used.checkingUnits = NATIVE_ADMISSION_UNITS + delta.known;
            }
            if (effective && (LIMIT_KEYS.some(key => used[key] > effective[key]) || effective.elapsedMs === 0)) {
                state = 'INCONCLUSIVE'; reasons = [...reasons, 'NATIVE_INSPECTION_LIMIT_EXHAUSTED'];
            }
            if (work.unknownPartialReplay) { state = 'INCONCLUSIVE'; reasons = [...reasons, 'UNKNOWN_PARTIAL_REPLAY_WORK_RETAINED']; }
            return own({schema: RECEIPT_SCHEMA, state, accepted: state === 'ACCEPTED_LOCAL_INSPECTION',
                requestDigest, reconciliationKey, binding: reportedBinding,
                route: validContext ? context.route : null, source: validContext ? context.source : null,
                payloadDigest: request && hash(request.payloadDigest) ? request.payloadDigest : null,
                docketDigest: request && hash(request.docketDigest) ? request.docketDigest : null,
                resourceUsed: used, work, reasons: [...new Set(reasons)], historicalState: retainedState,
                authority: [], externalSubmission: 'NOT_SUBMITTED', settlement: 'NOT_RUN',
                reconciliation: 'RECEIVER_HISTORY_COMMIT_REQUIRED', scope: 'LOCAL_FIXED_SOURCE_INSPECTION_ONLY'});
        };
        if (invalidFrame) return finish('REJECTED', ['INVALID_NATIVE_FRAME_OR_CONTEXT']);
        if (effective.elapsedMs === 0 || used.checkingUnits > effective.checkingUnits || memoryBytes > effective.memoryBytes) {
            return finish('INCONCLUSIVE', ['NATIVE_INSPECTION_PREFLIGHT_INCOMPLETE']);
        }
        const previous = inspectionQueue;
        let release;
        inspectionQueue = new Promise(resolve => { release = resolve; });
        await previous;
        try {
            if (now() - started >= effective.elapsedMs) return finish('INCONCLUSIVE', ['NATIVE_INSPECTION_QUEUE_DEADLINE']);
            requestDigest = await payloadDigest(request);
            await validateRequest(request, context, options.docket);
            need(LIMIT_KEYS.every(key => effective[key] <= request.limits[key]), 'Effective limit exceeds request commitment.');
            reconciliationKey = await payloadDigest({schema: 'autonomous-enterprise-native-reconciliation-key/v1',
                source: request.source, binding: request.binding, inspectionId: request.inspectionId,
                logicalCommissionId: request.logicalCommissionId, route: request.route});
            const docket = parseBounded(options.docket);
            need(exact(docket.files, DOCKET_PATHS), 'The canonical thirteen docket paths are required.');
            const run = parseBounded(docket.files['05_agialpha_runs/run.json']);
            need(same(run.workspace, request.payload.workspace), 'Docket and native payload identify different mission histories.');
            before = auditSnapshot(); replayStarted = true;
            const inspected = await workspace.inspectWorkspace(request.payload.workspace);
            const row = selectedRow(inspected, request.binding.attempt);
            retainedState = historicalState(row);
            need(same(await bindingFor(request.payload.workspace, inspected, row), request.binding)
                && sourceMatchesRow(request.source, row), 'Current replay differs from frozen mission or source bindings.');
            if (NATIVE_ADMISSION_UNITS + replayDelta(before, auditSnapshot()).known > effective.checkingUnits
                || now() - started >= effective.elapsedMs) return finish('INCONCLUSIVE', ['CURRENT_HISTORY_REPLAY_LIMIT_EXHAUSTED']);
            await verifyDiscoveryDocket(options.docket, {expectedMissionId: request.binding.missionId,
                expectedWorkspaceHead: request.binding.eventHead});
            if (!acceptableState(row)) return finish('INCONCLUSIVE', ['HISTORICAL_STATE_REQUIRES_RECONCILIATION']);
            return finish('ACCEPTED_LOCAL_INSPECTION', []);
        } catch {
            if (replayStarted) work.unknownPartialReplay = true;
            return finish(replayStarted ? 'INCONCLUSIVE' : 'REJECTED',
                [replayStarted ? 'CURRENT_FIXED_SOURCE_REPLAY_INCOMPLETE' : 'NATIVE_CONTEXT_OR_COMMITMENT_MISMATCH']);
        } finally { release(); }
    } finally { retainedNativeAdmissions--; }
}
