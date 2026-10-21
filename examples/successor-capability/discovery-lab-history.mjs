// SPDX-License-Identifier: Apache-2.0
// Versioned events in the existing capability history. No separate persistence store.
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
import * as artifacts from './discovery-lab-artifacts.mjs';

export const EVENT_KINDS = Object.freeze(['lab-started', 'lab-completed', 'lab-stopped']);
export const EXTENDED_SCHEMA = 'successor-capability-workspace/v2';
export const REPORT_RESERVE_BYTES = 500_000;
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const same = (a, b) => contract.canonical(a) === contract.canonical(b);
const copy = value => JSON.parse(contract.canonical(value));
const need = (condition, message) => { if (!condition) throw Error(message); };
const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const integer = value => Number.isSafeInteger(value) && value >= 0 && !Object.is(value, -0);
const SOURCE_KEYS = ['modelDigest', 'sourceDigest', 'evaluatorDigest'];
const sessionAudit = {id: crypto.randomUUID(), inspections: 0, resources: {}, cachedInspections: 0, cacheBytesPeak: 0};
const verifiedReports = new Map();
const CACHE_ENTRIES = 12;
const CACHE_BYTES = 8_000_000;
export function auditSnapshot() { return copy(sessionAudit); }
export function validateHistoryData(value) { return contract.canonical(value); }
function chargeReplay(resources) {
    sessionAudit.inspections += 1;
    for (const [key, value] of Object.entries(resources)) {
        sessionAudit.resources[key] = ['memoryWords', 'workerSlots'].includes(key)
            ? Math.max(sessionAudit.resources[key] || 0, value) : (sessionAudit.resources[key] || 0) + value;
    }
}
function freezeData(value) {
    if (value && typeof value === 'object') {
        for (const child of Object.values(value)) freezeData(child);
        if (!Object.isFrozen(value)) Object.freeze(value);
    }
    return value;
}
function verificationKey(charter, result, parent) {
    return contract.canonical({charter, result, parent});
}
function verifyReport(charter, result, parent, recording) {
    const key = verificationKey(charter, result, parent);
    if (!recording && verifiedReports.has(key)) {
        sessionAudit.cachedInspections += 1;
        const retained = verifiedReports.get(key);
        verifiedReports.delete(key); verifiedReports.set(key, retained);
        return retained;
    }
    let verification;
    try { verification = runtime.verifyCampaign(charter, result, {parent}); }
    catch (error) {
        if (error.verificationResources) chargeReplay(error.verificationResources);
        throw error;
    }
    need(verification?.verified === true, 'Discovery Lab finite replay rejected the result.');
    if (!recording) chargeReplay(verification.verificationResources);
    const checked = {result: freezeData(result), verification: freezeData(copy(verification))};
    verifiedReports.set(key, checked);
    const cacheBytes = () => [...verifiedReports].reduce((total, [item, record]) => total
        + new TextEncoder().encode(item).length + new TextEncoder().encode(contract.canonical(record)).length, 0);
    while (verifiedReports.size > CACHE_ENTRIES || cacheBytes() > CACHE_BYTES) {
        verifiedReports.delete(verifiedReports.keys().next().value);
    }
    sessionAudit.cacheBytesPeak = Math.max(sessionAudit.cacheBytesPeak, cacheBytes());
    return checked;
}
export function verifyForRecording(charter, result, parent = null) {
    return verifyReport(charter, result, parent, true).verification;
}
export function reservationFor(charter) {
    return {acquisitions: 2 * charter.budget.acquisitions, search: 2 * charter.budget.search,
        checking: 2 * charter.budget.checking, memoryBytes: 10_000_000, storageBytes: REPORT_RESERVE_BYTES,
        workerCapacity: charter.workerCapacity, installations: 2 * charter.budget.installations, elapsedMs: 120_000};
}

export function emptyDiscoveryState() { return {attempts: [], campaigns: [], active: null}; }

/** Select a completed attempt by its source-bound history identity, never its reusable numeric result. */
export function selectCampaign(campaigns, selection) {
    const identity = {};
    for (const key of ['campaignDigest', 'attempt', 'bindings', 'resultDigest']) {
        const descriptor = selection && Object.getOwnPropertyDescriptor(selection, key);
        need(descriptor && Object.hasOwn(descriptor, 'value'), 'Select one complete source-bound campaign identity.');
        identity[key] = descriptor.value;
    }
    contract.validateBindings(identity.bindings);
    need(hash(identity.campaignDigest) && hash(identity.resultDigest), 'Invalid campaign identity.');
    const matches = campaigns.filter(record => record.campaignDigest === identity.campaignDigest);
    need(matches.length === 1 && matches[0].attempt === identity.attempt
        && matches[0].resultDigest === identity.resultDigest && same(matches[0].bindings, identity.bindings),
    'The selected source-bound campaign is absent or changed.');
    need(matches[0].lineageQualified !== false,
        'This historical campaign has unresolved parent lineage; requalify it without inherited authority.');
    return matches[0];
}

