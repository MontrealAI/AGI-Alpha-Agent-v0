// SPDX-License-Identifier: Apache-2.0
import { canonical, importSearchCheckpoint, exportSearchCheckpoint } from './constructor.mjs';
import * as packages from './capability-package.mjs';

export const WORKSPACE_SCHEMA = 'out-evolve-workspace/v1';
export const WORKSPACE_LIMITS = Object.freeze({events: 256, bytes: 8_000_000});
export const EVENT_KINDS = Object.freeze([
    'brief', 'search-started', 'search-stopped', 'search-paused', 'package-frozen', 'reuse', 'comparison', 'successor', 'failure'
]);
const trustedHistories = new WeakMap();
const clone = value => JSON.parse(canonical(value));
const same = (a, b) => canonical(a) === canonical(b);
const exact = (value, names) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name));

export function createOutEvolveWorkspace(id = globalThis.crypto.randomUUID()) {
    if (typeof id !== 'string' || !/^[a-zA-Z0-9-]{8,80}$/.test(id)) throw Error('Invalid Out-Evolve history identity.');
    return {schema: WORKSPACE_SCHEMA, id, revision: 0, events: [], authority: [], paymentRoute: 'none'};
}

async function eventDigest(id, event) {
    const bytes = new TextEncoder().encode('out-evolve-workspace-event/v1\0' + canonical({
        id, sequence: event.sequence, previous: event.previous, kind: event.kind, payload: event.payload
    }));
    const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
}

function shape(input) {
    const encoded = canonical(input);
    if (new TextEncoder().encode(encoded).length > WORKSPACE_LIMITS.bytes) throw Error('Out-Evolve history exceeds its byte limit.');
    if (!exact(input, ['schema', 'id', 'revision', 'events', 'authority', 'paymentRoute'])
        || input.schema !== WORKSPACE_SCHEMA || typeof input.id !== 'string' || !/^[a-zA-Z0-9-]{8,80}$/.test(input.id)
        || !Array.isArray(input.events) || input.events.length > WORKSPACE_LIMITS.events
        || input.revision !== input.events.length || !same(input.authority, []) || input.paymentRoute !== 'none') {
        throw Error('Unsupported Out-Evolve history or authority.');
    }
    return encoded;
}

function payloadShape(kind, payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw Error('Invalid event payload.');
    if (kind === 'brief') {
        if (!exact(payload, ['purpose', 'constraints', 'budget', 'apparatus'])
            || !['purpose', 'constraints'].every(key => typeof payload[key] === 'string'
                && payload[key].trim() && payload[key].length <= 1000)
            || !Number.isSafeInteger(payload.budget) || payload.budget < 1 || payload.budget > 100000) {
            throw Error('Provide a bounded purpose, constraints and integer construction budget.');
        }
    }
    if (kind === 'failure' && (typeof payload.message !== 'string' || payload.message.length > 2000)) {
        throw Error('Invalid failure record.');
    }
    if (['package-frozen', 'successor'].includes(kind) && !payload.package) throw Error('Missing frozen capability package.');
    if (kind === 'search-stopped' && !['qualified', 'exhausted', 'cancelled', 'infeasible', 'searching'].includes(payload.status)) {
        throw Error('Invalid construction stopping status.');
    }
}

export async function inspectOutEvolveWorkspace(input) {
    const fingerprint = shape(input);
    let previous = null;
    let packageCount = 0;
    let failed = 0;
    let inconclusive = 0;
    let latestPackage = null;
    let checkpoint = null;
    const knownPackages = new Map();
    for (const [sequence, event] of input.events.entries()) {
        if (!exact(event, ['sequence', 'previous', 'kind', 'payload', 'digest'])
            || event.sequence !== sequence || event.previous !== previous || !EVENT_KINDS.includes(event.kind)) {
            throw Error('Invalid or reordered Out-Evolve event.');
        }
        payloadShape(event.kind, event.payload);
        if (await eventDigest(input.id, event) !== event.digest) throw Error('Out-Evolve event digest mismatch.');
        if (event.kind === 'package-frozen' || event.kind === 'successor') {
            await packages.importCapability(event.payload.package);
            latestPackage = event.payload.package;
            knownPackages.set(latestPackage.digest, latestPackage);
            packageCount += 1;
            checkpoint = null;
        }
        if (['search-started', 'search-stopped', 'search-paused'].includes(event.kind)) {
            const token = event.payload.checkpoint;
            const checked = importSearchCheckpoint(token, {parent: knownPackages.get(token?.inheritance?.parentDigest) || null});
            if (event.kind === 'search-paused' ? event.payload.status !== 'INCONCLUSIVE'
                : checked.status !== event.payload.status) throw Error('Search checkpoint status differs from its event.');
            checkpoint = checked.status === 'qualified' ? null : checked;
        }
        if (event.kind === 'failure' && String(event.payload.status || '').toLowerCase() !== 'inconclusive'
            || ['fail', 'failed', 'exhausted', 'infeasible'].includes(
            String(event.payload.status || '').toLowerCase())) failed += 1;
        if (String(event.payload.status || '').toLowerCase() === 'inconclusive') inconclusive += 1;
        previous = event.digest;
    }
    const result = {workspace: clone(input), packageCount, failed, inconclusive, latestPackage, checkpoint,
        evidenceStatus: failed ? 'retained-failure' : inconclusive ? 'retained-inconclusive' : 'no-recorded-failure',
        limits: 'Synthetic supplied-model checks only. Imported historical reports are records, not fresh evaluations.'};
    trustedHistories.set(input, fingerprint);
    trustedHistories.set(result.workspace, fingerprint);
    return result;
}

