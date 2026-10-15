// SPDX-License-Identifier: Apache-2.0
/**
 * Local-only Mission Command records for the existing public-data workbench.
 * Digests check consistency, not authenticity. A local review is self-reported,
 * never independent proof, operational admission, or a capability grant.
 *
 * Persistence must perform compare-and-swap in a single transaction (for example,
 * an IndexedDB readwrite transaction), comparing both revision and missionId.
 * These pure transitions cannot make localStorage atomic or synchronize devices.
 * After conflict or storage loss, keep the UI read-only until explicit reload or
 * import/fork; never retry a stale transition as an unconditional write.
 */
import { canonical, digest, parseBounded } from '../../docs/assets/successor/engine.mjs';
import { inspectPack, run, validate } from './engine.mjs';

export const RECORD_VERSION = 'successor-mission-record/v1';
export const RECORD_LIMITS = Object.freeze({
    bytes: 2_000_000, specBytes: 140_000, csvBytes: 100_000,
    artifactBytes: 200_000, artifactTotalBytes: 500_000, artifactCount: 3, history: 16,
});
export const RECORD_STATES = Object.freeze([
    'draft', 'running', 'result', 'reviewed', 'interrupted', 'stopped', 'rejected',
]);
const encoder = new TextEncoder();
const bytes = value => encoder.encode(value).length;
const HASH = /^[a-f0-9]{64}$/;
const ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
const fields = (value, keys, label) => {
    if (!value || typeof value !== 'object' || Array.isArray(value) ||
        Object.keys(value).sort().join('|') !== [...keys].sort().join('|')) fail('SCHEMA', label);
};
function fail(code, detail = '') {
    const error = new Error(detail ? `${code}: ${detail}` : code);
    error.code = code;
    throw error;
}
function integer(value, low, high, label) {
    if (!Number.isSafeInteger(value) || Object.is(value, -0) || value < low || value > high) fail('BOUNDS', label);
}
function string(value, maximum, label, empty = false) {
    if (typeof value !== 'string' || (!empty && !value.trim()) || bytes(value) > maximum) fail('TEXT', label);
}
function hash(value, label) {
    if (typeof value !== 'string' || !HASH.test(value)) fail('DIGEST', label);
}
function identity(value, label) {
    if (typeof value !== 'string' || !ID.test(value)) fail('IDENTITY', label);
}
function equal(actual, expected, label) {
    if (canonical(actual) !== canonical(expected)) fail('BINDING', label);
}
/** Refuse non-JSON object tricks before the shared canonical transport sees them. */
function plain(value, depth = 0, budget = { nodes: 0 }) {
    if (++budget.nodes > 100000 || depth > 32) fail('JSON_COMPLEXITY');
    if (!value || typeof value !== 'object') return;
    const array = Array.isArray(value);
    if (array ? Object.getPrototypeOf(value) !== Array.prototype :
        ![null, Object.prototype].includes(Object.getPrototypeOf(value))) fail('JSON_OBJECT');
    for (const key of Reflect.ownKeys(value)) {
        if (array && key === 'length') continue;
        if (typeof key !== 'string' || (array && !/^(0|[1-9][0-9]*)$/.test(key))) fail('JSON_KEY');
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) fail('JSON_PROPERTY');
        plain(descriptor.value, depth + 1, budget);
    }
}
function clone(value) {
    plain(value);
    return parseBounded(canonical(value));
}
function parse(input) {
    let text = input;
    if (input instanceof Uint8Array) {
        if (input.byteLength > RECORD_LIMITS.bytes) fail('RECORD_BYTES');
        try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(input); }
        catch { fail('UTF8_ENCODING'); }
    }
    if (typeof text !== 'string' || bytes(text) > RECORD_LIMITS.bytes) fail('RECORD_BYTES');
    return parseBounded(text);
}
function checkedSpec(value) {
    const spec = validate(clone(value));
    if (spec.family !== 'public-data') fail('PUBLIC_DATA_ONLY');
    if (bytes(canonical(spec)) > RECORD_LIMITS.specBytes || bytes(spec.inputs.csv) > RECORD_LIMITS.csvBytes) {
        fail('SPEC_BYTES');
    }
    return spec;
}
const specIdentity = spec => digest('mission-command-spec', spec);
const context = record => ({
    missionId: record.missionId, sourceHash: record.sourceHash, specDigest: record.specDigest,
});
const runContext = (record, value) => ({
    ...context(record), runId: value.runId, startedRevision: value.startedRevision,
});
const resultIdentity = (record, result) => digest('mission-command-result', {
    ...runContext(record, result), packDigest: result.pack.integrityDigest,
});
const reviewIdentity = (record, review) => digest('mission-command-review', {
    ...context(record), decision: review.decision, note: review.note, scope: review.scope,
    resultDigest: review.resultDigest, revision: review.revision,
});
function summary(value) {
    fields(value, ['rows', 'groups', 'total', 'unit'], 'summary');
    integer(value.rows, 1, 2001, 'rows');
    integer(value.groups, 1, value.rows, 'groups');
    integer(value.total, -2_001_000_000, 2_001_000_000, 'total');
    string(value.unit, 320, 'unit');
}
function checkHistory(item) {
    fields(item, ['kind', 'trust', 'missionId', 'sourceHash', 'specDigest', 'revision', 'state',
        'runId', 'resultDigest', 'packDigest', 'reviewDecision', 'reviewNote', 'summary', 'reason'], 'history');
    if (!['superseded', 'imported', 'interrupted', 'stopped'].includes(item.kind) ||
        item.trust !== 'historical-untrusted' || !RECORD_STATES.includes(item.state)) fail('HISTORY_STATE');
    identity(item.missionId, 'history mission');
    hash(item.sourceHash, 'history source');
    hash(item.specDigest, 'history specification');
    integer(item.revision, 0, Number.MAX_SAFE_INTEGER, 'history revision');
    if (item.runId !== null) identity(item.runId, 'history run');
    for (const key of ['resultDigest', 'packDigest']) if (item[key] !== null) hash(item[key], key);
    if (![null, 'accepted', 'rejected'].includes(item.reviewDecision)) fail('HISTORY_REVIEW');
    string(item.reviewNote, 2048, 'history review note', true);
    string(item.reason, 512, 'history reason', true);
    if (item.summary !== null) summary(item.summary);
    if ((item.resultDigest === null) !== (item.packDigest === null) ||
        (item.resultDigest === null) !== (item.summary === null) ||
        (item.reviewDecision !== null && item.resultDigest === null)) fail('HISTORY_BINDING');
}
function observe(record, kind, reason = '') {
    return {
        kind, trust: 'historical-untrusted', ...context(record), revision: record.revision, state: record.state,
        runId: record.run?.runId ?? record.result?.runId ?? null,
        resultDigest: record.result?.bindingDigest ?? null,
        packDigest: record.result?.pack.integrityDigest ?? null,
        reviewDecision: record.review?.decision ?? null, reviewNote: record.review?.note ?? '',
        summary: record.result?.pack.result.summary ?? null, reason,
    };
}
function remember(record, item) {
    record.history = [...record.history, item].slice(-RECORD_LIMITS.history);
}
async function seal(record) {
    const { recordDigest: ignored, ...body } = record;
    return clone({ ...body, recordDigest: await digest('mission-command-record', body) });
}
function compareRevision(record, expectedRevision) {
    integer(expectedRevision, 0, Number.MAX_SAFE_INTEGER, 'expected revision');
    if (record.revision !== expectedRevision) fail('REVISION_CONFLICT');
    if (record.revision === Number.MAX_SAFE_INTEGER) fail('REVISION_EXHAUSTED');
}
async function mutation(record, expectedRevision) {
    const checked = await validateRecord(record);
    compareRevision(checked, expectedRevision);
    return checked;
}
/**
 * Verify more than caller-recomputable hashes. Public-data output is deterministic,
 * so compare it to the existing fixed implementation. This verification computation
 * does not resume a persisted run, issue a new result, or confer review authority.
 */
