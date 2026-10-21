// SPDX-License-Identifier: Apache-2.0
import { canonical, importSearchCheckpoint, exportSearchCheckpoint } from './constructor.mjs';
import * as packages from './capability-package.mjs';
import {restoreExecution} from './out-execute/engine.mjs';

export const WORKSPACE_SCHEMA = 'out-evolve-workspace/v1';
export const WORKSPACE_LIMITS = Object.freeze({events: 256, bytes: 8_000_000});
export const EVENT_KINDS = Object.freeze([
    'brief', 'search-started', 'search-stopped', 'search-paused', 'package-frozen', 'reuse', 'comparison', 'successor', 'failure', 'execution'
]);
const trustedHistories = new WeakMap();
const clone = value => JSON.parse(canonical(value));
const same = (a, b) => canonical(a) === canonical(b);
const encodedBytes = value => new TextEncoder().encode(canonical(value)).length;
function structure(value) {
    let nodes = 0, depth = 0;
    const visit = (item, level) => {
        nodes += 1; depth = Math.max(depth, level);
        if (item && typeof item === 'object') Object.values(item).forEach(child => visit(child, level + 1));
    };
    visit(value, 0);
    return {nodes, depth};
}
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

/** An accepted package completes only the exact qualified search checkpoint it records. */
export function packageCompletesSearch(checkpoint, pkg) {
    return checkpoint?.status === 'qualified' && Boolean(pkg?.search?.checkpoint)
        && same(exportSearchCheckpoint(checkpoint), pkg.search.checkpoint);
}

export async function inspectOutEvolveWorkspace(input) {
    const fingerprint = shape(input);
    let previous = null;
    let packageCount = 0;
    let failed = 0;
    let inconclusive = 0;
    let latestPackage = null;
    let checkpoint = null;
    let latestExecution = null;
    let executionVerificationWork = 0;
    let recordedExecutionAdmissionWork = 0;
    const executionAttemptWork = new Map();
    const executionCompletions = [];
    const executionAttempts = new Set();
    const knownPackages = new Map();
    for (const [sequence, event] of input.events.entries()) {
        if (!exact(event, ['sequence', 'previous', 'kind', 'payload', 'digest'])
            || event.sequence !== sequence || event.previous !== previous || !EVENT_KINDS.includes(event.kind)) {
            throw Error('Invalid or reordered Out-Evolve event.');
        }
        payloadShape(event.kind, event.payload);
        if (event.kind === 'execution') {
            const payload = event.payload;
            if (!exact(payload, ['projectId', 'checkpoint', 'admissionVerification']) || payload.projectId !== input.id) {
                throw Error('Execution must belong to this existing project history.');
            }
            const inspected = await restoreExecution(payload.checkpoint);
            executionVerificationWork += inspected.countedVerificationWork;
            const current = inspected.checkpoint;
            executionAttemptWork.set(current.attemptId, Object.values(current.work).reduce((a, b) => a + b, 0));
            recordedExecutionAdmissionWork += payload.admissionVerification.total + payload.admissionVerification.historyRecheckTotal;
            if (!same(payload.admissionVerification, {work: inspected.verificationWork, total: inspected.countedVerificationWork, historyRecheckTotal: executionVerificationWork})) {
                throw Error('Execution admission verification costs do not reproduce.');
            }
            if (!same(current.archive.completions, executionCompletions)) {
                throw Error('Execution cannot omit, replace or import detached completion ancestry.');
            }
            if (latestExecution?.attemptId === current.attemptId) {
                if (['COMPLETE', 'INCONCLUSIVE'].includes(latestExecution.status) || !same(latestExecution.model, current.model)
                    || !same(latestExecution.source, current.source) || latestExecution.budget !== current.budget
                    || current.next < latestExecution.next || !same(latestExecution.selection, current.selection)) {
                    throw Error('Execution progress is stale or its frozen source changed.');
                }
                for (let i = 0; i < latestExecution.next; i++) if (!same(latestExecution.contracts[i], current.contracts[i])) {
                    throw Error('Completed local work cannot be replaced in the same attempt.');
                }
            } else {
                if (executionAttempts.has(current.attemptId) || latestExecution && ['PAUSED', 'CANCELLED'].includes(latestExecution.status)) {
                    throw Error('Finish the pending execution, or retain it in a separate history before starting another attempt.');
                }
                executionAttempts.add(current.attemptId);
            }
            if (current.status === 'COMPLETE') executionCompletions.push(current.completion);
            latestExecution = current;
        }
        if (await eventDigest(input.id, event) !== event.digest) throw Error('Out-Evolve event digest mismatch.');
        if (event.kind === 'package-frozen' || event.kind === 'successor') {
            await packages.importCapability(event.payload.package);
            latestPackage = event.payload.package;
            knownPackages.set(latestPackage.digest, latestPackage);
            packageCount += 1;
            // Package import does not finish an unrelated search, including one awaiting package acceptance.
            if (packageCompletesSearch(checkpoint, latestPackage)) checkpoint = null;
            else if (!['cancelled', 'searching', 'qualified'].includes(checkpoint?.status)) checkpoint = null;
        }
        if (['search-started', 'search-stopped', 'search-paused'].includes(event.kind)) {
            const token = event.payload.checkpoint;
            const checked = importSearchCheckpoint(token, {parent: knownPackages.get(token?.inheritance?.parentDigest) || null});
            if (event.kind === 'search-paused' ? event.payload.status !== 'INCONCLUSIVE'
                : checked.status !== event.payload.status) throw Error('Search checkpoint status differs from its event.');
            checkpoint = checked;
        }
        if (event.kind === 'failure' && String(event.payload.status || '').toLowerCase() !== 'inconclusive'
            || ['fail', 'failed', 'exhausted', 'infeasible'].includes(
            String(event.payload.status || '').toLowerCase())) failed += 1;
        if (String(event.payload.status || '').toLowerCase() === 'inconclusive'
            || event.kind === 'execution' && ['INCONCLUSIVE', 'CANCELLED'].includes(event.payload.checkpoint.status)) inconclusive += 1;
        previous = event.digest;
    }
    const result = {workspace: clone(input), packageCount, failed, inconclusive, latestPackage, checkpoint,
        latestExecution, executionCompletions, executionVerificationWork, recordedExecutionAdmissionWork,
        recordedExecutionAttemptWork: [...executionAttemptWork.values()].reduce((a, b) => a + b, 0),
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
    if (kind === 'execution') {
        if (payload.projectId !== input.id || !payload.checkpoint) throw Error('Execution needs this project identity.');
        const inspected = await restoreExecution(payload.checkpoint);
        savedPayload = {projectId: input.id, checkpoint: inspected.checkpoint,
            admissionVerification: {work: inspected.verificationWork, total: inspected.countedVerificationWork,
                historyRecheckTotal: inspected.countedVerificationWork + input.events.filter(event => event.kind === 'execution')
                    .reduce((total, event) => total + event.payload.admissionVerification.total, 0)}};
    }
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
    if (kind === 'execution') await inspectOutEvolveWorkspace(result);
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
        canFinalize: checkpoint.status === 'qualified' && remainingEvents >= 2 && remainingBytes >= terminalEvidenceReserve,
        remainingEvents, remainingBytes, tokenBytes, terminalEvidenceReserve};
}