/** Reconstruct events without converting imports into authority or externally qualified work. */
export async function inspectDiscoveryEvent(state, event, context) {
    const payload = event.payload;
    if (event.kind === 'lab-started') {
        need(exact(payload, ['attempt', 'version', 'bindings', 'charter', 'parentDigest', 'reservation']),
            'Unsupported Discovery Lab start fields.');
        need(state.active === null && /^lab-[0-9a-f-]{36}$/.test(payload.attempt)
            && !state.attempts.some(item => item.attempt === payload.attempt)
            && payload.version === context.version, 'Discovery Lab attempt or version conflict.');
        const bindings = contract.validateBindings(payload.bindings);
        need(bindings.missionId === context.missionId && bindings.revision === event.sequence,
            'Discovery Lab mission/revision binding mismatch.');
        const charter = runtime.validateCharter(payload.charter);
        need(bindings.charterDigest === await contract.payloadDigest(charter)
            && bindings.purposeDigest === await contract.payloadDigest({purpose: charter.purpose}),
            'Discovery Lab purpose or charter commitment mismatch.');
        contract.validateResources(payload.reservation);
        need(same(payload.reservation, reservationFor(charter)),
            'The total construction/replay reservation must bind the frozen per-phase caps.');
        need(payload.parentDigest === null || hash(payload.parentDigest), 'Invalid parent commitment.');
        const identifiedParent = payload.parentDigest === null ? null
            : state.campaigns.find(item => item.campaignDigest === payload.parentDigest && item.state === 'accepted');
        const legacyParents = identifiedParent || payload.parentDigest === null ? []
            : state.campaigns.filter(item => item.resultDigest === payload.parentDigest && item.state === 'accepted');
        // Old v2 histories keep their original first-match interpretation. New starts never create ambiguous references.
        const parent = identifiedParent || legacyParents[0] || null;
        need(payload.parentDigest === null || Boolean(parent), 'Accepted parent is absent from this history.');
        const lineageIssues = [...(parent?.lineageIssues || [])];
        if (legacyParents.length > 1) lineageIssues.push('AMBIGUOUS_LEGACY_PARENT');
        if (parent && !SOURCE_KEYS.every(key => parent.bindings[key] === bindings[key])) {
            lineageIssues.push('PARENT_SOURCE_MISMATCH');
        }
        need(!identifiedParent || lineageIssues.length === 0,
            'The identified parent is not qualified under the current source lineage.');
        const record = {...copy(payload), parent, state: 'searching', lineageQualified: lineageIssues.length === 0,
            lineageIssues: [...new Set(lineageIssues)]};
        state.attempts.push(record);
        state.active = record;
    } else if (event.kind === 'lab-completed') {
        need(exact(payload, ['attempt', 'result', 'resultDigest', 'elapsedMs', 'recordedVerification']),
            'Unsupported Discovery Lab completion fields.');
        const active = state.active;
        need(active && payload.attempt === active.attempt && integer(payload.elapsedMs),
            'Discovery Lab completion has no matching reserved attempt.');
        need(hash(payload.resultDigest) && payload.resultDigest === await contract.payloadDigest(payload.result),
            'Discovery Lab result commitment mismatch.');
        const checked = verifyReport(active.charter, copy(payload.result), active.parent?.result || null, false);
        const verification = checked.verification;
        need(same(payload.recordedVerification, verification.verificationResources),
            'Recorded verification work does not match current finite replay.');
        active.result = checked.result;
        active.artifacts = await artifacts.makeArtifacts(active.bindings, active.result);
        active.resultDigest = payload.resultDigest;
        // The verified completion hash includes the prior start, its mission/source bindings and this exact attempt.
        active.campaignDigest = event.digest;
        active.elapsedReceipt = {elapsedMs: payload.elapsedMs, limitMs: active.reservation.elapsedMs,
            scope: 'Self-reported local construction and verification wall-clock observation. Imports are not fresh measurements.'};
        active.state = payload.elapsedMs > active.reservation.elapsedMs ? 'inconclusive' : payload.result.state;
        active.wrapperOutcome = payload.elapsedMs > active.reservation.elapsedMs
            ? 'Measured local time cap exceeded; finite program evidence is retained without resource-qualified acceptance.' : null;
        active.historicalEvidenceOnly = true;
        active.verification = copy(verification === true || verification === undefined ? {} : verification);
        active.recordedVerification = copy(payload.recordedVerification);
        state.campaigns.push(active);
        state.active = null;
    } else if (event.kind === 'lab-stopped') {
        need(exact(payload, ['attempt', 'state', 'reason', 'resourceDisposition']) && state.active
            && payload.attempt === state.active.attempt && ['paused', 'rejected', 'inconclusive'].includes(payload.state)
            && typeof payload.reason === 'string' && payload.reason.trim() && payload.reason.length <= 1000
            && payload.resourceDisposition === 'reservation-retained-spent-work-unknown',
            'Unsupported Discovery Lab interruption evidence.');
        Object.assign(state.active, copy(payload));
        state.active = null;
    } else throw Error('Unsupported Discovery Lab event.');
    return state;
}