async function checkPack(value, spec, sourceHash) {
    const pack = clone(value);
    fields(pack, ['schema', 'spec', 'createdAt', 'frozen', 'releaseDigest', 'compilation', 'result',
        'economics', 'evaluation', 'chronicle', 'integrityDigest'], 'pack');
    equal(pack.spec, spec, 'exact specification');
    if (!pack.frozen || pack.frozen.sourceHash !== sourceHash) fail('SOURCE_MISMATCH');
    if (typeof pack.createdAt !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(pack.createdAt) ||
        !Number.isFinite(Date.parse(pack.createdAt)) || new Date(pack.createdAt).toISOString() !== pack.createdAt) {
        fail('PACK_DATE');
    }
    if (!Array.isArray(pack.result?.artifacts) || pack.result.artifacts.length !== RECORD_LIMITS.artifactCount) {
        fail('ARTIFACT_COUNT');
    }
    let total = 0;
    for (const artifact of pack.result.artifacts) {
        fields(artifact, ['name', 'type', 'content', 'digest'], 'artifact');
        string(artifact.content, RECORD_LIMITS.artifactBytes, 'artifact content', true);
        total += bytes(artifact.content);
    }
    if (total > RECORD_LIMITS.artifactTotalBytes) fail('ARTIFACT_BYTES');
    await inspectPack(pack);
    const expected = await run(spec, { sourceHash, clock: () => 0 });
    for (const key of ['schema', 'frozen', 'releaseDigest', 'result', 'evaluation', 'chronicle']) {
        equal(pack[key], expected[key], `public-data ${key}`);
    }
    integer(pack.economics?.elapsedMilliseconds, 0, 3_600_000, 'elapsed milliseconds');
    equal(pack.economics,
        { ...expected.economics, elapsedMilliseconds: pack.economics.elapsedMilliseconds }, 'economics');
    return pack;
}

