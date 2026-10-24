// SPDX-License-Identifier: Apache-2.0
import {canonical, payloadDigest} from '../successor-capability/discovery-lab-contract.mjs';

export const SCHEMA = 'autonomous-enterprise-charter/v1';
export const copy = value => JSON.parse(canonical(value));
export const same = (a, b) => canonical(a) === canonical(b);
export const digest = payloadDigest;
export const need = (condition, message) => { if (!condition) throw Error(message); };
export const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
export const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export const integer = (value, max = 100_000_000) => Number.isSafeInteger(value) && value >= 0
    && value <= max && !Object.is(value, -0);
const audit = {bundleReplayWork: 0, futureReplayWork: 0, successorReplayWork: 0};
let rejectedReplaysWithUnknownPartialWork = 0;
export function noteFailedReplay() { rejectedReplaysWithUnknownPartialWork++; }
export function chargeReplay(scope, work) {
    need(Object.hasOwn(audit, scope) && integer(work) && Number.isSafeInteger(audit[scope] + work), 'Invalid replay charge.');
    audit[scope] += work;
}
export function auditSnapshot() { return copy({...audit, rejectedReplaysWithUnknownPartialWork,
    failedReplayWork: rejectedReplaysWithUnknownPartialWork ? 'UNKNOWN_PARTIAL_WORK_RETAINED' : 'none-observed',
    scope: 'Current loaded session only; each actual counted replay retained.',
    totalComplete: false, unknown: ['hashing', 'serialization', 'coordination', 'review', 'energy', 'money']}); }
export function additionalCheckingWork(receipt) {
    return ['scopeChecks', 'dependencyChecks'].reduce((total, key) => total
        + (receipt[key]?.arithmetic || 0) + (receipt[key]?.comparisons || 0), 0);
}

export function defaultCharter(source) {
    return validateCharter({schema: SCHEMA, purpose: 'Construct checked means for later public synthetic computations.',
        source, maxN: 32, constructionLimit: 2_000_000, admissionLimit: 50_000_000,
        perTaskLimit: 2_000_000, taskLimit: 3,
        metric: 'paper-declared-arithmetic-work/v1', executionMode: 'synthetic-local', authority: [], obligations: []});
}
export function validateCharter(input) {
    const value = copy(input);
    need(exact(value, ['schema', 'purpose', 'source', 'maxN', 'constructionLimit', 'admissionLimit', 'perTaskLimit', 'taskLimit',
        'metric', 'executionMode', 'authority', 'obligations']) && value.schema === SCHEMA,
    'Unsupported enterprise charter.');
    need(typeof value.purpose === 'string' && value.purpose.trim() && value.purpose.length <= 1000,
        'Provide a bounded authorized purpose.');
    need(exact(value.source, ['constructor', 'checker', 'closure']) && Object.values(value.source).every(hash),
        'Bind constructor, checker and source closure.');
    need([2, 4, 8, 16, 32].includes(value.maxN) && integer(value.constructionLimit, 5_000_000)
        && integer(value.admissionLimit, 100_000_000)
        && integer(value.perTaskLimit, 5_000_000) && integer(value.taskLimit, 3) && value.taskLimit >= 1
        && value.metric === 'paper-declared-arithmetic-work/v1' && value.executionMode === 'synthetic-local'
        && same(value.authority, []) && same(value.obligations, []), 'Unsupported enterprise scope or budget.');
    return value;
}
export function completeConstructionWork(bundle) {
    const work = bundle.observedWorkLedger.totalCountedCampaignWork;
    need(integer(work), 'The full observed construction ledger is required.');
    return work;
}
export async function makeFreeze(charter, bundle, eventHead) {
    charter = validateCharter(charter); bundle = copy(bundle);
    need(hash(eventHead), 'Freeze needs an earlier accepted history event.');
    const value = {schema: 'autonomous-enterprise-freeze/v1', charterDigest: await digest(charter),
        bundleDigest: await digest(bundle), artifactDigests: bundle.envelopes.map(item => item.digest),
        source: charter.source, environment: 'restricted-json-ast/exact-rational/bounded-dimension32',
        obligations: [], acceptedAt: eventHead, expectedOutputs: 'not-included', authority: []};
    return {...value, digest: await digest(value)};
}
export async function makeTaskBank(freeze, seed, n, count = 3) {
    freeze = copy(freeze);
    need(hash(freeze.digest) && integer(seed, 0xffffffff) && [2, 4, 8, 16, 32].includes(n)
        && integer(count, 3) && count > 0, 'Freeze precedes bounded future input generation.');
    let state = seed >>> 0;
    const next = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return String(state % 15 - 7); };
    const tasks = ['walsh', 'xor-convolution', 'inverse'].slice(0, count).map((kind, index) => ({
        id: 'future-' + index, kind, inputs: Array.from({length: kind === 'xor-convolution' ? 2 : 1},
            () => Array.from({length: n}, next))}));
    const value = {schema: 'autonomous-enterprise-task-bank/v1', freezeDigest: freeze.digest, seed, tasks,
        exposure: 'public-seeded-synthetic-protocol-not-secret-validation'};
    return {...value, digest: await digest(value)};
}