export async function appendOutEvolveEvent(input, kind, payload) {
    if (trustedHistories.get(input) !== shape(input)) await inspectOutEvolveWorkspace(input);
    if (!EVENT_KINDS.includes(kind)) throw Error('Unsupported Out-Evolve event kind.');
    if (input.events.length >= WORKSPACE_LIMITS.events) throw Error('History is full. Export before beginning a separate history.');
    payloadShape(kind, payload);
    if (kind === 'package-frozen' || kind === 'successor') await packages.importCapability(payload.package);
    let savedPayload = payload;
    if (['search-started', 'search-stopped', 'search-paused'].includes(kind)) {
        const parentDigest = payload.checkpoint?.inheritance?.parentDigest;
        const parent = input.events.map(event => event.payload.package).find(value => value?.digest === parentDigest) || null;
        const checked = importSearchCheckpoint(payload.checkpoint, {parent});
        if (kind === 'search-paused' ? payload.status !== 'INCONCLUSIVE'
            : checked.status !== payload.status) throw Error('Search checkpoint status differs from its event.');
        const {attempts: ignoredAttempts, frontier: ignoredFrontier, ...summary} = payload;
        savedPayload = {...summary, checkpoint: exportSearchCheckpoint(checked)};
    }
    const result = clone(input);
    const event = {sequence: result.events.length, previous: result.events.at(-1)?.digest || null, kind, payload: clone(savedPayload)};
    event.digest = await eventDigest(result.id, event);
    result.events.push(event);
    result.revision = result.events.length;
    shape(result);
    trustedHistories.set(result, canonical(result));
    return result;
}

export function searchHistoryCapacity(workspace, checkpoint) {
    const bytes = new TextEncoder().encode(canonical(workspace)).length;
    const tokenBytes = new TextEncoder().encode(canonical(exportSearchCheckpoint(checkpoint))).length;
    const remainingEvents = WORKSPACE_LIMITS.events - workspace.events.length;
    const remainingBytes = WORKSPACE_LIMITS.bytes - bytes;
    const primitiveId = Math.max(...checkpoint.apparatus.primitives.map(primitive => primitive.id.length));
    const programEnvelope = 512 + checkpoint.options.maxProgramSize * (2 * primitiveId + 64);
    const attemptedPrograms = Math.min(checkpoint.options.maxStates, checkpoint.options.maxMemoryStates);
    const parentBytes = checkpoint.inheritance.parent ? new TextEncoder().encode(canonical(checkpoint.inheritance.parent)).length : 0;
    const terminalEvidenceReserve = 262_144 + attemptedPrograms * programEnvelope + 2 * parentBytes;
    return {canAdvance: remainingEvents >= 3 && remainingBytes >= 2 * tokenBytes + terminalEvidenceReserve,
        remainingEvents, remainingBytes, tokenBytes, terminalEvidenceReserve};
}

export function latestOutEvolveEvent(workspace, kind) {
    return workspace.events.filter(event => event.kind === kind).at(-1) || null;
}

export function requireHistoryContinuation(current, incoming) {
    if (current.id !== incoming.id) return;
    if (incoming.events.length < current.events.length
        || current.events.some((event, index) => event.digest !== incoming.events[index]?.digest)) {
        throw Error('Import would discard or replace events in this history. Keep both as separate histories.');
    }
}