/** Validate, verify digest bindings, and return a detached strict JSON record. */
export async function validateRecord(value) {
    const record = clone(value);
    fields(record, ['schema', 'missionId', 'revision', 'sourceHash', 'spec', 'specDigest', 'state',
        'run', 'result', 'review', 'history', 'recordDigest'], 'record');
    if (record.schema !== RECORD_VERSION) fail('RECORD_VERSION');
    if (!RECORD_STATES.includes(record.state)) fail('RECORD_STATE');
    identity(record.missionId, 'mission');
    hash(record.sourceHash, 'source');
    hash(record.specDigest, 'specification');
    hash(record.recordDigest, 'record');
    integer(record.revision, 0, Number.MAX_SAFE_INTEGER, 'revision');
    record.spec = checkedSpec(record.spec);
    if (record.specDigest !== await specIdentity(record.spec)) fail('SPEC_BINDING');
    const { recordDigest, ...body } = record;
    if (recordDigest !== await digest('mission-command-record', body)) fail('RECORD_INTEGRITY');
    if (!Array.isArray(record.history) || record.history.length > RECORD_LIMITS.history) fail('HISTORY_COUNT');
    record.history.forEach(checkHistory);
    const hasResult = ['result', 'reviewed', 'rejected'].includes(record.state);
    const hasReview = ['reviewed', 'rejected'].includes(record.state);
    if ((record.run !== null) !== (record.state === 'running') ||
        (record.result !== null) !== hasResult || (record.review !== null) !== hasReview) fail('STATE_BINDING');
    if (record.run !== null) {
        fields(record.run, ['runId', 'startedRevision', 'bindingDigest'], 'run');
        identity(record.run.runId, 'run');
        integer(record.run.startedRevision, record.revision, record.revision, 'run revision');
        if (record.run.bindingDigest !== await digest('mission-command-run', runContext(record, record.run))) {
            fail('RUN_BINDING');
        }
    }
    if (hasResult) {
        fields(record.result, ['runId', 'startedRevision', 'bindingDigest', 'pack'], 'result');
        identity(record.result.runId, 'result run');
        integer(record.result.startedRevision, 1, record.revision - (hasReview ? 2 : 1), 'result revision');
        await checkPack(record.result.pack, record.spec, record.sourceHash);
        if (record.result.bindingDigest !== await resultIdentity(record, record.result)) fail('RESULT_BINDING');
    }
    if (hasReview) {
        const review = record.review;
        fields(review, ['decision', 'note', 'scope', 'resultDigest', 'revision', 'reviewDigest'], 'review');
        if (review.scope !== 'LOCAL_SELF_REPORTED_REVIEW' ||
            review.decision !== (record.state === 'reviewed' ? 'accepted' : 'rejected')) fail('REVIEW_STATE');
        string(review.note, 2048, 'review note', true);
        integer(review.revision, record.revision, record.revision, 'review revision');
        if (review.resultDigest !== record.result.bindingDigest ||
            review.reviewDigest !== await reviewIdentity(record, review)) fail('REVIEW_BINDING');
    }
    return record;
}