/** Reserve conservative recovery and report capacity before any construction work. */
export function historyCapacity(workspace, eventLimit = 24, byteLimit = 2_000_000) {
    const usedBytes = new TextEncoder().encode(contract.canonical(workspace)).length;
    const remainingEvents = eventLimit - workspace.events.length;
    const remainingBytes = byteLimit - usedBytes;
    return {canRun: remainingEvents >= 3 && remainingBytes >= REPORT_RESERVE_BYTES,
        remainingEvents, remainingBytes, reportReserveBytes: REPORT_RESERVE_BYTES};
}

export async function startPayload(workspace, charter, sources, parentDigest = null) {
    charter = runtime.validateCharter(charter);
    need(exact(sources, ['modelDigest', 'sourceDigest', 'evaluatorDigest'])
        && Object.values(sources).every(hash), 'Installed Discovery Lab source identities are required.');
    const bindings = {missionId: workspace.missionId, revision: workspace.events.length,
        purposeDigest: await contract.payloadDigest({purpose: charter.purpose}),
        charterDigest: await contract.payloadDigest(charter), ...sources};
    const reservation = reservationFor(charter);
    const version = [...workspace.events].reverse().find(event => event.kind === 'version')?.payload.number;
    need(integer(version) && version > 0, 'A frozen capability version is required.');
    if (parentDigest !== null) {
        need(hash(parentDigest), 'Invalid parent commitment.');
        const completed = workspace.events.filter(event => event.kind === 'lab-completed');
        if (!completed.some(event => event.digest === parentDigest)) {
            const legacy = completed.filter(event => event.payload.resultDigest === parentDigest);
            need(legacy.length <= 1, 'Ambiguous result digest; select the unique source-bound campaign.');
            if (legacy.length === 1) parentDigest = legacy[0].digest;
        }
    }
    return {attempt: 'lab-' + crypto.randomUUID(), version, bindings, charter, parentDigest, reservation};
}

export async function completedPayload(attempt, result, elapsedMs, recordedVerification) {
    return {attempt, result: copy(result), resultDigest: await contract.payloadDigest(result), elapsedMs,
        recordedVerification: copy(recordedVerification)};
}

export function stoppedPayload(attempt, reason, state = 'paused') {
    return {attempt, state, reason: String(reason).slice(0, 1000),
        resourceDisposition: 'reservation-retained-spent-work-unknown'};
}

export async function workRequest(record, route, resourceUsed) {
    need(record?.result && record.state === 'accepted' && record.lineageQualified !== false && hash(record.resultDigest),
        'A retained resource-qualified campaign is required for a review draft.');
    const currency = route === 'USDC' ? 'USDC6' : route === 'AGIALPHA' ? 'AGIALPHA18' : null;
    need(currency, 'Select one supported commission route.');
    const ancestors = [];
    for (let parent = record.parent; parent; parent = parent.parent) {
        ancestors.unshift({charter: parent.charter, result: parent.result});
    }
    const payload = {schema: 'discovery-lab-review-payload/v1', charter: record.charter,
        result: record.result, ancestors};
    const inputArtifacts = record.artifacts.slice(0, 5).map(artifact => artifact.digest);
    return contract.validateWorkRequest({schema: contract.REQUEST_SCHEMA, ...record.bindings,
        stage: 'evolve', inputArtifacts, resourceLimits: contract.validateResources(resourceUsed),
        executionMode: 'synthetic-local', commission: {id: record.attempt,
            branch: `${record.attempt}-${route.toLowerCase()}`, route: currency === 'USDC6' ? 'manager-usdc' : 'jobs-agialpha',
            currency, capBaseUnits: '0', status: 'DRAFT_NOT_SUBMITTED'},
        payloadDigest: await contract.payloadDigest(payload), payload});
}