/** Preserve observed evaluation evidence; reconstruct duplicate constructor state from its token. */
export function retainedEvaluationReport(report) {
    if (report.kind !== 'scope-expanding-successor') return clone(report);
    const compact = result => {
        if (!result?.checkpoint) return result;
        const {attempts, frontier, checkpoint, ...retained} = result;
        return {...retained, checkpoint: exportSearchCheckpoint(checkpoint)};
    };
    // Strip raw duplicate state before canonicalizing: a raw report may exceed canonical's node bound.
    return clone({...report, result: compact(report.result), scratch: compact(report.scratch),
        retention: {schema: 'out-evolve-retained-evaluation/v1', parentDigest: report.parentDigest,
            constructorEvidence: 'Compact checkpoints reconstruct deterministic attempts, frontier, program and work; the original parent package is retained in this history.'}});
}

/** Reserve a complete retained report (or bounded failure) before RNG, imports or evaluation work. */
export function evaluationHistoryCapacity(workspace, pkg, kind, exposedCaseIds = []) {
    if (!['reuse', 'successor'].includes(kind)) throw Error('Unsupported retained evaluation kind.');
    const remainingEvents = WORKSPACE_LIMITS.events - workspace.events.length;
    const remainingBytes = WORKSPACE_LIMITS.bytes - encodedBytes(workspace);
    const packageBytes = encodedBytes(pkg), exposureBytes = encodedBytes(exposedCaseIds);
    const exposureCount = new Set(exposedCaseIds).size;
    const workspaceStructure = structure(workspace), packageStructure = structure(pkg);
    const exposureStructure = structure(exposedCaseIds), certificateStructure = structure(pkg.certificate);
    let reportBytes = 524_288 + exposureBytes + 2 * encodedBytes(pkg.certificate);
    let reportNodes = 100_000 + exposureStructure.nodes + 2 * certificateStructure.nodes;
    let attemptBytes = 0, maximumAttempts = 0;
    if (kind === 'successor') {
        const app = {...pkg.apparatus, id: pkg.apparatus.id.endsWith('-expanded')
            ? pkg.apparatus.id : `${pkg.apparatus.id}-expanded`, scope: ['standard', 'reservoir']};
        const limits = pkg.search.limits;
        const instructions = Math.max(limits.maxProgramSize, pkg.ast.installations.length);
        const longestId = Math.max(...app.primitives.map(primitive => primitive.id.length));
        const ast = {schema: 'out-evolve-ast/v1', installations: [], scope: ['standard', 'reservoir'],
            prepare: {op: 'sequence', steps: Array.from({length: instructions}, () => ({op: 'primitive', id: 'x'.repeat(longestId)}))}};
        // All-prepare syntax dominates installation syntax. IDs are bounded ASCII; program is escaped twice.
        attemptBytes = encodedBytes({index: Number.MAX_VALUE, program: canonical(ast), programCost: Number.MAX_VALUE,
            synthesisToDate: Number.MAX_VALUE, qualified: false, reason: 'x'.repeat(1024)}) + 256;
        maximumAttempts = Math.min(limits.maxStates, limits.maxMemoryStates + 1);
        // One accepted own-package attempt list; tokens omit raw state and embedded parent.
        // Explicit manifest/parent/exposure terms cover their copies; 1MiB covers finite task/certificate
        // records, event/failure wrappers, fresh token metadata and bounded evaluation-error evidence.
        reportBytes = 1_048_576 + 16 * encodedBytes(app) + 4 * packageBytes
            + 2 * exposureBytes + maximumAttempts * attemptBytes;
        reportNodes = 100_000 + 16 * structure(app).nodes + 4 * packageStructure.nodes
            + 2 * exposureStructure.nodes + maximumAttempts * 16;
    }
    const requiredBytes = reportBytes + 4096;
    const fitsSeparateHistory = packageBytes + requiredBytes
        - (kind === 'successor' ? 2 : 1) * exposureBytes + 4096 <= WORKSPACE_LIMITS.bytes
        && (kind !== 'successor' || packageStructure.depth <= 48)
        && packageStructure.nodes + reportNodes - (kind === 'successor' ? 2 : 1) * exposureStructure.nodes + 256 <= 2_000_000;
    const structureFits = workspaceStructure.nodes + reportNodes + 128 <= 2_000_000
        && exposureStructure.depth <= 48 && (kind !== 'successor' || packageStructure.depth <= 48);
    return {canRun: remainingEvents >= 1 && remainingBytes >= requiredBytes && exposureCount <= 4096 && structureFits,
        remainingEvents, remainingBytes, reportBytes, requiredBytes, fitsSeparateHistory,
        packageBytes, exposureBytes, exposureCount, attemptBytes, maximumAttempts, reportNodes,
        workspaceNodes: workspaceStructure.nodes, packageDepth: packageStructure.depth, exposureDepth: exposureStructure.depth,
        reason: exposureCount > 4096 ? 'exposure-limit' : remainingEvents < 1 ? 'event-limit'
            : remainingBytes < requiredBytes ? 'byte-reserve' : !structureFits ? 'structural-reserve' : null,
        representation: 'out-evolve-retained-evaluation/v1'};
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

/** Admit an exported checkpoint without discarding its original project or unappended work. */
export const EXECUTION_RECOVERY_SCHEMAS = Object.freeze(['out-execute-recovery/v1', 'out-execute-unsaved-recovery/v1']);
export const EXECUTION_RECOVERY_MAX_BYTES = WORKSPACE_LIMITS.bytes + 2_001_024;
export async function inspectExecutionRecovery(input, {current = null} = {}) {
    if (encodedBytes(input) > EXECUTION_RECOVERY_MAX_BYTES
        || !exact(input, ['schema', 'history', 'checkpoint']) || !EXECUTION_RECOVERY_SCHEMAS.includes(input.schema)) {
        throw Error('Unsupported or oversized execution recovery wrapper.');
    }
    let inspected = await inspectOutEvolveWorkspace(input.history);
    const initialVerificationWork = inspected.executionVerificationWork;
    let appended = false;
    if (!same(input.checkpoint, inspected.latestExecution)) {
        if (input.schema !== 'out-execute-unsaved-recovery/v1') throw Error('Saved recovery checkpoint differs from its retained history.');
        const recovered = await appendOutEvolveEvent(inspected.workspace, 'execution', {
            projectId: inspected.workspace.id, checkpoint: input.checkpoint
        });
        inspected = await inspectOutEvolveWorkspace(recovered);
        appended = true;
    }
    if (!inspected.latestExecution) throw Error('Recovery wrapper has no execution checkpoint.');
    if (current !== null) requireHistoryContinuation(current, inspected.workspace);
    return {...inspected, recovery: {appended, historicalOnly: true,
        additionalReadVerificationWork: initialVerificationWork + (appended ? inspected.executionVerificationWork : 0)}};
}