export async function createRecord(options) {
    fields(options, ['missionId', 'sourceHash', 'spec'], 'create options');
    identity(options.missionId, 'mission');
    hash(options.sourceHash, 'source');
    const spec = checkedSpec(options.spec);
    return seal({ schema: RECORD_VERSION, missionId: options.missionId, revision: 0,
        sourceHash: options.sourceHash, spec, specDigest: await specIdentity(spec), state: 'draft',
        run: null, result: null, review: null, history: [] });
}
export async function editRecord(value, spec, options) {
    fields(options, ['expectedRevision'], 'edit options');
    const record = await mutation(value, options.expectedRevision);
    const checked = checkedSpec(spec);
    remember(record, observe(record, 'superseded', 'Exact specification edited; previous checks are historical.'));
    record.spec = checked;
    record.specDigest = await specIdentity(checked);
    record.state = 'draft';
    record.run = record.result = record.review = null;
    record.revision++;
    return seal(record);
}
export async function startRun(value, options) {
    fields(options, ['expectedRevision', 'runId'], 'start options');
    const record = await mutation(value, options.expectedRevision);
    if (record.state === 'running') fail('ALREADY_RUNNING');
    identity(options.runId, 'run');
    // Revision is part of every binding even when a caller reuses an opaque run ID.
    if (record.result !== null) remember(record, observe(record, 'superseded', 'New local run requested.'));
    record.revision++;
    record.state = 'running';
    record.result = record.review = null;
    record.run = { runId: options.runId, startedRevision: record.revision };
    record.run.bindingDigest = await digest('mission-command-run', runContext(record, record.run));
    return seal(record);
}
export async function completeRun(value, pack, options) {
    fields(options, ['expectedRevision', 'runId'], 'complete options');
    const record = await mutation(value, options.expectedRevision);
    if (record.state !== 'running' || record.run.runId !== options.runId) fail('STALE_RUN');
    const checked = await checkPack(pack, record.spec, record.sourceHash);
    record.result = { runId: record.run.runId, startedRevision: record.run.startedRevision, pack: checked };
    record.result.bindingDigest = await resultIdentity(record, record.result);
    record.run = null;
    record.state = 'result';
    record.revision++;
    return seal(record);
}
async function endRun(value, options, state) {
    fields(options, ['expectedRevision', 'runId', 'reason'], `${state} options`);
    const record = await mutation(value, options.expectedRevision);
    if (record.state !== 'running' || record.run.runId !== options.runId) fail('STALE_RUN');
    string(options.reason, 512, 'stop reason', true);
    remember(record, observe(record, state, options.reason));
    record.state = state;
    record.run = null;
    record.revision++;
    return seal(record);
}
export const stopRun = (record, options) => endRun(record, options, 'stopped');
export const interruptRun = (record, options) => endRun(record, options, 'interrupted');

export async function reviewRecord(value, options) {
    fields(options, ['expectedRevision', 'decision', 'note'], 'review options');
    const record = await mutation(value, options.expectedRevision);
    if (record.state !== 'result') fail('RESULT_REQUIRED');
    if (!['accepted', 'rejected'].includes(options.decision)) fail('REVIEW_DECISION');
    string(options.note, 2048, 'review note', true);
    record.revision++;
    record.state = options.decision === 'accepted' ? 'reviewed' : 'rejected';
    record.review = { decision: options.decision, note: options.note, scope: 'LOCAL_SELF_REPORTED_REVIEW',
        resultDigest: record.result.bindingDigest, revision: record.revision };
    record.review.reviewDigest = await reviewIdentity(record, record.review);
    return seal(record);
}
export async function serializeRecord(record) {
    return canonical(await validateRecord(record));
}
/**
 * External JSON text or Uint8Array UTF-8 bytes are always historical.
 * For uploaded files prefer Uint8Array: invalid byte encodings are rejected, not replaced.
 * Use importRecord to explicitly fork a local draft.
 */
export async function restoreRecord(text, options) {
    fields(options, ['sourceHash'], 'restore options');
    hash(options.sourceHash, 'source');
    const record = await validateRecord(parse(text));
    return { record, mode: 'historical', readOnly: true, currentResult: null, currentReview: null,
        reason: record.sourceHash === options.sourceHash ? 'EXTERNAL_RESTORE' : 'SOURCE_MISMATCH' };
}
export async function importRecord(text, options) {
    fields(options, ['missionId', 'sourceHash'], 'import options');
    const historical = (await restoreRecord(text, { sourceHash: options.sourceHash })).record;
    if (options.missionId === historical.missionId) fail('NEW_MISSION_ID_REQUIRED');
    const record = await createRecord({ ...options, spec: historical.spec });
    record.history = [...historical.history, observe(historical, 'imported',
        'Imported claims are untrusted history; rerun and review locally.')].slice(-RECORD_LIMITS.history);
    return seal(record);
}
/** A view descriptor only; no storage access, writes, retry, or result promotion. */
export async function recoveryView(value, options) {
    fields(options, ['reason'], 'recovery options');
    if (!['REVISION_CONFLICT', 'LOST_STORAGE', 'SOURCE_MISMATCH'].includes(options.reason)) fail('RECOVERY_REASON');
    const record = value === null ? null : await validateRecord(value);
    return { record, mode: options.reason === 'LOST_STORAGE' ? 'lost-storage' :
        options.reason === 'REVISION_CONFLICT' ? 'conflict' : 'historical', readOnly: true,
        currentResult: null, currentReview: null, reason: options.reason };
}
